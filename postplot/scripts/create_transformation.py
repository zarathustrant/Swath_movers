#!/usr/bin/env python3
"""
Create and save coordinate transformation from control points
"""

import sys
import os
import csv
import psycopg2

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from postplot.enserv_transform import CoordinateTransform


def load_control_points(filepath: str):
    """Load control points from CSV file"""
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
    """Main script"""
    import argparse

    parser = argparse.ArgumentParser(description='Create coordinate transformation')
    parser.add_argument('control_points', help='Path to control points CSV file')
    parser.add_argument('--name', required=True, help='Name of transformation (e.g., Enserv_West_Belt)')
    parser.add_argument('--description', default='', help='Description of transformation')
    parser.add_argument('--db-host', default='localhost', help='PostgreSQL host')
    parser.add_argument('--db-name', default='swath_movers', help='Database name')
    parser.add_argument('--db-user', default='aerys', help='Database user')
    parser.add_argument('--db-password', default='aerys123', help='Database password')

    args = parser.parse_args()

    print(f"Loading control points from {args.control_points}...")
    control_points = load_control_points(args.control_points)
    print(f"  Loaded {len(control_points)} control points")

    # Connect to database
    print(f"\nConnecting to database...")
    conn = psycopg2.connect(
        host=args.db_host,
        database=args.db_name,
        user=args.db_user,
        password=args.db_password
    )
    print(f"  Connected to {args.db_name}")

    # Create transformation
    print(f"\nCalculating transformation coefficients...")
    transform = CoordinateTransform(name=args.name, db_conn=conn)

    rmse_lat, rmse_lon, rmse_meters = transform.calculate_coefficients(control_points)

    print(f"\n✓ Transformation calculated successfully!")
    print(f"  RMSE Latitude:  {rmse_lat:.8f}°")
    print(f"  RMSE Longitude: {rmse_lon:.8f}°")
    print(f"  RMSE (approx):  {rmse_meters:.2f} meters")

    # Print coefficient summary
    print(f"\nCoefficients:")
    print(f"  Longitude: {transform.coeffs_lon}")
    print(f"  Latitude:  {transform.coeffs_lat}")

    # Save to database
    print(f"\nSaving transformation to database...")
    transform.save_to_database(
        description=args.description,
        created_by='system'
    )

    # Validate on a few sample points
    print(f"\n\nValidation (first 5 control points):")
    for i, pt in enumerate(control_points[:5]):
        pred_lat, pred_lon = transform.transform(pt['x'], pt['y'])
        error_lat = pred_lat - pt['lat']
        error_lon = pred_lon - pt['lon']
        error_meters = error_lat * 111000

        print(f"  Point {i+1} (Line {pt['line']}, SP {pt['shotpoint']}):")
        print(f"    True:      ({pt['lat']:.8f}, {pt['lon']:.8f})")
        print(f"    Predicted: ({pred_lat:.8f}, {pred_lon:.8f})")
        print(f"    Error:     Lat {error_lat:.8f}° ({error_meters:.2f}m), Lon {error_lon:.8f}°")

    conn.close()

    print(f"\n✓ Done! Transformation '{args.name}' is ready to use.")

    return 0


if __name__ == '__main__':
    sys.exit(main())
