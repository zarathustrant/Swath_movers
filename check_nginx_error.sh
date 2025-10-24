#!/bin/bash
echo "Checking Nginx configuration and errors..."
echo ""
echo "1. Testing Nginx config:"
sudo /usr/sbin/nginx -t
echo ""
echo "2. Nginx status:"
sudo systemctl status nginx --no-pager -l | head -20
echo ""
echo "3. Recent Nginx errors:"
sudo journalctl -u nginx -n 20 --no-pager
echo ""
echo "4. Checking if port 80 is in use:"
sudo lsof -i :80
