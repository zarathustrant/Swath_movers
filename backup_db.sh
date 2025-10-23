#!/bin/bash
# Daily backup script for PostgreSQL database

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKUP_DIR="$SCRIPT_DIR/backups"
DB_NAME="swath_movers"
DB_USER="oluseyioyetunde"
DB_HOST="localhost"
DB_PORT="5432"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/swath_movers_$TIMESTAMP.sql"
LOG_FILE="$SCRIPT_DIR/backup.log"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Log function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Check if PostgreSQL is running
if ! pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" > /dev/null 2>&1; then
    log "ERROR: PostgreSQL database is not accessible"
    exit 1
fi

log "Starting backup of PostgreSQL database: $DB_NAME"

# Create PostgreSQL backup using pg_dump
pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$BACKUP_FILE" --no-owner --no-privileges --clean --if-exists

if [ $? -eq 0 ]; then
    DB_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    log "SUCCESS: Backup created at $BACKUP_FILE (Size: $DB_SIZE)"

    # Keep only last 30 days of backups
    find "$BACKUP_DIR" -name "swath_movers_*.sql" -type f -mtime +30 -delete
    log "Cleaned up backups older than 30 days"

    # Count remaining backups
    BACKUP_COUNT=$(ls -1 "$BACKUP_DIR"/swath_movers_*.sql 2>/dev/null | wc -l)
    log "Total backups: $BACKUP_COUNT"
else
    log "ERROR: Backup failed"
    exit 1
fi
