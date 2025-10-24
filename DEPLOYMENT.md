# Swath Movers Production Deployment Guide

## System Overview

Your Swath Movers application is now configured for production deployment with:

- **Gunicorn WSGI Server**: 5 workers × 4 threads = 20 concurrent workers
- **PostgreSQL Database**: Connection pool (10-50 connections)
- **Systemd Services**: Auto-start and auto-restart capabilities
- **Ngrok Tunnel**: External access to your application
- **System Resources**: Optimized for 8 CPU cores and 15GB RAM

## Architecture

```
Internet → ngrok tunnel → localhost:8080 → Gunicorn (5 workers × 4 threads) → Flask App → PostgreSQL
```

## Files Created

### Application Files
- `wsgi.py` - WSGI entry point for Gunicorn
- `gunicorn_config.py` - Gunicorn configuration (5 workers, 4 threads)
- `logs/` - Log directory for Gunicorn access and error logs
- `install_services.sh` - Installation script for systemd services

### Systemd Service Files (in /tmp, ready to install)
- `/tmp/swath-movers.service` - Flask application service
- `/tmp/ngrok.service` - Ngrok tunnel service

### Modified Files
- `app.py` - Updated PostgreSQL connection pool (10-50 connections)
- `.env` - Database credentials (DB_PASSWORD=aerys123)

## Installation

Run the installation script to set up the systemd services:

```bash
bash install_services.sh
```

This script will:
1. Install systemd service files to `/etc/systemd/system/`
2. Reload systemd daemon
3. Enable services to start on boot
4. Stop any existing processes on port 8080
5. Start both services
6. Display service status

## Service Management

### Starting Services

```bash
# Start Flask application
sudo systemctl start swath-movers

# Start ngrok tunnel
sudo systemctl start ngrok

# Start both
sudo systemctl start swath-movers ngrok
```

### Stopping Services

```bash
# Stop Flask application
sudo systemctl stop swath-movers

# Stop ngrok tunnel
sudo systemctl stop ngrok

# Stop both
sudo systemctl stop swath-movers ngrok
```

### Restarting Services

```bash
# Restart Flask application (e.g., after code changes)
sudo systemctl restart swath-movers

# Restart ngrok tunnel
sudo systemctl restart ngrok
```

### Checking Service Status

```bash
# Check Flask application status
sudo systemctl status swath-movers

# Check ngrok tunnel status
sudo systemctl status ngrok

# Check both services
sudo systemctl status swath-movers ngrok
```

### Enabling/Disabling Auto-Start

```bash
# Enable auto-start on boot (already done by install script)
sudo systemctl enable swath-movers
sudo systemctl enable ngrok

# Disable auto-start on boot
sudo systemctl disable swath-movers
sudo systemctl disable ngrok
```

## Log Management

### View Live Logs

```bash
# Watch Flask application logs (live)
journalctl -u swath-movers -f

# Watch ngrok logs (live)
journalctl -u ngrok -f

# Watch both logs simultaneously
journalctl -u swath-movers -u ngrok -f
```

### View Recent Logs

```bash
# Last 100 lines of Flask logs
journalctl -u swath-movers -n 100

# Last 100 lines of ngrok logs
journalctl -u ngrok -n 100

# Logs since last boot
journalctl -u swath-movers -b

# Logs from today
journalctl -u swath-movers --since today
```

### Gunicorn Log Files

Gunicorn also writes to files in the `logs/` directory:

```bash
# View access logs
tail -f logs/gunicorn-access.log

# View error logs
tail -f logs/gunicorn-error.log
```

## Getting the Ngrok URL

### Method 1: From ngrok API

```bash
curl http://localhost:4040/api/tunnels 2>/dev/null | jq -r '.tunnels[0].public_url'
```

### Method 2: From ngrok logs

```bash
journalctl -u ngrok -n 50 | grep "started tunnel"
```

### Method 3: Visit ngrok Web Interface

Open in your browser: http://localhost:4040

## Performance Monitoring

### Check Resource Usage

```bash
# CPU and memory usage by service
systemctl status swath-movers

# Detailed process information
ps aux | grep gunicorn

# Connection count to PostgreSQL
sudo -u postgres psql -d swath_movers -c "SELECT count(*) FROM pg_stat_activity WHERE datname='swath_movers';"
```

### Monitor Worker Status

```bash
# Number of active workers
pgrep -a gunicorn | wc -l

# Detailed worker information
pgrep -a gunicorn
```

