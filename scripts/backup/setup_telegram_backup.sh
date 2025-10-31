#!/bin/bash

echo "=========================================="
echo "Telegram Backup Service Setup"
echo "=========================================="
echo ""

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}❌ Don't run this as root/sudo${NC}"
    echo "Run as regular user: bash setup_telegram_backup.sh"
    exit 1
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ .env file not found${NC}"
    exit 1
fi

# Check if Telegram credentials are configured
source .env
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo -e "${YELLOW}⚠️  Telegram bot token not configured in .env${NC}"
    echo ""
    echo "Please add to .env:"
    echo "TELEGRAM_BOT_TOKEN=your_token_from_botfather"
    echo ""
    echo "Chat IDs will be auto-discovered when users message the bot"
    echo ""
    exit 1
fi

echo -e "${GREEN}✓ Configuration found${NC}"

# Install Python dependencies
echo ""
echo "Installing Python dependencies..."
pip install --user python-dotenv requests

# Make service script executable
chmod +x telegram_backup_service.py

echo ""
echo -e "${GREEN}✓ Python script configured${NC}"

# Install systemd service
echo ""
echo "Installing systemd service..."
sudo cp /tmp/telegram-backup.service /etc/systemd/system/
sudo systemctl daemon-reload

echo -e "${GREEN}✓ Systemd service installed${NC}"

# Enable and start service
echo ""
read -p "Do you want to enable auto-start on boot? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    sudo systemctl enable telegram-backup.service
    echo -e "${GREEN}✓ Service enabled for auto-start${NC}"
fi

echo ""
read -p "Do you want to start the service now? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    sudo systemctl start telegram-backup.service
    echo -e "${GREEN}✓ Service started${NC}"
fi

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Service Commands:"
echo "  Start:   sudo systemctl start telegram-backup"
echo "  Stop:    sudo systemctl stop telegram-backup"
echo "  Status:  sudo systemctl status telegram-backup"
echo "  Logs:    sudo journalctl -u telegram-backup -f"
echo ""
echo "Manual Backup:"
echo "  python3 telegram_backup_service.py --once"
echo ""
echo "The service will backup every 24 hours automatically."
echo ""
