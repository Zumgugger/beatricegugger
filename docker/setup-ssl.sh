#!/bin/bash
# SSL Setup Script for beatricegugger.ch
# Run this AFTER deploy.sh and Apache config is in place

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

DOMAIN="beatricegugger.ch"
WWW_DOMAIN="www.beatricegugger.ch"

echo "=========================================="
echo "  SSL Setup for $DOMAIN"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root (sudo)${NC}"
    exit 1
fi

# Check prerequisites
echo "Checking prerequisites..."

# Check certbot
if ! command -v certbot &> /dev/null; then
    echo -e "${YELLOW}Installing certbot...${NC}"
    apt update
    apt install -y certbot python3-certbot-apache
fi
echo -e "${GREEN}✓${NC} Certbot installed"

# Check Apache modules
a2enmod proxy proxy_http headers rewrite ssl > /dev/null 2>&1
echo -e "${GREEN}✓${NC} Apache modules enabled"

# Create challenge directory
mkdir -p /var/www/html/.well-known/acme-challenge
chmod 755 /var/www/html/.well-known/acme-challenge
echo -e "${GREEN}✓${NC} Challenge directory created"

# Test Apache config
apache2ctl configtest
echo -e "${GREEN}✓${NC} Apache config valid"

# Reload Apache
systemctl reload apache2
echo -e "${GREEN}✓${NC} Apache reloaded"

echo ""
echo "Choose SSL certificate method:"
echo "  1) HTTP challenge (automatic, recommended if port 80 works)"
echo "  2) DNS challenge (manual, works even if HTTP is blocked)"
echo ""
read -p "Select method [1/2]: " METHOD

if [ "$METHOD" = "2" ]; then
    echo ""
    echo -e "${BLUE}DNS Challenge Instructions:${NC}"
    echo "1. Certbot will give you a TXT record value"
    echo "2. Add it at your DNS provider as:"
    echo "   Name: _acme-challenge"
    echo "   Type: TXT"
    echo "   Value: (the string certbot shows)"
    echo "3. Wait 1-2 minutes for DNS propagation"
    echo "4. Press Enter in certbot"
    echo ""
    read -p "Press Enter to continue..."
    
    certbot certonly --manual --preferred-challenges dns \
        -d "$DOMAIN" -d "$WWW_DOMAIN"
else
    # Test HTTP challenge path first
    echo ""
    echo "Testing HTTP challenge path..."
    echo "test-$(date +%s)" > /var/www/html/.well-known/acme-challenge/test
    
    if curl -s "http://$DOMAIN/.well-known/acme-challenge/test" | grep -q "test-"; then
        echo -e "${GREEN}✓${NC} HTTP challenge path accessible"
        rm /var/www/html/.well-known/acme-challenge/test
        
        certbot --apache -d "$DOMAIN" -d "$WWW_DOMAIN"
    else
        echo -e "${RED}✗${NC} HTTP challenge path NOT accessible"
        echo ""
        echo "Falling back to DNS challenge..."
        rm -f /var/www/html/.well-known/acme-challenge/test
        
        certbot certonly --manual --preferred-challenges dns \
            -d "$DOMAIN" -d "$WWW_DOMAIN"
    fi
fi

# Check if certificate was obtained
if [ -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]; then
    echo ""
    echo -e "${GREEN}✓${NC} Certificate obtained successfully!"
    
    # Create SSL VirtualHost if certbot didn't do it automatically
    if ! grep -q "VirtualHost \*:443" /etc/apache2/sites-available/beatricegugger*.conf 2>/dev/null; then
        echo "Creating SSL VirtualHost..."
        
        cat > /etc/apache2/sites-available/beatricegugger-ssl.conf << 'EOF'
<VirtualHost *:443>
    ServerName beatricegugger.ch
    ServerAlias www.beatricegugger.ch

    SSLEngine on
    SSLCertificateFile /etc/letsencrypt/live/beatricegugger.ch/fullchain.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/beatricegugger.ch/privkey.pem
    Include /etc/letsencrypt/options-ssl-apache.conf

    ProxyPreserveHost On
    ProxyPass / http://127.0.0.1:5003/
    ProxyPassReverse / http://127.0.0.1:5003/

    RequestHeader set X-Forwarded-Proto "https"
    RequestHeader set X-Forwarded-Host "beatricegugger.ch"

    Header always set X-Frame-Options "SAMEORIGIN"
    Header always set X-Content-Type-Options "nosniff"
    Header always set X-XSS-Protection "1; mode=block"
    Header always set Strict-Transport-Security "max-age=31536000; includeSubDomains"

    ErrorLog ${APACHE_LOG_DIR}/beatricegugger_ssl_error.log
    CustomLog ${APACHE_LOG_DIR}/beatricegugger_ssl_access.log combined
</VirtualHost>
EOF
        
        a2ensite beatricegugger-ssl.conf
    fi
    
    # Update HTTP config to redirect to HTTPS
    if [ -f /etc/apache2/sites-available/beatricegugger.conf ]; then
        # Add redirect if not present
        if ! grep -q "RewriteRule.*https" /etc/apache2/sites-available/beatricegugger.conf; then
            sed -i 's|# RewriteEngine On|RewriteEngine On|' /etc/apache2/sites-available/beatricegugger.conf
            sed -i 's|# RewriteCond|RewriteCond|' /etc/apache2/sites-available/beatricegugger.conf
            sed -i 's|# RewriteRule|RewriteRule|' /etc/apache2/sites-available/beatricegugger.conf
        fi
    fi
    
    systemctl reload apache2
    
    echo ""
    echo "=========================================="
    echo -e "${GREEN}SSL Setup Complete!${NC}"
    echo "=========================================="
    echo ""
    echo "Your site is now available at:"
    echo "  https://$DOMAIN"
    echo "  https://$WWW_DOMAIN"
    echo ""
    echo "Certificate auto-renewal is configured via certbot timer."
    echo "Test renewal with: sudo certbot renew --dry-run"
    echo ""
else
    echo ""
    echo -e "${RED}Certificate was not obtained.${NC}"
    echo "Please check the error messages above."
    exit 1
fi
