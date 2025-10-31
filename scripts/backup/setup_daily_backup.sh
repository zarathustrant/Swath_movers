#!/bin/bash

echo "========================================"
echo "Setup Automated Daily Backup to Telegram"
echo "========================================"
echo ""

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "This will set up automatic daily backups at 2 AM"
echo ""

# Make backup script executable
chmod +x /home/aerys/Documents/ANTAN3D/backup_to_telegram.sh

echo "1. Creating cron job for daily backup..."

# Create cron job (runs daily at 2 AM)
CRON_JOB="0 2 * * * /home/aerys/Documents/ANTAN3D/backup_to_telegram.sh >> /home/aerys/Documents/ANTAN3D/logs/telegram_backup.log 2>&1"

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "backup_to_telegram.sh"; then
    echo -e "${YELLOW}Cron job already exists${NC}"
else
    # Add to crontab
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo -e "${GREEN}✓ Daily backup cron job created${NC}"
fi

echo ""
echo "2. Current cron jobs:"
crontab -l | grep backup

echo ""
echo "========================================"
echo "✓ Setup Complete!"
echo "========================================"
echo ""
echo "Automated backup schedule:"
echo "  • Time: 2:00 AM daily"
echo "  • Database: swath_movers"
echo "  • Recipients: 2 Telegram accounts"
echo "  • Retention: 7 days local storage"
echo ""
echo "Manual backup:"
echo "  bash backup_to_telegram.sh"
echo ""
echo "View backup logs:"
echo "  tail -f logs/telegram_backup.log"
echo ""
echo "Remove automated backup:"
echo "  crontab -e  (then delete the backup line)"
echo ""
