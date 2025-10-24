# Swath Movers - Quick Reference

## Installation

```bash
bash install_services.sh
```

## Essential Commands

### Service Control
```bash
sudo systemctl start swath-movers      # Start Flask app
sudo systemctl stop swath-movers       # Stop Flask app
sudo systemctl restart swath-movers    # Restart Flask app
sudo systemctl status swath-movers     # Check status

sudo systemctl start ngrok             # Start ngrok tunnel
sudo systemctl stop ngrok              # Stop ngrok tunnel
```

### View Logs
```bash
journalctl -u swath-movers -f          # Watch Flask logs (live)
journalctl -u ngrok -f                 # Watch ngrok logs (live)
tail -f logs/gunicorn-error.log        # Watch Gunicorn errors
```

### Get Ngrok URL
```bash
curl http://localhost:4040/api/tunnels 2>/dev/null | jq -r '.tunnels[0].public_url'
```

### After Code Changes
```bash
sudo systemctl restart swath-movers    # Restart to apply changes
journalctl -u swath-movers -f          # Watch for errors
```

### Check Performance
```bash
systemctl status swath-movers          # CPU & memory usage
ps aux | grep gunicorn                 # Worker processes
free -h                                # System memory
```

### Database Operations
```bash
sudo -u postgres psql -d swath_movers  # Connect to database
journalctl -u postgresql -n 50         # Check PostgreSQL logs
```

## Configuration Files

- **App Entry**: `wsgi.py`
- **Gunicorn Config**: `gunicorn_config.py`
- **Database Creds**: `.env`
- **Service Files**: `/etc/systemd/system/swath-movers.service`, `/etc/systemd/system/ngrok.service`
- **Logs**: `logs/gunicorn-access.log`, `logs/gunicorn-error.log`

## Performance Settings

- **Workers**: 5
- **Threads per Worker**: 4
- **Total Capacity**: ~100 concurrent requests
- **DB Connections**: 10-50
- **Memory Usage**: ~10-15GB

## Troubleshooting

### Port 8080 in use?
```bash
lsof -i :8080                          # Find process
kill <PID>                             # Kill process
```

### Service won't start?
```bash
journalctl -u swath-movers -n 100      # Check logs
systemctl status swath-movers          # Check status
```

### Database connection failed?
```bash
PGPASSWORD='aerys123' psql -h localhost -U aerys -d swath_movers -c "SELECT 1;"
```

## Full Documentation

See `DEPLOYMENT.md` for comprehensive documentation.
