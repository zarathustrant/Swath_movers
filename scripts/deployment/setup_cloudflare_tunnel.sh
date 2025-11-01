#!/bin/bash

# Cloudflare Tunnel Setup Script for seistools.space
# Run this script with: bash setup_cloudflare_tunnel.sh

set -e

echo "========================================"
echo "Cloudflare Tunnel Setup"
echo "Domain: seistools.space"
echo "========================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DOMAIN="seistools.space"
TUNNEL_NAME="antan3d"
CLOUDFLARED_DIR="$HOME/.cloudflared"
WORKING_DIR="/home/aerys/Documents/ANTAN3D"

# Check if running as root
if [ "$EUID" -eq 0 ]; then
   echo -e "${RED}Please do NOT run this script as root${NC}"
   echo "Run it as your regular user. It will prompt for sudo password when needed."
   exit 1
fi

echo -e "${BLUE}This script will:${NC}"
echo "  1. Install cloudflared"
echo "  2. Authenticate with Cloudflare (will open browser)"
echo "  3. Create tunnel '${TUNNEL_NAME}'"
echo "  4. Configure DNS for ${DOMAIN}"
echo "  5. Update Nginx configuration"
echo "  6. Create systemd service"
echo "  7. Remove ngrok service"
echo ""
read -p "Continue? (y/N): " confirm
if [[ ! $confirm =~ ^[Yy]$ ]]; then
    echo "Installation cancelled."
    exit 0
fi

echo ""
echo "========================================"
echo "Step 1: Installing cloudflared"
echo "========================================"
echo ""

# Check if already installed
if command -v cloudflared &> /dev/null; then
    echo -e "${YELLOW}cloudflared is already installed${NC}"
    cloudflared --version
else
    echo "Downloading cloudflared..."
    cd /tmp
    curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb

    echo "Installing cloudflared..."
    sudo dpkg -i cloudflared.deb

    echo -e "${GREEN}✓ cloudflared installed${NC}"
    cloudflared --version
fi

echo ""
echo "========================================"
echo "Step 2: Authenticate with Cloudflare"
echo "========================================"
echo ""

# Create cloudflared directory
mkdir -p "$CLOUDFLARED_DIR"

# Check if already authenticated
if [ -f "$CLOUDFLARED_DIR/cert.pem" ]; then
    echo -e "${YELLOW}Already authenticated (cert.pem exists)${NC}"
    echo "If you want to re-authenticate, delete: $CLOUDFLARED_DIR/cert.pem"
else
    echo -e "${BLUE}This will open a browser window for authentication...${NC}"
    echo "Please select your domain: ${DOMAIN}"
    echo ""
    read -p "Press Enter to continue..."

    cloudflared tunnel login

    if [ -f "$CLOUDFLARED_DIR/cert.pem" ]; then
        echo -e "${GREEN}✓ Authentication successful${NC}"
    else
        echo -e "${RED}✗ Authentication failed${NC}"
        exit 1
    fi
fi

echo ""
echo "========================================"
echo "Step 3: Create Tunnel"
echo "========================================"
echo ""

