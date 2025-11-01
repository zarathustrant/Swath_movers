#!/bin/bash

# Enable Ngrok Tunnel (alongside Cloudflare)
# This script sets up ngrok to run concurrently with Cloudflare Tunnel

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "========================================"
echo "Enable Ngrok Tunnel"
echo "Runs alongside Cloudflare Tunnel"
echo "========================================"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
   echo -e "${RED}Please do NOT run this script as root${NC}"
   exit 1
fi

echo -e "${BLUE}This will:${NC}"
echo "  • Re-enable ngrok systemd service"
echo "  • Start ngrok tunnel to localhost:80"
echo "  • Provide temporary ngrok URL"
echo ""
echo -e "${YELLOW}Note:${NC} Both Cloudflare and Ngrok will run simultaneously"
echo "  • Cloudflare: https://seistools.space (permanent)"
echo "  • Ngrok: https://xxxxx.ngrok.io (temporary)"
echo ""
read -p "Continue? (y/N): " confirm
if [[ ! $confirm =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

echo ""
echo "========================================"
echo "Step 1: Verify Ngrok Installation"
echo "========================================"
echo ""

if ! command -v ngrok &> /dev/null; then
    echo -e "${RED}✗ Ngrok is not installed${NC}"
    echo ""
    echo "Install ngrok with:"
    echo "  curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null"
    echo "  echo 'deb https://ngrok-agent.s3.amazonaws.com buster main' | sudo tee /etc/apt/sources.list.d/ngrok.list"
    echo "  sudo apt update && sudo apt install ngrok"
    exit 1
fi

echo -e "${GREEN}✓ Ngrok is installed${NC}"
ngrok version

echo ""
echo "========================================"
echo "Step 2: Check Ngrok Service File"
echo "========================================"
echo ""

if [ ! -f "/etc/systemd/system/ngrok.service" ]; then
    echo -e "${YELLOW}Creating ngrok.service file...${NC}"

    # Create ngrok service
    cat > /tmp/ngrok.service << EOF
[Unit]
Description=Ngrok Tunnel
After=network.target swath-movers.service nginx.service
Wants=swath-movers.service nginx.service

[Service]
Type=simple
User=$(whoami)
Group=$(whoami)
WorkingDirectory=/home/$(whoami)
ExecStart=/usr/local/bin/ngrok http 80 --log stdout
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=ngrok

[Install]
WantedBy=multi-user.target
EOF

    sudo cp /tmp/ngrok.service /etc/systemd/system/
    sudo systemctl daemon-reload
    echo -e "${GREEN}✓ ngrok.service created${NC}"
else
    echo -e "${GREEN}✓ ngrok.service already exists${NC}"
fi

echo ""
echo "========================================"
echo "Step 3: Enable and Start Ngrok"
echo "========================================"
echo ""

echo "Enabling ngrok service..."
sudo systemctl enable ngrok.service
echo -e "${GREEN}✓ ngrok enabled${NC}"

echo ""
echo "Starting ngrok..."
sudo systemctl start ngrok.service
sleep 3

if systemctl is-active --quiet ngrok.service; then
    echo -e "${GREEN}✓ ngrok started successfully${NC}"
else
    echo -e "${RED}✗ ngrok failed to start${NC}"
    echo "Check logs with: journalctl -u ngrok -n 50"
    exit 1
fi

echo ""
echo "========================================"
echo "Step 4: Get Ngrok URL"
echo "========================================"
echo ""

echo "Waiting for ngrok to establish tunnel..."
sleep 3

NGROK_URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null | grep -o '"public_url":"https://[^"]*' | grep -o 'https://[^"]*' | head -1)

if [ -n "$NGROK_URL" ]; then
    echo -e "${GREEN}✓ Ngrok tunnel established${NC}"
    echo ""
    echo -e "${BLUE}Ngrok URL: $NGROK_URL${NC}"
else
    echo -e "${YELLOW}Could not retrieve ngrok URL automatically${NC}"
    echo "Get your URL with:"
    echo "  curl http://localhost:4040/api/tunnels 2>/dev/null | jq -r '.tunnels[0].public_url'"
    echo "Or visit: http://localhost:4040"
fi

echo ""
echo "========================================"
echo "Active Tunnels"
echo "========================================"
echo ""

echo "Service Status:"
echo ""
echo "1. Cloudflared:"
systemctl is-active cloudflared.service >/dev/null 2>&1 && echo -e "   ${GREEN}✓ Running${NC}" || echo "   ✗ Not running"

echo "2. Ngrok:"
systemctl is-active ngrok.service >/dev/null 2>&1 && echo -e "   ${GREEN}✓ Running${NC}" || echo "   ✗ Not running"

echo ""
echo "Your URLs:"
echo ""
echo -e "  ${GREEN}Permanent:${NC} ${BLUE}https://seistools.space${NC} (Cloudflare)"
if [ -n "$NGROK_URL" ]; then
    echo -e "  ${GREEN}Temporary:${NC} ${BLUE}$NGROK_URL${NC} (Ngrok)"
fi
echo ""

echo "========================================"
echo "Useful Commands"
echo "========================================"
echo ""
echo "# Check ngrok status:"
echo "  sudo systemctl status ngrok"
echo ""
echo "# View ngrok logs:"
echo "  journalctl -u ngrok -f"
echo ""
echo "# Get ngrok URL:"
echo "  curl -s http://localhost:4040/api/tunnels | jq -r '.tunnels[0].public_url'"
echo ""
echo "# Ngrok web interface:"
echo "  http://localhost:4040"
echo ""
echo "# Stop ngrok:"
echo "  sudo systemctl stop ngrok"
echo ""
echo "# Disable ngrok (prevent auto-start):"
echo "  sudo systemctl disable ngrok"
echo ""
echo -e "${GREEN}Done! Both Cloudflare and Ngrok are now running.${NC}"
echo ""
