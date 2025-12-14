# Discord Bot - Deployment Complete

## Status: DEPLOYED AND OPERATIONAL

The Discord Progress Bot has been successfully migrated to PostgreSQL and deployed to seistools.space.

---

## Live URLs

- **Main Interface**: http://seistools.space/bot/Antan3D/
- **Admin Panel**: http://seistools.space/bot/Antan3D/admin
- **Map View**: http://seistools.space/bot/Antan3D/map

---

## Deployment Verification

### Service Status
- Systemd service: **ACTIVE**
- Discord Gateway: **CONNECTED**
- Auto-start on boot: **ENABLED**

### Database
- PostgreSQL: **CONNECTED**
- Database: `discordbot_progress`
- Tables: `progress_points`, `activity_log`, `duplicate_attempts`
- Records: 0 (fresh start as requested)

### Web Interface
- Main Page: **HTTP 200 ✓**
- Admin Page: **HTTP 200 ✓**
- Static Files: **HTTP 200 ✓**

---

## What Was Done

### 1. Database Migration
- Created PostgreSQL database `discordbot_progress` with separate user
- Completely rewrote [db_utils.py](discordbot_beta/src/core/db_utils.py) for PostgreSQL
- Updated all SQL queries from SQLite to PostgreSQL syntax
- Created empty tables (no migration of existing SQLite data)

### 2. Configuration
- Created [.env](discordbot_beta/.env) with production settings
- Port 8090 (isolated from swath-movers)
- URL prefix `/bot/` for reverse proxy support

### 3. Service Deployment
- Created systemd service: `/etc/systemd/system/discordbot.service`
- Service runs both Discord bot and web server via [run_both.py](discordbot_beta/run_both.py)
- Auto-restart on failure with 10-second delay
- Logs to systemd journal

### 4. Web Server Configuration
- Updated Nginx configuration: `/etc/nginx/sites-available/swath-movers`
- Added `/bot/` location block with WebSocket support
- Configured reverse proxy to port 8090

### 5. Template Updates
- Updated [upload.html](discordbot_beta/templates/upload.html) to use `url_for()` with URL prefix
- Updated [admin.html](discordbot_beta/templates/admin.html) to use `url_for()` with URL prefix
- Added custom context processor for URL prefix support

### 6. Bug Fixes
- Fixed Flask static file serving with URL prefix
- Fixed admin page PostgreSQL compatibility
- Added error handling for missing processing stats

---

## Complete Isolation from Swath-Movers

The Discord bot is **completely isolated**:

| Component | Discord Bot | Swath-Movers |
|-----------|-------------|--------------|
| Database | `discordbot_progress` | `swath_movers` |
| DB User | `discordbot` | `aerys` |
| Virtual Env | `progress_bot/discordbot_beta/venv` | `swathenv` |
| Port | 8090 | 8080, 8082 |
| Service | `discordbot` | `swath-movers-dev/prod` |
| URL Path | `/bot/` | `/`, `/postplot/` |

---

## Useful Commands

### Service Management
```bash
# View status
sudo systemctl status discordbot

# Restart service
sudo systemctl restart discordbot

# Stop service
sudo systemctl stop discordbot

# View live logs
sudo journalctl -u discordbot -f

# View recent logs
sudo journalctl -u discordbot -n 100
```

### Database Access
```bash
# Connect to database
PGPASSWORD='aerys123' psql -h localhost -U discordbot -d discordbot_progress

# View progress points
PGPASSWORD='aerys123' psql -h localhost -U discordbot -d discordbot_progress -c "SELECT * FROM progress_points LIMIT 10;"

# View activity log
PGPASSWORD='aerys123' psql -h localhost -U discordbot -d discordbot_progress -c "SELECT * FROM activity_log ORDER BY timestamp DESC LIMIT 10;"
```

### Testing
```bash
# Test web interface
curl http://localhost/bot/Antan3D/

# Test direct connection
curl http://localhost:8090/Antan3D/

# Check port is listening
sudo netstat -tlnp | grep 8090
```

---

## Configuration Files

### Service File
Location: `/etc/systemd/system/discordbot.service`
```ini
[Unit]
Description=Discord Progress Bot
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=aerys
WorkingDirectory=/home/aerys/Documents/ANTAN3D/progress_bot/discordbot_beta
EnvironmentFile=/home/aerys/Documents/ANTAN3D/progress_bot/discordbot_beta/.env
ExecStart=/home/aerys/Documents/ANTAN3D/progress_bot/discordbot_beta/venv/bin/python run_both.py
Restart=always
RestartSec=10
```

