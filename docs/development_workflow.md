# Development Workflow Guide

## Overview

This guide shows you how to safely test new features without breaking your production site.

---

## Architecture

### Production Environment
- **URL**: https://seistools.space
- **Port**: 8080 (Gunicorn)
- **Service**: `swath-movers.service`
- **Tunnel**: Cloudflare
- **Branch**: `production` (or `main`)

### Development Environment
- **URL**: http://localhost:8081
- **Port**: 8081 (Gunicorn)
- **Service**: `swath-movers-dev.service`
- **Testing**: Direct access or ngrok
- **Branch**: Feature branches (e.g., `feature/polygon-selection`)

---

## Quick Start: Testing New Features

### Step 1: Set Up Development Service (One-time setup)

```bash
cd /home/aerys/Documents/ANTAN3D
bash scripts/deployment/setup_dev_environment.sh
```

This creates a separate service running on port 8081.

### Step 2: Create Feature Branch

```bash
# Create and switch to new branch
git checkout -b feature/your-feature-name

# Example: git checkout -b feature/polygon-selection
```

### Step 3: Make Your Changes

Edit files as needed. Your changes are isolated to this branch.

### Step 4: Test on Development Service

After making changes, restart the dev service:

```bash
# Restart dev service to load changes
sudo systemctl restart swath-movers-dev

# View logs to check for errors
journalctl -u swath-movers-dev -f
```

Test at: http://localhost:8081

### Step 5: Test with Ngrok (Optional - for mobile/external testing)

```bash
# Start ngrok pointing to dev port
ngrok http 8081
```

This gives you a temporary public URL to test from anywhere.

### Step 6: Deploy to Production (when ready)

```bash
# If testing looks good, merge to production branch
git checkout production
git merge feature/your-feature-name

# Restart production service
sudo systemctl restart swath-movers

# Test production
curl -I https://seistools.space
```

### Step 7: Clean Up

```bash
# Delete feature branch after merging
git branch -d feature/your-feature-name
```

---

## Git Workflow Examples

### Example 1: Testing Polygon Selection Feature

```bash
# 1. Create feature branch
git checkout -b feature/polygon-selection

# 2. Make changes to postplot_map.html
nano postplot/templates/postplot_map.html

# 3. Test on development
sudo systemctl restart swath-movers-dev
curl http://localhost:8081/postplot/1

# 4. If broken, debug and fix (production still works!)
journalctl -u swath-movers-dev -n 100

# 5. Once working, commit changes
git add postplot/templates/postplot_map.html
git commit -m "Add polygon selection feature for unacquired shots"

# 6. Merge to production
git checkout production
git merge feature/polygon-selection

# 7. Deploy to production
sudo systemctl restart swath-movers
```

### Example 2: Quickly Revert a Broken Feature

```bash
# If you merged a broken feature to production:

# Option A: Revert the merge
git revert -m 1 HEAD
sudo systemctl restart swath-movers

# Option B: Reset to previous commit (if not pushed)
git reset --hard HEAD~1
sudo systemctl restart swath-movers

# Option C: Revert specific file
git checkout HEAD~1 -- path/to/file.html
sudo systemctl restart swath-movers
```

---

## Service Management

### View Both Services

```bash
# Status of both
systemctl status swath-movers.service swath-movers-dev.service

# Or individually
systemctl status swath-movers         # Production
systemctl status swath-movers-dev     # Development
```

### Restart Services

```bash
# Restart production (careful!)
sudo systemctl restart swath-movers

# Restart development (safe!)
sudo systemctl restart swath-movers-dev
```

### View Logs

```bash
# Production logs
journalctl -u swath-movers -f

# Development logs
journalctl -u swath-movers-dev -f

# Error logs only
journalctl -u swath-movers-dev -p err -f
```

### Stop Development Service (when not testing)

```bash
# Stop to save resources
sudo systemctl stop swath-movers-dev

# Start again when needed
sudo systemctl start swath-movers-dev
```

---

## Testing Strategy

### For Frontend Changes (HTML/CSS/JS)

1. Edit files in feature branch
2. Restart dev service
3. Test at `http://localhost:8081`
4. Check browser console for errors (F12)
5. Test on mobile via ngrok if needed
6. Merge to production when ready

### For Backend Changes (Python/Flask)

1. Edit files in feature branch
2. Restart dev service
3. Check logs: `journalctl -u swath-movers-dev -f`
4. Test API endpoints with curl
5. Merge to production when ready

### For Database Changes (PostgreSQL)

