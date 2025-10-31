#!/usr/bin/env python3
"""
Statistics Calculator Module for Telegram Bot
Handles statistics calculation, aggregation, and caching
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging
import time

logger = logging.getLogger(__name__)


class StatsCache:
    """Simple in-memory cache for statistics"""

    def __init__(self, ttl: int = 300):
        """
        Initialize cache

        Args:
            ttl: Time to live in seconds (default 5 minutes)
        """
        self.cache = {}
        self.ttl = ttl

    def get(self, key: str) -> Optional[any]:
        """Get value from cache if not expired"""
        if key in self.cache:
            value, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return value
            else:
                # Expired, remove from cache
                del self.cache[key]
        return None

    def set(self, key: str, value: any):
        """Set value in cache with current timestamp"""
        self.cache[key] = (value, time.time())

    def clear(self, key: str = None):
        """Clear specific key or entire cache"""
        if key:
            if key in self.cache:
                del self.cache[key]
        else:
            self.cache.clear()

    def clear_expired(self):
        """Remove all expired entries"""
        current_time = time.time()
        expired_keys = [
            key for key, (value, timestamp) in self.cache.items()
            if current_time - timestamp >= self.ttl
        ]
        for key in expired_keys:
            del self.cache[key]


class StatisticsCalculator:
    """Calculate and aggregate statistics with caching"""

    def __init__(self, db_queries, cache_ttl: int = 300):
        """
        Initialize statistics calculator

        Args:
            db_queries: DatabaseQueries instance
            cache_ttl: Cache time-to-live in seconds (default 5 minutes)
        """
        self.db = db_queries
        self.cache = StatsCache(ttl=cache_ttl)

    def get_project_summary(self) -> Dict:
        """
        Get comprehensive project summary with caching

        Returns:
            Dict with project-wide statistics
        """
        cache_key = 'project_summary'
        cached = self.cache.get(cache_key)
        if cached:
            logger.info("Returning cached project summary")
            return cached

        logger.info("Calculating project summary")
        summary = self.db.get_overall_stats()

        # Add calculated fields
        progress = self.db.get_progress_by_type()
        summary['progress_by_type'] = progress

        # Calculate overall completion
        total_deployed = sum(p.get('deployed', 0) for p in progress.values())
        total_retrieved = sum(p.get('retrieved', 0) for p in progress.values())
        summary['overall_completion'] = (total_retrieved / total_deployed * 100) if total_deployed > 0 else 0

        # Total outstanding
        summary['total_outstanding'] = total_deployed - total_retrieved

        self.cache.set(cache_key, summary)
        return summary

    def get_line_details(self, line_number: int) -> Dict:
        """
        Get detailed line statistics with caching

        Args:
            line_number: Line number to analyze

        Returns:
            Dict with line statistics
        """
        cache_key = f'line_{line_number}'
        cached = self.cache.get(cache_key)
        if cached:
            logger.info(f"Returning cached stats for line {line_number}")
            return cached

        logger.info(f"Calculating stats for line {line_number}")
        stats = self.db.get_line_stats(line_number)

        # Add calculated fields
        if stats['total_points'] > 0:
            stats['coverage_pct'] = (stats['total_deployments'] / stats['total_points'] * 100)
        else:
            stats['coverage_pct'] = 0

        # Calculate priority level
        total_outstanding = sum([
            stats.get('nodes', {}).get('outstanding', 0),
            stats.get('hydro', {}).get('outstanding', 0),
            stats.get('marsh', {}).get('outstanding', 0),
            stats.get('sm10', {}).get('outstanding', 0)
        ])

        if total_outstanding == 0:
            stats['priority'] = 'complete'
        elif total_outstanding > 50:
            stats['priority'] = 'high'
        elif total_outstanding > 20:
            stats['priority'] = 'medium'
        else:
            stats['priority'] = 'low'

        stats['total_outstanding'] = total_outstanding

        self.cache.set(cache_key, stats)
        return stats

    def get_swath_details(self, swath_number: int) -> Dict:
        """
        Get detailed swath statistics with caching

        Args:
            swath_number: Swath number (1-8)

        Returns:
            Dict with swath statistics
        """
        cache_key = f'swath_{swath_number}'
        cached = self.cache.get(cache_key)
        if cached:
            logger.info(f"Returning cached stats for swath {swath_number}")
            return cached

        logger.info(f"Calculating stats for swath {swath_number}")
        stats = self.db.get_swath_stats(swath_number)

        # Add priority lines (lines with >20 outstanding items in this swath)
        priority_lines = []
        for line in stats.get('lines', []):
            line_stats = self.db.get_line_stats(line)
            total_outstanding = sum([
                line_stats.get('nodes', {}).get('outstanding', 0),
                line_stats.get('hydro', {}).get('outstanding', 0),
                line_stats.get('marsh', {}).get('outstanding', 0),
                line_stats.get('sm10', {}).get('outstanding', 0)
            ])
            if total_outstanding > 20:
                priority_lines.append({'line': line, 'outstanding': total_outstanding})

        # Sort by outstanding count
        priority_lines.sort(key=lambda x: x['outstanding'], reverse=True)
        stats['priority_lines'] = priority_lines[:5]  # Top 5

        # Calculate status
        completion = stats.get('completion_pct', 0)
        if completion >= 95:
            stats['status'] = 'complete'
        elif completion >= 70:
            stats['status'] = 'on_track'
        else:
            stats['status'] = 'needs_attention'

        self.cache.set(cache_key, stats)
        return stats

    def get_all_swaths_comparison(self) -> List[Dict]:
        """
        Get comparison of all swaths with caching

        Returns:
            List of swath dicts with comparison data
        """
        cache_key = 'all_swaths_comparison'
        cached = self.cache.get(cache_key)
        if cached:
            logger.info("Returning cached swaths comparison")
            return cached

        logger.info("Calculating swaths comparison")
        swaths = self.db.get_all_swaths_summary()

        # Add calculated fields for each swath
        for swath in swaths:
            completion = swath.get('completion_pct', 0)
            if completion >= 95:
                swath['status'] = 'excellent'
            elif completion >= 85:
                swath['status'] = 'good'
            elif completion >= 70:
                swath['status'] = 'fair'
            else:
                swath['status'] = 'needs_work'

        self.cache.set(cache_key, swaths)
        return swaths

    def get_progress_summary(self, deployment_type: str = None) -> Dict:
        """
        Get progress summary with velocity calculations

        Args:
            deployment_type: Optional specific deployment type

        Returns:
            Dict with progress and velocity data
        """
        cache_key = f'progress_{deployment_type or "all"}'
        cached = self.cache.get(cache_key)
        if cached:
            logger.info(f"Returning cached progress for {deployment_type or 'all'}")
            return cached

        logger.info(f"Calculating progress for {deployment_type or 'all'}")
        progress = self.db.get_progress_by_type(deployment_type)

        # Calculate velocity (items per day)
        recent = self.db.get_recent_activity(days=7)

        # Sum retrievals in last 7 days
        total_retrievals_7d = sum(
            item['count'] for item in recent
            if 'RETRIEVED' in item['deployment_type']
        )
        avg_per_day = total_retrievals_7d / 7 if total_retrievals_7d > 0 else 0

        # Estimate completion
        if deployment_type:
            type_progress = progress.get(deployment_type, {})
            outstanding = type_progress.get('outstanding', 0)
        else:
            outstanding = sum(p.get('outstanding', 0) for p in progress.values())

        days_to_completion = outstanding / avg_per_day if avg_per_day > 0 else 0

        summary = {
            'progress': progress,
            'velocity': {
                'avg_per_day': avg_per_day,
                'last_7_days': total_retrievals_7d,
                'total_outstanding': outstanding,
                'estimated_days': days_to_completion,
                'estimated_date': (datetime.now() + timedelta(days=days_to_completion)).strftime('%Y-%m-%d')
            }
        }

        self.cache.set(cache_key, summary)
        return summary

    def get_retrieval_priority_list(self) -> Dict:
        """
        Get prioritized list of lines needing retrieval

        Returns:
            Dict with categorized priority lines
        """
        cache_key = 'retrieval_priorities'
        cached = self.cache.get(cache_key)
        if cached:
            logger.info("Returning cached retrieval priorities")
            return cached

        logger.info("Calculating retrieval priorities")
        report = self.db.get_retrieval_report()

        # Categorize lines
        high_priority = []  # >50 outstanding
        medium_priority = []  # 20-50 outstanding
        low_priority = []  # <20 outstanding

        for line, count in report['lines_with_outstanding']:
            item = {'line': line, 'outstanding': count}
            if count > 50:
                high_priority.append(item)
            elif count > 20:
                medium_priority.append(item)
            else:
                low_priority.append(item)

        priorities = {
            'high': high_priority,
            'medium': medium_priority,
            'low': low_priority,
            'outstanding_by_type': report['outstanding_by_type'],
            'total_lines': len(high_priority) + len(medium_priority) + len(low_priority),
            'total_outstanding': sum(report['outstanding_by_type'].values())
        }

        # Add velocity estimates
        progress_summary = self.get_progress_summary()
        priorities['velocity'] = progress_summary['velocity']

        self.cache.set(cache_key, priorities)
        return priorities

    def get_lines_by_filter(self, filter_type: str, line_range: tuple = None) -> List[Dict]:
        """
        Get filtered list of lines

        Args:
            filter_type: 'all', 'complete', 'incomplete', 'active'
            line_range: Optional tuple (start, end) for range filter

        Returns:
            List of line dicts matching filter
        """
        cache_key = f'lines_{filter_type}_{line_range}'
        cached = self.cache.get(cache_key)
        if cached:
            logger.info(f"Returning cached lines for filter {filter_type}")
            return cached

        logger.info(f"Calculating lines for filter {filter_type}")

        if filter_type == 'all':
            lines = self.db.get_all_lines_summary()
        else:
            line_numbers = self.db.get_lines_by_status(filter_type)
            lines = [self.db.get_line_stats(line) for line in line_numbers]

        # Apply range filter if specified
        if line_range:
            start, end = line_range
            lines = [l for l in lines if start <= l['line'] <= end]

        # Sort by outstanding (descending)
        lines.sort(key=lambda x: x.get('outstanding', 0), reverse=True)

        self.cache.set(cache_key, lines)
        return lines

    def get_user_summary(self) -> Dict:
        """
        Get user activity summary

        Returns:
            Dict with user statistics
        """
        cache_key = 'user_summary'
        cached = self.cache.get(cache_key)
        if cached:
            logger.info("Returning cached user summary")
            return cached

        logger.info("Calculating user summary")
        users = self.db.get_user_stats()

        # Calculate percentages
        total_deployments = sum(u['deployments'] for u in users)

        for user in users:
            user['percentage'] = (user['deployments'] / total_deployments * 100) if total_deployments > 0 else 0

            # Calculate days active
            if user['first_activity'] and user['last_activity']:
                days_active = (user['last_activity'] - user['first_activity']).days + 1
                user['days_active'] = days_active
                user['avg_per_day'] = user['deployments'] / days_active if days_active > 0 else 0
            else:
                user['days_active'] = 0
                user['avg_per_day'] = 0

        summary = {
            'users': users,
            'total_users': len(users),
            'total_deployments': total_deployments,
            'most_active': users[0] if users else None
        }

        self.cache.set(cache_key, summary)
        return summary

    def get_coverage_analysis(self) -> Dict:
        """
        Analyze survey coverage

        Returns:
            Dict with coverage statistics
        """
        cache_key = 'coverage_analysis'
        cached = self.cache.get(cache_key)
        if cached:
            logger.info("Returning cached coverage analysis")
            return cached

        logger.info("Calculating coverage analysis")
        overall = self.db.get_overall_stats()
        all_lines = self.db.get_all_lines_summary()

        # Calculate coverage statistics
        total_points = overall['total_coordinates']
        points_with_deployments = sum(1 for line in all_lines if line['deployments'] > 0)

        # Categorize lines by coverage
        high_coverage = []  # >80%
        medium_coverage = []  # 50-80%
        low_coverage = []  # <50%

        for line in all_lines:
            coverage = (line['deployments'] / line['total_points'] * 100) if line['total_points'] > 0 else 0
            line['coverage_pct'] = coverage

            if coverage >= 80:
                high_coverage.append(line)
            elif coverage >= 50:
                medium_coverage.append(line)
            else:
                low_coverage.append(line)

        analysis = {
            'total_shotpoints': total_points,
            'points_with_deployments': points_with_deployments,
            'overall_coverage_pct': (points_with_deployments / total_points * 100) if total_points > 0 else 0,
            'high_coverage_lines': len(high_coverage),
            'medium_coverage_lines': len(medium_coverage),
            'low_coverage_lines': len(low_coverage),
            'gaps': low_coverage[:10]  # Top 10 gaps
        }

        self.cache.set(cache_key, analysis)
        return analysis

    def get_daily_summary(self) -> Dict:
        """
        Get comprehensive daily summary

        Returns:
            Dict with today's complete summary
        """
        cache_key = 'daily_summary'
        cached = self.cache.get(cache_key)
        if cached:
            logger.info("Returning cached daily summary")
            return cached

        logger.info("Calculating daily summary")

        # Get today's stats
        today = self.db.get_today_stats()

        # Get overall project state
        project = self.get_project_summary()

        # Get recent activity trend
        recent = self.db.get_recent_activity(days=7)

        # Calculate 7-day average
        total_7d = sum(item['count'] for item in recent)
        avg_7d = total_7d / 7 if total_7d > 0 else 0

        # Compare today to average
        today_count = today.get('today_count', 0)
        comparison = 'above' if today_count > avg_7d else 'below' if today_count < avg_7d else 'equal'

        summary = {
            'today': today,
            'project': project,
            'trend': {
                'avg_7d': avg_7d,
                'total_7d': total_7d,
                'comparison': comparison,
                'difference': abs(today_count - avg_7d)
            }
        }

        self.cache.set(cache_key, summary)
        return summary

    def get_alerts(self) -> List[Dict]:
        """
        Generate alerts for critical conditions

        Returns:
            List of alert dicts with priority and message
        """
        alerts = []

        # Check for high priority lines
        retrieval = self.get_retrieval_priority_list()
        high_priority = retrieval.get('high', [])

        for item in high_priority[:5]:  # Top 5
            alerts.append({
                'priority': 'high',
                'type': 'retrieval',
                'message': f"Line {item['line']}: {item['outstanding']} outstanding items",
                'line': item['line'],
                'outstanding': item['outstanding']
            })

        # Check for inactive lines (no activity in 7 days)
        all_lines = self.db.get_all_lines_summary()
        seven_days_ago = datetime.now() - timedelta(days=7)

        for line in all_lines:
            if line['outstanding'] > 0:
                last_activity = line.get('last_activity')
                if not last_activity or last_activity < seven_days_ago:
                    alerts.append({
                        'priority': 'medium',
                        'type': 'inactive',
                        'message': f"Line {line['line']}: No activity in 7+ days",
                        'line': line['line'],
                        'outstanding': line['outstanding']
                    })

        # Check for swaths below 70% completion
        swaths = self.get_all_swaths_comparison()
        for swath in swaths:
            if swath.get('completion_pct', 0) < 70:
                alerts.append({
                    'priority': 'medium',
                    'type': 'completion',
                    'message': f"Swath {swath['swath']}: Only {swath['completion_pct']:.0f}% complete",
                    'swath': swath['swath'],
                    'completion': swath['completion_pct']
                })

        # Sort by priority
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        alerts.sort(key=lambda x: priority_order.get(x['priority'], 3))

        return alerts[:20]  # Top 20 alerts

    def clear_cache(self, cache_key: str = None):
        """Clear specific cache key or entire cache"""
        self.cache.clear(cache_key)
        logger.info(f"Cache cleared: {cache_key or 'all'}")

    def clear_expired_cache(self):
        """Remove expired cache entries"""
        self.cache.clear_expired()
