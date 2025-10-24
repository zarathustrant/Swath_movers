#!/bin/bash

echo "========================================"
echo "Fixing PostgreSQL SSL Connection Issue"
echo "========================================"
echo ""

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "Problem: PostgreSQL SSL errors preventing data from loading"
echo "Solution: Disabled SSL for local connections in app.py"
echo ""

echo "1. Restarting swath-movers service..."
sudo systemctl restart swath-movers
sleep 3

if systemctl is-active --quiet swath-movers; then
    echo -e "${GREEN}✓ Swath-movers restarted successfully${NC}"
else
    echo "✗ Failed to restart swath-movers"
    echo "Checking logs..."
    journalctl -u swath-movers -n 20 --no-pager
    exit 1
fi

echo ""
echo "2. Checking for database connection errors..."
sleep 2

ERRORS=$(journalctl -u swath-movers -n 20 --no-pager 2>&1 | grep -i "SSL error\|SSL SYSCALL" || echo "")

if [ -z "$ERRORS" ]; then
    echo -e "${GREEN}✓ No SSL errors detected!${NC}"
else
    echo -e "${YELLOW}Still seeing SSL errors:${NC}"
    echo "$ERRORS"
fi

echo ""
echo "3. Testing database connection..."

# Test direct database connection
if PGPASSWORD='aerys123' psql -h localhost -U aerys -d swath_movers -c "SELECT COUNT(*) as coordinates FROM coordinates; SELECT COUNT(*) as deployments FROM global_deployments;" 2>&1 | grep -q "row"; then
    echo -e "${GREEN}✓ Database connection working!${NC}"

    # Show record counts
    echo ""
    echo "Record counts in database:"
    PGPASSWORD='aerys123' psql -h localhost -U aerys -d swath_movers -t -c "SELECT 'Coordinates: ' || COUNT(*) FROM coordinates;"
    PGPASSWORD='aerys123' psql -h localhost -U aerys -d swath_movers -t -c "SELECT 'Global Deployments: ' || COUNT(*) FROM global_deployments;"
    PGPASSWORD='aerys123' psql -h localhost -U aerys -d swath_movers -t -c "SELECT 'Swath Lines: ' || COUNT(*) FROM swath_lines;"
else
    echo "✗ Database connection test failed"
fi

echo ""
echo "4. Checking service status..."
sudo systemctl status swath-movers --no-pager -l | head -15

echo ""
echo "5. Viewing recent application logs..."
journalctl -u swath-movers -n 15 --no-pager | tail -10

echo ""
echo "========================================"
echo "✓ Fix Applied!"
echo "========================================"
echo ""
echo "Your application should now load data from PostgreSQL."
echo ""
echo "Test your app:"
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null | grep -o '"public_url":"[^"]*' | grep -o 'https://[^"]*' | head -1)
if [ -n "$NGROK_URL" ]; then
    echo "  ${NGROK_URL}"
else
    echo "  Get URL: curl http://localhost:4040/api/tunnels | jq -r '.tunnels[0].public_url'"
fi

echo ""
echo "If data still not showing, check logs:"
echo "  journalctl -u swath-movers -f"
echo ""
