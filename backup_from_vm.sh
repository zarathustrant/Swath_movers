#!/bin/bash
# Pull PostgreSQL database backup from VM to local

PROJECT="antan-discord-bot"
ZONE="us-central1-a"
VM_NAME="discord-bot-vm"
LOCAL_BACKUP_DIR="/Users/oluseyioyetunde/SSH_VM/swath-movers/vm_backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$LOCAL_BACKUP_DIR"

echo "Pulling latest PostgreSQL backup from VM..."
gcloud compute scp --project=$PROJECT --zone=$ZONE $VM_NAME:~/swath-movers/backups/swath_movers_*.sql "$LOCAL_BACKUP_DIR/" 2>/dev/null || echo "No backup files found on VM"

# Find the most recent backup file
LATEST_BACKUP=$(ls -t "$LOCAL_BACKUP_DIR"/swath_movers_*.sql 2>/dev/null | head -1)

if [ -n "$LATEST_BACKUP" ]; then
    echo "✓ Latest backup saved to: $LATEST_BACKUP"
    # Keep only last 14 days locally
    find "$LOCAL_BACKUP_DIR" -name "swath_movers_*.sql" -type f -mtime +14 -delete
    echo "✓ Cleaned up local backups older than 14 days"
else
    echo "✗ No backup files found"
    exit 1
fi
