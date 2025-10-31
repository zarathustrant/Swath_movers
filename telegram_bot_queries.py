#!/usr/bin/env python3
"""
Database Query Module for Telegram Bot
Handles all PostgreSQL queries for statistics and reports
"""

import psycopg2
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class DatabaseQueries:
    def __init__(self, connection_func, return_func):
        """
        Initialize with connection pool functions

        Args:
            connection_func: Function to get DB connection from pool
            return_func: Function to return connection to pool
        """
        self.get_connection = connection_func
        self.return_connection = return_func

    def _execute_query(self, query: str, params: tuple = None) -> List[tuple]:
        """Execute query and return results"""
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor() as cursor:
                cursor.execute(query, params or ())
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Query error: {e}")
            return []
        finally:
            if conn:
                self.return_connection(conn)

    # === PROJECT-WIDE STATISTICS ===

    def get_overall_stats(self) -> Dict:
        """Get project-wide statistics"""
        stats = {}

        # Total coordinates
        query = "SELECT COUNT(*) FROM coordinates"
        result = self._execute_query(query)
        stats['total_coordinates'] = result[0][0] if result else 0

        # Total lines
        query = "SELECT COUNT(DISTINCT line) FROM coordinates"
        result = self._execute_query(query)
        stats['total_lines'] = result[0][0] if result else 0

        # Total deployments
        query = "SELECT COUNT(*) FROM global_deployments"
        result = self._execute_query(query)
        stats['total_deployments'] = result[0][0] if result else 0

        # Deployments by type
        query = """
        SELECT deployment_type, COUNT(*) as count
        FROM global_deployments
        GROUP BY deployment_type
        ORDER BY count DESC
        """
        result = self._execute_query(query)
        stats['deployments_by_type'] = {row[0]: row[1] for row in result}

        # Last activity
        query = "SELECT MAX(timestamp) FROM global_deployments"
        result = self._execute_query(query)
        stats['last_activity'] = result[0][0] if result and result[0][0] else None

        # Active users
        query = """
        SELECT COUNT(DISTINCT username)
        FROM global_deployments
        WHERE username IS NOT NULL
        """
        result = self._execute_query(query)
        stats['active_users'] = result[0][0] if result else 0

        return stats

    def get_today_stats(self) -> Dict:
        """Get today's activity statistics"""
        stats = {}

        # Today's deployments
        query = """
        SELECT COUNT(*)
        FROM global_deployments
        WHERE DATE(timestamp) = CURRENT_DATE
        """
        result = self._execute_query(query)
        stats['today_count'] = result[0][0] if result else 0

        # Today's by type
        query = """
        SELECT deployment_type, COUNT(*) as count
        FROM global_deployments
        WHERE DATE(timestamp) = CURRENT_DATE
        GROUP BY deployment_type
        ORDER BY count DESC
        """
        result = self._execute_query(query)
        stats['today_by_type'] = {row[0]: row[1] for row in result}

        # Most active user today
        query = """
        SELECT username, COUNT(*) as count
        FROM global_deployments
        WHERE DATE(timestamp) = CURRENT_DATE AND username IS NOT NULL
        GROUP BY username
        ORDER BY count DESC
        LIMIT 1
        """
        result = self._execute_query(query)
        stats['most_active_user'] = result[0] if result else (None, 0)

        # Most active line today
        query = """
        SELECT line, COUNT(*) as count
        FROM global_deployments
        WHERE DATE(timestamp) = CURRENT_DATE
        GROUP BY line
        ORDER BY count DESC
        LIMIT 1
        """
        result = self._execute_query(query)
        stats['most_active_line'] = result[0] if result else (None, 0)

        return stats

    # === LINE STATISTICS ===

    def get_line_stats(self, line_number: int) -> Dict:
        """Get detailed statistics for a specific line"""
        stats = {'line': line_number}

        # Total shotpoints on line
        query = "SELECT COUNT(*) FROM coordinates WHERE line = %s"
        result = self._execute_query(query, (line_number,))
        stats['total_points'] = result[0][0] if result else 0

        # Total deployments on line
        query = "SELECT COUNT(*) FROM global_deployments WHERE line = %s"
        result = self._execute_query(query, (line_number,))
        stats['total_deployments'] = result[0][0] if result else 0

        # Deployments by type
        query = """
        SELECT
            COUNT(CASE WHEN deployment_type = 'NODES DEPLOYED' THEN 1 END) as nodes_deployed,
            COUNT(CASE WHEN deployment_type = 'NODES RETRIEVED' THEN 1 END) as nodes_retrieved,
            COUNT(CASE WHEN deployment_type = 'HYDROPHONES DEPLOYED' THEN 1 END) as hydro_deployed,
            COUNT(CASE WHEN deployment_type = 'HYDROPHONES RETRIEVED' THEN 1 END) as hydro_retrieved,
            COUNT(CASE WHEN deployment_type = 'MARSH GEOPHONES DEPLOYED' THEN 1 END) as marsh_deployed,
            COUNT(CASE WHEN deployment_type = 'MARSH GEOPHONES RETRIEVED' THEN 1 END) as marsh_retrieved,
            COUNT(CASE WHEN deployment_type = 'SM10 GEOPHONES DEPLOYED' THEN 1 END) as sm10_deployed,
            COUNT(CASE WHEN deployment_type = 'SM10 GEOPHONES RETRIEVED' THEN 1 END) as sm10_retrieved
        FROM global_deployments
        WHERE line = %s
        """
        result = self._execute_query(query, (line_number,))
        if result:
            row = result[0]
            stats['nodes'] = {'deployed': row[0], 'retrieved': row[1], 'outstanding': row[0] - row[1]}
            stats['hydro'] = {'deployed': row[2], 'retrieved': row[3], 'outstanding': row[2] - row[3]}
            stats['marsh'] = {'deployed': row[4], 'retrieved': row[5], 'outstanding': row[4] - row[5]}
            stats['sm10'] = {'deployed': row[6], 'retrieved': row[7], 'outstanding': row[6] - row[7]}

        # Last activity
        query = "SELECT MAX(timestamp) FROM global_deployments WHERE line = %s"
        result = self._execute_query(query, (line_number,))
        stats['last_activity'] = result[0][0] if result and result[0][0] else None

        # Calculate completion percentage
        total_deployed = sum([
            stats.get('nodes', {}).get('deployed', 0),
            stats.get('hydro', {}).get('deployed', 0),
            stats.get('marsh', {}).get('deployed', 0),
            stats.get('sm10', {}).get('deployed', 0)
        ])
        total_retrieved = sum([
            stats.get('nodes', {}).get('retrieved', 0),
            stats.get('hydro', {}).get('retrieved', 0),
            stats.get('marsh', {}).get('retrieved', 0),
            stats.get('sm10', {}).get('retrieved', 0)
        ])
        stats['completion_pct'] = (total_retrieved / total_deployed * 100) if total_deployed > 0 else 0

        return stats

    def get_all_lines_summary(self) -> List[Dict]:
        """Get summary statistics for all lines"""
        query = """
        SELECT
            c.line,
            COUNT(DISTINCT c.shotpoint) as total_points,
            COUNT(d.shotpoint) as deployments,
            COUNT(CASE WHEN d.deployment_type LIKE '%DEPLOYED' AND d.deployment_type NOT LIKE '%RETRIEVED' THEN 1 END) as deployed,
            COUNT(CASE WHEN d.deployment_type LIKE '%RETRIEVED' THEN 1 END) as retrieved,
            MAX(d.timestamp) as last_activity
        FROM coordinates c
        LEFT JOIN global_deployments d ON c.line = d.line AND c.shotpoint = d.shotpoint
        GROUP BY c.line
        ORDER BY c.line
        """
        results = self._execute_query(query)

        lines = []
        for row in results:
            deployed = row[3] or 0
            retrieved = row[4] or 0
            total = deployed + retrieved
            completion = (retrieved / total * 100) if total > 0 else 0

            lines.append({
                'line': row[0],
                'total_points': row[1],
                'deployments': row[2],
                'deployed': deployed,
                'retrieved': retrieved,
                'outstanding': deployed - retrieved,
                'completion_pct': completion,
                'last_activity': row[5]
            })

        return lines

    def get_lines_by_status(self, status: str) -> List[int]:
        """Get lines filtered by status (complete, incomplete, active)"""
        all_lines = self.get_all_lines_summary()

        if status == 'complete':
            return [line['line'] for line in all_lines if line['outstanding'] == 0 and line['deployed'] > 0]
        elif status == 'incomplete':
            return [line['line'] for line in all_lines if line['outstanding'] > 0]
        elif status == 'active':
            today = datetime.now().date()
            return [line['line'] for line in all_lines
                   if line['last_activity'] and line['last_activity'].date() == today]
        else:
            return [line['line'] for line in all_lines]

    # === SWATH STATISTICS ===

    def get_swath_stats(self, swath_number: int) -> Dict:
        """Get statistics for a specific swath"""
        stats = {'swath': swath_number}

        # Get total deployments in swath table
        query = f"SELECT COUNT(*) FROM swath_{swath_number}"
        result = self._execute_query(query)
        stats['total_deployments'] = result[0][0] if result else 0

        # Get deployment types breakdown
        query = f"""
        SELECT deployment_type, COUNT(*) as count
        FROM swath_{swath_number}
        GROUP BY deployment_type
        ORDER BY count DESC
        """
        result = self._execute_query(query)
        stats['deployments_by_type'] = {row[0]: row[1] for row in result}

        # Get unique lines in swath
        query = f"SELECT COUNT(DISTINCT line) FROM swath_{swath_number}"
        result = self._execute_query(query)
        stats['line_count'] = result[0][0] if result else 0

        # Get lines list
        query = f"SELECT DISTINCT line FROM swath_{swath_number} ORDER BY line"
        result = self._execute_query(query)
        stats['lines'] = [row[0] for row in result]

        # Calculate completion (based on deployed vs retrieved)
        query = f"""
        SELECT
            COUNT(CASE WHEN deployment_type LIKE '%DEPLOYED' AND deployment_type NOT LIKE '%RETRIEVED' THEN 1 END) as deployed,
            COUNT(CASE WHEN deployment_type LIKE '%RETRIEVED' THEN 1 END) as retrieved
        FROM swath_{swath_number}
        """
        result = self._execute_query(query)
        if result:
            deployed = result[0][0] or 0
            retrieved = result[0][1] or 0
            total = deployed + retrieved
            stats['completion_pct'] = (retrieved / total * 100) if total > 0 else 0
            stats['outstanding'] = deployed - retrieved

        return stats

    def get_all_swaths_summary(self) -> List[Dict]:
        """Get summary for all 8 swaths"""
        swaths = []
        for i in range(1, 9):
            swaths.append(self.get_swath_stats(i))
        return swaths

    # === PROGRESS & RETRIEVAL ===

    def get_progress_by_type(self, deployment_type: str = None) -> Dict:
        """Get progress statistics by deployment type"""
        if deployment_type:
            # Specific type
            query = """
            SELECT
                COUNT(CASE WHEN deployment_type = %s THEN 1 END) as deployed,
                COUNT(CASE WHEN deployment_type = %s THEN 1 END) as retrieved
            FROM global_deployments
            """
            deployed_type = deployment_type.replace('RETRIEVED', 'DEPLOYED')
            retrieved_type = deployment_type.replace('DEPLOYED', 'RETRIEVED')
            result = self._execute_query(query, (deployed_type, retrieved_type))
        else:
            # All types
            query = """
            SELECT
                deployment_type,
                COUNT(*) as count
            FROM global_deployments
            GROUP BY deployment_type
            ORDER BY count DESC
            """
            result = self._execute_query(query)

            # Group by deployed/retrieved
            progress = {}
            for row in result:
                dtype = row[0]
                count = row[1]
                if 'DEPLOYED' in dtype and 'RETRIEVED' not in dtype:
                    base_type = dtype.replace(' DEPLOYED', '')
                    if base_type not in progress:
                        progress[base_type] = {'deployed': 0, 'retrieved': 0}
                    progress[base_type]['deployed'] = count
                elif 'RETRIEVED' in dtype:
                    base_type = dtype.replace(' RETRIEVED', '')
                    if base_type not in progress:
                        progress[base_type] = {'deployed': 0, 'retrieved': 0}
                    progress[base_type]['retrieved'] = count

            # Calculate percentages
            for dtype in progress:
                deployed = progress[dtype]['deployed']
                retrieved = progress[dtype]['retrieved']
                progress[dtype]['outstanding'] = deployed - retrieved
                progress[dtype]['completion_pct'] = (retrieved / deployed * 100) if deployed > 0 else 0

            return progress

        return {}

    def get_retrieval_report(self) -> Dict:
        """Get comprehensive retrieval status report"""
        report = {}

        # Get all lines with outstanding items
        query = """
        SELECT
            line,
            COUNT(CASE WHEN deployment_type LIKE '%DEPLOYED' AND deployment_type NOT LIKE '%RETRIEVED' THEN 1 END) as outstanding
        FROM global_deployments
        GROUP BY line
        HAVING COUNT(CASE WHEN deployment_type LIKE '%DEPLOYED' AND deployment_type NOT LIKE '%RETRIEVED' THEN 1 END) > 0
        ORDER BY outstanding DESC
        """
        result = self._execute_query(query)
        report['lines_with_outstanding'] = [(row[0], row[1]) for row in result]

        # Total outstanding by type
        progress = self.get_progress_by_type()
        report['outstanding_by_type'] = {dtype: data['outstanding'] for dtype, data in progress.items()}

        # Priority lines (>50 outstanding)
        report['priority_lines'] = [(line, count) for line, count in report['lines_with_outstanding'] if count > 50]

        return report

    # === USER STATISTICS ===

    def get_user_stats(self) -> List[Dict]:
        """Get user activity statistics"""
        query = """
        SELECT
            username,
            COUNT(*) as deployments,
            COUNT(DISTINCT line) as lines_worked,
            MIN(timestamp) as first_activity,
            MAX(timestamp) as last_activity
        FROM global_deployments
        WHERE username IS NOT NULL
        GROUP BY username
        ORDER BY deployments DESC
        """
        results = self._execute_query(query)

        users = []
        for row in results:
            users.append({
                'username': row[0],
                'deployments': row[1],
                'lines_worked': row[2],
                'first_activity': row[3],
                'last_activity': row[4]
            })

        return users

    # === TIMELINE & ACTIVITY ===

    def get_recent_activity(self, days: int = 7) -> List[Dict]:
        """Get recent activity for the last N days"""
        query = """
        SELECT
            DATE(timestamp) as date,
            deployment_type,
            COUNT(*) as count
        FROM global_deployments
        WHERE timestamp >= CURRENT_DATE - INTERVAL '%s days'
        GROUP BY DATE(timestamp), deployment_type
        ORDER BY date DESC, count DESC
        """
        results = self._execute_query(query, (days,))

        activity = []
        for row in results:
            activity.append({
                'date': row[0],
                'deployment_type': row[1],
                'count': row[2]
            })

        return activity

    def get_line_timeline(self, line_number: int) -> List[Dict]:
        """Get deployment timeline for a specific line"""
        query = """
        SELECT
            DATE(timestamp) as date,
            deployment_type,
            COUNT(*) as count
        FROM global_deployments
        WHERE line = %s
        GROUP BY DATE(timestamp), deployment_type
        ORDER BY date, deployment_type
        """
        results = self._execute_query(query, (line_number,))

        timeline = []
        for row in results:
            timeline.append({
                'date': row[0],
                'deployment_type': row[1],
                'count': row[2]
            })

        return timeline

    # === GAP DETECTION ===

    def get_line_gaps(self, line_number: int, min_gap_size: int = 1) -> List[Dict]:
        """
        Detect gaps (consecutive shotpoints without deployments) on a line

        Args:
            line_number: Line number to check
            min_gap_size: Minimum number of consecutive empty shotpoints to report

        Returns:
            List of gap dicts with start, end, and size
        """
        query = """
        SELECT
            c.shotpoint,
            CASE WHEN d.shotpoint IS NULL THEN 0 ELSE 1 END as has_deployment
        FROM coordinates c
        LEFT JOIN global_deployments d ON c.line = d.line AND c.shotpoint = d.shotpoint
        WHERE c.line = %s
        ORDER BY c.shotpoint
        """
        results = self._execute_query(query, (line_number,))

        if not results:
            return []

        gaps = []
        gap_start = None
        gap_size = 0

        for shotpoint, has_deployment in results:
            if has_deployment == 0:
                # Empty shotpoint
                if gap_start is None:
                    gap_start = shotpoint
                gap_size += 1
            else:
                # Deployed shotpoint - check if we had a gap
                if gap_start is not None and gap_size >= min_gap_size:
                    gaps.append({
                        'line': line_number,
                        'start_shotpoint': gap_start,
                        'end_shotpoint': shotpoint - 1,
                        'size': gap_size
                    })
                # Reset gap tracking
                gap_start = None
                gap_size = 0

        # Check for gap at end of line
        if gap_start is not None and gap_size >= min_gap_size:
            last_shotpoint = results[-1][0]
            gaps.append({
                'line': line_number,
                'start_shotpoint': gap_start,
                'end_shotpoint': last_shotpoint,
                'size': gap_size
            })

        return gaps

    def get_all_lines_with_gaps(self, min_gap_size: int = 1) -> List[Dict]:
        """
        Find all lines that have gaps in deployment coverage

        Args:
            min_gap_size: Minimum gap size to report

        Returns:
            List of dicts with line number and gap count
        """
        # Get all lines
        query = "SELECT DISTINCT line FROM coordinates ORDER BY line"
        results = self._execute_query(query)

        lines_with_gaps = []

        for (line_number,) in results:
            gaps = self.get_line_gaps(line_number, min_gap_size)
            if gaps:
                total_gap_points = sum(gap['size'] for gap in gaps)
                lines_with_gaps.append({
                    'line': line_number,
                    'gap_count': len(gaps),
                    'total_gap_points': total_gap_points,
                    'gaps': gaps
                })

        # Sort by total gap points (descending)
        lines_with_gaps.sort(key=lambda x: x['total_gap_points'], reverse=True)

        return lines_with_gaps

    def get_swath_gaps(self, swath_number: int, min_gap_size: int = 1) -> List[Dict]:
        """
        Get gap analysis for all lines in a swath

        Args:
            swath_number: Swath number (1-8)
            min_gap_size: Minimum gap size to report

        Returns:
            List of line gap dicts
        """
        # Get lines in swath
        query = f"SELECT DISTINCT line FROM swath_{swath_number} ORDER BY line"
        results = self._execute_query(query)

        swath_gaps = []
        for (line_number,) in results:
            gaps = self.get_line_gaps(line_number, min_gap_size)
            if gaps:
                total_gap_points = sum(gap['size'] for gap in gaps)
                swath_gaps.append({
                    'line': line_number,
                    'gap_count': len(gaps),
                    'total_gap_points': total_gap_points,
                    'gaps': gaps
                })

        return swath_gaps

    def get_gap_statistics(self) -> Dict:
        """
        Get project-wide gap statistics

        Returns:
            Dict with gap statistics
        """
        lines_with_gaps = self.get_all_lines_with_gaps(min_gap_size=5)

        stats = {
            'total_lines_with_gaps': len(lines_with_gaps),
            'total_gaps': sum(l['gap_count'] for l in lines_with_gaps),
            'total_gap_points': sum(l['total_gap_points'] for l in lines_with_gaps),
            'lines_by_severity': {
                'critical': [],  # >50 gap points
                'high': [],      # 20-50 gap points
                'medium': [],    # 10-20 gap points
                'low': []        # 5-10 gap points
            }
        }

        # Categorize by severity
        for line_data in lines_with_gaps:
            total_gaps = line_data['total_gap_points']
            line = line_data['line']

            if total_gaps > 50:
                stats['lines_by_severity']['critical'].append(line)
            elif total_gaps > 20:
                stats['lines_by_severity']['high'].append(line)
            elif total_gaps > 10:
                stats['lines_by_severity']['medium'].append(line)
            else:
                stats['lines_by_severity']['low'].append(line)

        return stats
