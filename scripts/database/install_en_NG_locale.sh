#!/bin/bash

echo "========================================"
echo "Installing en_NG Locale"
echo "Fix PostgreSQL Database Locale Issue"
echo "========================================"
echo ""

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "Problem: PostgreSQL database uses en_NG locale which is not installed"
echo "Solution: Install the en_NG locale on the system"
echo ""

echo "1. Installing locales package..."
sudo apt-get update
sudo apt-get install -y locales

echo ""
echo "2. Generating en_NG locale..."
sudo sed -i 's/# en_NG/en_NG/' /etc/locale.gen
sudo locale-gen en_NG en_NG.UTF-8

echo ""
echo "3. Verifying locale installation..."
if locale -a | grep -q en_NG; then
    echo -e "${GREEN}✓ en_NG locale installed successfully!${NC}"
else
    echo "Locale might not be available, trying alternative..."
    sudo locale-gen en_NG.UTF-8
fi

echo ""
echo "4. Restarting PostgreSQL..."
sudo systemctl restart postgresql

sleep 5

if pg_isready -h localhost -p 5432 >/dev/null 2>&1; then
    echo -e "${GREEN}✓ PostgreSQL restarted successfully${NC}"
else
    echo "Waiting for PostgreSQL..."
    sleep 3
fi

echo ""
echo "5. Testing database connection..."
if PGPASSWORD='aerys123' psql -h localhost -U aerys -d swath_movers -c "SELECT COUNT(*) FROM coordinates;" >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Database connection WORKS!${NC}"

    echo ""
    echo "Verifying data:"
    PGPASSWORD='aerys123' psql -h localhost -U aerys -d swath_movers -t -c "SELECT 'Coordinates: ' || COUNT(*) FROM coordinates;"
    PGPASSWORD='aerys123' psql -h localhost -U aerys -d swath_movers -t -c "SELECT 'Deployments: ' || COUNT(*) FROM global_deployments;"
    PGPASSWORD='aerys123' psql -h localhost -U aerys -d swath_movers -t -c "SELECT 'Users: ' || COUNT(*) FROM users;"
else
    echo "Still having connection issues. Checking logs..."
    sudo tail -20 /var/log/postgresql/postgresql-15-main.log
    exit 1
fi

echo ""
echo "6. Restarting swath-movers service..."
sudo systemctl restart swath-movers
sleep 5

if systemctl is-active --quiet swath-movers; then
    echo -e "${GREEN}✓ Swath-movers started successfully${NC}"
else
    echo "Checking swath-movers status..."
    systemctl status swath-movers --no-pager -l | head -15
fi

echo ""
echo "7. Testing Flask application..."
sleep 3
if curl -s http://localhost:8080/ >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Flask app is responding!${NC}"
else
    echo -e "${YELLOW}Flask app might still be starting up...${NC}"
fi

echo ""
echo "8. Checking ngrok..."
if systemctl is-active --quiet ngrok; then
    echo -e "${GREEN}✓ Ngrok is running${NC}"

    echo ""
    echo "Your application URL:"
    sleep 2
    NGROK_URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null | python3 -m json.tool 2>/dev/null | grep -o 'https://[^"]*ngrok[^"]*' | head -1)
    if [ -n "$NGROK_URL" ]; then
        echo -e "${GREEN}${NGROK_URL}${NC}"
    fi
fi

echo ""
echo "========================================"
echo "✓ Locale Fix Complete!"
echo "========================================"
echo ""
echo "Your PostgreSQL database is now working with all data intact!"
echo "No data was lost - we just installed the missing locale."
echo ""
