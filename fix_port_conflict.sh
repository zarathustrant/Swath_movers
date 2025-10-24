#!/bin/bash

echo "========================================"
echo "Fixing Port 80 Conflict"
echo "========================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "Problem: Apache2 is using port 80, blocking Nginx"
echo ""
echo "Solution: Stopping Apache2 and starting Nginx"
echo ""

# Stop Apache2
echo "1. Stopping Apache2..."
sudo systemctl stop apache2
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Apache2 stopped${NC}"
else
    echo -e "${RED}✗ Failed to stop Apache2${NC}"
    exit 1
fi

# Disable Apache2 from auto-starting
echo "2. Disabling Apache2 auto-start..."
sudo systemctl disable apache2
echo -e "${GREEN}✓ Apache2 disabled${NC}"

# Verify port 80 is free
echo "3. Verifying port 80 is free..."
sleep 1
PORT_CHECK=$(sudo lsof -i :80 2>/dev/null)
if [ -z "$PORT_CHECK" ]; then
    echo -e "${GREEN}✓ Port 80 is now free${NC}"
else
    echo -e "${RED}✗ Port 80 still in use${NC}"
    echo "$PORT_CHECK"
    exit 1
fi

# Start Nginx
echo "4. Starting Nginx..."
sudo systemctl start nginx
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Nginx started successfully${NC}"
else
    echo -e "${RED}✗ Failed to start Nginx${NC}"
    sudo journalctl -u nginx -n 10 --no-pager
    exit 1
fi

# Check Nginx status
echo "5. Checking Nginx status..."
sleep 1
sudo systemctl status nginx --no-pager -l | head -15

echo ""
echo "========================================"
echo "✓ Port conflict resolved!"
echo "========================================"
echo ""
echo "Nginx is now running on port 80"
echo ""
echo "Test it:"
echo "  curl http://localhost/"
echo ""

# Check if swath-movers is running
if systemctl is-active --quiet swath-movers; then
    echo -e "${GREEN}✓ Swath-movers is running${NC}"
else
    echo -e "${YELLOW}Note: Swath-movers service is not running${NC}"
    echo "Start it with: sudo systemctl start swath-movers"
fi

# Check if ngrok is running
if systemctl is-active --quiet ngrok; then
    echo -e "${GREEN}✓ Ngrok is running${NC}"
    echo ""
    echo "Getting ngrok URL..."
    sleep 2
    NGROK_URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null | grep -o '"public_url":"[^"]*' | grep -o 'https://[^"]*' | head -1)
    if [ -n "$NGROK_URL" ]; then
        echo -e "${GREEN}Your app is accessible at:${NC}"
        echo -e "${GREEN}${NGROK_URL}${NC}"
    fi
else
    echo -e "${YELLOW}Note: Ngrok service is not running${NC}"
    echo "Start it with: sudo systemctl start ngrok"
fi

echo ""
