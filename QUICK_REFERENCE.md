# Swath Movers - Quick Reference

## Installation

### With Nginx CDN (Recommended - 10x faster!)
```bash
bash install_with_nginx.sh
```

### Without Nginx (Basic setup)
```bash
bash install_services.sh
```

## Essential Commands

### Service Control
```bash
sudo systemctl start swath-movers      # Start Flask app
sudo systemctl start nginx             # Start reverse proxy
sudo systemctl start ngrok             # Start ngrok tunnel

sudo systemctl stop swath-movers       # Stop Flask app
sudo systemctl stop nginx              # Stop nginx

sudo systemctl restart swath-movers    # Restart Flask app
sudo systemctl reload nginx            # Reload nginx config (no downtime)

sudo systemctl status swath-movers     # Check status
sudo systemctl status nginx            # Check nginx status
```

### View Logs
```bash
journalctl -u swath-movers -f          # Watch Flask logs (live)
journalctl -u nginx -f                 # Watch nginx logs (live)
journalctl -u ngrok -f                 # Watch ngrok logs (live)
tail -f logs/gunicorn-error.log        # Watch Gunicorn errors
tail -f /var/log/nginx/swath_movers_error.log  # Watch nginx errors
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
- **Nginx Config**: `/etc/nginx/sites-available/swath-movers`
- **Database Creds**: `.env`
- **Service Files**: `/etc/systemd/system/swath-movers.service`, `/etc/systemd/system/ngrok.service`
- **Logs**: `logs/gunicorn-*.log`, `/var/log/nginx/swath_movers_*.log`

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

## Performance Testing

### Test Static File Caching
```bash
curl -I http://localhost/static/css/table.css  # Check Cache-Control header
```

### Test API Caching
```bash
curl -I http://localhost/get_coordinates        # Check X-Cache-Status header
```

### Clear Nginx Cache
```bash
sudo rm -rf /var/cache/nginx/swath_movers/*
sudo systemctl reload nginx
```

## Full Documentation

- **Nginx CDN Setup**: See `CDN_SETUP.md` for caching & performance details
- **Full Deployment Guide**: See `DEPLOYMENT.md` for comprehensive documentation
