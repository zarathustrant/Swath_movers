#!/usr/bin/env python3
"""
Command Handler Module for Telegram Bot
Routes and processes all user commands
"""

import re
import logging
from typing import Dict, Tuple, Optional, List
from datetime import datetime
import requests

# Import our modules
from telegram_bot_queries import DatabaseQueries
from telegram_bot_stats import StatisticsCalculator
from telegram_bot_formatting import TelegramFormatter
from telegram_bot_charts import ChartGenerator
from telegram_bot_exports import DataExporter

logger = logging.getLogger(__name__)


class CommandHandler:
    """Handle and route Telegram bot commands"""

    def __init__(self, db_connection_func, db_return_func, bot_token: str):
        """
        Initialize command handler

        Args:
            db_connection_func: Function to get DB connection
            db_return_func: Function to return DB connection
            bot_token: Telegram bot token
        """
        self.bot_token = bot_token

        # Initialize modules
        self.db_queries = DatabaseQueries(db_connection_func, db_return_func)
        self.stats = StatisticsCalculator(self.db_queries)
        self.formatter = TelegramFormatter()
        self.charts = ChartGenerator()
        self.exporter = DataExporter(self.db_queries)

        # Rate limiting (simple in-memory)
        self.user_commands = {}  # {chat_id: [timestamps]}
        self.max_commands_per_minute = 10

        logger.info("CommandHandler initialized")

    def parse_command(self, message_text: str) -> Tuple[str, List[str]]:
        """
        Parse command and arguments from message

        Args:
            message_text: Raw message text

        Returns:
            Tuple of (command, arguments_list)
        """
        # Remove leading/trailing whitespace
        text = message_text.strip()

        # Check if it starts with /
        if not text.startswith('/'):
            return ('', [])

        # Split command and arguments
        parts = text.split()
        command = parts[0].lower().replace('/', '')
        args = parts[1:] if len(parts) > 1 else []

        return (command, args)

    def check_rate_limit(self, chat_id: int) -> bool:
        """
        Check if user is within rate limits

        Args:
            chat_id: Telegram chat ID

        Returns:
            True if within limits, False if exceeded
        """
        current_time = datetime.now()
        minute_ago = current_time.timestamp() - 60

        # Get user's command history
        if chat_id not in self.user_commands:
            self.user_commands[chat_id] = []

        # Remove commands older than 1 minute
        self.user_commands[chat_id] = [
            ts for ts in self.user_commands[chat_id] if ts > minute_ago
        ]

        # Check limit
        if len(self.user_commands[chat_id]) >= self.max_commands_per_minute:
            return False

        # Add current command
        self.user_commands[chat_id].append(current_time.timestamp())
        return True

    def handle_message(self, chat_id: int, message_text: str) -> Dict:
        """
        Main message handler - routes commands to appropriate handlers

        Args:
            chat_id: Telegram chat ID
            message_text: Message text from user

        Returns:
            Dict with response data: {
                'type': 'text' | 'photo' | 'document',
                'content': text or file data,
                'caption': optional caption for files,
                'filename': optional filename for documents
            }
        """
        try:
            # Check rate limit
            if not self.check_rate_limit(chat_id):
                return {
                    'type': 'text',
                    'content': self.formatter.format_error_message(
                        "Rate limit exceeded. Please wait a minute and try again."
                    )
                }

            # Parse command
            command, args = self.parse_command(message_text)

            if not command:
                return None  # Not a command, ignore

            logger.info(f"Processing command: /{command} with args: {args}")

            # Route to handler
            handler_map = {
                'start': self.cmd_start,
                'help': self.cmd_help,
                'stats': self.cmd_stats,
                'today': self.cmd_today,
                'line': self.cmd_line,
                'lines': self.cmd_lines,
                'swath': self.cmd_swath,
                'swaths': self.cmd_swaths,
                'progress': self.cmd_progress,
                'retrieval': self.cmd_retrieval,
                'users': self.cmd_users,
                'backup': self.cmd_backup,
                'export': self.cmd_export,
                'alerts': self.cmd_alerts,
                'coverage': self.cmd_coverage,
                'gaps': self.cmd_gaps,
            }

            handler = handler_map.get(command)

            if handler:
                return handler(chat_id, args)
            else:
                return {
                    'type': 'text',
                    'content': self.formatter.format_error_message(
                        f"Unknown command: /{command}\n\nUse /help to see available commands."
                    )
                }

        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)
            return {
                'type': 'text',
                'content': self.formatter.format_error_message(
                    f"An error occurred: {str(e)}\n\nPlease try again or contact support."
                )
            }

    # === COMMAND HANDLERS ===

    def cmd_start(self, chat_id: int, args: List[str]) -> Dict:
        """Handle /start command"""
        message = """👋 <b>Welcome to Swath Movers Bot!</b>

I'm your seismic survey management assistant. I can help you:

📊 Check project statistics
📍 Monitor line and swath status
📈 Track deployment progress
💾 Export data and generate reports
🔔 Get alerts and notifications

<b>Quick Start:</b>
• /help - See all commands
• /stats - Project overview
• /line 5000 - Check specific line
• /swaths - Compare all swaths

Let's get started! Try /stats to see your project overview.
"""
        return {'type': 'text', 'content': message}

    def cmd_help(self, chat_id: int, args: List[str]) -> Dict:
        """Handle /help command"""
        return {
            'type': 'text',
            'content': self.formatter.format_help_message()
        }

    def cmd_stats(self, chat_id: int, args: List[str]) -> Dict:
        """Handle /stats command"""
        summary = self.stats.get_project_summary()
        return {
            'type': 'text',
            'content': self.formatter.format_stats_message(summary)
        }

    def cmd_today(self, chat_id: int, args: List[str]) -> Dict:
        """Handle /today command"""
        today_stats = self.db_queries.get_today_stats()
        return {
            'type': 'text',
            'content': self.formatter.format_today_message(today_stats)
        }

    def cmd_line(self, chat_id: int, args: List[str]) -> Dict:
        """Handle /line [number] command"""
        if not args:
            return {
                'type': 'text',
                'content': self.formatter.format_error_message(
                    "Please specify a line number.\n\nExample: /line 5000"
                )
            }

        try:
            line_number = int(args[0])
            line_stats = self.stats.get_line_details(line_number)

            # Check if line exists
            if line_stats.get('total_points', 0) == 0:
                return {
                    'type': 'text',
                    'content': self.formatter.format_error_message(
                        f"Line {line_number} not found in database."
                    )
                }

            return {
                'type': 'text',
                'content': self.formatter.format_line_details(line_stats)
            }

        except ValueError:
            return {
                'type': 'text',
                'content': self.formatter.format_error_message(
                    "Invalid line number. Please use a numeric value.\n\nExample: /line 5000"
                )
            }

    def cmd_lines(self, chat_id: int, args: List[str]) -> Dict:
        """Handle /lines [filter] command"""
        filter_type = args[0].lower() if args else 'all'

        # Parse range filter (e.g., "range 5000-5100")
        line_range = None
        if filter_type == 'range' and len(args) > 1:
            try:
                range_str = args[1]
                if '-' in range_str:
                    start, end = map(int, range_str.split('-'))
                    line_range = (start, end)
                    filter_type = 'all'  # Get all lines, then filter by range
            except ValueError:
                return {
                    'type': 'text',
                    'content': self.formatter.format_error_message(
                        "Invalid range format.\n\nExample: /lines range 5000-5100"
                    )
                }

        # Validate filter type
        valid_filters = ['all', 'complete', 'incomplete', 'active']
        if filter_type not in valid_filters:
            return {
                'type': 'text',
                'content': self.formatter.format_error_message(
                    f"Invalid filter: {filter_type}\n\nValid filters: {', '.join(valid_filters)}"
                )
            }

        # Get lines
        lines = self.stats.get_lines_by_filter(filter_type, line_range)

        if not lines:
            return {
                'type': 'text',
                'content': f"No lines found for filter: <b>{filter_type}</b>"
            }

        # Format message
        range_text = f" ({line_range[0]}-{line_range[1]})" if line_range else ""
        message = f"📋 <b>Lines - {filter_type.title()}{range_text}</b>\n\n"

        # Show top 20 lines
        for line_data in lines[:20]:
            message += self.formatter.format_line_summary(line_data) + "\n"

        if len(lines) > 20:
            message += f"\n... and {len(lines) - 20} more lines"

        message += f"\n\n<b>Total:</b> {len(lines)} lines"

        return {'type': 'text', 'content': message}

    def cmd_swath(self, chat_id: int, args: List[str]) -> Dict:
        """Handle /swath [number] command"""
        if not args:
            return {
                'type': 'text',
                'content': self.formatter.format_error_message(
                    "Please specify a swath number (1-8).\n\nExample: /swath 3"
                )
            }

        try:
            swath_number = int(args[0])

            if swath_number < 1 or swath_number > 8:
                return {
                    'type': 'text',
                    'content': self.formatter.format_error_message(
                        "Swath number must be between 1 and 8."
                    )
                }

            swath_stats = self.stats.get_swath_details(swath_number)
            return {
                'type': 'text',
                'content': self.formatter.format_swath_details(swath_stats)
            }

        except ValueError:
            return {
                'type': 'text',
                'content': self.formatter.format_error_message(
                    "Invalid swath number. Please use 1-8.\n\nExample: /swath 3"
                )
            }

    def cmd_swaths(self, chat_id: int, args: List[str]) -> Dict:
        """Handle /swaths command"""
        all_swaths = self.stats.get_all_swaths_comparison()
        return {
            'type': 'text',
            'content': self.formatter.format_swaths_comparison(all_swaths)
        }

    def cmd_progress(self, chat_id: int, args: List[str]) -> Dict:
        """Handle /progress [type] command"""
        deployment_type = args[0].upper() if args else None

        progress_summary = self.stats.get_progress_summary(deployment_type)
        return {
            'type': 'text',
            'content': self.formatter.format_progress_report(progress_summary['progress'])
        }

    def cmd_retrieval(self, chat_id: int, args: List[str]) -> Dict:
        """Handle /retrieval command"""
        retrieval = self.stats.get_retrieval_priority_list()
        return {
            'type': 'text',
            'content': self.formatter.format_retrieval_report(retrieval)
        }

    def cmd_users(self, chat_id: int, args: List[str]) -> Dict:
        """Handle /users command"""
        user_summary = self.stats.get_user_summary()
        return {
            'type': 'text',
            'content': self.formatter.format_user_stats(user_summary['users'])
        }

    def cmd_backup(self, chat_id: int, args: List[str]) -> Dict:
        """Handle /backup command"""
        import subprocess
        import gzip
        import shutil
        from pathlib import Path
        from datetime import datetime
        import os

        try:
            # Send initial message
            self.send_message(chat_id, "⏳ <b>Backup Triggered</b>\n\nCreating database backup...")

            # Get database credentials from environment
            from dotenv import load_dotenv
            env_path = Path(__file__).parent / ".env"
            load_dotenv(env_path)

            db_name = os.getenv("DB_NAME", "swath_movers")
            db_user = os.getenv("DB_USER", "aerys")
            db_password = os.getenv("DB_PASSWORD", "")
            db_host = os.getenv("DB_HOST", "localhost")
            db_port = os.getenv("DB_PORT", "5432")

            # Create backup directory
            backup_dir = Path(__file__).parent / "backups"
            backup_dir.mkdir(exist_ok=True)

            # Create backup
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = backup_dir / f"{db_name}_backup_{timestamp}.sql"

            logger.info(f"Creating backup: {backup_file.name}")

            # Run pg_dump
            env = os.environ.copy()
            env['PGPASSWORD'] = db_password

            cmd = [
                'pg_dump',
                '-h', db_host,
                '-p', db_port,
                '-U', db_user,
                '-d', db_name,
                '-f', str(backup_file)
            ]

            result = subprocess.run(cmd, env=env, capture_output=True, text=True)

            if result.returncode != 0:
                logger.error(f"pg_dump failed: {result.stderr}")
                return {
                    'type': 'text',
                    'content': f"❌ <b>Backup Failed</b>\n\nError: {result.stderr[:200]}"
                }

            # Compress backup
            backup_gz = Path(f"{backup_file}.gz")
            with open(backup_file, 'rb') as f_in:
                with gzip.open(backup_gz, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)

            # Remove uncompressed file
            backup_file.unlink()

            # Get file size
            size_mb = backup_gz.stat().st_size / (1024 * 1024)
            logger.info(f"Backup compressed: {size_mb:.2f} MB")

            # Send file to Telegram
            url = f"https://api.telegram.org/bot{self.bot_token}/sendDocument"

            caption = f"""🗄️ <b>Database Backup</b>

📅 Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
📦 Database: {db_name}
💾 Size: {size_mb:.2f} MB

✅ Backup completed successfully"""

            with open(backup_gz, 'rb') as f:
                files = {'document': f}
                data = {
                    'chat_id': chat_id,
                    'caption': caption,
                    'parse_mode': 'HTML'
                }

                response = requests.post(url, files=files, data=data, timeout=120)

                if response.status_code == 200:
                    logger.info(f"✓ Backup sent to chat {chat_id}")
                    # Don't return anything - file is already sent
                    return {'type': 'none'}
                else:
                    logger.error(f"Failed to send backup: {response.text}")
                    return {
                        'type': 'text',
                        'content': f"❌ <b>Failed to send backup</b>\n\nFile created but couldn't send: {response.text[:200]}"
                    }

        except Exception as e:
            logger.error(f"Backup command failed: {e}", exc_info=True)
            return {
                'type': 'text',
                'content': f"❌ <b>Backup Failed</b>\n\nError: {str(e)}"
            }

    def cmd_export(self, chat_id: int, args: List[str]) -> Dict:
        """Handle /export [type] [id] command"""
        if not args:
            return {
                'type': 'text',
                'content': self.formatter.format_error_message(
                    "Please specify export type.\n\nExamples:\n• /export line 5000\n• /export swath 3\n• /export retrieval\n• /export all"
                )
            }

        export_type = args[0].lower()

        try:
            if export_type == 'line':
                if len(args) < 2:
                    return {
                        'type': 'text',
                        'content': self.formatter.format_error_message("Please specify line number.\n\nExample: /export line 5000")
                    }
                line_number = int(args[1])
                csv_data = self.exporter.export_line_csv(line_number)
                filename = self.exporter.generate_filename('line', str(line_number))

            elif export_type == 'swath':
                if len(args) < 2:
                    return {
                        'type': 'text',
                        'content': self.formatter.format_error_message("Please specify swath number.\n\nExample: /export swath 3")
                    }
                swath_number = int(args[1])
                if swath_number < 1 or swath_number > 8:
                    return {
                        'type': 'text',
                        'content': self.formatter.format_error_message("Swath number must be between 1 and 8.")
                    }
                csv_data = self.exporter.export_swath_csv(swath_number)
                filename = self.exporter.generate_filename('swath', str(swath_number))

            elif export_type == 'retrieval':
                csv_data = self.exporter.export_retrieval_csv()
                filename = self.exporter.generate_filename('retrieval')

            elif export_type == 'all':
                csv_data = self.exporter.export_all_lines_csv()
                filename = self.exporter.generate_filename('all_lines')

            else:
                return {
                    'type': 'text',
                    'content': self.formatter.format_error_message(
                        f"Unknown export type: {export_type}\n\nValid types: line, swath, retrieval, all"
                    )
                }

            if csv_data:
                return {
                    'type': 'document',
                    'content': csv_data,
                    'filename': filename,
                    'caption': f"📊 Export: {export_type.title()}\n\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                }
            else:
                return {
                    'type': 'text',
                    'content': self.formatter.format_error_message("Failed to generate export. Please try again.")
                }

        except ValueError as e:
            return {
                'type': 'text',
                'content': self.formatter.format_error_message(f"Invalid input: {str(e)}")
            }
        except Exception as e:
            logger.error(f"Export error: {e}", exc_info=True)
            return {
                'type': 'text',
                'content': self.formatter.format_error_message(f"Export failed: {str(e)}")
            }

    def cmd_alerts(self, chat_id: int, args: List[str]) -> Dict:
        """Handle /alerts command"""
        alerts = self.stats.get_alerts()

        if not alerts:
            return {
                'type': 'text',
                'content': "✅ <b>No Critical Alerts</b>\n\nAll systems looking good!"
            }

        message = "🚨 <b>Critical Alerts</b>\n\n"

        # Group by priority
        high = [a for a in alerts if a['priority'] == 'high']
        medium = [a for a in alerts if a['priority'] == 'medium']

        if high:
            message += "🔴 <b>HIGH PRIORITY</b>\n"
            for alert in high[:5]:
                message += f"• {alert['message']}\n"
            message += "\n"

        if medium:
            message += "🟡 <b>MEDIUM PRIORITY</b>\n"
            for alert in medium[:10]:
                message += f"• {alert['message']}\n"
            message += "\n"

        message += f"<b>Total Alerts:</b> {len(alerts)}"

        return {'type': 'text', 'content': message}

    def cmd_coverage(self, chat_id: int, args: List[str]) -> Dict:
        """Handle /coverage command"""
        coverage = self.stats.get_coverage_analysis()

        message = f"""📊 <b>Survey Coverage Analysis</b>

🎯 <b>Overall Coverage</b>
• Total Shotpoints: {self.formatter.format_number(coverage['total_shotpoints'])}
• Points with Deployments: {self.formatter.format_number(coverage['points_with_deployments'])}
• Coverage: {self.formatter.format_percentage(coverage['overall_coverage_pct'])}

📍 <b>Lines by Coverage</b>
• High Coverage (>80%): {coverage['high_coverage_lines']} lines
• Medium Coverage (50-80%): {coverage['medium_coverage_lines']} lines
• Low Coverage (<50%): {coverage['low_coverage_lines']} lines
"""

        # Add gaps
        if coverage['gaps']:
            message += "\n⚠️ <b>Low Coverage Lines:</b>\n"
            for gap in coverage['gaps'][:5]:
                message += f"• Line {gap['line']}: {self.formatter.format_percentage(gap['coverage_pct'])}\n"

        return {'type': 'text', 'content': message}

    def cmd_gaps(self, chat_id: int, args: List[str]) -> Dict:
        """Handle /gaps [line|swath|all] [number] command"""
        if not args:
            # No args - show project-wide gap statistics
            try:
                stats = self.db_queries.get_gap_statistics()
                return {
                    'type': 'text',
                    'content': self.formatter.format_gap_statistics(stats)
                }
            except Exception as e:
                logger.error(f"Error getting gap statistics: {e}", exc_info=True)
                return {
                    'type': 'text',
                    'content': self.formatter.format_error_message(
                        f"Failed to get gap statistics: {str(e)}"
                    )
                }

        sub_command = args[0].lower()

        try:
            if sub_command == 'line':
                # /gaps line [number]
                if len(args) < 2:
                    return {
                        'type': 'text',
                        'content': self.formatter.format_error_message(
                            "Please specify a line number.\n\nExample: /gaps line 5000"
                        )
                    }

                line_number = int(args[1])
                min_gap_size = 1  # Default minimum gap size (1 point = gap)

                # Optional: allow custom gap size - /gaps line 5000 10
                if len(args) > 2:
                    try:
                        min_gap_size = int(args[2])
                    except ValueError:
                        pass

                gaps = self.db_queries.get_line_gaps(line_number, min_gap_size)
                return {
                    'type': 'text',
                    'content': self.formatter.format_line_gaps(line_number, gaps)
                }

            elif sub_command == 'swath':
                # /gaps swath [number]
                if len(args) < 2:
                    return {
                        'type': 'text',
                        'content': self.formatter.format_error_message(
                            "Please specify a swath number (1-8).\n\nExample: /gaps swath 3"
                        )
                    }

                swath_number = int(args[1])

                if swath_number < 1 or swath_number > 8:
                    return {
                        'type': 'text',
                        'content': self.formatter.format_error_message(
                            "Swath number must be between 1 and 8."
                        )
                    }

                min_gap_size = 1  # Default minimum gap size (1 point = gap)
                if len(args) > 2:
                    try:
                        min_gap_size = int(args[2])
                    except ValueError:
                        pass

                swath_gaps = self.db_queries.get_swath_gaps(swath_number, min_gap_size)

                # Format response using swath gap summary
                message = f"🔍 <b>Swath {swath_number} - Gap Analysis</b>\n\n"

                if not swath_gaps:
                    message += "✅ No gaps detected in this swath!"
                else:
                    total_gaps = sum(len(line_data['gaps']) for line_data in swath_gaps)
                    total_gap_points = sum(
                        sum(gap['size'] for gap in line_data['gaps'])
                        for line_data in swath_gaps
                    )

                    message += f"⚠️ <b>Total Gaps:</b> {total_gaps}\n"
                    message += f"📍 <b>Total Gap Points:</b> {total_gap_points}\n\n"
                    message += "<b>Lines with Gaps:</b>\n"

                    for line_data in swath_gaps[:15]:  # Show first 15 lines
                        line = line_data['line']
                        gaps = line_data['gaps']
                        gap_count = len(gaps)
                        gap_points = sum(gap['size'] for gap in gaps)

                        message += f"\n• Line {line}: {gap_count} gap(s), {gap_points} points\n"

                        # Show first 3 gaps for each line
                        for gap in gaps[:3]:
                            message += f"  └ SP {gap['start_shotpoint']}-{gap['end_shotpoint']} ({gap['size']} pts)\n"

                        if len(gaps) > 3:
                            message += f"  └ ... and {len(gaps) - 3} more gap(s)\n"

                    if len(swath_gaps) > 15:
                        message += f"\n... and {len(swath_gaps) - 15} more lines"

                return {'type': 'text', 'content': message}

            elif sub_command == 'all':
                # /gaps all - show all lines with gaps
                min_gap_size = 1  # Default minimum gap size (1 point = gap)
                if len(args) > 1:
                    try:
                        min_gap_size = int(args[1])
                    except ValueError:
                        pass

                lines_with_gaps = self.db_queries.get_all_lines_with_gaps(min_gap_size)
                return {
                    'type': 'text',
                    'content': self.formatter.format_all_gaps_summary(lines_with_gaps)
                }

            else:
                return {
                    'type': 'text',
                    'content': self.formatter.format_error_message(
                        f"Invalid gaps sub-command: {sub_command}\n\n"
                        "Valid commands:\n"
                        "• /gaps - Project gap statistics\n"
                        "• /gaps line [number] - Line gap analysis\n"
                        "• /gaps swath [number] - Swath gap analysis\n"
                        "• /gaps all - All lines with gaps"
                    )
                }

        except ValueError as e:
            return {
                'type': 'text',
                'content': self.formatter.format_error_message(
                    f"Invalid input: {str(e)}\n\nPlease use numeric values for line/swath numbers."
                )
            }
        except Exception as e:
            logger.error(f"Error in gaps command: {e}", exc_info=True)
            return {
                'type': 'text',
                'content': self.formatter.format_error_message(
                    f"Failed to analyze gaps: {str(e)}"
                )
            }

    def send_message(self, chat_id: int, text: str, parse_mode: str = 'HTML'):
        """
        Send text message to Telegram

        Args:
            chat_id: Telegram chat ID
            text: Message text
            parse_mode: HTML or Markdown
        """
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': parse_mode
        }

        try:
            response = requests.post(url, data=data, timeout=30)
            if response.status_code == 200:
                logger.info(f"Message sent to {chat_id}")
                return True
            else:
                logger.error(f"Failed to send message: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False

    def send_document(self, chat_id: int, document: bytes, filename: str, caption: str = None):
        """
        Send document to Telegram

        Args:
            chat_id: Telegram chat ID
            document: Document bytes (BytesIO)
            filename: Filename
            caption: Optional caption
        """
        url = f"https://api.telegram.org/bot{self.bot_token}/sendDocument"

        try:
            files = {'document': (filename, document, 'application/octet-stream')}
            data = {'chat_id': chat_id}
            if caption:
                data['caption'] = caption
                data['parse_mode'] = 'HTML'

            response = requests.post(url, data=data, files=files, timeout=120)
            if response.status_code == 200:
                logger.info(f"Document sent to {chat_id}: {filename}")
                return True
            else:
                logger.error(f"Failed to send document: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error sending document: {e}")
            return False

    def send_photo(self, chat_id: int, photo: bytes, caption: str = None):
        """
        Send photo to Telegram

        Args:
            chat_id: Telegram chat ID
            photo: Photo bytes (BytesIO)
            caption: Optional caption
        """
        url = f"https://api.telegram.org/bot{self.bot_token}/sendPhoto"

        try:
            files = {'photo': photo}
            data = {'chat_id': chat_id}
            if caption:
                data['caption'] = caption
                data['parse_mode'] = 'HTML'

            response = requests.post(url, data=data, files=files, timeout=120)
            if response.status_code == 200:
                logger.info(f"Photo sent to {chat_id}")
                return True
            else:
                logger.error(f"Failed to send photo: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error sending photo: {e}")
            return False
