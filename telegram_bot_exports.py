#!/usr/bin/env python3
"""
Data Export Module for Telegram Bot
Handles CSV and Excel exports of deployment data
"""

import csv
from io import StringIO, BytesIO
from typing import Dict, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class DataExporter:
    """Export data to various formats"""

    def __init__(self, db_queries):
        """
        Initialize data exporter

        Args:
            db_queries: DatabaseQueries instance
        """
        self.db = db_queries

    def export_line_csv(self, line_number: int) -> BytesIO:
        """
        Export single line data to CSV

        Args:
            line_number: Line number to export

        Returns:
            BytesIO containing CSV data
        """
        try:
            logger.info(f"Exporting line {line_number} to CSV")

            # Get line details
            query = f"""
            SELECT
                c.line,
                c.shotpoint,
                c.latitude,
                c.longitude,
                c.type,
                d.deployment_type,
                d.username,
                d.timestamp
            FROM coordinates c
            LEFT JOIN global_deployments d
                ON c.line = d.line AND c.shotpoint = d.shotpoint
            WHERE c.line = {line_number}
            ORDER BY c.shotpoint
            """

            # Execute query through db connection
            results = self.db._execute_query(query)

            # Create CSV in memory
            output = StringIO()
            writer = csv.writer(output)

            # Write header
            writer.writerow([
                'Line', 'Shotpoint', 'Latitude', 'Longitude',
                'Type', 'Deployment Type', 'Username', 'Timestamp'
            ])

            # Write data
            for row in results:
                writer.writerow(row)

            # Convert to bytes
            csv_bytes = BytesIO(output.getvalue().encode('utf-8'))
            csv_bytes.seek(0)

            logger.info(f"Line {line_number} CSV exported: {len(results)} rows")
            return csv_bytes

        except Exception as e:
            logger.error(f"Error exporting line {line_number} to CSV: {e}")
            return None

    def export_swath_csv(self, swath_number: int) -> BytesIO:
        """
        Export swath data to CSV

        Args:
            swath_number: Swath number (1-8) to export

        Returns:
            BytesIO containing CSV data
        """
        try:
            logger.info(f"Exporting swath {swath_number} to CSV")

            # Get swath deployments
            query = f"""
            SELECT
                line,
                shotpoint,
                deployment_type,
                username,
                timestamp
            FROM swath_{swath_number}
            ORDER BY line, shotpoint
            """

            results = self.db._execute_query(query)

            # Create CSV
            output = StringIO()
            writer = csv.writer(output)

            # Write header
            writer.writerow([
                'Line', 'Shotpoint', 'Deployment Type', 'Username', 'Timestamp'
            ])

            # Write data
            for row in results:
                writer.writerow(row)

            # Convert to bytes
            csv_bytes = BytesIO(output.getvalue().encode('utf-8'))
            csv_bytes.seek(0)

            logger.info(f"Swath {swath_number} CSV exported: {len(results)} rows")
            return csv_bytes

        except Exception as e:
            logger.error(f"Error exporting swath {swath_number} to CSV: {e}")
            return None

    def export_retrieval_csv(self) -> BytesIO:
        """
        Export retrieval status report to CSV

        Returns:
            BytesIO containing CSV data
        """
        try:
            logger.info("Exporting retrieval report to CSV")

            # Get all lines with outstanding items
            all_lines = self.db.get_all_lines_summary()

            # Filter lines with outstanding items
            lines_with_outstanding = [
                line for line in all_lines if line.get('outstanding', 0) > 0
            ]

            # Sort by outstanding count (descending)
            lines_with_outstanding.sort(key=lambda x: x['outstanding'], reverse=True)

            # Create CSV
            output = StringIO()
            writer = csv.writer(output)

            # Write header
            writer.writerow([
                'Line', 'Total Points', 'Deployed', 'Retrieved',
                'Outstanding', 'Completion %', 'Priority', 'Last Activity'
            ])

            # Write data
            for line in lines_with_outstanding:
                outstanding = line['outstanding']

                # Determine priority
                if outstanding > 50:
                    priority = 'HIGH'
                elif outstanding > 20:
                    priority = 'MEDIUM'
                else:
                    priority = 'LOW'

                completion = line.get('completion_pct', 0)
                last_activity = line.get('last_activity')
                last_activity_str = last_activity.strftime('%Y-%m-%d %H:%M') if last_activity else 'Never'

                writer.writerow([
                    line['line'],
                    line['total_points'],
                    line['deployed'],
                    line['retrieved'],
                    outstanding,
                    f"{completion:.1f}",
                    priority,
                    last_activity_str
                ])

            # Add summary row
            writer.writerow([])
            writer.writerow([
                'TOTAL',
                sum(l['total_points'] for l in lines_with_outstanding),
                sum(l['deployed'] for l in lines_with_outstanding),
                sum(l['retrieved'] for l in lines_with_outstanding),
                sum(l['outstanding'] for l in lines_with_outstanding),
                '',
                '',
                ''
            ])

            # Convert to bytes
            csv_bytes = BytesIO(output.getvalue().encode('utf-8'))
            csv_bytes.seek(0)

            logger.info(f"Retrieval report CSV exported: {len(lines_with_outstanding)} lines")
            return csv_bytes

        except Exception as e:
            logger.error(f"Error exporting retrieval report to CSV: {e}")
            return None

    def export_all_lines_csv(self) -> BytesIO:
        """
        Export summary of all lines to CSV

        Returns:
            BytesIO containing CSV data
        """
        try:
            logger.info("Exporting all lines summary to CSV")

            # Get all lines
            all_lines = self.db.get_all_lines_summary()

            # Create CSV
            output = StringIO()
            writer = csv.writer(output)

            # Write header
            writer.writerow([
                'Line', 'Total Shotpoints', 'Total Deployments',
                'Deployed', 'Retrieved', 'Outstanding',
                'Completion %', 'Coverage %', 'Last Activity'
            ])

            # Write data
            for line in all_lines:
                outstanding = line.get('outstanding', 0)
                completion = line.get('completion_pct', 0)

                # Calculate coverage
                coverage = (line['deployments'] / line['total_points'] * 100) if line['total_points'] > 0 else 0

                last_activity = line.get('last_activity')
                last_activity_str = last_activity.strftime('%Y-%m-%d %H:%M') if last_activity else 'Never'

                writer.writerow([
                    line['line'],
                    line['total_points'],
                    line['deployments'],
                    line.get('deployed', 0),
                    line.get('retrieved', 0),
                    outstanding,
                    f"{completion:.1f}",
                    f"{coverage:.1f}",
                    last_activity_str
                ])

            # Add summary row
            writer.writerow([])
            writer.writerow([
                'TOTAL',
                sum(l['total_points'] for l in all_lines),
                sum(l['deployments'] for l in all_lines),
                sum(l.get('deployed', 0) for l in all_lines),
                sum(l.get('retrieved', 0) for l in all_lines),
                sum(l.get('outstanding', 0) for l in all_lines),
                '',
                '',
                ''
            ])

            # Convert to bytes
            csv_bytes = BytesIO(output.getvalue().encode('utf-8'))
            csv_bytes.seek(0)

            logger.info(f"All lines CSV exported: {len(all_lines)} lines")
            return csv_bytes

        except Exception as e:
            logger.error(f"Error exporting all lines to CSV: {e}")
            return None

    def export_deployments_by_type_csv(self) -> BytesIO:
        """
        Export deployment statistics by type to CSV

        Returns:
            BytesIO containing CSV data
        """
        try:
            logger.info("Exporting deployments by type to CSV")

            # Get progress by type
            progress = self.db.get_progress_by_type()

            # Create CSV
            output = StringIO()
            writer = csv.writer(output)

            # Write header
            writer.writerow([
                'Deployment Type', 'Deployed', 'Retrieved',
                'Outstanding', 'Completion %'
            ])

            # Write data
            for dtype, data in progress.items():
                writer.writerow([
                    dtype,
                    data.get('deployed', 0),
                    data.get('retrieved', 0),
                    data.get('outstanding', 0),
                    f"{data.get('completion_pct', 0):.1f}"
                ])

            # Add summary row
            writer.writerow([])
            writer.writerow([
                'TOTAL',
                sum(d.get('deployed', 0) for d in progress.values()),
                sum(d.get('retrieved', 0) for d in progress.values()),
                sum(d.get('outstanding', 0) for d in progress.values()),
                ''
            ])

            # Convert to bytes
            csv_bytes = BytesIO(output.getvalue().encode('utf-8'))
            csv_bytes.seek(0)

            logger.info(f"Deployments by type CSV exported: {len(progress)} types")
            return csv_bytes

        except Exception as e:
            logger.error(f"Error exporting deployments by type to CSV: {e}")
            return None

    def export_user_activity_csv(self) -> BytesIO:
        """
        Export user activity statistics to CSV

        Returns:
            BytesIO containing CSV data
        """
        try:
            logger.info("Exporting user activity to CSV")

            # Get user stats
            users = self.db.get_user_stats()

            # Create CSV
            output = StringIO()
            writer = csv.writer(output)

            # Write header
            writer.writerow([
                'Username', 'Total Deployments', 'Lines Worked',
                'First Activity', 'Last Activity', 'Days Active'
            ])

            # Write data
            for user in users:
                first_activity = user.get('first_activity')
                last_activity = user.get('last_activity')

                first_str = first_activity.strftime('%Y-%m-%d') if first_activity else 'Never'
                last_str = last_activity.strftime('%Y-%m-%d') if last_activity else 'Never'

                # Calculate days active
                if first_activity and last_activity:
                    days_active = (last_activity - first_activity).days + 1
                else:
                    days_active = 0

                writer.writerow([
                    user['username'],
                    user['deployments'],
                    user['lines_worked'],
                    first_str,
                    last_str,
                    days_active
                ])

            # Add summary row
            writer.writerow([])
            writer.writerow([
                'TOTAL',
                sum(u['deployments'] for u in users),
                '',
                '',
                '',
                ''
            ])

            # Convert to bytes
            csv_bytes = BytesIO(output.getvalue().encode('utf-8'))
            csv_bytes.seek(0)

            logger.info(f"User activity CSV exported: {len(users)} users")
            return csv_bytes

        except Exception as e:
            logger.error(f"Error exporting user activity to CSV: {e}")
            return None

    def generate_filename(self, export_type: str, identifier: str = None) -> str:
        """
        Generate standardized filename for exports

        Args:
            export_type: Type of export (line, swath, retrieval, etc.)
            identifier: Optional identifier (line number, swath number, etc.)

        Returns:
            Filename string
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        if identifier:
            return f"swath_movers_{export_type}_{identifier}_{timestamp}.csv"
        else:
            return f"swath_movers_{export_type}_{timestamp}.csv"
