#!/bin/bash

echo "Checking PostgreSQL error logs..."
echo ""

echo "1. PostgreSQL log file:"
sudo tail -50 /var/log/postgresql/postgresql-15-main.log

echo ""
echo "2. Systemd service status:"
sudo systemctl status postgresql@15-main --no-pager -l

echo ""
echo "3. Checking port 5432:"
sudo lsof -i :5432 || echo "Port 5432 is free"

echo ""
echo "4. Checking PostgreSQL data directory:"
sudo ls -la /var/lib/postgresql/15/main/ | head -10
