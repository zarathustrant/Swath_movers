#!/bin/bash
# Daily backup script for swath_movers.db

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DB_FILE="$SCRIPT_DIR/swath_movers.db"
BACKUP_DIR="$SCRIPT_DIR/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/swath_movers_$TIMESTAMP.db"
LOG_FILE="$SCRIPT_DIR/backup.log"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Log function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Check if database exists
if [ ! -f "$DB_FILE" ]; then
    log "ERROR: Database file not found at $DB_FILE"
    exit 1
fi

log "Starting backup of swath_movers.db"

# Copy the database file
cp "$DB_FILE" "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    DB_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    log "SUCCESS: Backup created at $BACKUP_FILE (Size: $DB_SIZE)"

    # Keep only last 30 days of backups
    find "$BACKUP_DIR" -name "swath_movers_*.db" -type f -mtime +30 -delete
    log "Cleaned up backups older than 30 days"

    # Count remaining backups
    BACKUP_COUNT=$(ls -1 "$BACKUP_DIR"/swath_movers_*.db 2>/dev/null | wc -l)
    log "Total backups: $BACKUP_COUNT"
else
    log "ERROR: Backup failed"
    exit 1
fi