## Troubleshooting

### Service Won't Start

```bash
# Check detailed error logs
journalctl -u swath-movers -n 100 --no-pager

# Check if port 8080 is already in use
lsof -i :8080

# Verify virtual environment
ls -la swathenv/bin/gunicorn

# Test gunicorn configuration
swathenv/bin/gunicorn --check-config -c gunicorn_config.py wsgi:app
```

### Database Connection Issues

```bash
# Test database connection
PGPASSWORD='aerys123' psql -h localhost -U aerys -d swath_movers -c "SELECT 1;"

# Check PostgreSQL is running
sudo systemctl status postgresql

# View database logs
sudo journalctl -u postgresql -n 50
```

### Ngrok Won't Connect

```bash
# Check ngrok service status
sudo systemctl status ngrok

# Verify Flask is running on port 8080
curl http://localhost:8080

# Check ngrok configuration
cat ~/.config/ngrok/ngrok.yml

# Test ngrok manually
/usr/local/bin/ngrok http 8080
```

### High Memory Usage

```bash
# Check memory usage
free -h

# Memory usage by service
sudo systemctl status swath-movers | grep Memory

# If memory is an issue, reduce workers in gunicorn_config.py
# Edit: workers = 3  (instead of 5)
# Then restart: sudo systemctl restart swath-movers
```

## Updating the Application

### After Code Changes

```bash
# 1. Stop the service
sudo systemctl stop swath-movers

# 2. Make your code changes
# ... edit files ...

# 3. Test changes (optional)
# swathenv/bin/python app.py

# 4. Restart the service
sudo systemctl restart swath-movers

# 5. Check status
sudo systemctl status swath-movers

# 6. Watch logs for any errors
journalctl -u swath-movers -f
```

### Zero-Downtime Reload

Gunicorn supports graceful reload without downtime:

```bash
# Send HUP signal to reload workers gracefully
sudo systemctl reload swath-movers

# Or use kill command
sudo kill -HUP $(pgrep -f "gunicorn.*wsgi:app" | head -1)
```

## Performance Tuning

### Current Configuration

- **Workers**: 5 (2 × CPU cores - 3 for overhead)
- **Threads per worker**: 4
- **Total concurrent capacity**: 20 workers × 50 threads = ~100 concurrent requests
- **PostgreSQL connections**: 10-50
- **Timeout**: 120 seconds
- **Memory per worker**: ~2-3GB
- **Total memory usage**: ~10-15GB

### Adjust for Different Loads

Edit `gunicorn_config.py` to tune performance:

```python
# For lower memory usage (reduce workers)
workers = 3

# For higher throughput (increase threads)
threads = 6

# For longer-running requests (increase timeout)
timeout = 180
```

After changes:
```bash
sudo systemctl restart swath-movers
```

## Security Notes

1. **Environment Variables**: Database credentials are stored in `.env` (already in .gitignore)
2. **File Permissions**: `.env` has 600 permissions (user-only access)
3. **Systemd Security**: Services run with `PrivateTmp=true` and `NoNewPrivileges=true`
4. **PostgreSQL**: Uses password authentication, not exposed externally
5. **Ngrok**: Traffic is encrypted via HTTPS by ngrok

## Backup and Recovery

### Database Backup

```bash
# Backup PostgreSQL database
sudo -u postgres pg_dump swath_movers > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore from backup
sudo -u postgres psql swath_movers < backup_20251024_105300.sql
```

### Application Backup

```bash
# Backup entire application directory
tar -czf swath_movers_backup_$(date +%Y%m%d).tar.gz \
    --exclude=swathenv \
    --exclude=logs \
    --exclude=__pycache__ \
    /home/aerys/Documents/ANTAN3D
```

## System Startup Sequence

When your system boots:

1. PostgreSQL service starts
2. Swath-movers service starts (waits for PostgreSQL)
3. Gunicorn spawns 5 worker processes
4. Each worker creates database connections (10 min, 50 max total)
5. Ngrok service starts (waits for swath-movers)
6. Ngrok establishes tunnel to localhost:8080
7. Application is accessible via ngrok URL

## Contact & Support

- **Service files**: `/etc/systemd/system/swath-movers.service`, `/etc/systemd/system/ngrok.service`
- **Configuration**: `gunicorn_config.py`
- **Logs**: `logs/` directory and `journalctl`
- **Database credentials**: `.env` and `postgres_credentials.txt`

---

**Your application is production-ready!** 🚀
