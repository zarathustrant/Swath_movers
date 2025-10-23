#!/bin/bash
# Deploy swath-movers to discord-bot-vm

set -e  # Exit on error

# Configuration
PROJECT="antan-discord-bot"
ZONE="us-central1-a"
VM_NAME="discord-bot-vm"
VM_USER=$(whoami)
REMOTE_DIR="/home/$VM_USER/swath-movers"
LOCAL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✓${NC} $1"
}

error() {
    echo -e "${RED}✗${NC} $1"
    exit 1
}

warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Check if gcloud is configured correctly
log "Checking gcloud configuration..."
CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null)
if [ "$CURRENT_PROJECT" != "$PROJECT" ]; then
    warning "Switching to project: $PROJECT"
    gcloud config set project $PROJECT
fi
success "Project: $PROJECT"

# Check if VM is running
log "Checking VM status..."
VM_STATUS=$(gcloud compute instances describe $VM_NAME --zone=$ZONE --format="get(status)" 2>/dev/null || echo "NOT_FOUND")
if [ "$VM_STATUS" != "RUNNING" ]; then
    error "VM $VM_NAME is not running (Status: $VM_STATUS)"
fi
success "VM is running"

# Get external IP
EXTERNAL_IP=$(gcloud compute instances describe $VM_NAME --zone=$ZONE --format="get(networkInterfaces[0].accessConfigs[0].natIP)")
success "External IP: $EXTERNAL_IP"

# Create archive excluding unnecessary files
log "Creating deployment archive..."
cd "$LOCAL_DIR"
tar -czf /tmp/swath-movers-deploy.tar.gz \
    --exclude='swathenv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.git' \
    --exclude='backups' \
    --exclude='*.log' \
    --exclude='.DS_Store' \
    --exclude='*.db' \
    --exclude='vm_backups' \
    --exclude='swath-movers-deploy.tar.gz' \
    .
success "Archive created"

# Upload to VM
log "Uploading to VM..."
gcloud compute scp /tmp/swath-movers-deploy.tar.gz $VM_NAME:/tmp/ --zone=$ZONE
success "Upload complete"

# Deploy on VM
log "Deploying application on VM..."
gcloud compute ssh $VM_NAME --zone=$ZONE --command="bash -s" << 'ENDSSH'
set -e

# Create directory
mkdir -p ~/swath-movers
cd ~/swath-movers

# Extract archive
echo "Extracting files..."
tar -xzf /tmp/swath-movers-deploy.tar.gz
rm /tmp/swath-movers-deploy.tar.gz