# Check if tunnel credentials file exists (more reliable than API)
EXISTING_CREDS=$(ls "$CLOUDFLARED_DIR"/*.json 2>/dev/null | head -1 || true)

if [ -n "$EXISTING_CREDS" ]; then
    # Extract tunnel ID from credentials filename
    TUNNEL_ID=$(basename "$EXISTING_CREDS" .json)
    echo -e "${YELLOW}Found existing tunnel credentials (ID: ${TUNNEL_ID})${NC}"

    # Try to get tunnel name to verify
    TUNNEL_INFO=$(cloudflared tunnel info "$TUNNEL_ID" 2>/dev/null || echo "")
    if [ -n "$TUNNEL_INFO" ]; then
        echo -e "${GREEN}✓ Tunnel verified${NC}"
    else
        echo -e "${YELLOW}Note: Could not verify tunnel via API, but credentials exist${NC}"
    fi
else
    echo "Creating tunnel: ${TUNNEL_NAME}"
    CREATE_OUTPUT=$(cloudflared tunnel create "$TUNNEL_NAME" 2>&1)

    # Extract tunnel ID from create output (format: "Created tunnel antan3d with id 6c224381...")
    TUNNEL_ID=$(echo "$CREATE_OUTPUT" | grep -oP 'with id \K[a-f0-9-]+' || true)

    if [ -z "$TUNNEL_ID" ]; then
        # Try to find the credentials file
        CREDS_FILE=$(ls "$CLOUDFLARED_DIR"/*.json 2>/dev/null | head -1 || true)
        if [ -n "$CREDS_FILE" ]; then
            TUNNEL_ID=$(basename "$CREDS_FILE" .json)
            echo -e "${YELLOW}Extracted tunnel ID from credentials: ${TUNNEL_ID}${NC}"
        fi
    fi

    if [ -n "$TUNNEL_ID" ]; then
        echo -e "${GREEN}✓ Tunnel created with ID: ${TUNNEL_ID}${NC}"
    else
        echo -e "${RED}✗ Failed to create tunnel or extract tunnel ID${NC}"
        echo "Output: $CREATE_OUTPUT"
        exit 1
    fi
fi

echo ""
echo "Tunnel ID: ${TUNNEL_ID}"
echo "Credentials file: $CLOUDFLARED_DIR/${TUNNEL_ID}.json"

echo ""
echo "========================================"
echo "Step 4: Configure Tunnel"
echo "========================================"
echo ""

# Create config.yml
echo "Creating tunnel configuration..."
cat > "$CLOUDFLARED_DIR/config.yml" << EOF
tunnel: ${TUNNEL_ID}
credentials-file: ${CLOUDFLARED_DIR}/${TUNNEL_ID}.json

ingress:
  # Route seistools.space to local nginx
  - hostname: ${DOMAIN}
    service: http://localhost:80

  # Support www subdomain
  - hostname: www.${DOMAIN}
    service: http://localhost:80

  # Catch-all rule (required)
  - service: http_status:404
EOF

echo -e "${GREEN}✓ Configuration file created: $CLOUDFLARED_DIR/config.yml${NC}"
cat "$CLOUDFLARED_DIR/config.yml"

echo ""
echo "========================================"
echo "Step 5: Configure DNS Routes"
echo "========================================"
echo ""

# Route DNS through tunnel
echo "Setting up DNS for ${DOMAIN}..."
cloudflared tunnel route dns "$TUNNEL_NAME" "$DOMAIN" 2>&1 || echo -e "${YELLOW}DNS route may already exist${NC}"

echo "Setting up DNS for www.${DOMAIN}..."
cloudflared tunnel route dns "$TUNNEL_NAME" "www.${DOMAIN}" 2>&1 || echo -e "${YELLOW}DNS route may already exist${NC}"

echo -e "${GREEN}✓ DNS routes configured${NC}"

echo ""
echo "========================================"
echo "Step 6: Update Nginx Configuration"
echo "========================================"
echo ""

# Backup existing nginx config
if [ -f "/etc/nginx/sites-available/swath-movers" ]; then
    echo "Backing up existing Nginx config..."
    sudo cp /etc/nginx/sites-available/swath-movers /etc/nginx/sites-available/swath-movers.backup.$(date +%Y%m%d_%H%M%S)
    echo -e "${GREEN}✓ Backup created${NC}"
fi

# Create updated nginx config
echo "Creating updated Nginx configuration..."
cat > /tmp/swath-movers-cloudflare.conf << 'NGINX_EOF'
# Nginx Configuration for Swath Movers Application with Cloudflare
# Optimized for performance with static file caching and compression

# Upstream Gunicorn backend
upstream swath_movers_backend {
    # Gunicorn running on localhost:8080
    server 127.0.0.1:8080 fail_timeout=0;

    # Keep-alive connections to backend
    keepalive 32;
}

# Cache configuration
proxy_cache_path /var/cache/nginx/swath_movers levels=1:2 keys_zone=swath_cache:10m max_size=100m inactive=60m use_temp_path=off;

server {
    listen 80;
    listen [::]:80;

    server_name seistools.space www.seistools.space;

    # Get real client IP from Cloudflare
    set_real_ip_from 173.245.48.0/20;
    set_real_ip_from 103.21.244.0/22;
    set_real_ip_from 103.22.200.0/22;
    set_real_ip_from 103.31.4.0/22;
    set_real_ip_from 141.101.64.0/18;
    set_real_ip_from 108.162.192.0/18;
    set_real_ip_from 190.93.240.0/20;
    set_real_ip_from 188.114.96.0/20;
    set_real_ip_from 197.234.240.0/22;
    set_real_ip_from 198.41.128.0/17;
    set_real_ip_from 162.158.0.0/15;
    set_real_ip_from 104.16.0.0/13;
    set_real_ip_from 104.24.0.0/14;
    set_real_ip_from 172.64.0.0/13;
    set_real_ip_from 131.0.72.0/22;
    set_real_ip_from 2400:cb00::/32;
    set_real_ip_from 2606:4700::/32;
    set_real_ip_from 2803:f800::/32;
    set_real_ip_from 2405:b500::/32;
    set_real_ip_from 2405:8100::/32;
    set_real_ip_from 2a06:98c0::/29;
    set_real_ip_from 2c0f:f248::/32;
    real_ip_header CF-Connecting-IP;

    # Increase client body size for file uploads
    client_max_body_size 50M;

    # Root directory for static files
    root /home/aerys/Documents/ANTAN3D;

    # Logging
    access_log /var/log/nginx/swath_movers_access.log;
    error_log /var/log/nginx/swath_movers_error.log warn;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # ==========================================
    # Static Files - Served directly by Nginx
    # ==========================================

    # Static files with aggressive caching
    location /static/ {
        alias /home/aerys/Documents/ANTAN3D/static/;

        # Cache for 1 year (immutable files)
        expires 1y;
        add_header Cache-Control "public, immutable";

        # Enable gzip compression
        gzip on;
        gzip_vary on;
        gzip_min_length 1000;
        gzip_types text/css application/javascript application/json image/svg+xml;

        # Disable access logs for static files (performance)
        access_log off;

        # Enable sendfile for better performance
        sendfile on;
        tcp_nopush on;
        tcp_nodelay on;

        # CORS headers for fonts/assets if needed
        add_header Access-Control-Allow-Origin *;
    }

    # Favicon with long cache
    location = /favicon.ico {
        alias /home/aerys/Documents/ANTAN3D/static/favicon.png;
        expires 1y;
        add_header Cache-Control "public, immutable";
        access_log off;
    }

    # Swaths directory (CSV files)
    location /swaths/ {
        alias /home/aerys/Documents/ANTAN3D/swaths/;

        # Cache CSV files for 1 hour
        expires 1h;
        add_header Cache-Control "public, must-revalidate";

        # Enable gzip
        gzip on;
        gzip_types text/csv text/plain;
    }

    # ==========================================
    # API Endpoints - Proxied to Gunicorn
    # ==========================================

    # Cacheable API endpoints with short TTL
    location ~ ^/(get_coordinates|geojson|geojson_lines|load_polygons|postplot/geojson) {
        # Proxy cache configuration
        proxy_cache swath_cache;
        proxy_cache_key "$scheme$request_method$host$request_uri";
        proxy_cache_valid 200 5m;
        proxy_cache_valid 404 1m;
        proxy_cache_use_stale error timeout updating http_500 http_502 http_503 http_504;
        proxy_cache_background_update on;
        proxy_cache_lock on;

        # Add cache status header for debugging
        add_header X-Cache-Status $upstream_cache_status;

        # Proxy to Gunicorn
        proxy_pass http://swath_movers_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection "";

        # Timeouts
        proxy_connect_timeout 30s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # All other routes (no caching for dynamic content)
    location / {
        # Proxy to Gunicorn
        proxy_pass http://swath_movers_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection "";

        # Timeouts for file uploads
        proxy_connect_timeout 60s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
}
NGINX_EOF

echo "Installing updated Nginx configuration..."
sudo cp /tmp/swath-movers-cloudflare.conf /etc/nginx/sites-available/swath-movers

# Test nginx configuration
echo "Testing Nginx configuration..."
sudo nginx -t

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Nginx configuration is valid${NC}"
else
    echo -e "${RED}✗ Nginx configuration error${NC}"
    exit 1
fi

echo ""
echo "========================================"
echo "Step 7: Create Systemd Service"
echo "========================================"
echo ""

# Create systemd service for cloudflared
echo "Creating cloudflared.service..."
cat > /tmp/cloudflared.service << EOF
[Unit]
Description=Cloudflare Tunnel for seistools.space
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=$(whoami)
Group=$(whoami)
ExecStart=/usr/local/bin/cloudflared tunnel --config ${CLOUDFLARED_DIR}/config.yml run
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=cloudflared

# Security settings
PrivateTmp=true
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
EOF

sudo cp /tmp/cloudflared.service /etc/systemd/system/
echo -e "${GREEN}✓ cloudflared.service created${NC}"

echo ""
echo "========================================"
echo "Step 8: Remove Ngrok Service"
echo "========================================"
echo ""

if systemctl is-active --quiet ngrok.service; then
    echo "Stopping ngrok service..."
    sudo systemctl stop ngrok.service
    echo -e "${GREEN}✓ ngrok stopped${NC}"
fi

if systemctl is-enabled --quiet ngrok.service 2>/dev/null; then
    echo "Disabling ngrok service..."
    sudo systemctl disable ngrok.service
    echo -e "${GREEN}✓ ngrok disabled${NC}"
fi

if [ -f "/etc/systemd/system/ngrok.service" ]; then
    echo "Removing ngrok service file..."
    sudo rm /etc/systemd/system/ngrok.service
    echo -e "${GREEN}✓ ngrok.service removed${NC}"
fi

echo ""
echo "========================================"
echo "Step 9: Start Services"
echo "========================================"
echo ""

echo "Reloading systemd daemon..."
sudo systemctl daemon-reload
echo -e "${GREEN}✓ Systemd daemon reloaded${NC}"

echo ""
echo "Enabling cloudflared service..."
sudo systemctl enable cloudflared.service
echo -e "${GREEN}✓ cloudflared enabled for auto-start${NC}"

echo ""
echo "Starting cloudflared..."
sudo systemctl start cloudflared.service
sleep 3
echo -e "${GREEN}✓ cloudflared started${NC}"

echo ""
echo "Reloading Nginx..."
sudo systemctl reload nginx.service
echo -e "${GREEN}✓ Nginx reloaded${NC}"

echo ""
echo "========================================"
echo "Installation Complete!"
echo "========================================"
echo ""

echo -e "${GREEN}✓ All services are configured!${NC}"
echo ""

echo "Service Status:"
echo "---------------"
echo ""
echo "Cloudflared Tunnel:"
sudo systemctl status cloudflared.service --no-pager -l | head -15
echo ""
echo "Nginx:"
sudo systemctl status nginx.service --no-pager -l | head -10
echo ""
echo "Swath Movers:"
sudo systemctl status swath-movers.service --no-pager -l | head -10

echo ""
echo ""
echo "========================================"
echo "Your Application URLs:"
echo "========================================"
echo -e "${GREEN}Primary: ${BLUE}https://${DOMAIN}${NC}"
echo -e "${GREEN}WWW:     ${BLUE}https://www.${DOMAIN}${NC}"
echo ""

echo "========================================"
echo "Cloudflare Dashboard:"
echo "========================================"
echo "View your tunnel at:"
echo "https://one.dash.cloudflare.com/"
echo ""

echo "========================================"
echo "Next Steps:"
echo "========================================"
echo ""
echo "1. Visit https://${DOMAIN} to test your site"
echo "2. Configure Cloudflare settings:"
echo "   - SSL/TLS: Set to 'Flexible' mode"
echo "   - Speed: Enable Auto Minify"
echo "   - Caching: Standard mode"
echo ""
echo "3. Update any hardcoded URLs in your app to use ${DOMAIN}"
echo ""

echo "========================================"
echo "Useful Commands:"
echo "========================================"
echo ""
echo "# Check tunnel status:"
echo "  sudo systemctl status cloudflared"
echo "  cloudflared tunnel info ${TUNNEL_NAME}"
echo ""
echo "# View tunnel logs:"
echo "  journalctl -u cloudflared -f"
echo ""
echo "# List all tunnels:"
echo "  cloudflared tunnel list"
echo ""
echo "# Restart tunnel:"
echo "  sudo systemctl restart cloudflared"
echo ""
echo -e "${GREEN}Setup complete! Your site is live at https://${DOMAIN}${NC}"
echo ""
