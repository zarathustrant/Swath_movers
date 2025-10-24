#!/bin/bash

# Installation script for Swath Movers systemd services
# Run this script with: bash install_services.sh

set -e

echo "========================================"
echo "Swath Movers Service Installation"
echo "========================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -eq 0 ]; then
   echo -e "${RED}Please do NOT run this script as root${NC}"
   echo "Run it as your regular user. It will prompt for sudo password when needed."
   exit 1
fi

echo "Step 1: Installing systemd service files..."
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
echo "Step 2: Reloading systemd daemon..."
sudo systemctl daemon-reload
echo -e "${GREEN}✓ Systemd daemon reloaded${NC}"

echo ""
echo "Step 3: Enabling services to start on boot..."
sudo systemctl enable swath-movers.service
sudo systemctl enable ngrok.service
echo -e "${GREEN}✓ Services enabled${NC}"

echo ""
echo "Step 4: Starting services..."

# Stop any existing Flask process on port 8080
EXISTING_PID=$(lsof -ti:8080 2>/dev/null || true)
if [ -n "$EXISTING_PID" ]; then
    echo -e "${YELLOW}Found existing process on port 8080 (PID: $EXISTING_PID), stopping it...${NC}"
    kill $EXISTING_PID 2>/dev/null || true
    sleep 2
fi

# Stop existing ngrok process
EXISTING_NGROK=$(pgrep -f "ngrok http" || true)
if [ -n "$EXISTING_NGROK" ]; then
    echo -e "${YELLOW}Found existing ngrok process (PID: $EXISTING_NGROK), stopping it...${NC}"
    kill $EXISTING_NGROK 2>/dev/null || true
    sleep 2
fi

echo "Starting swath-movers service..."
sudo systemctl start swath-movers.service
sleep 3

echo "Starting ngrok service..."
sudo systemctl start ngrok.service
sleep 3

echo -e "${GREEN}✓ Services started${NC}"

echo ""
echo "========================================"
echo "Installation Complete!"
echo "========================================"
echo ""

echo "Service Status:"
echo "---------------"
sudo systemctl status swath-movers.service --no-pager -l | head -15
echo ""
sudo systemctl status ngrok.service --no-pager -l | head -15

echo ""
echo ""
echo "Useful Commands:"
echo "----------------"
echo "# Check service status:"
echo "  sudo systemctl status swath-movers"
echo "  sudo systemctl status ngrok"
echo ""
echo "# View live logs:"
echo "  journalctl -u swath-movers -f"
echo "  journalctl -u ngrok -f"
echo ""
echo "# Restart services:"
echo "  sudo systemctl restart swath-movers"
echo "  sudo systemctl restart ngrok"
echo ""
echo "# Stop services:"
echo "  sudo systemctl stop swath-movers"
echo "  sudo systemctl stop ngrok"
echo ""
echo "# Get ngrok URL:"
echo "  curl http://localhost:4040/api/tunnels 2>/dev/null | jq -r '.tunnels[0].public_url'"
echo ""
echo -e "${GREEN}Your application is now running!${NC}"
echo ""
