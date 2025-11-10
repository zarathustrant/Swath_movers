#!/bin/bash

# Fix Development Service
# Applies the corrected configuration

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "========================================"
echo "Fixing Development Service"
echo "========================================"
echo ""

echo "Copying fixed service file..."
sudo cp /tmp/swath-movers-dev-fixed.service /etc/systemd/system/swath-movers-dev.service
echo -e "${GREEN}✓ Service file updated${NC}"

echo ""
echo "Reloading systemd..."
sudo systemctl daemon-reload
echo -e "${GREEN}✓ Systemd reloaded${NC}"

echo ""
echo "Restarting development service..."
sudo systemctl restart swath-movers-dev
sleep 3

echo ""
echo "Checking status..."
if systemctl is-active --quiet swath-movers-dev.service; then
    echo -e "${GREEN}✓ Development service is running!${NC}"
    echo ""
    systemctl status swath-movers-dev.service --no-pager -l | head -10
    echo ""
    echo "========================================"
    echo "Testing connection..."
    echo "========================================"
    sleep 2
    echo -n "Development (port 8081): "
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8081)
    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "302" ] || [ "$HTTP_CODE" = "301" ]; then
        echo -e "${GREEN}✓ OK (HTTP $HTTP_CODE)${NC}"
    else
        echo -e "${YELLOW}⚠ HTTP $HTTP_CODE${NC}"
    fi
    echo ""
    echo -e "${GREEN}Success! Development service is ready.${NC}"
    echo ""
    echo "Test the polygon feature at:"
    echo -e "  ${BLUE}http://localhost:8081/postplot/1${NC}"
    echo ""
else
    echo -e "${YELLOW}✗ Service failed to start${NC}"
    echo ""
    echo "Checking logs..."
    journalctl -u swath-movers-dev -n 20 --no-pager
    echo ""
    echo "Error log:"
    tail -20 /var/log/swath-movers-dev-error.log
fi

echo ""
