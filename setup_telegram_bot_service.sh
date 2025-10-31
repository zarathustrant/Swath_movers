#!/bin/bash

echo "=========================================="
echo "Telegram Bot Service Setup"
echo "=========================================="
echo ""

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}❌ Don't run this as root/sudo${NC}"
    echo "Run as regular user: bash setup_telegram_bot_service.sh"
    exit 1
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ .env file not found${NC}"
    exit 1
fi

# Check if bot token is configured
source .env
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo -e "${YELLOW}⚠️  TELEGRAM_BOT_TOKEN not configured in .env${NC}"
    echo ""
    echo "Please add to .env:"
    echo "TELEGRAM_BOT_TOKEN=your_bot_token_here"
    echo ""
    exit 1
fi

echo -e "${GREEN}✓ Configuration found${NC}"

# Install Python dependencies
echo ""
echo "Installing Python dependencies..."
pip install --user python-dotenv requests matplotlib pillow

echo ""
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Make script executable
chmod +x telegram_bot.py

echo ""
echo -e "${GREEN}✓ Script configured${NC}"

# Install systemd service
echo ""
echo "Installing systemd service..."
sudo cp /tmp/telegram-bot.service /etc/systemd/system/
sudo systemctl daemon-reload

echo -e "${GREEN}✓ Systemd service installed${NC}"

# Enable and start service
echo ""
read -p "Do you want to enable auto-start on boot? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    sudo systemctl enable telegram-bot.service
    echo -e "${GREEN}✓ Service enabled for auto-start${NC}"
fi

echo ""
read -p "Do you want to start the service now? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    sudo systemctl start telegram-bot.service
    echo -e "${GREEN}✓ Service started${NC}"
    echo ""
    echo "Checking service status..."
    sleep 2
    sudo systemctl status telegram-bot.service --no-pager -l
fi

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Service Commands:"
echo "  Start:   sudo systemctl start telegram-bot"
echo "  Stop:    sudo systemctl stop telegram-bot"
echo "  Status:  sudo systemctl status telegram-bot"
echo "  Logs:    sudo journalctl -u telegram-bot -f"
echo ""
echo "Test the bot:"
echo "  Send /start to your bot on Telegram"
echo "  Try /stats to see project statistics"
echo ""
echo "Your bot is now running continuously!"
echo ""