### Environment Variables
Location: `/home/aerys/Documents/ANTAN3D/progress_bot/discordbot_beta/.env`
- Discord bot token configured
- PostgreSQL connection: localhost:5432
- Web server: port 8090
- URL prefix: `/bot`

### Nginx Configuration
Location: `/etc/nginx/sites-available/swath-movers`
- Upstream: `discord_bot_backend` → `127.0.0.1:8090`
- Location: `/bot/` → proxies to Discord bot
- WebSocket support enabled

---

## File Structure

```
/home/aerys/Documents/ANTAN3D/progress_bot/
├── discordbot_beta/
│   ├── .env                          # Production configuration
│   ├── run_both.py                   # Unified launcher
│   ├── deploy.sh                     # Deployment script
│   ├── quick_deploy.sh               # Quick deployment
│   ├── venv/                         # Isolated virtual environment
│   ├── src/
│   │   ├── core/
│   │   │   └── db_utils.py          # PostgreSQL database utilities
│   │   └── applications/
│   │       └── web_upload_server.py # Flask web server
│   ├── templates/
│   │   ├── upload.html              # Main upload page
│   │   └── admin.html               # Admin interface
│   └── scripts/
│       └── init_postgres.sql        # PostgreSQL schema
├── DEPLOYMENT_READY.md              # Pre-deployment documentation
└── DEPLOYMENT_SUMMARY.md            # This file
```

---

## Troubleshooting

### Service Won't Start
```bash
# Check service status
sudo systemctl status discordbot

# View error logs
sudo journalctl -u discordbot -n 50

# Check if port is in use
sudo netstat -tlnp | grep 8090
```

### Database Connection Issues
```bash
# Test PostgreSQL connection
PGPASSWORD='aerys123' psql -h localhost -U discordbot -d discordbot_progress -c "SELECT 1;"

# Check PostgreSQL is running
sudo systemctl status postgresql
```

### Web Interface Not Loading
```bash
# Test Flask directly
curl http://localhost:8090/Antan3D/

# Test through Nginx
curl http://localhost/bot/Antan3D/

# Check Nginx configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

### Discord Bot Not Responding
- Check Discord bot token in `.env`
- Verify bot permissions in Discord Developer Portal
- Check gateway connection in logs: `sudo journalctl -u discordbot | grep Gateway`

---

## Next Steps

1. **Test Discord Commands**
   - Use Discord commands in your server
   - Verify progress points are saved to PostgreSQL
   - Check activity log is being populated

2. **Test Web Upload**
   - Upload Excel files via web interface
   - Verify file processing works correctly
   - Check screenshots are generated

3. **Monitor Performance**
   - Watch logs for any errors: `sudo journalctl -u discordbot -f`
   - Monitor database growth
   - Check memory/CPU usage

4. **Optional Enhancements**
   - Migrate processing_pipeline.py to PostgreSQL (currently uses fallbacks)
   - Set up automated backups for PostgreSQL database
   - Configure SSL/HTTPS for web interface

---

## Rollback Instructions

If you need to rollback the deployment:

```bash
# Stop and disable service
sudo systemctl stop discordbot
sudo systemctl disable discordbot

# Remove service file
sudo rm /etc/systemd/system/discordbot.service
sudo systemctl daemon-reload

# Restore Nginx configuration (use appropriate backup)
sudo cp /etc/nginx/sites-available/swath-movers.backup.YYYYMMDD_HHMMSS /etc/nginx/sites-available/swath-movers
sudo nginx -t
sudo systemctl reload nginx

# Optionally remove PostgreSQL database
PGPASSWORD='aerys123' psql -h localhost -U postgres -c "DROP DATABASE discordbot_progress;"
PGPASSWORD='aerys123' psql -h localhost -U postgres -c "DROP USER discordbot;"
```

---

## Support

For issues or questions:
- Check logs: `sudo journalctl -u discordbot -f`
- Review configuration: `/home/aerys/Documents/ANTAN3D/progress_bot/discordbot_beta/.env`
- Test endpoints manually using curl commands above

**Deployment completed**: 2025-11-19
**Status**: Operational and serving at http://seistools.space/bot/
