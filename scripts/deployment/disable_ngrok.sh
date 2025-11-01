#!/bin/bash

# Disable Ngrok Tunnel
# Stops and disables ngrok while keeping Cloudflare running

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "========================================"
echo "Disable Ngrok Tunnel"
echo "Cloudflare will continue running"
echo "========================================"
echo ""

if [ "$EUID" -eq 0 ]; then
   echo -e "${RED}Please do NOT run this script as root${NC}"
   exit 1
fi

echo -e "${BLUE}This will:${NC}"
echo "  • Stop ngrok service"
echo "  • Disable ngrok auto-start"
echo "  • Keep Cloudflare Tunnel running"
echo ""
read -p "Continue? (y/N): " confirm
if [[ ! $confirm =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

echo ""
echo "Stopping ngrok service..."
if systemctl is-active --quiet ngrok.service 2>/dev/null; then
    sudo systemctl stop ngrok.service
    echo -e "${GREEN}✓ ngrok stopped${NC}"
else
    echo -e "${YELLOW}ngrok was not running${NC}"
fi

echo ""
echo "Disabling ngrok auto-start..."
if systemctl is-enabled --quiet ngrok.service 2>/dev/null; then
    sudo systemctl disable ngrok.service
    echo -e "${GREEN}✓ ngrok disabled${NC}"
else
    echo -e "${YELLOW}ngrok was not enabled${NC}"
fi

echo ""
echo "========================================"
echo "Status"
echo "========================================"
echo ""

echo "Cloudflared:"
systemctl is-active cloudflared.service >/dev/null 2>&1 && echo -e "  ${GREEN}✓ Running${NC}" || echo "  ✗ Not running"

echo "Ngrok:"
systemctl is-active ngrok.service >/dev/null 2>&1 && echo -e "  ${GREEN}✓ Running${NC}" || echo -e "  ${YELLOW}✓ Stopped${NC}"

echo ""
echo "Your site is still accessible at:"
echo -e "  ${BLUE}https://seistools.space${NC} (Cloudflare)"
echo ""
echo -e "${GREEN}Done! Ngrok has been disabled.${NC}"
echo ""
echo "To re-enable ngrok, run:"
echo "  bash /home/aerys/Documents/ANTAN3D/scripts/deployment/enable_ngrok.sh"
echo ""
