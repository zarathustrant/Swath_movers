# Scripts Directory

This directory contains all shell scripts organized by category.

## Directory Structure

```
scripts/
├── backup/              # Database backup and restore scripts
├── database/            # PostgreSQL setup and management scripts
├── deployment/          # Application deployment and service setup
├── maintenance/         # System maintenance scripts
└── troubleshooting/     # Debugging and error checking scripts
```

## Backup Scripts (`scripts/backup/`)

Scripts for backing up and restoring the database.

| Script | Description |
|--------|-------------|
| `backup_db.sh` | Manual database backup script |
| `backup_from_vm.sh` | Backup script for VM environment |
| `backup_to_telegram.sh` | Legacy bash script to send backups to Telegram |
| `export_to_sqlite_backup.sh` | Export PostgreSQL data to SQLite format |
| `restore_db.sh` | Restore database from backup |
| `setup_daily_backup.sh` | Setup cron job for daily backups |
| `setup_telegram_backup.sh` | Setup Python Telegram backup service |

**Usage:**
```bash
# Setup automated Telegram backups (recommended)
bash scripts/backup/setup_telegram_backup.sh

# Manual backup
bash scripts/backup/backup_db.sh

# Restore from backup
bash scripts/backup/restore_db.sh
```

## Database Scripts (`scripts/database/`)

Scripts for PostgreSQL setup, configuration, and troubleshooting.

| Script | Description |
|--------|-------------|
| `migrate_to_postgres.sh` | Migrate from SQLite to PostgreSQL |
| `install_en_NG_locale.sh` | Install missing en_NG locale (fixes startup issues) |
| `fix_postgres_locale.sh` | Fix PostgreSQL locale configuration |
| `start_postgresql.sh` | Start PostgreSQL service |
| `start_postgres_cluster.sh` | Start PostgreSQL cluster manually |
| `fix_database_connection.sh` | Fix database connection issues |
| `copydb.sh` | Copy database between environments |
| `set_locale.sh` | Set system locale configuration |

**Usage:**
```bash
# Install missing locale (if PostgreSQL won't start)
bash scripts/database/install_en_NG_locale.sh

# Migrate from SQLite to PostgreSQL
bash scripts/database/migrate_to_postgres.sh

# Start PostgreSQL
bash scripts/database/start_postgresql.sh
```

## Deployment Scripts (`scripts/deployment/`)

Scripts for deploying the application and setting up services.

| Script | Description |
|--------|-------------|
| `install_services.sh` | Install and configure systemd services |
| `deploy.sh` | Deploy application updates |
| `revert_to_simple.sh` | Revert to simple architecture (no Nginx) |
| `install_with_nginx.sh` | Install with Nginx reverse proxy |
| `install_with_nginx_auto.sh` | Automated Nginx installation |

**Usage:**
```bash
# Setup systemd services (swath-movers, ngrok, telegram-backup)
bash scripts/deployment/install_services.sh

# Deploy updates
bash scripts/deployment/deploy.sh

# Revert from Nginx to simple setup
bash scripts/deployment/revert_to_simple.sh
```

## Troubleshooting Scripts (`scripts/troubleshooting/`)

Scripts for diagnosing and fixing common issues.

| Script | Description |
|--------|-------------|
| `check_postgres_error.sh` | Check PostgreSQL error logs |
| `check_nginx_error.sh` | Check Nginx error logs |
| `fix_port_conflict.sh` | Fix port 80/8080 conflicts |

**Usage:**
```bash
# Check PostgreSQL logs for errors
bash scripts/troubleshooting/check_postgres_error.sh

# Fix port conflicts
bash scripts/troubleshooting/fix_port_conflict.sh
```

## Maintenance Scripts (`scripts/maintenance/`)

Future location for routine maintenance scripts.

Currently empty - maintenance tasks are handled by services:
- Database backups: `telegram_backup_service.py`
- Log rotation: systemd journal
- Old backup cleanup: built into backup service

## Important Notes

### File Paths
Some scripts may need path updates since they were moved. If a script fails with "file not found", you may need to:
1. Run it from the project root: `bash scripts/category/script.sh`
2. Or update internal paths in the script

### Service Files
Systemd service files are located in `/tmp/` and need to be copied to `/etc/systemd/system/`:
- `/tmp/swath-movers.service`
- `/tmp/ngrok.service`
- `/tmp/telegram-backup.service`

Use the installation scripts to set them up properly.

### Execution Permissions
All scripts in this directory should be executable. If not:
```bash
chmod +x scripts/backup/*.sh
chmod +x scripts/database/*.sh
chmod +x scripts/deployment/*.sh
chmod +x scripts/troubleshooting/*.sh
```

## Quick Start Guide

### First Time Setup

1. **Setup Database:**
```bash
# Install locale if needed
bash scripts/database/install_en_NG_locale.sh

# Or migrate from SQLite
bash scripts/database/migrate_to_postgres.sh
```

2. **Deploy Services:**
```bash
bash scripts/deployment/install_services.sh
```

3. **Setup Backups:**
```bash
# Add bot token to .env first
bash scripts/backup/setup_telegram_backup.sh
```

### Regular Operations

**Check Service Status:**
```bash
sudo systemctl status swath-movers
sudo systemctl status ngrok
sudo systemctl status telegram-backup
```

**View Logs:**
```bash
sudo journalctl -u swath-movers -f
sudo journalctl -u telegram-backup -f
```

**Manual Backup:**
```bash
python3 telegram_backup_service.py --once
```

## Related Files

- `telegram_backup_service.py` - Python backup service (project root)
- `TELEGRAM_BACKUP_README.md` - Telegram backup documentation (project root)
- `.env` - Environment configuration (project root)
- `app.py` - Main Flask application (project root)
- `gunicorn_config.py` - Gunicorn configuration (project root)

---

For detailed information about the backup system, see [TELEGRAM_BACKUP_README.md](../TELEGRAM_BACKUP_README.md)
