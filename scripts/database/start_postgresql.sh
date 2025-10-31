#!/bin/bash

echo "========================================"
echo "Starting PostgreSQL Database"
echo "========================================"
echo ""

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "1. Starting PostgreSQL service..."
sudo systemctl start postgresql

sleep 2

if pg_isready -h localhost -p 5432 >/dev/null 2>&1; then
    echo -e "${GREEN}✓ PostgreSQL is now running${NC}"
else
    echo -e "${RED}✗ PostgreSQL failed to start${NC}"
    echo "Checking status..."
    sudo systemctl status postgresql --no-pager -l | head -20
    exit 1
fi

echo ""
echo "2. Testing database connection..."
if PGPASSWORD='aerys123' psql -h localhost -U aerys -d swath_movers -c "SELECT 1;" >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Database connection successful${NC}"
else
    echo -e "${RED}✗ Database connection failed${NC}"
    exit 1
fi

echo ""
echo "3. Restarting swath-movers service..."
sudo systemctl restart swath-movers
sleep 5

if systemctl is-active --quiet swath-movers; then
    echo -e "${GREEN}✓ Swath-movers restarted${NC}"
else
    echo -e "${RED}✗ Swath-movers failed to start${NC}"
    journalctl -u swath-movers -n 10 --no-pager
    exit 1
fi

echo ""
echo "4. Checking ngrok..."
if systemctl is-active --quiet ngrok; then
    echo -e "${GREEN}✓ Ngrok is running${NC}"
else
    echo "Starting ngrok..."
    sudo systemctl restart ngrok
    sleep 3
fi

echo ""
echo "========================================"
echo "✓ All Services Running!"
echo "========================================"
echo ""

echo "Your ngrok URL:"
sleep 2
curl -s http://localhost:4040/api/tunnels 2>/dev/null | python3 -m json.tool | grep "public_url" | head -1

echo ""
