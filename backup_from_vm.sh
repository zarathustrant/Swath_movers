#!/bin/bash
# Pull database backup from discord-bot-vm to local

PROJECT="antan-discord-bot"
ZONE="us-central1-a"
VM_NAME="discord-bot-vm"
LOCAL_BACKUP_DIR="/Users/oluseyioyetunde/SSH_VM/swath-movers/vm_backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$LOCAL_BACKUP_DIR"

echo "Pulling latest backup from VM..."
gcloud compute scp --project=$PROJECT --zone=$ZONE $VM_NAME:~/swath-movers/swath_movers.db "$LOCAL_BACKUP_DIR/swath_movers_$TIMESTAMP.db"

if [ $? -eq 0 ]; then
    echo "✓ Backup saved to: $LOCAL_BACKUP_DIR/swath_movers_$TIMESTAMP.db"
    # Keep only last 14 days locally
    find "$LOCAL_BACKUP_DIR" -name "swath_movers_*.db" -type f -mtime +14 -delete
    echo "✓ Cleaned up local backups older than 14 days"
else
    echo "✗ Backup failed"
    exit 1
fi
