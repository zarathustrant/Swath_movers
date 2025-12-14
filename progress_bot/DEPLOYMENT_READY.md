# Discord Bot Deployment - Ready to Deploy

## Summary

The Discord bot has been fully configured for PostgreSQL and is ready for deployment to seistools.space. All code modifications and configuration files have been prepared.

## What's Been Completed

### 1. Database Setup ✓
- PostgreSQL database: `discordbot_progress`
- Database user: `discordbot` (password: `aerys123`)
- Schema created with empty tables (no SQLite migration)
- Tables: `progress_points`, `activity_log`, `duplicate_attempts`

### 2. Code Migration ✓
- Completely rewrote `src/core/db_utils.py` from SQLite to PostgreSQL
- All SQL queries updated to PostgreSQL syntax
- Added `psycopg2-binary` to `requirements.txt`
- Created `run_both.py` unified launcher for Discord bot + web server

### 3. Configuration Files ✓
- `.env` file with production settings
- Port 8090 (isolated from swath-movers on 8080/8082)
- Absolute file paths for systemd compatibility

### 4. Service Files ✓
- Systemd service: `/tmp/discordbot.service`
- Runs as user `aerys`
- Auto-restart on failure
- Logs to systemd journal

### 5. Nginx Configuration ✓
- Updated config: `/tmp/swath-movers-with-bot`
- Added `/bot/` location block
- WebSocket support for SocketIO
- Proxies to port 8090

### 6. Deployment Script ✓
- Automated deployment script: `deploy.sh`
- Installs all components
- Tests connections
- Handles rollback on failure

## Complete Isolation from Swath-Movers

The Discord bot is completely isolated:
- **Separate database**: `discordbot_progress` (not `swath_movers`)
- **Separate DB user**: `discordbot` (not `aerys`)
- **Separate virtual environment**: `progress_bot/discordbot_beta/venv` (not `swathenv`)
- **Separate port**: 8090 (not 8080/8082)
- **Separate systemd service**: `discordbot` (not `swath-movers-dev/prod`)
- **Separate URL path**: `/bot/` (not `/` or `/postplot/`)

## Final Deployment Steps

You just need to run the deployment script with your sudo password:

```bash
cd /home/aerys/Documents/ANTAN3D/progress_bot/discordbot_beta
./deploy.sh
```

The script will:
1. Install systemd service file
2. Update Nginx configuration (creates backup first)
3. Install Python dependencies in virtual environment
4. Create required directories (uploads, processed, screenshots, logs)
5. Test database connection
6. Start and enable the service
7. Test endpoints

## Manual Deployment (Alternative)

If you prefer to run commands manually:

```bash
# 1. Install systemd service
sudo cp /tmp/discordbot.service /etc/systemd/system/discordbot.service
sudo systemctl daemon-reload

# 2. Update Nginx
sudo cp /etc/nginx/sites-available/swath-movers /etc/nginx/sites-available/swath-movers.backup.$(date +%Y%m%d_%H%M%S)
sudo cp /tmp/swath-movers-with-bot /etc/nginx/sites-available/swath-movers
sudo nginx -t
sudo systemctl reload nginx

# 3. Install dependencies
cd /home/aerys/Documents/ANTAN3D/progress_bot/discordbot_beta
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
playwright install chromium

# 4. Create directories
mkdir -p uploads processed screenshots logs

# 5. Start service
sudo systemctl enable discordbot
sudo systemctl start discordbot

# 6. Check status
sudo systemctl status discordbot
```

## Testing After Deployment

### Check Service Status
```bash
sudo systemctl status discordbot
```

### View Live Logs
```bash
sudo journalctl -u discordbot -f
```

### Test Endpoints
```bash
# Direct connection
curl http://localhost:8090

# Via Nginx
curl http://localhost/bot/
```

### Access Web Interface
- **Local**: http://localhost:8090
- **Public**: http://seistools.space/bot/

## Troubleshooting

### Service won't start
```bash
# Check logs
sudo journalctl -u discordbot -n 50

# Check if port 8090 is available
sudo netstat -tlnp | grep 8090

# Test database connection
PGPASSWORD='aerys123' psql -h localhost -U discordbot -d discordbot_progress -c "SELECT 1;"
```

### Web interface not accessible
```bash
# Check Nginx status
sudo systemctl status nginx

# Test Nginx config
sudo nginx -t

# Check if service is running on correct port
curl http://localhost:8090
```

### Discord bot not responding
- Check Discord bot token in `.env`
- Verify bot has correct permissions in Discord developer portal
- Check service logs for connection errors

## File Locations

- **Working Directory**: `/home/aerys/Documents/ANTAN3D/progress_bot/discordbot_beta`
- **Virtual Environment**: `./venv`
- **Configuration**: `./.env`
- **Logs**: `./logs/`
- **Uploads**: `./uploads/`
- **Service File**: `/etc/systemd/system/discordbot.service`
- **Nginx Config**: `/etc/nginx/sites-available/swath-movers`

## Useful Commands

```bash
# Service management
sudo systemctl start discordbot
sudo systemctl stop discordbot
sudo systemctl restart discordbot
sudo systemctl status discordbot

# View logs
sudo journalctl -u discordbot -n 100      # Last 100 lines
sudo journalctl -u discordbot -f          # Follow live
sudo journalctl -u discordbot --since "10 minutes ago"

# Database
PGPASSWORD='aerys123' psql -h localhost -U discordbot -d discordbot_progress

# Check what's using port 8090
sudo netstat -tlnp | grep 8090
sudo lsof -i :8090
```

## Next Steps After Deployment

1. Test Discord bot commands in your Discord server
2. Test web file upload interface
3. Verify progress points are being saved to PostgreSQL
4. Check that screenshots are being generated
5. Monitor logs for any errors

## Rollback Plan

If anything goes wrong:

```bash
# Stop the service
sudo systemctl stop discordbot
sudo systemctl disable discordbot

# Restore Nginx backup (use the backup filename from deployment)
sudo cp /etc/nginx/sites-available/swath-movers.backup.YYYYMMDD_HHMMSS /etc/nginx/sites-available/swath-movers
sudo systemctl reload nginx

# Remove service file
sudo rm /etc/systemd/system/discordbot.service
sudo systemctl daemon-reload
```

The swath-movers application will continue running unaffected.
