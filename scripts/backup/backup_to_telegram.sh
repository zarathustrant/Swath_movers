#!/bin/bash

# PostgreSQL Database Backup to Telegram
# Backs up database and sends to multiple Telegram chat IDs

set -e

echo "========================================"
echo "PostgreSQL Database Backup to Telegram"
echo "========================================"
echo ""

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Load environment variables from .env
ENV_FILE="/home/aerys/Documents/ANTAN3D/.env"

if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}Error: .env file not found!${NC}"
    exit 1
fi

# Load .env file
export $(grep -v '^#' "$ENV_FILE" | xargs)

# Check if Telegram credentials are configured
if [ -z "$TELEGRAM_BOT_TOKEN" ] || [ -z "$TELEGRAM_CHAT_ID_1" ] || [ -z "$TELEGRAM_CHAT_ID_2" ]; then
    echo -e "${YELLOW}Telegram credentials not found in .env!${NC}"
    echo ""
    echo "Please add the following to your .env file:"
    echo ""

    read -p "Enter your Telegram Bot Token: " BOT_TOKEN_INPUT
    read -p "Enter first Telegram Chat ID: " CHAT_ID_1_INPUT
    read -p "Enter second Telegram Chat ID: " CHAT_ID_2_INPUT

    # Append to .env file
    echo "" >> "$ENV_FILE"
    echo "# Telegram Backup Configuration (added by backup script)" >> "$ENV_FILE"
    echo "TELEGRAM_BOT_TOKEN=$BOT_TOKEN_INPUT" >> "$ENV_FILE"
    echo "TELEGRAM_CHAT_ID_1=$CHAT_ID_1_INPUT" >> "$ENV_FILE"
    echo "TELEGRAM_CHAT_ID_2=$CHAT_ID_2_INPUT" >> "$ENV_FILE"

    # Reload environment
    export TELEGRAM_BOT_TOKEN="$BOT_TOKEN_INPUT"
    export TELEGRAM_CHAT_ID_1="$CHAT_ID_1_INPUT"
    export TELEGRAM_CHAT_ID_2="$CHAT_ID_2_INPUT"

    echo -e "${GREEN}✓ Configuration saved to .env${NC}"
    echo ""
fi

# Set variables from environment
BOT_TOKEN="$TELEGRAM_BOT_TOKEN"
CHAT_ID_1="$TELEGRAM_CHAT_ID_1"
CHAT_ID_2="$TELEGRAM_CHAT_ID_2"

# Backup settings
BACKUP_DIR="/home/aerys/Documents/ANTAN3D/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/swath_movers_backup_$TIMESTAMP.sql"
BACKUP_ARCHIVE="$BACKUP_DIR/swath_movers_backup_$TIMESTAMP.sql.gz"

# Create backup directory
mkdir -p "$BACKUP_DIR"

echo "1. Creating PostgreSQL backup..."
if PGPASSWORD='aerys123' pg_dump -h localhost -U aerys -d swath_movers > "$BACKUP_FILE" 2>/dev/null; then
    echo -e "${GREEN}✓ Database backup created${NC}"

    # Get database stats
    COORDS=$(PGPASSWORD='aerys123' psql -h localhost -U aerys -d swath_movers -t -c "SELECT COUNT(*) FROM coordinates;" 2>/dev/null | tr -d ' ')
    DEPLOYS=$(PGPASSWORD='aerys123' psql -h localhost -U aerys -d swath_movers -t -c "SELECT COUNT(*) FROM global_deployments;" 2>/dev/null | tr -d ' ')
    USERS=$(PGPASSWORD='aerys123' psql -h localhost -U aerys -d swath_movers -t -c "SELECT COUNT(*) FROM users;" 2>/dev/null | tr -d ' ')
else
    echo -e "${RED}✗ Backup failed${NC}"
    exit 1
fi

echo ""
echo "2. Compressing backup..."
gzip "$BACKUP_FILE"
BACKUP_SIZE=$(du -h "$BACKUP_ARCHIVE" | cut -f1)
echo -e "${GREEN}✓ Backup compressed: $BACKUP_SIZE${NC}"

echo ""
echo "3. Preparing backup message..."
CAPTION="🗄️ *Swath Movers Database Backup*

📅 Date: $(date '+%Y-%m-%d %H:%M:%S')
💾 Size: $BACKUP_SIZE

📊 *Database Statistics:*
• Coordinates: $COORDS
• Deployments: $DEPLOYS
• Users: $USERS

✅ Backup completed successfully!"

echo ""
echo "4. Sending to Telegram (Chat ID: $CHAT_ID_1)..."

# Send to first chat ID
RESPONSE=$(curl -s -X POST "https://api.telegram.org/bot$BOT_TOKEN/sendDocument" \
    -F chat_id="$CHAT_ID_1" \
    -F document=@"$BACKUP_ARCHIVE" \
    -F caption="$CAPTION" \
    -F parse_mode="Markdown")

if echo "$RESPONSE" | grep -q '"ok":true'; then
    echo -e "${GREEN}✓ Sent to Chat ID: $CHAT_ID_1${NC}"
else
    echo -e "${RED}✗ Failed to send to Chat ID: $CHAT_ID_1${NC}"
    echo "Response: $RESPONSE"
fi

echo ""
echo "5. Sending to Telegram (Chat ID: $CHAT_ID_2)..."

# Send to second chat ID
RESPONSE=$(curl -s -X POST "https://api.telegram.org/bot$BOT_TOKEN/sendDocument" \
    -F chat_id="$CHAT_ID_2" \
    -F document=@"$BACKUP_ARCHIVE" \
    -F caption="$CAPTION" \
    -F parse_mode="Markdown")

if echo "$RESPONSE" | grep -q '"ok":true'; then
    echo -e "${GREEN}✓ Sent to Chat ID: $CHAT_ID_2${NC}"
else
    echo -e "${RED}✗ Failed to send to Chat ID: $CHAT_ID_2${NC}"
    echo "Response: $RESPONSE"
fi

echo ""
echo "6. Cleanup old backups (keeping last 7 days)..."
find "$BACKUP_DIR" -name "swath_movers_backup_*.sql.gz" -mtime +7 -delete
echo -e "${GREEN}✓ Old backups cleaned${NC}"

echo ""
echo "========================================"
echo "✓ Backup Complete!"
echo "========================================"
echo ""
echo "Backup file: $BACKUP_ARCHIVE"
echo "Sent to 2 Telegram recipients"
echo ""

# Summary
BACKUP_COUNT=$(ls -1 "$BACKUP_DIR"/swath_movers_backup_*.sql.gz 2>/dev/null | wc -l)
echo "Total backups stored locally: $BACKUP_COUNT"
echo ""
