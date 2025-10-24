#!/bin/bash

echo "========================================"
echo "Reverting to Simple Setup"
echo "Direct: Ngrok → Gunicorn → Flask"
echo "========================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "1. Stopping Nginx (if running)..."
sudo systemctl stop nginx 2>/dev/null || true
sudo systemctl disable nginx 2>/dev/null || true
echo -e "${GREEN}✓ Nginx stopped and disabled${NC}"

echo ""
echo "2. Restoring ngrok service to port 8080..."

# Create corrected ngrok service file pointing to 8080
cat > /tmp/ngrok-simple.service << 'EOF'
[Unit]
Description=Ngrok Tunnel for Swath Movers Application
Documentation=https://ngrok.com/docs
After=network.target swath-movers.service
Requires=swath-movers.service

[Service]
Type=simple
User=aerys
Group=aerys
WorkingDirectory=/home/aerys

# Start ngrok tunnel to port 8080 (Gunicorn directly)
ExecStart=/usr/local/bin/ngrok http 8080 --log=stdout --log-level=info

# Restart policy
Restart=always
RestartSec=5

# Security settings
PrivateTmp=true
NoNewPrivileges=true

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=ngrok

[Install]
WantedBy=multi-user.target
EOF

sudo cp /tmp/ngrok-simple.service /etc/systemd/system/ngrok.service
echo -e "${GREEN}✓ Ngrok service updated to port 8080${NC}"

echo ""
echo "3. Reloading systemd..."
sudo systemctl daemon-reload
echo -e "${GREEN}✓ Systemd reloaded${NC}"

echo ""
echo "4. Stopping existing services..."
sudo systemctl stop ngrok 2>/dev/null || true
sudo systemctl stop swath-movers 2>/dev/null || true
echo -e "${GREEN}✓ Services stopped${NC}"

echo ""
echo "5. Starting swath-movers (Gunicorn on port 8080)..."
sudo systemctl start swath-movers
sleep 3

if systemctl is-active --quiet swath-movers; then
    echo -e "${GREEN}✓ Swath-movers started successfully${NC}"
else
    echo -e "${RED}✗ Failed to start swath-movers${NC}"
    echo "Check logs: journalctl -u swath-movers -n 20"
    exit 1
fi

echo ""
echo "6. Starting ngrok (tunneling to port 8080)..."
sudo systemctl start ngrok
sleep 3

if systemctl is-active --quiet ngrok; then
    echo -e "${GREEN}✓ Ngrok started successfully${NC}"
else
    echo -e "${RED}✗ Failed to start ngrok${NC}"
    echo "Check logs: journalctl -u ngrok -n 20"
    exit 1
fi

echo ""
echo "========================================"
echo "✓ Revert Complete!"
echo "========================================"
echo ""

echo "Architecture:"
echo "  Internet → Ngrok → Gunicorn:8080 → Flask → PostgreSQL"
echo ""

echo "Service Status:"
echo "---------------"
sudo systemctl status swath-movers --no-pager -l | head -10
echo ""
sudo systemctl status ngrok --no-pager -l | head -10

echo ""
echo "Getting your ngrok URL..."
sleep 2

NGROK_URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null | grep -o '"public_url":"[^"]*' | grep -o 'https://[^"]*' | head -1)

if [ -n "$NGROK_URL" ]; then
    echo -e "${GREEN}Your application is accessible at:${NC}"
    echo -e "${GREEN}${NGROK_URL}${NC}"
else
    echo "Get URL with: curl http://localhost:4040/api/tunnels | jq -r '.tunnels[0].public_url'"
    echo "Or visit: http://localhost:4040"
fi

echo ""
echo "Quick Commands:"
echo "  journalctl -u swath-movers -f    # View Flask logs"
echo "  journalctl -u ngrok -f           # View ngrok logs"
echo ""
