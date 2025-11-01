#!/bin/bash

# Continue Cloudflare Tunnel Setup (after tunnel creation)
# For existing tunnel: antan3d (ID: 6c224381-4eb1-4842-b581-bfb8b949c74f)

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
DOMAIN="seistools.space"
TUNNEL_NAME="antan3d"
TUNNEL_ID="6c224381-4eb1-4842-b581-bfb8b949c74f"
CLOUDFLARED_DIR="$HOME/.cloudflared"

echo "========================================"
echo "Cloudflare Tunnel Setup (Continue)"
echo "Domain: seistools.space"
echo "Tunnel ID: ${TUNNEL_ID}"
echo "========================================"
echo ""

# Verify tunnel exists
if [ ! -f "$CLOUDFLARED_DIR/${TUNNEL_ID}.json" ]; then
    echo -e "${RED}✗ Tunnel credentials not found: $CLOUDFLARED_DIR/${TUNNEL_ID}.json${NC}"
    echo "Please run the full setup script first."
    exit 1
fi

echo -e "${GREEN}✓ Found tunnel credentials${NC}"

echo ""
echo "========================================"
echo "Step 1: Configure Tunnel"
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

echo -e "${GREEN}✓ Configuration file created${NC}"
cat "$CLOUDFLARED_DIR/config.yml"

echo ""
echo "========================================"
echo "Step 2: Configure DNS Routes"
echo "========================================"
echo ""

echo "Setting up DNS for ${DOMAIN}..."
cloudflared tunnel route dns "$TUNNEL_ID" "$DOMAIN" 2>&1 || echo -e "${YELLOW}DNS route may already exist (this is OK)${NC}"

echo "Setting up DNS for www.${DOMAIN}..."
cloudflared tunnel route dns "$TUNNEL_ID" "www.${DOMAIN}" 2>&1 || echo -e "${YELLOW}DNS route may already exist (this is OK)${NC}"

echo -e "${GREEN}✓ DNS routes configured${NC}"

echo ""
echo "========================================"
echo "Step 3: Fix Static File Permissions"
echo "========================================"
echo ""

# Fix home directory permissions for nginx to access static files
echo "Setting permissions for nginx access..."
chmod 755 /home/aerys
chmod 755 /home/aerys/Documents
chmod 755 /home/aerys/Documents/ANTAN3D
echo -e "${GREEN}✓ Permissions fixed${NC}"

echo ""
echo "========================================"
echo "Step 4: Update Nginx Configuration"
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
echo "Step 5: Create Systemd Service"
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
echo "Step 6: Stop Ngrok Service"
echo "========================================"
echo ""

if systemctl is-active --quiet ngrok.service 2>/dev/null; then
    echo "Stopping ngrok service..."
    sudo systemctl stop ngrok.service
    echo -e "${GREEN}✓ ngrok stopped${NC}"
else
    echo -e "${YELLOW}ngrok service not running${NC}"
fi

if systemctl is-enabled --quiet ngrok.service 2>/dev/null; then
    echo "Disabling ngrok service..."
    sudo systemctl disable ngrok.service
    echo -e "${GREEN}✓ ngrok disabled${NC}"
fi

echo ""
echo "========================================"
echo "Step 7: Start Services"
echo "========================================"
echo ""

echo "Reloading systemd daemon..."
sudo systemctl daemon-reload
echo -e "${GREEN}✓ Systemd reloaded${NC}"

echo ""
echo "Enabling cloudflared..."
sudo systemctl enable cloudflared.service
echo -e "${GREEN}✓ cloudflared enabled${NC}"

echo ""
echo "Starting cloudflared..."
sudo systemctl start cloudflared.service
sleep 3

if systemctl is-active --quiet cloudflared.service; then
    echo -e "${GREEN}✓ cloudflared started successfully${NC}"
else
    echo -e "${RED}✗ cloudflared failed to start${NC}"
    echo "Check logs with: journalctl -u cloudflared -n 50"
    exit 1
fi

echo ""
echo "Starting Nginx..."
sudo systemctl start nginx.service 2>/dev/null || sudo systemctl reload nginx.service
echo -e "${GREEN}✓ Nginx started${NC}"

echo ""
echo "========================================"
echo "Setup Complete!"
echo "========================================"
echo ""

echo "Service Status:"
echo "---------------"
echo ""

echo "1. Cloudflared Tunnel:"
sudo systemctl status cloudflared.service --no-pager -l | head -8
echo ""

echo "2. Swath Movers (Gunicorn):"
systemctl status swath-movers.service --no-pager -l | head -8
echo ""

echo "3. Nginx:"
systemctl status nginx.service --no-pager -l | head -8 || echo "   Nginx not configured as systemd service"
echo ""

echo "Testing Local Connections:"
echo "-------------------------"
echo -n "Gunicorn (port 8080): "
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080 && echo "✓ OK" || echo "✗ FAIL"
echo -n "Nginx (port 80):      "
curl -s -o /dev/null -w "%{http_code}" http://localhost:80 && echo "✓ OK" || echo "✗ FAIL"
echo ""

echo "========================================"
echo "Your Application is Live!"
echo "========================================"
echo -e "${GREEN}Primary URL: ${BLUE}https://${DOMAIN}${NC}"
echo -e "${GREEN}WWW URL:     ${BLUE}https://www.${DOMAIN}${NC}"
echo ""

echo "========================================"
echo "IMPORTANT: Configure Cloudflare Settings"
echo "========================================"
echo ""
echo "Go to: https://dash.cloudflare.com/"
echo "Select: ${DOMAIN}"
echo ""
echo -e "${BLUE}Required Settings:${NC}"
echo ""
echo "1. SSL/TLS Configuration:"
echo "   → SSL/TLS → Overview"
echo "   → Set encryption mode to: ${YELLOW}Flexible${NC}"
echo ""
echo "2. Caching Configuration (to work like ngrok):"
echo "   → Caching → Configuration"
echo "   → Caching Level: ${YELLOW}Standard${NC}"
echo "   → Browser Cache TTL: ${YELLOW}Respect Existing Headers${NC}"
echo ""
echo -e "${BLUE}This will:${NC}"
echo "  ✓ Let YOUR nginx control all caching (same as ngrok)"
echo "  ✓ Cloudflare only acts as tunnel + SSL"
echo "  ✓ Static files served by your server with your cache rules"
echo ""
echo "========================================"
echo "Useful Commands:"
echo "========================================"
echo ""
echo "View tunnel logs:"
echo "  journalctl -u cloudflared -f"
echo ""
echo "Check tunnel status:"
echo "  systemctl status cloudflared"
echo ""
echo "Test your site:"
echo "  curl -I https://${DOMAIN}"
echo ""
echo -e "${GREEN}Done! Your site is now live at https://${DOMAIN}${NC}"
echo ""
