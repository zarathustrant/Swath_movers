#!/usr/bin/env python3
"""
Telegram Bot Service - Command Handler
Separate service from backup - handles user commands continuously
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import requests
import time

# Import our bot modules
from telegram_bot_commands import CommandHandler
from app import get_postgres_connection, return_postgres_connection

# Setup logging
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "telegram_bot.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class TelegramBotService:
    """Telegram Bot Service - Handles commands continuously"""

    def __init__(self):
        """Initialize the bot service"""
        # Load environment variables
        env_path = Path(__file__).parent / ".env"
        if not env_path.exists():
            logger.error(f"❌ .env file not found at {env_path}")
            sys.exit(1)

        load_dotenv(env_path)

        # Load configuration
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not self.bot_token:
            logger.error("❌ TELEGRAM_BOT_TOKEN not found in .env file")
            sys.exit(1)

        # Initialize command handler
        self.command_handler = CommandHandler(
            get_postgres_connection,
            return_postgres_connection,
            self.bot_token
        )

        # Track last update ID
        self.last_update_id = 0

        # Poll interval (seconds)
        self.poll_interval = 2

        logger.info("✓ Telegram Bot Service initialized")
        logger.info(f"✓ Bot token: {self.bot_token[:10]}...")

    def get_updates(self, timeout: int = 30) -> list:
        """
        Get updates from Telegram using long polling

        Args:
            timeout: Long polling timeout in seconds

        Returns:
            List of update objects
        """
        url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"
        params = {
            'offset': self.last_update_id + 1,
            'timeout': timeout,
            'allowed_updates': ['message']
        }

        try:
            response = requests.get(url, params=params, timeout=timeout + 5)

            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    return data.get('result', [])
                else:
                    logger.error(f"Telegram API error: {data}")
                    return []
            else:
                logger.error(f"HTTP error {response.status_code}: {response.text}")
                return []

        except requests.exceptions.Timeout:
            # Timeout is normal with long polling
            return []
        except Exception as e:
            logger.error(f"Error getting updates: {e}")
            return []

    def process_update(self, update: dict):
        """
        Process a single update from Telegram

        Args:
            update: Update object from Telegram
        """
        try:
            # Update last_update_id
            update_id = update.get('update_id')
            if update_id:
                self.last_update_id = max(self.last_update_id, update_id)

            # Extract message
            message = update.get('message')
            if not message:
                return

            # Extract chat and text
            chat = message.get('chat', {})
            chat_id = chat.get('id')
            text = message.get('text', '')

            if not chat_id or not text:
                return

            # Log incoming message
            username = message.get('from', {}).get('first_name', 'Unknown')
            logger.info(f"Message from {username} (ID: {chat_id}): {text}")

            # Check if it's a command
            if not text.startswith('/'):
                return

            # Handle command
            response = self.command_handler.handle_message(chat_id, text)

            if response:
                self.send_response(chat_id, response)

        except Exception as e:
            logger.error(f"Error processing update: {e}", exc_info=True)

    def send_response(self, chat_id: int, response: dict):
        """
        Send response to user

        Args:
            chat_id: Telegram chat ID
            response: Response dict from command handler
        """
        try:
            response_type = response.get('type')

            if response_type == 'text':
                # Send text message
                content = response.get('content')
                self.command_handler.send_message(chat_id, content)

            elif response_type == 'document':
                # Send document
                content = response.get('content')  # BytesIO
                filename = response.get('filename')
                caption = response.get('caption')

                self.command_handler.send_document(chat_id, content, filename, caption)

            elif response_type == 'photo':
                # Send photo
                content = response.get('content')  # BytesIO
                caption = response.get('caption')

                self.command_handler.send_photo(chat_id, content, caption)

            else:
                logger.warning(f"Unknown response type: {response_type}")

        except Exception as e:
            logger.error(f"Error sending response: {e}", exc_info=True)

    def run(self):
        """Main bot loop - continuously poll for updates"""
        logger.info("🤖 Telegram Bot Service started")
        logger.info("🔄 Polling for updates...")

        # Send startup notification to first chat ID if available
        try:
            chat_id = os.getenv('TELEGRAM_CHAT_ID_1')
            if chat_id:
                startup_msg = f"""🤖 <b>Bot Started</b>

Service: Telegram Bot (Commands)
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Status: ✅ Online

Ready to receive commands!
Type /help for available commands."""

                self.command_handler.send_message(int(chat_id), startup_msg)
        except Exception as e:
            logger.warning(f"Could not send startup notification: {e}")

        # Main polling loop
        consecutive_errors = 0
        max_errors = 5

        while True:
            try:
                # Get updates from Telegram
                updates = self.get_updates(timeout=30)

                if updates:
                    logger.info(f"📬 Received {len(updates)} update(s)")

                    # Process each update
                    for update in updates:
                        self.process_update(update)

                    # Reset error counter on success
                    consecutive_errors = 0

                else:
                    # No updates - this is normal
                    pass

            except KeyboardInterrupt:
                logger.info("🛑 Bot stopped by user")
                break

            except Exception as e:
                consecutive_errors += 1
                logger.error(f"Error in main loop (attempt {consecutive_errors}/{max_errors}): {e}")

                # If too many consecutive errors, wait longer
                if consecutive_errors >= max_errors:
                    logger.error(f"Too many consecutive errors ({consecutive_errors}), sleeping for 60 seconds...")
                    time.sleep(60)
                    consecutive_errors = 0
                else:
                    time.sleep(5)

        logger.info("🛑 Telegram Bot Service stopped")


def main():
    """Main entry point"""
    try:
        # Create and run bot service
        bot = TelegramBotService()
        bot.run()

    except KeyboardInterrupt:
        logger.info("\n🛑 Service stopped by user")
        sys.exit(0)

    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