# Create virtual environment if it doesn't exist
if [ ! -d "swathenv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv swathenv
fi

# Activate and install requirements
echo "Installing requirements..."
source swathenv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Stop existing gunicorn processes
echo "Stopping existing gunicorn processes..."
pkill -f "gunicorn.*swath-movers" || true
sleep 2

# Setup database backup
echo "Setting up PostgreSQL database backup..."
cat > ~/swath-movers/backup_db.sh << 'EOF'
#!/bin/bash
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKUP_DIR="$SCRIPT_DIR/backups"
DB_NAME="swath_movers"
DB_USER="postgres"
DB_HOST="localhost"
DB_PORT="5432"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/swath_movers_$TIMESTAMP.sql"
LOG_FILE="$SCRIPT_DIR/backup.log"

mkdir -p "$BACKUP_DIR"

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
    find "$BACKUP_DIR" -name "swath_movers_*.sql" -type f -mtime +30 -delete
    log "Cleaned up backups older than 30 days"
    BACKUP_COUNT=$(ls -1 "$BACKUP_DIR"/swath_movers_*.sql 2>/dev/null | wc -l)
    log "Total backups: $BACKUP_COUNT"
else
    log "ERROR: Backup failed"
    exit 1
fi
EOF

chmod +x ~/swath-movers/backup_db.sh
mkdir -p ~/swath-movers/backups

# Setup cron job for VM backup
(crontab -l 2>/dev/null | grep -v backup_db.sh; echo "0 2 * * * ~/swath-movers/backup_db.sh >> ~/swath-movers/backup_cron.log 2>&1") | crontab -

# Run migrations
echo "Running migrations..."
cd ~/swath-movers
source swathenv/bin/activate
python app.py

# Start gunicorn in background
echo "Starting gunicorn..."
nohup ~/swath-movers/swathenv/bin/gunicorn -b 0.0.0.0:8080 -w 4 --chdir ~/swath-movers app:app > ~/swath-movers/gunicorn.log 2>&1 &

# Wait a moment and check if it started
sleep 3
if pgrep -f "gunicorn.*app:app" > /dev/null; then
    echo "✓ Gunicorn started successfully"
    echo "✓ PID: $(pgrep -f 'gunicorn.*app:app' | head -1)"
else
    echo "✗ Gunicorn failed to start"
    exit 1
fi

ENDSSH

success "Deployment complete"

# Clean up local temp file
rm /tmp/swath-movers-deploy.tar.gz

# Show status
log "Application Status:"
echo ""
echo "  🌐 External URL: http://$EXTERNAL_IP:8080"
echo "  🖥️  VM Name: $VM_NAME"
echo "  📍 Zone: $ZONE"
echo "  💾 Database backups: ~/swath-movers/backups (on VM)"
echo ""

# Setup local backup script
log "Setting up local backup from VM..."
cat > "$LOCAL_DIR/backup_from_vm.sh" << EOF
#!/bin/bash
# Pull PostgreSQL database backup from VM to local

PROJECT="$PROJECT"
ZONE="$ZONE"
VM_NAME="$VM_NAME"
LOCAL_BACKUP_DIR="$LOCAL_DIR/vm_backups"
TIMESTAMP=\$(date +%Y%m%d_%H%M%S)

mkdir -p "\$LOCAL_BACKUP_DIR"

echo "Pulling latest PostgreSQL backup from VM..."
gcloud compute scp --project=\$PROJECT --zone=\$ZONE \$VM_NAME:~/swath-movers/backups/swath_movers_*.sql "\$LOCAL_BACKUP_DIR/" 2>/dev/null || echo "No backup files found on VM"

# Find the most recent backup file
LATEST_BACKUP=\$(ls -t "\$LOCAL_BACKUP_DIR"/swath_movers_*.sql 2>/dev/null | head -1)

if [ -n "\$LATEST_BACKUP" ]; then
    echo "✓ Latest backup saved to: \$LATEST_BACKUP"
    # Keep only last 14 days locally
    find "\$LOCAL_BACKUP_DIR" -name "swath_movers_*.sql" -type f -mtime +14 -delete
    echo "✓ Cleaned up local backups older than 14 days"
else
    echo "✗ No backup files found"
    exit 1
fi
EOF

chmod +x "$LOCAL_DIR/backup_from_vm.sh"
success "Local backup script created: $LOCAL_DIR/backup_from_vm.sh"

# Setup local backup cron
log "Setting up daily local backup at 3 AM..."
(crontab -l 2>/dev/null | grep -v backup_from_vm.sh; echo "0 3 * * * $LOCAL_DIR/backup_from_vm.sh >> $LOCAL_DIR/vm_backup.log 2>&1") | crontab -
success "Local backup cron job added"

echo ""
success "🎉 Deployment Complete!"
echo ""
echo "Access your app at: ${GREEN}http://$EXTERNAL_IP:8080${NC}"
echo ""
echo "Useful commands:"
echo "  • View logs: gcloud compute ssh $VM_NAME --zone=$ZONE --command='tail -f ~/swath-movers/gunicorn.log'"
echo "  • Restart app: gcloud compute ssh $VM_NAME --zone=$ZONE --command='pkill -f gunicorn && cd ~/swath-movers && nohup swathenv/bin/gunicorn -b 0.0.0.0:8080 -w 4 app:app > gunicorn.log 2>&1 &'"
echo "  • Backup now: ./backup_from_vm.sh"
echo "  • SSH to VM: gcloud compute ssh $VM_NAME --zone=$ZONE"
echo ""
