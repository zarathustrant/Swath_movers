#!/usr/bin/env python3
"""
Chart Generation Module for Telegram Bot
Creates matplotlib charts for reports and statistics
"""

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from io import BytesIO
import numpy as np
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)


class ChartGenerator:
    """Generate charts for Telegram bot reports"""

    # Color scheme
    COLORS = {
        'nodes': '#f6ee02',
        'hydro': '#057af0',
        'marsh': '#95cef0',
        'sm10': '#f18807',
        'complete': '#06e418',
        'incomplete': '#f50303',
        'warning': '#f6ee02',
        'primary': '#2196F3',
        'success': '#4CAF50',
        'danger': '#F44336',
        'warning_orange': '#FF9800'
    }

    def __init__(self):
        """Initialize chart generator"""
        plt.style.use('seaborn-v0_8-darkgrid')

    def _save_to_bytes(self, fig) -> BytesIO:
        """Save matplotlib figure to BytesIO"""
        buf = BytesIO()
        fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        plt.close(fig)
        return buf

    def create_progress_bar_chart(self, progress_data: Dict) -> BytesIO:
        """
        Create horizontal bar chart showing progress by deployment type

        Args:
            progress_data: Dict with deployment types and their progress
                          {type: {'deployed': int, 'retrieved': int, 'completion_pct': float}}

        Returns:
            BytesIO containing PNG image
        """
        try:
            fig, ax = plt.subplots(figsize=(10, 6))

            types = list(progress_data.keys())
            deployed = [progress_data[t]['deployed'] for t in types]
            retrieved = [progress_data[t]['retrieved'] for t in types]

            y_pos = np.arange(len(types))
            bar_height = 0.35

            # Create bars
            bars1 = ax.barh(y_pos - bar_height/2, deployed, bar_height,
                           label='Deployed', color=self.COLORS['warning_orange'], alpha=0.8)
            bars2 = ax.barh(y_pos + bar_height/2, retrieved, bar_height,
                           label='Retrieved', color=self.COLORS['success'], alpha=0.8)

            ax.set_yticks(y_pos)
            ax.set_yticklabels(types)
            ax.set_xlabel('Count', fontweight='bold')
            ax.set_title('Deployment Progress by Type', fontweight='bold', fontsize=14)
            ax.legend()

            # Add value labels on bars
            for bar in bars1:
                width = bar.get_width()
                ax.text(width, bar.get_y() + bar.get_height()/2,
                       f'{int(width):,}', ha='left', va='center', fontsize=9)

            for bar in bars2:
                width = bar.get_width()
                ax.text(width, bar.get_y() + bar.get_height()/2,
                       f'{int(width):,}', ha='left', va='center', fontsize=9)

            plt.tight_layout()
            return self._save_to_bytes(fig)

        except Exception as e:
            logger.error(f"Error creating progress bar chart: {e}")
            return None

    def create_pie_chart(self, data: Dict, title: str) -> BytesIO:
        """
        Create pie chart from data

        Args:
            data: Dict with labels and values {label: value}
            title: Chart title

        Returns:
            BytesIO containing PNG image
        """
        try:
            fig, ax = plt.subplots(figsize=(10, 8))

            labels = list(data.keys())
            values = list(data.values())
            colors = plt.cm.Set3(np.linspace(0, 1, len(labels)))

            # Create pie chart
            wedges, texts, autotexts = ax.pie(values, labels=labels, autopct='%1.1f%%',
                                               colors=colors, startangle=90)

            # Make percentage text bold
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontweight('bold')
                autotext.set_fontsize(10)

            ax.set_title(title, fontweight='bold', fontsize=14)
            plt.tight_layout()
            return self._save_to_bytes(fig)

        except Exception as e:
            logger.error(f"Error creating pie chart: {e}")
            return None

    def create_timeline_chart(self, timeline_data: List[Dict]) -> BytesIO:
        """
        Create line chart showing activity over time

        Args:
            timeline_data: List of dicts with 'date' and 'count' keys

        Returns:
            BytesIO containing PNG image
        """
        try:
            fig, ax = plt.subplots(figsize=(12, 6))

            # Group by date
            from collections import defaultdict
            date_counts = defaultdict(int)

            for entry in timeline_data:
                date = entry['date']
                count = entry['count']
                date_counts[date] += count

            # Sort by date
            dates = sorted(date_counts.keys())
            counts = [date_counts[d] for d in dates]

            ax.plot(dates, counts, marker='o', linewidth=2, markersize=6,
                   color=self.COLORS['primary'])
            ax.fill_between(dates, counts, alpha=0.3, color=self.COLORS['primary'])

            ax.set_xlabel('Date', fontweight='bold')
            ax.set_ylabel('Deployments', fontweight='bold')
            ax.set_title('Deployment Activity Timeline', fontweight='bold', fontsize=14)
            ax.grid(True, alpha=0.3)

            # Rotate date labels
            plt.xticks(rotation=45, ha='right')

            plt.tight_layout()
            return self._save_to_bytes(fig)

        except Exception as e:
            logger.error(f"Error creating timeline chart: {e}")
            return None

    def create_completion_gauge(self, completion_pct: float) -> BytesIO:
        """
        Create gauge/donut chart showing completion percentage

        Args:
            completion_pct: Completion percentage (0-100)

        Returns:
            BytesIO containing PNG image
        """
        try:
            fig, ax = plt.subplots(figsize=(8, 6))

            # Determine color based on percentage
            if completion_pct >= 90:
                color = self.COLORS['success']
            elif completion_pct >= 70:
                color = self.COLORS['warning']
            else:
                color = self.COLORS['danger']

            # Create donut chart
            sizes = [completion_pct, 100 - completion_pct]
            colors = [color, '#E0E0E0']
            explode = (0.05, 0)

            wedges, texts = ax.pie(sizes, colors=colors, explode=explode,
                                   startangle=90, counterclock=False)

            # Draw circle for donut effect
            centre_circle = plt.Circle((0, 0), 0.70, fc='white')
            ax.add_artist(centre_circle)

            # Add percentage text in center
            ax.text(0, 0, f'{completion_pct:.1f}%',
                   ha='center', va='center', fontsize=40, fontweight='bold')
            ax.text(0, -0.15, 'Complete',
                   ha='center', va='center', fontsize=16, color='gray')

            ax.set_title('Project Completion', fontweight='bold', fontsize=14, pad=20)
            plt.tight_layout()
            return self._save_to_bytes(fig)

        except Exception as e:
            logger.error(f"Error creating completion gauge: {e}")
            return None

    def create_swath_comparison_chart(self, swaths_data: List[Dict]) -> BytesIO:
        """
        Create bar chart comparing all swaths

        Args:
            swaths_data: List of swath dicts with completion data

        Returns:
            BytesIO containing PNG image
        """
        try:
            fig, ax = plt.subplots(figsize=(12, 6))

            swath_nums = [s['swath'] for s in swaths_data]
            completions = [s.get('completion_pct', 0) for s in swaths_data]

            # Color bars based on completion
            colors = [self.COLORS['success'] if c >= 90 else
                     self.COLORS['warning'] if c >= 70 else
                     self.COLORS['danger'] for c in completions]

            bars = ax.bar(swath_nums, completions, color=colors, alpha=0.8, edgecolor='black')

            ax.set_xlabel('Swath Number', fontweight='bold')
            ax.set_ylabel('Completion %', fontweight='bold')
            ax.set_title('Swath Completion Comparison', fontweight='bold', fontsize=14)
            ax.set_ylim(0, 105)
            ax.set_xticks(swath_nums)
            ax.grid(True, axis='y', alpha=0.3)

            # Add percentage labels on bars
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{height:.0f}%', ha='center', va='bottom', fontweight='bold')

            # Add reference line at 100%
            ax.axhline(y=100, color='green', linestyle='--', alpha=0.5, label='Target')

            plt.tight_layout()
            return self._save_to_bytes(fig)

        except Exception as e:
            logger.error(f"Error creating swath comparison chart: {e}")
            return None

    def create_line_status_chart(self, lines_data: List[Dict], top_n: int = 20) -> BytesIO:
        """
        Create chart showing top lines by outstanding items

        Args:
            lines_data: List of line dicts with outstanding data
            top_n: Number of top lines to show

        Returns:
            BytesIO containing PNG image
        """
        try:
            # Sort by outstanding and take top N
            sorted_lines = sorted(lines_data, key=lambda x: x.get('outstanding', 0), reverse=True)[:top_n]

            fig, ax = plt.subplots(figsize=(12, 8))

            lines = [f"Line {l['line']}" for l in sorted_lines]
            outstanding = [l.get('outstanding', 0) for l in sorted_lines]

            # Color based on priority
            colors = [self.COLORS['danger'] if o > 50 else
                     self.COLORS['warning_orange'] if o > 20 else
                     self.COLORS['warning'] for o in outstanding]

            y_pos = np.arange(len(lines))
            bars = ax.barh(y_pos, outstanding, color=colors, alpha=0.8, edgecolor='black')

            ax.set_yticks(y_pos)
            ax.set_yticklabels(lines, fontsize=9)
            ax.set_xlabel('Outstanding Items', fontweight='bold')
            ax.set_title(f'Top {top_n} Lines by Outstanding Items', fontweight='bold', fontsize=14)
            ax.grid(True, axis='x', alpha=0.3)

            # Add value labels
            for bar in bars:
                width = bar.get_width()
                ax.text(width, bar.get_y() + bar.get_height()/2,
                       f' {int(width)}', ha='left', va='center', fontsize=9)

            # Add legend
            high = mpatches.Patch(color=self.COLORS['danger'], label='High Priority (>50)')
            med = mpatches.Patch(color=self.COLORS['warning_orange'], label='Medium Priority (20-50)')
            low = mpatches.Patch(color=self.COLORS['warning'], label='Low Priority (<20)')
            ax.legend(handles=[high, med, low], loc='lower right')

            plt.tight_layout()
            return self._save_to_bytes(fig)

        except Exception as e:
            logger.error(f"Error creating line status chart: {e}")
            return None

    def create_user_activity_chart(self, users_data: List[Dict]) -> BytesIO:
        """
        Create bar chart showing user activity

        Args:
            users_data: List of user dicts with deployment counts

        Returns:
            BytesIO containing PNG image
        """
        try:
            fig, ax = plt.subplots(figsize=(10, 6))

            usernames = [u['username'] for u in users_data]
            deployments = [u['deployments'] for u in users_data]

            bars = ax.bar(usernames, deployments, color=self.COLORS['primary'],
                         alpha=0.8, edgecolor='black')

            ax.set_xlabel('User', fontweight='bold')
            ax.set_ylabel('Deployments', fontweight='bold')
            ax.set_title('User Activity', fontweight='bold', fontsize=14)
            ax.grid(True, axis='y', alpha=0.3)

            # Add value labels on bars
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{int(height):,}', ha='center', va='bottom', fontweight='bold')

            # Rotate labels if many users
            if len(usernames) > 5:
                plt.xticks(rotation=45, ha='right')

            plt.tight_layout()
            return self._save_to_bytes(fig)

        except Exception as e:
            logger.error(f"Error creating user activity chart: {e}")
            return None

    def create_heatmap(self, data: List[List[float]], x_labels: List[str],
                       y_labels: List[str], title: str) -> BytesIO:
        """
        Create heatmap visualization

        Args:
            data: 2D array of values
            x_labels: Labels for x-axis
            y_labels: Labels for y-axis
            title: Chart title

        Returns:
            BytesIO containing PNG image
        """
        try:
            fig, ax = plt.subplots(figsize=(12, 8))

            im = ax.imshow(data, cmap='RdYlGn', aspect='auto', vmin=0, vmax=100)

            # Set ticks
            ax.set_xticks(np.arange(len(x_labels)))
            ax.set_yticks(np.arange(len(y_labels)))
            ax.set_xticklabels(x_labels)
            ax.set_yticklabels(y_labels)

            # Rotate x labels
            plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")

            # Add colorbar
            cbar = ax.figure.colorbar(im, ax=ax)
            cbar.ax.set_ylabel('Completion %', rotation=-90, va="bottom", fontweight='bold')

            # Add text annotations
            for i in range(len(y_labels)):
                for j in range(len(x_labels)):
                    text = ax.text(j, i, f'{data[i][j]:.0f}%',
                                 ha="center", va="center", color="black", fontsize=8)

            ax.set_title(title, fontweight='bold', fontsize=14)
            plt.tight_layout()
            return self._save_to_bytes(fig)

        except Exception as e:
            logger.error(f"Error creating heatmap: {e}")
            return None
