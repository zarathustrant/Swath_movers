#!/bin/bash

# Verify Cloudflare CDN Setup

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

DOMAIN="seistools.space"

echo "========================================="
echo "Cloudflare CDN Verification"
echo "========================================="
echo ""

echo "1. Checking DNS Resolution:"
echo "-------------------------"
dig +short $DOMAIN | head -3
echo ""

echo "2. Testing HTTPS Connection:"
echo "-------------------------"
echo -n "Status: "
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" https://$DOMAIN)
if [ "$HTTP_CODE" == "200" ] || [ "$HTTP_CODE" == "302" ]; then
    echo -e "${GREEN}✓ $HTTP_CODE OK${NC}"
else
    echo -e "${YELLOW}$HTTP_CODE${NC}"
fi
echo ""

echo "3. Cloudflare CDN Detection:"
echo "-------------------------"
curl -sI https://$DOMAIN | grep -E "(cf-|server:|cache)" | while read line; do
    if echo "$line" | grep -q "cf-"; then
        echo -e "${GREEN}✓ $line${NC}"
    else
        echo "  $line"
    fi
done
echo ""

echo "4. SSL Certificate:"
echo "-------------------------"
echo | openssl s_client -servername $DOMAIN -connect $DOMAIN:443 2>/dev/null | openssl x509 -noout -issuer -dates 2>/dev/null || echo "Could not verify certificate"
echo ""

echo "5. Local Services Status:"
echo "-------------------------"
echo -n "Cloudflared: "
systemctl is-active cloudflared.service && echo -e "${GREEN}✓ Running${NC}" || echo "✗ Not running"

echo -n "Swath Movers: "
systemctl is-active swath-movers.service && echo -e "${GREEN}✓ Running${NC}" || echo "✗ Not running"

echo -n "Nginx: "
systemctl is-active nginx.service && echo -e "${GREEN}✓ Running${NC}" || echo "✗ Not running"
echo ""

echo "========================================="
echo "Your Site URLs:"
echo "========================================="
echo -e "${BLUE}https://seistools.space${NC}"
echo -e "${BLUE}https://www.seistools.space${NC}"
echo ""

echo "========================================="
echo "Cloudflare Dashboard:"
echo "========================================="
echo "https://dash.cloudflare.com/"
echo ""
echo "Check these tabs:"
echo "  • Analytics → Traffic"
echo "  • Caching → Configuration"
echo "  • SSL/TLS → Overview (set to Flexible)"
echo "  • Speed → Optimization"
echo ""
