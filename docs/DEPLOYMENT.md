# Deployment Guide for beatricegugger.ch

## Why This App Was Harder to Deploy

The other apps (orbis, songtrainer, ggame) likely had SSL certificates set up BEFORE the Apache proxy was configured. The issue with beatricegugger was:

1. **Apache was proxying ALL requests** to the Flask app, including Let's Encrypt validation requests
2. Let's Encrypt couldn't verify domain ownership because the challenge files weren't being served
3. Each failed attempt counted against a **rate limit** (5 failures per hour per domain)

### The Fix

The Apache config must **exclude** the `.well-known/acme-challenge/` path from proxying:

```apache
# This MUST come BEFORE ProxyPass directives
ProxyPass /.well-known/acme-challenge/ !
```

---

## Quick Deployment Steps

### 1. On your local machine - Push code to server

```bash
cd /mnt/e/Programmierenab24/beatricegugger
git add -A && git commit -m "Deploy" && git push
```

### 2. On the server - Pull and deploy

```bash
cd /var/www/beatricegugger
git pull

# Run deployment script
cd docker
bash deploy.sh
```

### 3. Apache + SSL Setup

The deploy script will offer to set up Apache and SSL. If you need to do it manually:

```bash
# Copy Apache config
sudo cp /var/www/beatricegugger/docker/apache/beatricegugger.conf /etc/apache2/sites-available/

# Enable modules and site
sudo a2enmod proxy proxy_http headers rewrite ssl
sudo a2ensite beatricegugger.conf
sudo systemctl reload apache2

# Create challenge directory (CRITICAL!)
sudo mkdir -p /var/www/html/.well-known/acme-challenge

# Get SSL certificate
sudo bash /var/www/beatricegugger/docker/setup-ssl.sh
```

---

## SSL Certificate Methods

### Method 1: HTTP Challenge (Automatic)

Works if port 80 is accessible and Apache is properly configured:

```bash
sudo certbot --apache -d beatricegugger.ch -d www.beatricegugger.ch
```

### Method 2: DNS Challenge (Manual but Reliable)

Use this if HTTP challenge keeps failing:

```bash
sudo certbot certonly --manual --preferred-challenges dns -d beatricegugger.ch -d www.beatricegugger.ch
```

1. Certbot shows a TXT record value
2. Add it at your DNS provider:
   - **Name:** `_acme-challenge`
   - **Type:** `TXT`
   - **Value:** (string from certbot)
3. Wait 1-2 minutes
4. Press Enter

---

## Troubleshooting

### Rate Limit Hit

If you see "too many failed authorizations", wait 1 hour from the last failure:

```bash
date -u  # Check current UTC time
# Compare with the "retry after" time in the error message
```

### Test Challenge Path

```bash
echo "test" | sudo tee /var/www/html/.well-known/acme-challenge/test
curl http://beatricegugger.ch/.well-known/acme-challenge/test
# Should return "test"
```

### Check Apache Logs

```bash
sudo tail -f /var/log/apache2/beatricegugger_error.log
```

### Check Docker Container

```bash
docker ps  # Check if container is running
docker logs docker-web-1 --tail 50  # View logs
```

---

## Architecture

```
Internet
    │
    ▼
Apache2 (ports 80/443)
    │
    ├── /.well-known/acme-challenge/ → /var/www/html/ (for SSL)
    │
    └── Everything else → Docker container (port 5003)
                              │
                              └── Flask app (Gunicorn)
```

---

## Certificate Renewal

Certbot sets up automatic renewal. Test it with:

```bash
sudo certbot renew --dry-run
```

---

## Files

- `docker/deploy.sh` - Main deployment script
- `docker/setup-ssl.sh` - SSL certificate setup
- `docker/apache/beatricegugger.conf` - Apache VirtualHost config
- `docker/docker-compose.yml` - Docker configuration
- `docker/Dockerfile` - Docker image definition
