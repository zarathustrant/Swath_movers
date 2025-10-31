#!/bin/bash

echo "========================================"
echo "Starting PostgreSQL 15 Cluster"
echo "========================================"
echo ""

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "Current cluster status:"
pg_lsclusters

echo ""
echo "1. Starting PostgreSQL cluster..."
sudo pg_ctlcluster 15 main start

sleep 3

echo ""
echo "2. Checking cluster status..."
pg_lsclusters

if pg_isready -h localhost -p 5432 >/dev/null 2>&1; then
    echo -e "${GREEN}✓ PostgreSQL cluster is now running${NC}"
else
    echo -e "${RED}✗ PostgreSQL cluster failed to start${NC}"
    echo ""
    echo "Check logs:"
    echo "  sudo tail -50 /var/log/postgresql/postgresql-15-main.log"
    exit 1
fi

echo ""
echo "3. Testing database connection..."
if PGPASSWORD='aerys123' psql -h localhost -U aerys -d swath_movers -c "SELECT COUNT(*) FROM coordinates;" >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Database connection successful${NC}"

    echo ""
    echo "Record counts:"
    PGPASSWORD='aerys123' psql -h localhost -U aerys -d swath_movers -t -c "SELECT 'Coordinates: ' || COUNT(*) FROM coordinates;"
    PGPASSWORD='aerys123' psql -h localhost -U aerys -d swath_movers -t -c "SELECT 'Deployments: ' || COUNT(*) FROM global_deployments;"
else
    echo -e "${RED}✗ Database connection failed${NC}"
    exit 1
fi

echo ""
echo "4. Restarting swath-movers service..."
sudo systemctl restart swath-movers
sleep 5

if systemctl is-active --quiet swath-movers; then
    echo -e "${GREEN}✓ Swath-movers started successfully${NC}"
else
    echo -e "${YELLOW}Checking swath-movers status...${NC}"
    sudo systemctl status swath-movers --no-pager -l | head -15
fi

echo ""
echo "5. Testing Flask application..."
sleep 3
if curl -s http://localhost:8080/ >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Flask app is responding${NC}"
else
    echo -e "${YELLOW}Flask app might still be starting up...${NC}"
fi

echo ""
echo "6. Checking ngrok..."
if systemctl is-active --quiet ngrok; then
    echo -e "${GREEN}✓ Ngrok is running${NC}"

    echo ""
    echo "Your ngrok URL:"
    sleep 2
    NGROK_URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null | python3 -m json.tool 2>/dev/null | grep -o 'https://[^"]*ngrok[^"]*' | head -1)
    if [ -n "$NGROK_URL" ]; then
        echo -e "${GREEN}${NGROK_URL}${NC}"
    else
        echo "Getting URL..."
        curl -s http://localhost:4040/api/tunnels | python3 -m json.tool | grep "public_url" | head -1
    fi
else
    echo -e "${YELLOW}Ngrok not running, starting it...${NC}"
    sudo systemctl restart ngrok
    sleep 3
    echo -e "${GREEN}✓ Ngrok restarted${NC}"
fi

echo ""
echo "========================================"
echo "✓ Setup Complete!"
echo "========================================"
echo ""
echo "All services should now be running."
echo ""
echo "Useful commands:"
echo "  journalctl -u swath-movers -f    # View Flask logs"
echo "  journalctl -u ngrok -f           # View ngrok logs"
echo "  pg_lsclusters                    # Check PostgreSQL status"
echo ""
