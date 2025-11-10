#!/bin/bash

# Setup Development Environment for Testing New Features
# This creates a separate service running on port 8081 for testing

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

APP_DIR="/home/aerys/Documents/ANTAN3D"
VENV_DIR="$APP_DIR/venv"

echo "========================================"
echo "Development Environment Setup"
echo "========================================"
echo ""

echo -e "${BLUE}This will create:${NC}"
echo "  • Separate systemd service on port 8081"
echo "  • Uses same database (safe for testing)"
echo "  • Uses same virtual environment"
echo "  • Perfect for testing new features"
echo ""

# Create dev systemd service
echo "Creating swath-movers-dev.service..."
cat > /tmp/swath-movers-dev.service << EOF
[Unit]
Description=Swath Movers Application (Development)
After=network.target postgresql.service

[Service]
Type=notify
User=$(whoami)
Group=$(whoami)
WorkingDirectory=$APP_DIR
Environment="PATH=$VENV_DIR/bin"
Environment="FLASK_ENV=development"
Environment="FLASK_DEBUG=1"

# Run on different port (8081)
ExecStart=$VENV_DIR/bin/gunicorn \\
    --bind 127.0.0.1:8081 \\
    --workers 2 \\
    --worker-class gevent \\
    --timeout 300 \\
    --access-logfile /var/log/swath-movers-dev-access.log \\
    --error-logfile /var/log/swath-movers-dev-error.log \\
    --log-level debug \\
    app:app

Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

sudo cp /tmp/swath-movers-dev.service /etc/systemd/system/
echo -e "${GREEN}✓ Development service created${NC}"

echo ""
echo "Creating log files..."
sudo touch /var/log/swath-movers-dev-access.log
sudo touch /var/log/swath-movers-dev-error.log
sudo chown $(whoami):$(whoami) /var/log/swath-movers-dev-access.log
sudo chown $(whoami):$(whoami) /var/log/swath-movers-dev-error.log
echo -e "${GREEN}✓ Log files created${NC}"

echo ""
echo "Enabling and starting development service..."
sudo systemctl daemon-reload
sudo systemctl enable swath-movers-dev.service
sudo systemctl start swath-movers-dev.service

sleep 2

if systemctl is-active --quiet swath-movers-dev.service; then
    echo -e "${GREEN}✓ Development service started successfully${NC}"
else
    echo -e "${RED}✗ Development service failed to start${NC}"
    echo "Check logs with: journalctl -u swath-movers-dev -n 50"
    exit 1
fi

echo ""
echo "========================================"
echo "Development Environment Ready!"
echo "========================================"
echo ""

echo "Service Status:"
echo "---------------"
systemctl status swath-movers-dev.service --no-pager -l | head -8
echo ""

echo "Testing Connections:"
echo "-------------------"
echo -n "Production (port 8080): "
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080 && echo "✓ OK" || echo "✗ FAIL"
echo -n "Development (port 8081): "
curl -s -o /dev/null -w "%{http_code}" http://localhost:8081 && echo "✓ OK" || echo "✗ FAIL"
echo ""

echo "========================================"
echo "How to Use:"
echo "========================================"
echo ""
echo "1. Production (seistools.space):"
echo "   URL: https://seistools.space"
echo "   Port: 8080 (via Cloudflare)"
echo "   Service: swath-movers.service"
echo ""
echo "2. Development (local testing):"
echo "   URL: http://localhost:8081"
echo "   Service: swath-movers-dev.service"
echo ""
echo "3. Test with ngrok (optional):"
echo "   Run: ngrok http 8081"
echo "   Get temporary public URL for testing"
echo ""
echo "========================================"
echo "Quick Commands:"
echo "========================================"
echo ""
echo "View dev logs:"
echo "  journalctl -u swath-movers-dev -f"
echo ""
echo "Restart dev service:"
echo "  sudo systemctl restart swath-movers-dev"
echo ""
echo "Stop dev service:"
echo "  sudo systemctl stop swath-movers-dev"
echo ""
echo "View both services:"
echo "  systemctl status swath-movers.service swath-movers-dev.service"
echo ""
echo -e "${GREEN}Done! Development environment is ready.${NC}"
echo ""
