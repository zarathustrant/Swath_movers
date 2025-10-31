#!/usr/bin/env python3
"""
Create and save coordinate transformation from control points (standalone version)
"""

import sys
import csv
import psycopg2
from psycopg2.extras import Json
import numpy as np


def create_polynomial_matrix(XY, order=3):
    """Create design matrix for polynomial transformation"""
    X = XY[:, 0]
    Y = XY[:, 1]

    A = np.column_stack([
        np.ones(len(X)),
        X, Y,
        X**2, X*Y, Y**2,
        X**3, X**2*Y, X*Y**2, Y**3
    ])
    return A


def calculate_transformation(control_points):
    """Calculate transformation coefficients"""
    XY = np.array([[pt['x'], pt['y']] for pt in control_points])
    latlon = np.array([[pt['lat'], pt['lon']] for pt in control_points])

    A = create_polynomial_matrix(XY)

    coeffs_lon, _, _, _ = np.linalg.lstsq(A, latlon[:, 1], rcond=None)
    coeffs_lat, _, _, _ = np.linalg.lstsq(A, latlon[:, 0], rcond=None)

    predicted_lon = A @ coeffs_lon
    predicted_lat = A @ coeffs_lat

    rmse_lon = float(np.sqrt(np.mean((predicted_lon - latlon[:, 1])**2)))
    rmse_lat = float(np.sqrt(np.mean((predicted_lat - latlon[:, 0])**2)))
    rmse_meters = float(rmse_lat * 111000)

    return coeffs_lon, coeffs_lat, rmse_lon, rmse_lat, rmse_meters


def load_control_points(filepath):
    """Load control points from CSV"""
    points = []
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            points.append({
                'line': int(row['line']),
                'shotpoint': int(row['shotpoint']),
                'x': float(row['x']),
                'y': float(row['y']),
                'lat': float(row['lat']),
                'lon': float(row['lon'])
            })
    return points


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('control_points', help='Path to control points CSV')
    parser.add_argument('--name', required=True, help='Transformation name')
    parser.add_argument('--description', default='', help='Description')
    parser.add_argument('--db-host', default='localhost')
    parser.add_argument('--db-name', default='swath_movers')
    parser.add_argument('--db-user', default='aerys')
    parser.add_argument('--db-password', default='aerys123')

    args = parser.parse_args()

    print(f"Loading control points from {args.control_points}...")
    control_points = load_control_points(args.control_points)
    print(f"  Loaded {len(control_points)} control points")

    print(f"\nCalculating transformation coefficients...")
    coeffs_lon, coeffs_lat, rmse_lon, rmse_lat, rmse_meters = calculate_transformation(control_points)

    print(f"\n✓ Transformation calculated successfully!")
    print(f"  RMSE Latitude:  {rmse_lat:.8f}°")
    print(f"  RMSE Longitude: {rmse_lon:.8f}°")
    print(f"  RMSE (approx):  {rmse_meters:.2f} meters")

    # Connect to database
    print(f"\nConnecting to database...")
    conn = psycopg2.connect(
        host=args.db_host,
        database=args.db_name,
        user=args.db_user,
        password=args.db_password
    )

    cursor = conn.cursor()

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
            args.name,
            args.description,
            Json(coeffs_lon.tolist()),
            Json(coeffs_lat.tolist()),
            rmse_lon,
            rmse_lat,
            rmse_meters,
            len(control_points),
            'system'
        ))

        conn.commit()
        print(f"\n✓ Saved transformation '{args.name}' to database")

    except Exception as e:
        conn.rollback()
        print(f"\n✗ Error saving to database: {e}")
        return 1
    finally:
        cursor.close()
        conn.close()

    # Test on first few points
    print(f"\nValidation (first 5 control points):")
    for i, pt in enumerate(control_points[:5]):
        terms = np.array([
            1,
            pt['x'], pt['y'],
            pt['x']**2, pt['x']*pt['y'], pt['y']**2,
            pt['x']**3, pt['x']**2*pt['y'], pt['x']*pt['y']**2, pt['y']**3
        ])

        pred_lon = float(np.dot(coeffs_lon, terms))
        pred_lat = float(np.dot(coeffs_lat, terms))

        error_lat = pred_lat - pt['lat']
        error_lon = pred_lon - pt['lon']
        error_meters = error_lat * 111000

        print(f"  Point {i+1} (Line {pt['line']}, SP {pt['shotpoint']}):")
        print(f"    Error: Lat {error_lat:.8f}° ({error_meters:.2f}m), Lon {error_lon:.8f}°")

    print(f"\n✓ Done! Transformation '{args.name}' is ready to use.")

    return 0


if __name__ == '__main__':
    sys.exit(main())
