#!/usr/bin/env python3
"""
PostgreSQL Database Backup to Telegram Service
Automatically backs up the database and sends to multiple Telegram recipients
"""

import os
import sys
import subprocess
import gzip
import shutil
from datetime import datetime, timedelta
from pathlib import Path
import requests
from dotenv import load_dotenv
import logging
import time

# Setup logging
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "telegram_backup.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class TelegramBackupService:
    def __init__(self):
        """Initialize the backup service"""
        # Load environment variables
        env_path = Path(__file__).parent / ".env"
        if not env_path.exists():
            logger.error(f"❌ .env file not found at {env_path}")
            sys.exit(1)

        load_dotenv(env_path)

        # Load configuration
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")

        self.db_name = os.getenv("DB_NAME", "swath_movers")
        self.db_user = os.getenv("DB_USER", "aerys")
        self.db_password = os.getenv("DB_PASSWORD")
        self.db_host = os.getenv("DB_HOST", "localhost")
        self.db_port = os.getenv("DB_PORT", "5432")

        # Validate configuration
        if not self.bot_token:
            logger.error("❌ Missing TELEGRAM_BOT_TOKEN in .env file")
            logger.error("Please add: TELEGRAM_BOT_TOKEN=your_bot_token")
            sys.exit(1)

        if not self.db_password:
            logger.error("❌ Missing DB_PASSWORD in .env file")
            sys.exit(1)

        # Setup directories
        self.project_root = Path(__file__).parent
        self.backup_dir = self.project_root / "backups"
        self.backup_dir.mkdir(exist_ok=True)

        # Backup settings
        self.retention_days = 7

        # Chat IDs will be discovered from messages and persisted
        self.chat_ids_file = self.project_root / "telegram_chat_ids.txt"
        self.chat_ids = self.load_chat_ids()

        logger.info("✓ Telegram Backup Service initialized")
        if self.chat_ids:
            logger.info(f"✓ Loaded {len(self.chat_ids)} saved chat ID(s)")
        else:
            logger.info("✓ Bot ready - will discover chat IDs from messages")

    def load_chat_ids(self):
        """Load chat IDs from persistent storage"""
        try:
            if self.chat_ids_file.exists():
                with open(self.chat_ids_file, 'r') as f:
                    chat_ids = set()
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            try:
                                chat_ids.add(int(line))
                            except ValueError:
                                logger.warning(f"Invalid chat ID in file: {line}")
                    return chat_ids
            return set()
        except Exception as e:
            logger.warning(f"Could not load chat IDs: {e}")
            return set()

    def save_chat_ids(self):
        """Save chat IDs to persistent storage"""
        try:
            with open(self.chat_ids_file, 'w') as f:
                f.write("# Telegram Chat IDs for backup notifications\n")
                f.write(f"# Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                for chat_id in sorted(self.chat_ids):
                    f.write(f"{chat_id}\n")
            logger.info(f"✓ Saved {len(self.chat_ids)} chat ID(s)")
        except Exception as e:
            logger.error(f"Failed to save chat IDs: {e}")

    def create_backup(self):
        """Create PostgreSQL database backup"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_dir / f"{self.db_name}_backup_{timestamp}.sql"

        logger.info(f"Creating backup: {backup_file.name}")

        try:
            # Create PostgreSQL dump
            env = os.environ.copy()
            env['PGPASSWORD'] = self.db_password

            cmd = [
                'pg_dump',
                '-h', self.db_host,
                '-p', self.db_port,
                '-U', self.db_user,
                '-d', self.db_name,
                '-f', str(backup_file)
            ]

            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                logger.error(f"❌ pg_dump failed: {result.stderr}")
                return None

            logger.info(f"✓ Database dumped successfully")

            # Compress backup
            backup_gz = Path(f"{backup_file}.gz")
            with open(backup_file, 'rb') as f_in:
                with gzip.open(backup_gz, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)

            # Remove uncompressed file
            backup_file.unlink()

            # Get file size
            size_mb = backup_gz.stat().st_size / (1024 * 1024)
            logger.info(f"✓ Backup compressed: {size_mb:.2f} MB")

            return backup_gz

        except Exception as e:
            logger.error(f"❌ Backup creation failed: {e}")
            return None

    def get_database_stats(self):
        """Get database statistics"""
        try:
            env = os.environ.copy()
            env['PGPASSWORD'] = self.db_password

            query = """
            SELECT
                schemaname,
                tablename,
                n_tup_ins as inserts,
                n_tup_upd as updates,
                n_tup_del as deletes
            FROM pg_stat_user_tables
            ORDER BY schemaname, tablename;
            """

            cmd = [
                'psql',
                '-h', self.db_host,
                '-p', self.db_port,
                '-U', self.db_user,
                '-d', self.db_name,
                '-c', query,
                '-t'  # Tuples only
            ]

            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return "Stats unavailable"

        except Exception as e:
            logger.warning(f"Could not fetch stats: {e}")
            return "Stats unavailable"

    def get_chat_ids_from_updates(self):
        """Get chat IDs from users who have messaged the bot"""
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"
            response = requests.get(url, timeout=30)

            if response.status_code == 200:
                data = response.json()
                if data.get('ok') and data.get('result'):
                    initial_count = len(self.chat_ids)

                    for update in data['result']:
                        if 'message' in update:
                            chat_id = update['message']['chat']['id']
                            chat_name = update['message']['chat'].get('first_name', 'Unknown')

                            if chat_id not in self.chat_ids:
                                self.chat_ids.add(chat_id)
                                logger.info(f"✓ New chat ID discovered: {chat_id} ({chat_name})")

                    # Save if new chat IDs were found
                    if len(self.chat_ids) > initial_count:
                        self.save_chat_ids()
                        logger.info(f"✓ Total chat IDs: {len(self.chat_ids)}")

                    if self.chat_ids:
                        return True
                    else:
                        logger.warning("⚠️  No messages found - users need to start the bot first")
                        return False
                else:
                    # If we have saved chat IDs, use those
                    if self.chat_ids:
                        logger.info(f"✓ Using {len(self.chat_ids)} saved chat ID(s)")
                        return True
                    else:
                        logger.error(f"❌ No saved chat IDs and API returned: {data}")
                        return False
            else:
                # If we have saved chat IDs, use those even if API fails
                if self.chat_ids:
                    logger.warning(f"⚠️  API failed but using {len(self.chat_ids)} saved chat ID(s)")
                    return True
                else:
                    logger.error(f"❌ Failed to get updates: {response.status_code}")
                    return False

        except Exception as e:
            # If we have saved chat IDs, use those even if API fails
            if self.chat_ids:
                logger.warning(f"⚠️  API error but using {len(self.chat_ids)} saved chat ID(s)")
                return True
            else:
                logger.error(f"❌ Failed to get chat IDs: {e}")
                return False

    def send_to_telegram(self, backup_file, chat_id):
        """Send backup file to Telegram"""
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendDocument"

            # Get database stats (but don't parse as markdown to avoid issues)
            stats = self.get_database_stats()

            # Create caption - use HTML instead of Markdown for better compatibility
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            size_mb = backup_file.stat().st_size / (1024 * 1024)

            # Escape HTML special characters in stats
            stats_escaped = stats.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

            caption = f"""🗄️ <b>Database Backup</b>

📅 Date: {timestamp}
💾 Database: {self.db_name}
📦 Size: {size_mb:.2f} MB
🖥️ Host: {self.db_host}

📊 <b>Statistics</b>
<pre>{stats_escaped}</pre>

✅ Backup completed successfully"""

            # Send file
            with open(backup_file, 'rb') as f:
                files = {'document': f}
                data = {
                    'chat_id': chat_id,
                    'caption': caption,
                    'parse_mode': 'HTML'
                }

                response = requests.post(url, data=data, files=files, timeout=300)

                if response.status_code == 200:
                    logger.info(f"✓ Backup sent to {chat_id}")
                    return True
                else:
                    logger.error(f"❌ Telegram API error: {response.text}")
                    return False

        except Exception as e:
            logger.error(f"❌ Failed to send to {chat_id}: {e}")
            return False

    def cleanup_old_backups(self):
        """Remove backups older than retention period"""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.retention_days)
            deleted_count = 0

            for backup_file in self.backup_dir.glob("*.sql.gz"):
                file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)

                if file_time < cutoff_date:
                    backup_file.unlink()
                    deleted_count += 1
                    logger.info(f"Deleted old backup: {backup_file.name}")

            if deleted_count > 0:
                logger.info(f"✓ Cleaned up {deleted_count} old backup(s)")

        except Exception as e:
            logger.warning(f"Cleanup warning: {e}")

    def run_backup(self):
        """Run complete backup process"""
        logger.info("=" * 50)
        logger.info("Starting backup process")
        logger.info("=" * 50)

        # Get chat IDs from users who have messaged the bot
        logger.info("Discovering chat IDs from bot messages...")
        self.get_chat_ids_from_updates()

        if not self.chat_ids:
            logger.error("❌ No chat IDs found!")
            logger.error("💡 Users need to start a chat with the bot first")
            logger.error("💡 Tell users to search for your bot on Telegram and click START")
            return False

        # Create backup
        backup_file = self.create_backup()
        if not backup_file:
            logger.error("❌ Backup failed - aborting")
            return False

        # Send to all discovered recipients
        success_count = 0
        total_recipients = len(self.chat_ids)

        for chat_id in self.chat_ids:
            logger.info(f"Sending to chat ID: {chat_id}")
            if self.send_to_telegram(backup_file, chat_id):
                success_count += 1

        # Cleanup old backups
        self.cleanup_old_backups()

        logger.info("=" * 50)
        logger.info(f"Backup complete: {success_count}/{total_recipients} recipients received backup")
        logger.info("=" * 50)

        return success_count > 0

    def run_scheduled(self, interval_hours=24):
        """Run backup on schedule"""
        logger.info(f"Starting scheduled backup service (every {interval_hours} hours)")

        while True:
            try:
                self.run_backup()

                # Wait for next backup
                logger.info(f"Next backup in {interval_hours} hours")
                time.sleep(interval_hours * 3600)

            except KeyboardInterrupt:
                logger.info("Service stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in scheduled run: {e}")
                logger.info("Retrying in 1 hour...")
                time.sleep(3600)


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="PostgreSQL Telegram Backup Service")
    parser.add_argument('--once', action='store_true', help='Run backup once and exit')
    parser.add_argument('--interval', type=int, default=24, help='Backup interval in hours (default: 24)')

    args = parser.parse_args()

    service = TelegramBackupService()

    if args.once:
        # Run once and exit
        success = service.run_backup()
        sys.exit(0 if success else 1)
    else:
        # Run on schedule
        service.run_scheduled(args.interval)


if __name__ == "__main__":
    main()
