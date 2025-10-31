# Telegram Database Backup System (Python Service)

Automatically backs up your PostgreSQL database and sends it to anyone who messages your bot.

## Setup Instructions

### Step 1: Create a Telegram Bot

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` command
3. Follow instructions to create your bot
4. Copy the **Bot Token** (looks like: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### Step 2: Configure .env File

Edit your `.env` file and add the bot token:

```bash
nano .env
```

Add this line:
```bash
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
```

### Step 3: Setup the Service

```bash
bash setup_telegram_backup.sh
```

This will:
- Install Python dependencies (python-dotenv, requests)
- Install systemd service
- Optionally enable auto-start on boot
- Optionally start the service immediately

### Step 4: Start Receiving Backups

Anyone who wants to receive backups should:
1. Search for your bot on Telegram (by name or username)
2. Click "START" or send any message to the bot
3. They will automatically receive backups!

**That's it!** No need to configure chat IDs - the bot auto-discovers recipients.

## How It Works

- Bot automatically discovers chat IDs from anyone who messages it
- When backup runs, it sends to ALL users who have messaged the bot
- New users can be added anytime - just message the bot
- No configuration needed after adding bot token

## What Gets Backed Up

- ✅ All coordinates (58,641+ records)
- ✅ All deployments (22,818+ records)
- ✅ All swath lines
- ✅ All users (with password hashes)
- ✅ Complete database schema
- ✅ Database statistics

## Backup Features

- 📦 **Compressed**: .sql.gz format (smaller file size)
- 🔐 **Secure**: Credentials stored in .env file
- 📊 **Statistics**: Shows database stats in message
- 🗑️ **Auto-cleanup**: Deletes backups older than 7 days
- 👥 **Auto-discovery**: Sends to anyone who messages the bot
- ⏰ **Automated**: Runs every 24 hours as systemd service
- 🔄 **Auto-restart**: Service restarts automatically if it crashes
- 📝 **Logging**: Full logging to file and systemd journal

## Service Commands

### Control the service
```bash
# Start service
sudo systemctl start telegram-backup

# Stop service
sudo systemctl stop telegram-backup

# Restart service
sudo systemctl restart telegram-backup

# Check status
sudo systemctl status telegram-backup

# Enable auto-start on boot
sudo systemctl enable telegram-backup

# Disable auto-start
sudo systemctl disable telegram-backup
```

### View logs
```bash
# Follow live logs
sudo journalctl -u telegram-backup -f

# View recent logs
sudo journalctl -u telegram-backup -n 100

# View log file
tail -f logs/telegram_backup.log
```

## Manual Backup

Run backup once without starting the service:

```bash
python3 telegram_backup_service.py --once
```

This will:
1. Discover all chat IDs from bot messages
2. Create database backup
3. Send to all discovered users
4. Show results in terminal

## Change Backup Interval

Edit the service file to change from 24 hours:

```bash
sudo nano /etc/systemd/system/telegram-backup.service
```

Change the `--interval` parameter:
```ini
ExecStart=/usr/bin/python3 /home/aerys/Documents/ANTAN3D/telegram_backup_service.py --interval 12
```

Then reload:
```bash
sudo systemctl daemon-reload
sudo systemctl restart telegram-backup
```

## Restore from Backup

```bash
# Extract backup
gunzip backups/swath_movers_backup_YYYYMMDD_HHMMSS.sql.gz

# Restore to database
PGPASSWORD='aerys123' psql -h localhost -U aerys -d swath_movers < backups/swath_movers_backup_YYYYMMDD_HHMMSS.sql
```

## Configuration File

Location: `.env`

```bash
# Database credentials
DB_NAME=swath_movers
DB_USER=aerys
DB_PASSWORD=aerys123
DB_HOST=localhost
DB_PORT=5432

# Telegram configuration
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

To update credentials:
```bash
nano .env
```

## Telegram Message Format

```
🗄️ Database Backup

📅 Date: 2025-10-27 02:00:00
💾 Database: swath_movers
📦 Size: 1.2 MB
🖥️ Host: localhost

📊 Statistics
[Database table statistics]

✅ Backup completed successfully
```

## Troubleshooting

### Backup not received on Telegram

1. Check bot token is correct in `.env`
2. Verify you've started a chat with the bot (send any message)
3. Test manually: `python3 telegram_backup_service.py --once`
4. Check logs for chat IDs discovered: `sudo journalctl -u telegram-backup -n 50`

### No chat IDs found

This means no one has messaged the bot yet:
- Search for your bot on Telegram
- Click START or send any message
- The bot will automatically discover your chat ID
- Run backup again

### Service won't start

```bash
# Check service status
sudo systemctl status telegram-backup

# View detailed logs
sudo journalctl -u telegram-backup -n 50

# Check if PostgreSQL is running
sudo systemctl status postgresql

# Verify .env file exists and has bot token
cat .env | grep TELEGRAM
```

### Permission denied

```bash
chmod +x telegram_backup_service.py
chmod 600 .env
```

### Missing Python dependencies

```bash
pip install --user python-dotenv requests
```

## Security Notes

- ✅ Credentials stored in .env file (already in .gitignore)
- ✅ .env file should have 600 permissions (owner read/write only)
- ✅ Bot token is kept private
- ✅ Backup files are compressed and encrypted in transit (HTTPS)
- ✅ Service runs as regular user (not root)
- ✅ Only users who message the bot receive backups
- ⚠️ Backups contain sensitive data - only share bot with trusted users

## Adding/Removing Recipients

### Add a recipient
Just have them message the bot - that's it!

### Remove a recipient
Currently, all users who have ever messaged the bot will receive backups. To restrict this, you would need to:
1. Delete bot messages: Use Telegram's "Delete All Messages" feature
2. Or manually configure chat IDs in the code if you need fine-grained control

### List current recipients
```bash
# Run once and check logs
python3 telegram_backup_service.py --once | grep "Found chat ID"
```

## Files

- `telegram_backup_service.py` - Python backup service (main)
- `setup_telegram_backup.sh` - Setup script
- `backup_to_telegram.sh` - Legacy bash script (still works)
- `.env` - Credentials (secure, in .gitignore)
- `backups/` - Local backup storage
- `logs/telegram_backup.log` - Backup history
- `/etc/systemd/system/telegram-backup.service` - Systemd service file

## Architecture

```
telegram_backup_service.py (Python)
    ↓
Gets chat IDs from bot updates (auto-discovery)
    ↓
Creates PostgreSQL dump (pg_dump)
    ↓
Compresses with gzip
    ↓
Sends via Telegram Bot API to all discovered users
    ↓
Cleans up old backups (7+ days)
    ↓
Repeats every 24 hours
```

## Advantages of Auto-Discovery

- ✅ No need to manually configure chat IDs
- ✅ New recipients can be added without editing config
- ✅ Works with any number of recipients
- ✅ Simpler setup - just need bot token
- ✅ Recipients can add themselves

## Advantages of Python Service vs Cron

- ✅ Better error handling and logging
- ✅ Auto-restart on failure
- ✅ Easier to monitor (systemctl status)
- ✅ Consistent environment
- ✅ No cron configuration needed
- ✅ Starts automatically on boot (if enabled)

## Support

Get your Bot Token: @BotFather

---

**Your database is now automatically backed up to Telegram!** 🚀
