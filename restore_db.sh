#!/bin/bash
# Restore PostgreSQL database from backup

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKUP_DIR="$SCRIPT_DIR/backups"
DB_NAME="swath_movers"
DB_USER="oluseyioyetunde"
DB_HOST="localhost"
DB_PORT="5432"
LOG_FILE="$SCRIPT_DIR/restore.log"

# Log function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Check if backup directory exists
if [ ! -d "$BACKUP_DIR" ]; then
    log "ERROR: Backup directory not found: $BACKUP_DIR"
    exit 1
fi

# Find the most recent backup
LATEST_BACKUP=$(ls -t "$BACKUP_DIR"/swath_movers_*.sql 2>/dev/null | head -1)

if [ -z "$LATEST_BACKUP" ]; then
    log "ERROR: No backup files found in $BACKUP_DIR"
    exit 1
fi

log "Found latest backup: $LATEST_BACKUP"

# Check if PostgreSQL is running
if ! pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" > /dev/null 2>&1; then
    log "ERROR: PostgreSQL database is not accessible"
    exit 1
fi

# Confirm restore operation
read -p "Are you sure you want to restore from $LATEST_BACKUP? This will overwrite the current database (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log "Restore cancelled by user"
    exit 0
fi

log "Starting restore of PostgreSQL database: $DB_NAME"

# Drop and recreate database
log "Dropping existing database..."
dropdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME" 2>/dev/null || true

log "Creating fresh database..."
createdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME"

# Restore from backup
log "Restoring from backup..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$LATEST_BACKUP"

if [ $? -eq 0 ]; then
    log "SUCCESS: Database restored successfully from $LATEST_BACKUP"
else
    log "ERROR: Restore failed"
    exit 1
fi
