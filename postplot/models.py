"""
Database operations for post plot acquisition tracking
Handles all database queries for source points and acquisition status
"""

import logging
from typing import List, Dict, Callable, Tuple, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class PostPlotDB:
    """Database operations for post plot acquisition tracking"""

    def __init__(self, get_conn_func: Callable, return_conn_func: Callable):
        """
        Initialize with database connection functions

        Args:
            get_conn_func: Function to get database connection
            return_conn_func: Function to return connection to pool
        """
        self.get_connection = get_conn_func
        self.return_connection = return_conn_func

    def get_source_points_geojson(self, swath_numbers: List[int]) -> Dict:
        """
        Get source points as GeoJSON for specified swaths

        Args:
            swath_numbers: List of swath numbers (1-8)

        Returns:
            GeoJSON FeatureCollection
        """
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            features = []

            for swath_num in swath_numbers:
                if swath_num < 1 or swath_num > 8:
                    continue

                table_name = f"post_plot_swath_{swath_num}_sources"

                query = f"""
                    SELECT line, shotpoint, latitude, longitude,
                           is_acquired, acquired_at
                    FROM {table_name}
                    ORDER BY line, shotpoint
                """

                cursor.execute(query)
                rows = cursor.fetchall()

                for row in rows:
                    line, shotpoint, lat, lon, is_acquired, acquired_at = row

                    features.append({
                        "type": "Feature",
                        "geometry": {
                            "type": "Point",
                            "coordinates": [float(lon), float(lat)]
                        },
                        "properties": {
                            "line": line,
                            "shotpoint": shotpoint,
                            "swath": swath_num,
                            "is_acquired": is_acquired,
                            "acquired_at": acquired_at.isoformat() if acquired_at else None
                        }
                    })

            return {
                "type": "FeatureCollection",
                "features": features
            }

        except Exception as e:
            logger.error(f"Error getting source points GeoJSON: {e}", exc_info=True)
            raise
        finally:
            cursor.close()
            self.return_connection(conn)

    def insert_source_points(self, swath_num: int, data: List[Dict], username: str) -> int:
        """
        Insert source points for a swath (clears existing data first)

        Args:
            swath_num: Swath number (1-8)
            data: List of dicts with keys: line, shotpoint, lat, lon
            username: Username uploading the data

        Returns:
            Number of rows inserted

        Raises:
            Exception on database error
        """
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            table_name = f"post_plot_swath_{swath_num}_sources"

            # Clear existing data for this swath
            cursor.execute(f"DELETE FROM {table_name}")
            logger.info(f"Cleared {cursor.rowcount} existing records from {table_name}")

            # Insert new data
            insert_query = f"""
                INSERT INTO {table_name}
                (line, shotpoint, latitude, longitude, is_acquired, uploaded_by, uploaded_at)
                VALUES (%s, %s, %s, %s, FALSE, %s, NOW())
            """

            rows = [
                (row['line'], row['shotpoint'], row['lat'], row['lon'], username)
                for row in data
            ]

            cursor.executemany(insert_query, rows)
            conn.commit()

            logger.info(f"Inserted {len(rows)} source points into {table_name}")
            return len(rows)

        except Exception as e:
            conn.rollback()
            logger.error(f"Error inserting source points: {e}", exc_info=True)
            raise
        finally:
            cursor.close()
            self.return_connection(conn)

    def mark_as_acquired(self, swath_num: int, acquisitions: List[Dict]) -> Tuple[int, int]:
        """
        Mark source points as acquired (row-by-row: Line, Station)

        Args:
            swath_num: Swath number (1-8)
            acquisitions: List of dicts with keys: line, station

        Returns:
            Tuple of (updated_count, not_found_count)

        Raises:
            Exception on database error
        """
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            table_name = f"post_plot_swath_{swath_num}_sources"

            updated_count = 0
            not_found_count = 0

            for acq in acquisitions:
                update_query = f"""
                    UPDATE {table_name}
                    SET is_acquired = TRUE, acquired_at = NOW()
                    WHERE line = %s AND shotpoint = %s
                """
                cursor.execute(update_query, (acq['line'], acq['station']))

                if cursor.rowcount > 0:
                    updated_count += 1
                else:
                    not_found_count += 1

            conn.commit()

            logger.info(f"Marked {updated_count} shots as acquired in {table_name}, {not_found_count} not found")
            return (updated_count, not_found_count)

        except Exception as e:
            conn.rollback()
            logger.error(f"Error marking shots as acquired: {e}", exc_info=True)
            raise
        finally:
            cursor.close()
            self.return_connection(conn)

    def get_all_swath_stats(self) -> List[Dict]:
        """
        Get statistics for all swaths

        Returns:
            List of dicts with swath statistics
        """
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            stats = []

            for swath_num in range(1, 9):
                table_name = f"post_plot_swath_{swath_num}_sources"

                query = f"""
                    SELECT
                        COUNT(*) as total,
                        SUM(CASE WHEN is_acquired THEN 1 ELSE 0 END) as acquired,
                        MAX(uploaded_at) as last_upload
                    FROM {table_name}
                """

                cursor.execute(query)
                row = cursor.fetchone()

                total = row[0] if row[0] else 0
                acquired = row[1] if row[1] else 0
                pending = total - acquired
                pct = (acquired / total * 100) if total > 0 else 0

                stats.append({
                    'swath': swath_num,
                    'total': total,
                    'acquired': acquired,
                    'pending': pending,
                    'percentage': pct,
                    'last_upload': row[2]
                })

            return stats

        except Exception as e:
            logger.error(f"Error getting swath statistics: {e}", exc_info=True)
            raise
        finally:
            cursor.close()
            self.return_connection(conn)

    def clear_swath(self, swath_num: int) -> int:
        """
        Clear all data for a swath

        Args:
            swath_num: Swath number (1-8)

        Returns:
            Number of rows deleted

        Raises:
            Exception on database error
        """
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            table_name = f"post_plot_swath_{swath_num}_sources"

            cursor.execute(f"DELETE FROM {table_name}")
            deleted_count = cursor.rowcount
            conn.commit()

            logger.info(f"Cleared {deleted_count} records from {table_name}")
            return deleted_count

        except Exception as e:
            conn.rollback()
            logger.error(f"Error clearing swath data: {e}", exc_info=True)
            raise
        finally:
            cursor.close()
            self.return_connection(conn)

    def get_swath_summary(self, swath_num: int) -> Optional[Dict]:
        """
        Get summary statistics for a single swath

        Args:
            swath_num: Swath number (1-8)

        Returns:
            Dict with swath statistics or None if error
        """
        if swath_num < 1 or swath_num > 8:
            return None

        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            table_name = f"post_plot_swath_{swath_num}_sources"

            query = f"""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN is_acquired THEN 1 ELSE 0 END) as acquired,
                    COUNT(DISTINCT line) as line_count,
                    MIN(line) as min_line,
                    MAX(line) as max_line,
                    MAX(uploaded_at) as last_upload,
                    MAX(acquired_at) as last_acquisition
                FROM {table_name}
            """

            cursor.execute(query)
            row = cursor.fetchone()

            if not row:
                return None

            total = row[0] if row[0] else 0
            acquired = row[1] if row[1] else 0
            pending = total - acquired
            pct = (acquired / total * 100) if total > 0 else 0

            return {
                'swath': swath_num,
                'total': total,
                'acquired': acquired,
                'pending': pending,
                'percentage': pct,
                'line_count': row[2] if row[2] else 0,
                'min_line': row[3],
                'max_line': row[4],
                'last_upload': row[5],
                'last_acquisition': row[6]
            }

        except Exception as e:
            logger.error(f"Error getting swath summary: {e}", exc_info=True)
            return None
        finally:
            cursor.close()
            self.return_connection(conn)