**Warning**: Both services use the same database!

If you need to test schema changes:

```bash
# Create a backup first
bash scripts/backup/backup_db.sh

# Make changes carefully
# Consider using migrations (Flask-Migrate/Alembic)
```

For major database changes, consider creating a separate test database.

---

## Useful Testing Commands

### Test Specific Endpoints

```bash
# Production
curl -I https://seistools.space/postplot/1
curl -I https://seistools.space/static/js/table.js

# Development
curl -I http://localhost:8081/postplot/1
curl -I http://localhost:8081/static/js/table.js
```

### Check for JavaScript Errors

Open browser console (F12) and look for:
- Red errors in Console tab
- Failed network requests in Network tab
- Check Sources tab for loaded files

### Compare Production vs Development

```bash
# Test both simultaneously
echo "Production:" && curl -s http://localhost:8080 | grep -o '<title>.*</title>'
echo "Development:" && curl -s http://localhost:8081 | grep -o '<title>.*</title>'
```

---

## Best Practices

### 1. Always Use Feature Branches

❌ **Don't do this:**
```bash
# Editing directly on production branch
git checkout production
nano postplot/templates/postplot_map.html  # RISKY!
```

✅ **Do this:**
```bash
# Create feature branch first
git checkout -b feature/new-feature
nano postplot/templates/postplot_map.html  # SAFE!
```

### 2. Test on Development First

Always test on port 8081 before deploying to production:

```bash
# 1. Make changes
# 2. Restart dev service
sudo systemctl restart swath-movers-dev
# 3. Test thoroughly
curl http://localhost:8081/your-endpoint
# 4. Only then deploy to production
```

### 3. Commit Often

```bash
# Commit working states frequently
git add .
git commit -m "Work in progress: polygon drawing works"

# Easy to revert to any commit
git log --oneline
git checkout abc123 -- path/to/file.html
```

### 4. Use Descriptive Branch Names

```bash
# Good branch names
git checkout -b feature/polygon-selection
git checkout -b fix/static-files-403
git checkout -b refactor/map-rendering

# Bad branch names
git checkout -b test
git checkout -b new-stuff
```

### 5. Keep Production Stable

- Never commit untested code to production branch
- Always test on development first
- Keep production branch clean and working

---

## Troubleshooting

### Development service won't start

```bash
# Check what's using port 8081
sudo lsof -i :8081

# View detailed error logs
journalctl -u swath-movers-dev -n 100 --no-pager

# Check service configuration
systemctl cat swath-movers-dev
```

### Changes not appearing after restart

```bash
# Hard restart
sudo systemctl stop swath-movers-dev
sleep 2
sudo systemctl start swath-movers-dev

# Check if service is actually running
systemctl is-active swath-movers-dev

# Clear browser cache (Ctrl+Shift+R)
```

### Git branch confusion

```bash
# See all branches
git branch -a

# See current branch
git branch --show-current

# Switch branches
git checkout branch-name

# See uncommitted changes
git status
```

---

## Summary: Safe Feature Development Workflow

1. **Create feature branch**: `git checkout -b feature/name`
2. **Make changes**: Edit files
3. **Test on dev**: `sudo systemctl restart swath-movers-dev`
4. **Access dev**: `http://localhost:8081`
5. **Debug if needed**: `journalctl -u swath-movers-dev -f`
6. **Commit when working**: `git commit -m "Feature working"`
7. **Merge to production**: `git checkout production && git merge feature/name`
8. **Deploy**: `sudo systemctl restart swath-movers`
9. **Test production**: `https://seistools.space`

**Key Principle**: Production (port 8080, seistools.space) always stays working. Test everything on development (port 8081) first!

---

## Quick Reference Card

| Action | Command |
|--------|---------|
| Create feature branch | `git checkout -b feature/name` |
| Restart dev service | `sudo systemctl restart swath-movers-dev` |
| Restart prod service | `sudo systemctl restart swath-movers` |
| View dev logs | `journalctl -u swath-movers-dev -f` |
| Test dev | `http://localhost:8081` |
| Test prod | `https://seistools.space` |
| Merge to prod | `git checkout production && git merge feature/name` |
| Revert file | `git checkout HEAD~1 -- path/to/file` |
| Start ngrok for dev | `ngrok http 8081` |

---

## Next Steps

1. Run the setup script to create dev environment
2. Practice creating a feature branch
3. Make a small test change
4. Test on development service
5. Deploy to production only when confident

**Remember**: With this setup, you can break development as much as you want while production stays stable!
