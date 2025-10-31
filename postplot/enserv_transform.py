"""
Enserv West Belt Coordinate Transformation Module

Implements 3rd-order polynomial transformation for converting UTM (X, Y) coordinates
to Geographic (Lat, Lon) coordinates using control points.

Transformation equations:
    lon = a₀ + a₁X + a₂Y + a₃X² + a₄XY + a₅Y² + a₆X³ + a₇X²Y + a₈XY² + a₉Y³
    lat = b₀ + b₁X + b₂Y + b₃X² + b₄XY + b₅Y² + b₆X³ + b₇X²Y + b₈XY² + b₉Y³
"""

import numpy as np
import json
from typing import List, Dict, Tuple, Optional
import psycopg2
from psycopg2.extras import Json


class CoordinateTransform:
    """3rd-order polynomial coordinate transformation"""

    def __init__(self, name: str = None, db_conn=None):
        """
        Initialize coordinate transformation

        Args:
            name: Name of the transformation (e.g., "Enserv_West_Belt")
            db_conn: PostgreSQL database connection
        """
        self.name = name
        self.db_conn = db_conn
        self.coeffs_lon = None
        self.coeffs_lat = None
        self.rmse_lon = None
        self.rmse_lat = None
        self.rmse_meters = None
        self.control_point_count = 0

    @staticmethod
    def create_polynomial_matrix(XY: np.ndarray, order: int = 3) -> np.ndarray:
        """
        Create design matrix for polynomial transformation

        Args:
            XY: Array of shape (n, 2) with X and Y coordinates
            order: Polynomial order (default 3)

        Returns:
            Design matrix A of shape (n, 10) for 3rd order polynomial
        """
        X = XY[:, 0]
        Y = XY[:, 1]

        # 3rd order polynomial terms: 1, X, Y, X², XY, Y², X³, X²Y, XY², Y³
        A = np.column_stack([
            np.ones(len(X)),  # a₀/b₀: constant
            X, Y,              # a₁/b₁, a₂/b₂: 1st order
            X**2, X*Y, Y**2,   # a₃/b₃, a₄/b₄, a₅/b₅: 2nd order
            X**3, X**2*Y, X*Y**2, Y**3  # a₆/b₆, a₇/b₇, a₈/b₈, a₉/b₉: 3rd order
        ])

        return A

    def calculate_coefficients(self, control_points: List[Dict]) -> Tuple[float, float, float]:
        """
        Calculate transformation coefficients from control points

        Args:
            control_points: List of dicts with keys: 'x', 'y', 'lat', 'lon'

        Returns:
            Tuple of (rmse_lat, rmse_lon, rmse_meters)
        """
        # Extract arrays
        XY = np.array([[pt['x'], pt['y']] for pt in control_points])
        latlon = np.array([[pt['lat'], pt['lon']] for pt in control_points])

        # Create design matrix
        A = self.create_polynomial_matrix(XY)

        # Solve for coefficients using least squares
        self.coeffs_lon, _, _, _ = np.linalg.lstsq(A, latlon[:, 1], rcond=None)
        self.coeffs_lat, _, _, _ = np.linalg.lstsq(A, latlon[:, 0], rcond=None)

        # Calculate RMSE on control points
        predicted_lon = A @ self.coeffs_lon
        predicted_lat = A @ self.coeffs_lat

        self.rmse_lon = float(np.sqrt(np.mean((predicted_lon - latlon[:, 1])**2)))
        self.rmse_lat = float(np.sqrt(np.mean((predicted_lat - latlon[:, 0])**2)))

        # Convert to approximate meters (1 degree ≈ 111 km)
        self.rmse_meters = float(self.rmse_lat * 111000)

        self.control_point_count = len(control_points)

        return self.rmse_lat, self.rmse_lon, self.rmse_meters

    def transform(self, x: float, y: float) -> Tuple[float, float]:
        """
        Transform single XY coordinate to lat/lon

        Args:
            x: X coordinate (Easting)
            y: Y coordinate (Northing)

        Returns:
            Tuple of (latitude, longitude)
        """
        if self.coeffs_lon is None or self.coeffs_lat is None:
            raise ValueError("Transformation coefficients not calculated or loaded")

        # Create polynomial terms
        terms = np.array([
            1,
            x, y,
            x**2, x*y, y**2,
            x**3, x**2*y, x*y**2, y**3
        ])

        lon = float(np.dot(self.coeffs_lon, terms))
        lat = float(np.dot(self.coeffs_lat, terms))

        return lat, lon

    def transform_batch(self, XY: np.ndarray) -> np.ndarray:
        """
        Transform multiple XY coordinates to lat/lon

        Args:
            XY: Array of shape (n, 2) with X and Y coordinates

        Returns:
            Array of shape (n, 2) with latitude and longitude
        """
        if self.coeffs_lon is None or self.coeffs_lat is None:
            raise ValueError("Transformation coefficients not calculated or loaded")

        A = self.create_polynomial_matrix(XY)
        lons = A @ self.coeffs_lon
        lats = A @ self.coeffs_lat

        return np.column_stack([lats, lons])

    def save_to_database(self, description: str = "", created_by: str = "system"):
        """
        Save transformation to database

        Args:
            description: Description of the transformation
            created_by: Username who created this transformation
        """
        if self.db_conn is None:
            raise ValueError("Database connection not provided")

        if self.coeffs_lon is None or self.coeffs_lat is None:
            raise ValueError("No coefficients to save. Calculate first.")

        cursor = self.db_conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO coordinate_transforms (
                    name, description,
                    coefficients_lon, coefficients_lat,
                    rmse_lon, rmse_lat, rmse_meters,
                    control_point_count, created_by
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (name)
                DO UPDATE SET
                    description = EXCLUDED.description,
                    coefficients_lon = EXCLUDED.coefficients_lon,
                    coefficients_lat = EXCLUDED.coefficients_lat,
                    rmse_lon = EXCLUDED.rmse_lon,
                    rmse_lat = EXCLUDED.rmse_lat,
                    rmse_meters = EXCLUDED.rmse_meters,
                    control_point_count = EXCLUDED.control_point_count,
                    created_by = EXCLUDED.created_by,
                    created_at = CURRENT_TIMESTAMP
            """, (
                self.name,
                description,
                Json(self.coeffs_lon.tolist()),
                Json(self.coeffs_lat.tolist()),
                self.rmse_lon,
                self.rmse_lat,
                self.rmse_meters,
                self.control_point_count,
                created_by
            ))

            self.db_conn.commit()
            print(f"✓ Saved transformation '{self.name}' to database")
            print(f"  RMSE: {self.rmse_meters:.2f} meters")
            print(f"  Control points: {self.control_point_count}")

        except Exception as e:
            self.db_conn.rollback()
            raise Exception(f"Failed to save transformation: {str(e)}")
        finally:
            cursor.close()

    def load_from_database(self, name: str = None):
        """
        Load transformation from database

        Args:
            name: Name of transformation to load (uses self.name if not provided)
        """
        if self.db_conn is None:
            raise ValueError("Database connection not provided")

        load_name = name or self.name
        if not load_name:
            raise ValueError("No transformation name provided")

        cursor = self.db_conn.cursor()

        try:
            cursor.execute("""
                SELECT
                    coefficients_lon, coefficients_lat,
                    rmse_lon, rmse_lat, rmse_meters,
                    control_point_count
                FROM coordinate_transforms
                WHERE name = %s
            """, (load_name,))

            row = cursor.fetchone()

            if row is None:
                raise ValueError(f"Transformation '{load_name}' not found in database")

            self.name = load_name
            self.coeffs_lon = np.array(row[0])
            self.coeffs_lat = np.array(row[1])
            self.rmse_lon = float(row[2])
            self.rmse_lat = float(row[3])
            self.rmse_meters = float(row[4]) if row[4] else None
            self.control_point_count = row[5]

            print(f"✓ Loaded transformation '{self.name}'")
            print(f"  RMSE: {self.rmse_meters:.2f} meters")
            print(f"  Control points: {self.control_point_count}")

        finally:
            cursor.close()

    def validate(self, control_points: List[Dict]) -> Dict[str, float]:
        """
        Validate transformation against control points

        Args:
            control_points: List of dicts with keys: 'x', 'y', 'lat', 'lon'

        Returns:
            Dict with validation metrics
        """
        XY = np.array([[pt['x'], pt['y']] for pt in control_points])
        latlon_true = np.array([[pt['lat'], pt['lon']] for pt in control_points])

        latlon_pred = self.transform_batch(XY)

        errors_lat = latlon_pred[:, 0] - latlon_true[:, 0]
        errors_lon = latlon_pred[:, 1] - latlon_true[:, 1]

        return {
            'rmse_lat': float(np.sqrt(np.mean(errors_lat**2))),
            'rmse_lon': float(np.sqrt(np.mean(errors_lon**2))),
            'rmse_meters': float(np.sqrt(np.mean(errors_lat**2)) * 111000),
            'max_error_lat': float(np.max(np.abs(errors_lat))),
            'max_error_lon': float(np.max(np.abs(errors_lon))),
            'max_error_meters': float(np.max(np.abs(errors_lat)) * 111000),
            'mean_error_lat': float(np.mean(errors_lat)),
            'mean_error_lon': float(np.mean(errors_lon)),
            'point_count': len(control_points)
        }


def get_all_transformations(db_conn) -> List[Dict]:
    """
    Get list of all available transformations from database

    Args:
        db_conn: PostgreSQL database connection

    Returns:
        List of transformation dictionaries
    """
    cursor = db_conn.cursor()

    try:
        cursor.execute("""
            SELECT
                name, description,
                rmse_meters, control_point_count,
                created_by, created_at
            FROM coordinate_transforms
            ORDER BY created_at DESC
        """)

        results = []
        for row in cursor.fetchall():
            results.append({
                'name': row[0],
                'description': row[1],
                'rmse_meters': float(row[2]) if row[2] else None,
                'control_point_count': row[3],
                'created_by': row[4],
                'created_at': row[5].strftime('%Y-%m-%d %H:%M:%S') if row[5] else None
            })

        return results

    finally:
        cursor.close()
