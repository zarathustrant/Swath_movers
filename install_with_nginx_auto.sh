#!/bin/bash

# Automatic Installation script for Swath Movers with Nginx CDN
# Run this script with: bash install_with_nginx_auto.sh
# This version runs without prompts

set -e

echo "========================================"
echo "Swath Movers Automatic Installation"
echo "With Nginx Reverse Proxy & Caching"
echo "========================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -eq 0 ]; then
   echo -e "${RED}Please do NOT run this script as root${NC}"
   echo "Run it as your regular user. It will prompt for sudo password when needed."
   exit 1
fi

echo -e "${BLUE}Installing:${NC}"
echo "  1. Nginx web server (reverse proxy + static file CDN)"
echo "  2. Swath Movers systemd service (Flask + Gunicorn)"
echo "  3. Ngrok systemd service (external access)"
echo ""

echo "========================================"
echo "Step 1: Checking Nginx Installation"
echo "========================================"
echo ""

# Check if nginx is already installed
if command -v nginx &> /dev/null || [ -x /usr/sbin/nginx ]; then
    echo -e "${YELLOW}Nginx is already installed${NC}"
    /usr/sbin/nginx -v 2>&1 | head -1
else
    echo "Installing Nginx..."
    sudo apt update
    sudo apt install -y nginx
    echo -e "${GREEN}✓ Nginx installed${NC}"
    /usr/sbin/nginx -v 2>&1 | head -1
fi

echo ""
echo "========================================"
echo "Step 2: Configuring Nginx"
echo "========================================"
echo ""

# Create cache directory
echo "Creating cache directory..."
sudo mkdir -p /var/cache/nginx/swath_movers
sudo chown www-data:www-data /var/cache/nginx/swath_movers
echo -e "${GREEN}✓ Cache directory created${NC}"

# Install nginx configuration
if [ -f "/tmp/swath-movers-nginx.conf" ]; then
    echo "Installing Nginx configuration..."
    sudo cp /tmp/swath-movers-nginx.conf /etc/nginx/sites-available/swath-movers

    # Remove default site
    sudo rm -f /etc/nginx/sites-enabled/default

    # Enable swath-movers site
    sudo ln -sf /etc/nginx/sites-available/swath-movers /etc/nginx/sites-enabled/swath-movers

    echo -e "${GREEN}✓ Nginx configuration installed${NC}"
else
    echo -e "${RED}✗ Error: /tmp/swath-movers-nginx.conf not found${NC}"
    exit 1
fi

# Test nginx configuration
echo "Testing Nginx configuration..."
sudo /usr/sbin/nginx -t
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Nginx configuration is valid${NC}"
else
    echo -e "${RED}✗ Nginx configuration error${NC}"
    exit 1
fi

echo ""
echo "========================================"
echo "Step 3: Installing Systemd Services"
echo "========================================"
echo ""

# Install swath-movers service
if [ -f "/tmp/swath-movers.service" ]; then
    echo "Installing swath-movers.service..."
    sudo cp /tmp/swath-movers.service /etc/systemd/system/
    echo -e "${GREEN}✓ swath-movers.service installed${NC}"
else
    echo -e "${RED}✗ Error: /tmp/swath-movers.service not found${NC}"
    exit 1
fi

# Install ngrok service
if [ -f "/tmp/ngrok.service" ]; then
    echo "Installing ngrok.service..."
    sudo cp /tmp/ngrok.service /etc/systemd/system/
    echo -e "${GREEN}✓ ngrok.service installed${NC}"
else
    echo -e "${RED}✗ Error: /tmp/ngrok.service not found${NC}"
    exit 1
fi

echo ""
echo "Step 4: Reloading systemd daemon..."
sudo systemctl daemon-reload
echo -e "${GREEN}✓ Systemd daemon reloaded${NC}"

echo ""
echo "========================================"
echo "Step 5: Enabling Services"
echo "========================================"
echo ""

