#!/usr/bin/env python3
"""
Text Formatting Module for Telegram Bot
Handles message formatting, progress bars, tables, and HTML formatting
"""

from datetime import datetime
from typing import Dict, List, Any


class TelegramFormatter:
    """Formats data for Telegram messages with HTML formatting"""

    @staticmethod
    def progress_bar(percentage: float, length: int = 10, filled: str = "▓", empty: str = "░") -> str:
        """
        Generate a text-based progress bar

        Args:
            percentage: Completion percentage (0-100)
            length: Length of progress bar in characters
            filled: Character for filled portion
            empty: Character for empty portion

        Returns:
            Progress bar string like "▓▓▓▓▓▓▓░░░"
        """
        filled_length = int(length * percentage / 100)
        return filled * filled_length + empty * (length - filled_length)

    @staticmethod
    def format_percentage(value: float, decimals: int = 1) -> str:
        """Format percentage with specified decimal places"""
        return f"{value:.{decimals}f}%"

    @staticmethod
    def format_number(value: int) -> str:
        """Format number with thousand separators"""
        return f"{value:,}"

    @staticmethod
    def format_date(dt: datetime) -> str:
        """Format datetime for display"""
        if not dt:
            return "Never"
        return dt.strftime("%Y-%m-%d %H:%M")

    @staticmethod
    def format_date_short(dt: datetime) -> str:
        """Format date only (no time)"""
        if not dt:
            return "Never"
        return dt.strftime("%Y-%m-%d")

    @staticmethod
    def status_icon(percentage: float) -> str:
        """Get status icon based on completion percentage"""
        if percentage >= 100:
            return "✅"
        elif percentage >= 90:
            return "🟢"
        elif percentage >= 70:
            return "🟡"
        elif percentage >= 50:
            return "🟠"
        else:
            return "🔴"

    @staticmethod
    def priority_icon(outstanding: int) -> str:
        """Get priority icon based on outstanding items"""
        if outstanding == 0:
            return "✅"
        elif outstanding > 50:
            return "🔴"
        elif outstanding > 20:
            return "🟡"
        else:
            return "🟢"

    @staticmethod
    def format_line_summary(line_data: Dict) -> str:
        """Format a single line summary for list view"""
        line = line_data['line']
        completion = line_data.get('completion_pct', 0)
        outstanding = line_data.get('outstanding', 0)

        bar = TelegramFormatter.progress_bar(completion)
        pct = TelegramFormatter.format_percentage(completion, 0)
        icon = TelegramFormatter.priority_icon(outstanding)

        return f"{icon} Line {line}: {pct} {bar} ({outstanding} outstanding)"

    @staticmethod
    def format_stats_message(stats: Dict) -> str:
        """Format overall project statistics message"""
        total_coords = TelegramFormatter.format_number(stats.get('total_coordinates', 0))
        total_lines = stats.get('total_lines', 0)
        total_deps = TelegramFormatter.format_number(stats.get('total_deployments', 0))
        last_activity = TelegramFormatter.format_date(stats.get('last_activity'))

        msg = f"""📊 <b>Swath Movers Statistics</b>

📍 <b>Survey Coverage</b>
• Total Coordinates: {total_coords}
• Survey Lines: {total_lines}
• Active Swaths: 8

🎯 <b>Deployments:</b> {total_deps} total
"""

        # Add deployment breakdown
        deps_by_type = stats.get('deployments_by_type', {})
        if deps_by_type:
            msg += "\n<b>By Type:</b>\n"
            for dtype, count in list(deps_by_type.items())[:5]:  # Top 5
                msg += f"• {dtype}: {TelegramFormatter.format_number(count)}\n"

        msg += f"\n👥 Active Users: {stats.get('active_users', 0)}"
        msg += f"\n📅 Last Activity: {last_activity}"

        return msg

    @staticmethod
    def format_today_message(stats: Dict) -> str:
        """Format today's activity message"""
        today_count = stats.get('today_count', 0)
        user_data = stats.get('most_active_user', (None, 0))
        line_data = stats.get('most_active_line', (None, 0))

        msg = f"""📅 <b>Today's Activity</b> ({datetime.now().strftime('%b %d, %Y')})

✅ <b>Deployments:</b> {today_count}
"""

        if user_data[0]:
            msg += f"👤 <b>Most Active:</b> {user_data[0]} ({user_data[1]})\n"

        if line_data[0]:
            msg += f"📍 <b>Most Active Line:</b> Line {line_data[0]} ({line_data[1]})\n"

        # Types used today
        today_by_type = stats.get('today_by_type', {})
        if today_by_type:
            msg += "\n<b>Types Used Today:</b>\n"
            for dtype, count in list(today_by_type.items())[:5]:
                msg += f"• {dtype}: {count}\n"

        return msg

    @staticmethod
    def format_line_details(line_stats: Dict) -> str:
        """Format detailed line statistics message"""
        line = line_stats['line']
        total_points = line_stats.get('total_points', 0)
        total_deps = line_stats.get('total_deployments', 0)
        coverage = (total_deps / total_points * 100) if total_points > 0 else 0
        completion = line_stats.get('completion_pct', 0)
        last_activity = TelegramFormatter.format_date(line_stats.get('last_activity'))

        msg = f"""📍 <b>Line {line} - Detailed Report</b>

📊 <b>Coverage</b>
• Total Shotpoints: {total_points}
• Deployments: {total_deps} ({TelegramFormatter.format_percentage(coverage)} of points)
• Last Activity: {last_activity}

🎯 <b>Equipment Status</b>

"""

        # Nodes
        nodes = line_stats.get('nodes', {})
        if nodes:
            deployed = nodes.get('deployed', 0)
            retrieved = nodes.get('retrieved', 0)
            outstanding = nodes.get('outstanding', 0)
            node_pct = (retrieved / deployed * 100) if deployed > 0 else 0

            status_emoji = "✅" if outstanding == 0 else "⚠️" if outstanding < 10 else "❌"
            msg += f"""🟨 <b>Nodes</b>
  Deployed: {deployed}
  Retrieved: {retrieved}
  Outstanding: {outstanding}
  {status_emoji} {TelegramFormatter.format_percentage(node_pct)} retrieved

"""

        # Hydrophones
        hydro = line_stats.get('hydro', {})
        if hydro and hydro.get('deployed', 0) > 0:
            deployed = hydro.get('deployed', 0)
            retrieved = hydro.get('retrieved', 0)
            outstanding = hydro.get('outstanding', 0)
            hydro_pct = (retrieved / deployed * 100) if deployed > 0 else 0

            status_emoji = "✅" if outstanding == 0 else "⚠️" if outstanding < 10 else "❌"
            msg += f"""🔵 <b>Hydrophones</b>
  Deployed: {deployed}
  Retrieved: {retrieved}
  Outstanding: {outstanding}
  {status_emoji} {TelegramFormatter.format_percentage(hydro_pct)} retrieved

"""

        # Marsh Geophones
        marsh = line_stats.get('marsh', {})
        if marsh and marsh.get('deployed', 0) > 0:
            deployed = marsh.get('deployed', 0)
            retrieved = marsh.get('retrieved', 0)
            outstanding = marsh.get('outstanding', 0)
            marsh_pct = (retrieved / deployed * 100) if deployed > 0 else 0

            status_emoji = "✅" if outstanding == 0 else "⚠️"
            msg += f"""🟦 <b>Marsh Geophones</b>
  Deployed: {deployed}
  Retrieved: {retrieved}
  Outstanding: {outstanding}
  {status_emoji} {TelegramFormatter.format_percentage(marsh_pct)} retrieved

"""

        # Progress bar
        bar = TelegramFormatter.progress_bar(completion)
        pct_str = TelegramFormatter.format_percentage(completion, 0)
        status_icon = TelegramFormatter.status_icon(completion)

        msg += f"""📈 <b>Line Progress</b>
{bar} {pct_str}
Status: {status_icon} """

        # Status text
        total_outstanding = sum([
            nodes.get('outstanding', 0),
            hydro.get('outstanding', 0),
            marsh.get('outstanding', 0)
        ])

        if total_outstanding == 0:
            msg += "COMPLETE - All equipment retrieved"
        elif total_outstanding < 10:
            msg += f"ALMOST DONE - {total_outstanding} items outstanding"
        else:
            msg += f"IN PROGRESS - {total_outstanding} items outstanding"

        if total_outstanding > 20:
            msg += f"\n\nPriority: 🔴 HIGH ({total_outstanding} items)"

        return msg

    @staticmethod
    def format_swath_details(swath_stats: Dict) -> str:
        """Format detailed swath statistics message"""
        swath = swath_stats['swath']
        total_deps = TelegramFormatter.format_number(swath_stats.get('total_deployments', 0))
        line_count = swath_stats.get('line_count', 0)
        completion = swath_stats.get('completion_pct', 0)
        outstanding = swath_stats.get('outstanding', 0)

        msg = f"""🗂️ <b>Swath {swath} - Detailed Report</b>

📊 <b>Overview</b>
• Lines in Swath: {line_count}
• Total Deployments: {total_deps}
• Outstanding: {outstanding}

🎯 <b>Deployment Breakdown</b>

"""

        # Deployment types
        deps_by_type = swath_stats.get('deployments_by_type', {})
        total = sum(deps_by_type.values())

        for dtype, count in deps_by_type.items():
            pct = (count / total * 100) if total > 0 else 0
            emoji = "🟨" if "NODE" in dtype else "🔵" if "HYDRO" in dtype else "🟦"
            msg += f"""{emoji} <b>{dtype}</b>
  Count: {TelegramFormatter.format_number(count)} ({TelegramFormatter.format_percentage(pct)})

"""

        # Progress
        bar = TelegramFormatter.progress_bar(completion)
        pct_str = TelegramFormatter.format_percentage(completion, 0)
        status_icon = TelegramFormatter.status_icon(completion)

        msg += f"""📈 <b>Swath Progress</b>
{bar} {pct_str}
Status: {status_icon}

"""

        # Lines in swath
        lines = swath_stats.get('lines', [])
        if lines:
            msg += f"📍 <b>Lines:</b> {len(lines)} total\n"
            if len(lines) <= 10:
                msg += f"Lines: {', '.join(map(str, lines))}"
            else:
                msg += f"Lines: {lines[0]} to {lines[-1]}"

        return msg

    @staticmethod
    def format_swaths_comparison(all_swaths: List[Dict]) -> str:
        """Format comparison of all swaths"""
        msg = """🗂️ <b>All Swaths - Comparison</b>

"""

        for swath_data in all_swaths:
            swath = swath_data['swath']
            completion = swath_data.get('completion_pct', 0)
            total_deps = swath_data.get('total_deployments', 0)
            outstanding = swath_data.get('outstanding', 0)

            bar = TelegramFormatter.progress_bar(completion)
            pct = TelegramFormatter.format_percentage(completion, 0)
            icon = TelegramFormatter.status_icon(completion)

            msg += f"{icon} Swath {swath}: {pct} {bar} ({TelegramFormatter.format_number(total_deps)} deps, {outstanding} out)\n"

        # Overall progress
        total_completion = sum(s.get('completion_pct', 0) for s in all_swaths) / len(all_swaths)
        msg += f"\n📊 <b>Overall Progress:</b> {TelegramFormatter.format_percentage(total_completion)}"

        # Best and worst
        best = max(all_swaths, key=lambda x: x.get('completion_pct', 0))
        worst = min(all_swaths, key=lambda x: x.get('completion_pct', 0))

        msg += f"\n🏆 <b>Best:</b> Swath {best['swath']} ({TelegramFormatter.format_percentage(best.get('completion_pct', 0))})"
        msg += f"\n⚠️ <b>Needs Attention:</b> Swath {worst['swath']} ({TelegramFormatter.format_percentage(worst.get('completion_pct', 0))})"

        total_outstanding = sum(s.get('outstanding', 0) for s in all_swaths)
        msg += f"\n\nTotal Outstanding: {TelegramFormatter.format_number(total_outstanding)} items across all swaths"

        return msg

    @staticmethod
    def format_progress_report(progress: Dict) -> str:
        """Format progress report by deployment type"""
        msg = """📈 <b>Deployment Progress Report</b>

"""

        for dtype, data in progress.items():
            deployed = data.get('deployed', 0)
            retrieved = data.get('retrieved', 0)
            outstanding = data.get('outstanding', 0)
            completion = data.get('completion_pct', 0)

            bar = TelegramFormatter.progress_bar(completion)
            pct = TelegramFormatter.format_percentage(completion)

            emoji = "🟨" if "NODE" in dtype else "🔵" if "HYDRO" in dtype else "🟦"

            msg += f"""{emoji} <b>{dtype}</b>
{bar} {pct}
• Deployed: {TelegramFormatter.format_number(deployed)}
• Retrieved: {TelegramFormatter.format_number(retrieved)}
• Outstanding: {TelegramFormatter.format_number(outstanding)}

"""

        return msg

    @staticmethod
    def format_retrieval_report(report: Dict) -> str:
        """Format retrieval status report"""
        msg = """🔄 <b>Retrieval Status Report</b>

⚠️ <b>Equipment Still Deployed</b>

"""

        outstanding_by_type = report.get('outstanding_by_type', {})
        for dtype, count in outstanding_by_type.items():
            if count > 0:
                emoji = "🟨" if "NODE" in dtype else "🔵" if "HYDRO" in dtype else "🟦"
                msg += f"{emoji} {dtype}: {TelegramFormatter.format_number(count)} units\n"

        # Priority lines
        priority_lines = report.get('priority_lines', [])
        if priority_lines:
            msg += f"\n🔴 <b>High Priority Lines (>50 outstanding):</b>\n"
            for line, count in priority_lines[:10]:  # Top 10
                msg += f"• Line {line}: {count} outstanding\n"

        # Total summary
        total_outstanding = sum(outstanding_by_type.values())
        msg += f"\n📊 <b>Total Outstanding:</b> {TelegramFormatter.format_number(total_outstanding)} items"

        # Estimate
        avg_per_day = 160  # Average retrieval rate
        days_needed = total_outstanding / avg_per_day if avg_per_day > 0 else 0
        msg += f"\n⏱️ <b>Estimated Time:</b> {days_needed:.0f} days"
        msg += f"\n(Based on avg {avg_per_day} retrievals/day)"

        return msg

    @staticmethod
    def format_user_stats(users: List[Dict]) -> str:
        """Format user activity statistics"""
        msg = """👥 <b>User Activity Statistics</b>

"""

        for user_data in users[:10]:  # Top 10 users
            username = user_data['username']
            deployments = TelegramFormatter.format_number(user_data['deployments'])
            lines_worked = user_data['lines_worked']
            last_activity = TelegramFormatter.format_date_short(user_data.get('last_activity'))

            msg += f"""<b>{username}</b>
• Deployments: {deployments}
• Lines: {lines_worked}
• Last Active: {last_activity}

"""

        return msg

    @staticmethod
    def format_help_message() -> str:
        """Format help message with all commands"""
        msg = """🤖 <b>Swath Movers Bot - Commands</b>

<b>📊 Statistics</b>
/stats - Overall project statistics
/today - Today's activity summary
/users - User activity statistics

<b>📍 Line Commands</b>
/line [number] - Detailed line report
/lines all - List all lines
/lines complete - Completed lines only
/lines incomplete - Lines needing work
/lines active - Lines with today's activity

<b>🗂️ Swath Commands</b>
/swath [1-8] - Detailed swath report
/swaths - Compare all 8 swaths

<b>📈 Progress & Analysis</b>
/progress - Overall progress by type
/progress nodes - Node deployment status
/progress hydro - Hydrophone status
/retrieval - Retrieval status report
/coverage - Survey coverage analysis
/alerts - Critical alerts and warnings

<b>🔍 Gap Analysis</b>
/gaps - Project-wide gap statistics
/gaps line [number] - Line gap analysis
/gaps swath [1-8] - Swath gap analysis
/gaps all - All lines with gaps

<b>💾 Backup & Export</b>
/backup - Create manual database backup
/export line [num] - Export line data (CSV)
/export swath [num] - Export swath data
/export retrieval - Retrieval status report
/export all - All lines summary

<b>ℹ️ Help</b>
/help - Show this message
/start - Welcome message

---
💡 <b>Tips:</b>
• Commands are case-insensitive
• Line numbers like: /line 5000
• Gap detection finds empty shotpoints
• All reports sent directly to chat
"""

        return msg

    @staticmethod
    def format_error_message(error: str) -> str:
        """Format error message"""
        return f"❌ <b>Error:</b> {error}\n\nUse /help for available commands"

    @staticmethod
    def truncate_list(items: List, max_items: int = 10, show_total: bool = True) -> str:
        """Truncate long lists with summary"""
        if len(items) <= max_items:
            return ""

        remaining = len(items) - max_items
        return f"\n... and {remaining} more" if show_total else ""

    @staticmethod
    def format_line_gaps(line_number: int, gaps: List[Dict]) -> str:
        """Format gap report for a specific line"""
        if not gaps:
            return f"✅ <b>Line {line_number}</b>\n\nNo gaps detected! Line has continuous coverage."

        total_gap_points = sum(gap['size'] for gap in gaps)

        msg = f"""🔍 <b>Line {line_number} - Gap Analysis</b>

⚠️ <b>Gaps Detected:</b> {len(gaps)} gap(s)
📍 <b>Total Gap Points:</b> {total_gap_points}

<b>Gap Details:</b>
"""

        for i, gap in enumerate(gaps, 1):
            msg += f"\n{i}. Shotpoints {gap['start_shotpoint']} - {gap['end_shotpoint']}"
            msg += f"\n   Size: {gap['size']} consecutive empty points\n"

        # Severity assessment
        if total_gap_points > 50:
            msg += "\n🔴 <b>Severity:</b> CRITICAL - Large gaps detected"
        elif total_gap_points > 20:
            msg += "\n🟡 <b>Severity:</b> HIGH - Significant gaps"
        elif total_gap_points > 10:
            msg += "\n🟠 <b>Severity:</b> MEDIUM - Moderate gaps"
        else:
            msg += "\n🟢 <b>Severity:</b> LOW - Minor gaps"

        msg += "\n\n💡 <b>Action:</b> Deploy equipment at these shotpoints to fill gaps"

        return msg

    @staticmethod
    def format_all_gaps_summary(lines_with_gaps: List[Dict], limit: int = 20) -> str:
        """Format summary of all lines with gaps"""
        if not lines_with_gaps:
            return "✅ <b>No Gaps Detected</b>\n\nAll lines have continuous coverage!"

        msg = f"""🔍 <b>Gap Analysis - All Lines</b>

📊 <b>Summary:</b>
• Lines with Gaps: {len(lines_with_gaps)}
• Total Gaps: {sum(l['gap_count'] for l in lines_with_gaps)}
• Total Gap Points: {TelegramFormatter.format_number(sum(l['total_gap_points'] for l in lines_with_gaps))}

<b>Lines by Severity:</b>
"""

        # Show top lines with most gaps
        for line_data in lines_with_gaps[:limit]:
            line = line_data['line']
            gaps = line_data['gap_count']
            points = line_data['total_gap_points']

            # Severity emoji
            if points > 50:
                emoji = "🔴"
            elif points > 20:
                emoji = "🟡"
            elif points > 10:
                emoji = "🟠"
            else:
                emoji = "🟢"

            msg += f"\n{emoji} Line {line}: {gaps} gap(s), {points} points"

        if len(lines_with_gaps) > limit:
            remaining = len(lines_with_gaps) - limit
            msg += f"\n\n... and {remaining} more lines with gaps"

        msg += "\n\nUse: /gaps line [number] for detailed gap info"

        return msg

    @staticmethod
    def format_gap_statistics(stats: Dict) -> str:
        """Format project-wide gap statistics"""
        msg = f"""📊 <b>Project Gap Statistics</b>

<b>Overview:</b>
• Total Lines with Gaps: {stats['total_lines_with_gaps']}
• Total Gaps Detected: {stats['total_gaps']}
• Total Gap Points: {TelegramFormatter.format_number(stats['total_gap_points'])}

<b>Lines by Severity:</b>
"""

        severity = stats['lines_by_severity']

        if severity['critical']:
            msg += f"\n🔴 <b>CRITICAL</b> (>50 gap points): {len(severity['critical'])} lines"
            msg += f"\n   Lines: {', '.join(map(str, severity['critical'][:5]))}"
            if len(severity['critical']) > 5:
                msg += f" +{len(severity['critical']) - 5} more"

        if severity['high']:
            msg += f"\n🟡 <b>HIGH</b> (20-50 gap points): {len(severity['high'])} lines"
            msg += f"\n   Lines: {', '.join(map(str, severity['high'][:5]))}"
            if len(severity['high']) > 5:
                msg += f" +{len(severity['high']) - 5} more"

        if severity['medium']:
            msg += f"\n🟠 <b>MEDIUM</b> (10-20 gap points): {len(severity['medium'])} lines"

        if severity['low']:
            msg += f"\n🟢 <b>LOW</b> (5-10 gap points): {len(severity['low'])} lines"

        if not any(severity.values()):
            msg += "\n✅ <b>No gaps detected!</b>"

        msg += "\n\nUse: /gaps line [number] for specific line details"

        return msg
