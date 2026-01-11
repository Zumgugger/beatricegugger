#!/bin/bash
# Production Deployment Script for beatricegugger.ch
# This script validates all security requirements before deployment

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "  Beatrice Gugger - Production Deployment"
echo "=========================================="
echo ""

# Track if we have any errors
ERRORS=0

# Function to check requirement
check_requirement() {
    local name="$1"
    local result="$2"
    local required="$3"
    
    if [ "$result" = "OK" ]; then
        echo -e "${GREEN}✓${NC} $name"
    elif [ "$required" = "required" ]; then
        echo -e "${RED}✗${NC} $name"
        ERRORS=$((ERRORS + 1))
    else
        echo -e "${YELLOW}⚠${NC} $name (warning)"
    fi
}

echo "Checking production requirements..."
echo ""

# 1. Check .env file exists
if [ -f "$PROJECT_ROOT/.env" ]; then
    check_requirement ".env file exists" "OK" "required"
else
    check_requirement ".env file exists - MISSING!" "FAIL" "required"
fi

# 2. Check SECRET_KEY is set and not default
if [ -f "$PROJECT_ROOT/.env" ]; then
    SECRET_KEY=$(grep -E "^SECRET_KEY=" "$PROJECT_ROOT/.env" | cut -d'=' -f2)
    if [ -z "$SECRET_KEY" ]; then
        check_requirement "SECRET_KEY is set - NOT SET!" "FAIL" "required"
    elif [ "$SECRET_KEY" = "dev-secret-key-change-in-production" ] || [ "$SECRET_KEY" = "your-secret-key-change-this-in-production" ]; then
        check_requirement "SECRET_KEY is secure - USING DEFAULT VALUE!" "FAIL" "required"
    elif [ ${#SECRET_KEY} -lt 32 ]; then
        check_requirement "SECRET_KEY length (>= 32 chars) - TOO SHORT: ${#SECRET_KEY} chars" "FAIL" "required"
    else
        check_requirement "SECRET_KEY is secure (${#SECRET_KEY} chars)" "OK" "required"
    fi
fi

# 3. Check FLASK_ENV is production
if [ -f "$PROJECT_ROOT/.env" ]; then
    FLASK_ENV=$(grep -E "^FLASK_ENV=" "$PROJECT_ROOT/.env" | cut -d'=' -f2)
    if [ "$FLASK_ENV" = "production" ]; then
        check_requirement "FLASK_ENV=production" "OK" "required"
    else
        check_requirement "FLASK_ENV=production - Currently: $FLASK_ENV" "FAIL" "required"
    fi
fi

# 4. Check database file exists
if [ -f "$PROJECT_ROOT/beatricegugger.db" ]; then
    check_requirement "Database file exists" "OK" "required"
else
    check_requirement "Database file exists - MISSING!" "FAIL" "required"
fi

# 5. Check uploads directory exists
if [ -d "$PROJECT_ROOT/uploads" ]; then
    check_requirement "Uploads directory exists" "OK" "required"
else
    check_requirement "Uploads directory exists - MISSING!" "FAIL" "required"
fi

# 6. Check Docker is installed
if command -v docker &> /dev/null; then
    check_requirement "Docker installed" "OK" "required"
else
    check_requirement "Docker installed - NOT FOUND!" "FAIL" "required"
fi

# 7. Check docker-compose is installed
if command -v docker-compose &> /dev/null || docker compose version &> /dev/null; then
    check_requirement "Docker Compose installed" "OK" "required"
else
    check_requirement "Docker Compose installed - NOT FOUND!" "FAIL" "required"
fi

# 8. Check for debug prints in code (warning only)
DEBUG_PRINTS=$(grep -r "print(" "$PROJECT_ROOT/app" --include="*.py" 2>/dev/null | grep -v "__pycache__" | wc -l)
if [ "$DEBUG_PRINTS" -eq 0 ]; then
    check_requirement "No debug print statements in code" "OK" "warning"
else
    check_requirement "Found $DEBUG_PRINTS print() statements in code" "WARN" "warning"
fi

# 9. Check MAIL settings (warning)
if [ -f "$PROJECT_ROOT/.env" ]; then
    MAIL_SERVER=$(grep -E "^MAIL_SERVER=" "$PROJECT_ROOT/.env" | cut -d'=' -f2)
    if [ "$MAIL_SERVER" = "localhost" ] || [ -z "$MAIL_SERVER" ]; then
        check_requirement "MAIL_SERVER configured (currently: localhost)" "WARN" "warning"
    else
        check_requirement "MAIL_SERVER configured ($MAIL_SERVER)" "OK" "warning"
    fi
fi

echo ""
echo "=========================================="

if [ $ERRORS -gt 0 ]; then
    echo -e "${RED}DEPLOYMENT BLOCKED: $ERRORS critical issue(s) found${NC}"
    echo ""
    echo "Please fix the issues above before deploying to production."
    echo ""
    echo "Quick fixes:"
    echo "  1. Generate secure SECRET_KEY:"
    echo "     python3 -c \"import secrets; print(secrets.token_hex(32))\""
    echo ""
    echo "  2. Set FLASK_ENV=production in .env"
    echo ""
    exit 1
fi

echo -e "${GREEN}All checks passed!${NC}"
echo ""
read -p "Deploy to production? [y/N] " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled."
    exit 0
fi

echo ""
echo "Starting deployment..."
echo ""

# Create backup before deployment
BACKUP_DIR="$PROJECT_ROOT/backups"
mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
cp "$PROJECT_ROOT/beatricegugger.db" "$BACKUP_DIR/beatricegugger_predeploy_$TIMESTAMP.db"
echo -e "${GREEN}✓${NC} Database backup created: beatricegugger_predeploy_$TIMESTAMP.db"

# Build and deploy with Docker Compose
cd "$PROJECT_ROOT/docker"

echo "Building Docker image..."
docker compose build

echo "Starting containers..."
docker compose up -d

echo ""
echo "Waiting for health check..."
sleep 10

# Check if container is healthy
if docker compose ps | grep -q "healthy"; then
    echo -e "${GREEN}✓${NC} Container is healthy"
else
    echo -e "${YELLOW}⚠${NC} Container health status unknown, checking manually..."
    curl -s http://localhost:5003/health || echo "Health check endpoint not responding yet"
fi

echo ""
echo "=========================================="
echo -e "${GREEN}Docker Deployment complete!${NC}"
echo "=========================================="
echo ""

# Check if we're on the production server
if [ -d "/etc/apache2" ]; then
    echo "Detected Apache2 installation."
    read -p "Set up Apache reverse proxy now? [y/N] " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo ""
        echo "Setting up Apache..."
        
        # Copy Apache config
        APACHE_CONF="$SCRIPT_DIR/apache/beatricegugger.conf"
        if [ -f "$APACHE_CONF" ]; then
            sudo cp "$APACHE_CONF" /etc/apache2/sites-available/beatricegugger.conf
            echo -e "${GREEN}✓${NC} Apache config copied"
        fi
        
        # Enable required modules
        sudo a2enmod proxy proxy_http headers rewrite ssl > /dev/null 2>&1
        echo -e "${GREEN}✓${NC} Apache modules enabled"
        
        # Create challenge directory
        sudo mkdir -p /var/www/html/.well-known/acme-challenge
        echo -e "${GREEN}✓${NC} Let's Encrypt challenge directory created"
        
        # Enable site
        sudo a2ensite beatricegugger.conf > /dev/null 2>&1
        echo -e "${GREEN}✓${NC} Site enabled"
        
        # Test and reload
        sudo apache2ctl configtest && sudo systemctl reload apache2
        echo -e "${GREEN}✓${NC} Apache reloaded"
        
        echo ""
        read -p "Set up SSL certificate now? [y/N] " -n 1 -r
        echo ""
        
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            if [ -f "$SCRIPT_DIR/setup-ssl.sh" ]; then
                sudo bash "$SCRIPT_DIR/setup-ssl.sh"
            else
                echo "Running certbot..."
                echo ""
                echo "Choose method:"
                echo "  1) HTTP challenge (if port 80 works)"
                echo "  2) DNS challenge (more reliable)"
                read -p "Select [1/2]: " SSL_METHOD
                
                if [ "$SSL_METHOD" = "2" ]; then
                    sudo certbot certonly --manual --preferred-challenges dns \
                        -d beatricegugger.ch -d www.beatricegugger.ch
                else
                    sudo certbot --apache -d beatricegugger.ch -d www.beatricegugger.ch
                fi
            fi
        fi
    fi
fi

echo ""
echo "=========================================="
echo -e "${GREEN}All done!${NC}"
echo "=========================================="
echo ""
echo "Your site should be available at:"
echo "  http://beatricegugger.ch (or https if SSL was set up)"
echo ""
echo "Useful commands:"
echo "  View logs:    docker compose -f $SCRIPT_DIR/docker-compose.yml logs -f"
echo "  Restart app:  docker compose -f $SCRIPT_DIR/docker-compose.yml restart"
echo "  Stop app:     docker compose -f $SCRIPT_DIR/docker-compose.yml down"
echo ""
echo "SSL renewal test: sudo certbot renew --dry-run"
echo "=========================================="