sudo systemctl enable nginx.service
sudo systemctl enable swath-movers.service
sudo systemctl enable ngrok.service
echo -e "${GREEN}✓ All services enabled for auto-start${NC}"

echo ""
echo "========================================"
echo "Step 6: Starting Services"
echo "========================================"
echo ""

# Stop any existing processes
EXISTING_PID=$(lsof -ti:8080 2>/dev/null || true)
if [ -n "$EXISTING_PID" ]; then
    echo -e "${YELLOW}Found existing process on port 8080 (PID: $EXISTING_PID), stopping it...${NC}"
    kill $EXISTING_PID 2>/dev/null || true
    sleep 2
fi

EXISTING_NGROK=$(pgrep -f "ngrok http" || true)
if [ -n "$EXISTING_NGROK" ]; then
    echo -e "${YELLOW}Found existing ngrok process (PID: $EXISTING_NGROK), stopping it...${NC}"
    kill $EXISTING_NGROK 2>/dev/null || true
    sleep 2
fi

echo "1. Starting swath-movers (Flask + Gunicorn)..."
sudo systemctl start swath-movers.service
sleep 3
echo -e "${GREEN}✓ Swath-movers started${NC}"

echo "2. Starting nginx (Reverse Proxy)..."
sudo systemctl restart nginx.service
sleep 2
echo -e "${GREEN}✓ Nginx started${NC}"

echo "3. Starting ngrok (External Tunnel)..."
sudo systemctl start ngrok.service
sleep 3
echo -e "${GREEN}✓ Ngrok started${NC}"

echo ""
echo "========================================"
echo "Installation Complete!"
echo "========================================"
echo ""

echo -e "${GREEN}✓ All services are running!${NC}"
echo ""

echo "Service Status:"
echo "---------------"
sudo systemctl status swath-movers.service --no-pager -l | head -12
echo ""
sudo systemctl status nginx.service --no-pager -l | head -12
echo ""
sudo systemctl status ngrok.service --no-pager -l | head -12

echo ""
echo ""
echo "========================================"
echo "Performance Improvements Enabled:"
echo "========================================"
echo -e "${GREEN}✓ Static files served by Nginx (10x faster)${NC}"
echo -e "${GREEN}✓ Gzip compression enabled${NC}"
echo -e "${GREEN}✓ Browser caching (1 year for static assets)${NC}"
echo -e "${GREEN}✓ API response caching (5-10 minutes)${NC}"
echo -e "${GREEN}✓ 5 Gunicorn workers × 4 threads${NC}"
echo -e "${GREEN}✓ PostgreSQL connection pool (10-50)${NC}"
echo ""

echo "========================================"
echo "Getting Your Ngrok URL..."
echo "========================================"
sleep 2

# Try to get ngrok URL
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null | grep -o '"public_url":"[^"]*' | grep -o 'https://[^"]*' | head -1)

if [ -n "$NGROK_URL" ]; then
    echo -e "${GREEN}Your application is accessible at:${NC}"
    echo -e "${BLUE}${NGROK_URL}${NC}"
    echo ""
else
    echo -e "${YELLOW}Ngrok URL will be available in a few seconds...${NC}"
    echo "Get your URL with:"
    echo "  curl http://localhost:4040/api/tunnels 2>/dev/null | jq -r '.tunnels[0].public_url'"
    echo "Or visit: http://localhost:4040"
    echo ""
fi

echo "========================================"
echo "Quick Commands:"
echo "========================================"
echo ""
echo "# View logs:"
echo "  journalctl -u swath-movers -f"
echo "  journalctl -u nginx -f"
echo ""
echo "# Restart after code changes:"
echo "  sudo systemctl restart swath-movers"
echo ""
echo "# Get ngrok URL:"
echo "  curl http://localhost:4040/api/tunnels 2>/dev/null | jq -r '.tunnels[0].public_url'"
echo ""
echo -e "${GREEN}Setup complete! Your application is production-ready.${NC}"
echo ""
