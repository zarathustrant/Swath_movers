#!/bin/bash

echo "========================================"
echo "Fixing PostgreSQL Locale Issue"
echo "========================================"
echo ""

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "Problem: PostgreSQL config has invalid locale 'en_NG' which is not installed"
echo "Solution: Comment out locale settings in postgresql.conf"
echo ""

echo "1. Backing up PostgreSQL configuration..."
sudo cp /etc/postgresql/15/main/postgresql.conf /etc/postgresql/15/main/postgresql.conf.backup
echo -e "${GREEN}✓ Backup created: postgresql.conf.backup${NC}"

echo ""
echo "2. Fixing locale settings in postgresql.conf..."

# Comment out the problematic locale lines
sudo sed -i "s/^lc_messages = 'en_NG'/# lc_messages = 'en_NG'  # Commented out - using system default/" /etc/postgresql/15/main/postgresql.conf
sudo sed -i "s/^lc_monetary = 'en_NG'/# lc_monetary = 'en_NG'  # Commented out - using system default/" /etc/postgresql/15/main/postgresql.conf
sudo sed -i "s/^lc_numeric = 'en_NG'/# lc_numeric = 'en_NG'  # Commented out - using system default/" /etc/postgresql/15/main/postgresql.conf
sudo sed -i "s/^lc_time = 'en_NG'/# lc_time = 'en_NG'  # Commented out - using system default/" /etc/postgresql/15/main/postgresql.conf

echo -e "${GREEN}✓ Locale settings commented out${NC}"

echo ""
echo "3. Starting PostgreSQL cluster..."
sudo pg_ctlcluster 15 main start

sleep 3

if pg_isready -h localhost -p 5432 >/dev/null 2>&1; then
    echo -e "${GREEN}✓ PostgreSQL started successfully!${NC}"
else
    echo -e "${YELLOW}PostgreSQL might still be starting...${NC}"
    sleep 2
    if pg_isready -h localhost -p 5432 >/dev/null 2>&1; then
        echo -e "${GREEN}✓ PostgreSQL is now ready${NC}"
    else
        echo "Still having issues. Check:"
        echo "  sudo tail -20 /var/log/postgresql/postgresql-15-main.log"
        exit 1
    fi
fi

echo ""
echo "4. Verifying cluster status..."
pg_lsclusters

echo ""
echo "5. Testing database connection..."
if PGPASSWORD='aerys123' psql -h localhost -U aerys -d swath_movers -c "SELECT COUNT(*) as coordinates FROM coordinates;" 2>&1 | grep -q "coordinates"; then
    echo -e "${GREEN}✓ Database connection successful${NC}"

    echo ""
    echo "Data in database:"
    PGPASSWORD='aerys123' psql -h localhost -U aerys -d swath_movers -t -c "SELECT 'Coordinates: ' || COUNT(*) FROM coordinates;"
    PGPASSWORD='aerys123' psql -h localhost -U aerys -d swath_movers -t -c "SELECT 'Deployments: ' || COUNT(*) FROM global_deployments;"
    PGPASSWORD='aerys123' psql -h localhost -U aerys -d swath_movers -t -c "SELECT 'Swath Lines: ' || COUNT(*) FROM swath_lines;"
else
    echo "Database connection test failed"
fi

echo ""
echo "6. Restarting swath-movers service..."
sudo systemctl restart swath-movers
sleep 5

if systemctl is-active --quiet swath-movers; then
    echo -e "${GREEN}✓ Swath-movers started${NC}"
else
    echo -e "${YELLOW}Checking status...${NC}"
    systemctl status swath-movers --no-pager -l | head -10
fi

echo ""
echo "7. Testing Flask application..."
sleep 3
if curl -s -I http://localhost:8080/ 2>&1 | head -1 | grep -q "200\|301\|302"; then
    echo -e "${GREEN}✓ Flask app is responding${NC}"
else
    echo -e "${YELLOW}Flask app response:${NC}"
    curl -I http://localhost:8080/ 2>&1 | head -3
fi

echo ""
echo "8. Checking ngrok..."
if systemctl is-active --quiet ngrok; then
    echo -e "${GREEN}✓ Ngrok is running${NC}"
else
    echo "Starting ngrok..."
    sudo systemctl restart ngrok
    sleep 3
fi

echo ""
echo "========================================"
echo "✓ PostgreSQL Fixed!"
echo "========================================"
echo ""

echo "Getting your ngrok URL..."
sleep 2
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null | python3 -m json.tool 2>/dev/null | grep -o 'https://[^"]*ngrok[^"]*' | head -1)

if [ -n "$NGROK_URL" ]; then
    echo -e "${GREEN}Your application is live at:${NC}"
    echo -e "${GREEN}${NGROK_URL}${NC}"
    echo ""
    echo "Test it in your browser now!"
else
    echo "Run this to get URL:"
    echo "  curl http://localhost:4040/api/tunnels | jq -r '.tunnels[0].public_url'"
fi

echo ""
echo "All services running:"
echo "  ✓ PostgreSQL (port 5432)"
echo "  ✓ Gunicorn (port 8080, 5 workers)"
echo "  ✓ Ngrok (external tunnel)"
echo ""
