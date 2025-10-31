#!/usr/bin/env python3
"""
Control Point Extraction Script

Extracts matching control points from .s01 file (X, Y) and base.csv (Lat, Lon)
for calculating coordinate transformation coefficients.
"""

import sys
import os
import csv
import re
from typing import Dict, List, Tuple

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))


def parse_s01_file(filepath: str) -> Dict[Tuple[int, int], Tuple[float, float]]:
    """
    Parse .s01 file and extract Line, Shotpoint, X, Y

    Args:
        filepath: Path to .s01 file

    Returns:
        Dict mapping (line, shotpoint) -> (x, y)
    """
    points = {}

    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            # Skip empty lines
            if not line.strip():
                continue

            # Parse fixed-width format - split by multiple spaces
            # S      2112      5231  1                       480457.0  173961.0  16.1
            # Split on any whitespace (handles multiple spaces)
            fields = line.split()

            if len(fields) < 7:  # Need at least 7 fields (type, line, sp, fid, x, y, depth)
                continue

            try:
                point_type = fields[0]  # S, R, etc.
                line_num = int(fields[1])
                shotpoint = int(fields[2])
                # field[3] is field file ID
                # fields[4] might be empty column
                # Find the numeric X and Y coordinates (should be after field ID)

                # Get last 3 numeric fields: X, Y, Depth
                numeric_fields = []
                for field in fields[1:]:  # Skip point type
                    try:
                        numeric_fields.append(float(field))
                    except ValueError:
                        pass

                if len(numeric_fields) >= 4:  # line, shotpoint, X, Y at minimum
                    # numeric_fields = [line, shotpoint, X, Y, depth] or similar
                    # X and Y should be the larger coordinate values
                    x = numeric_fields[-3]  # Third from end
                    y = numeric_fields[-2]  # Second from end

                    # Only store source points
                    if point_type == 'S':
                        points[(line_num, shotpoint)] = (x, y)

            except (ValueError, IndexError) as e:
                # Skip malformed lines
                continue

    return points


def parse_base_csv(filepath: str) -> Dict[Tuple[int, int], Tuple[float, float]]:
    """
    Parse base.csv and extract Line, Shotpoint, Lat, Lon

    Args:
        filepath: Path to base.csv file

    Returns:
        Dict mapping (line, shotpoint) -> (lat, lon)
    """
    points = {}

    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)

        for row in reader:
            try:
                line_num = int(row['Line'])
                shotpoint = int(row['Shotpoint'])
                lat = float(row['Latitude'])
                lon = float(row['Longitude'])

                points[(line_num, shotpoint)] = (lat, lon)

            except (ValueError, KeyError):
                # Skip malformed rows
                continue

    return points


def match_control_points(s01_points: Dict, base_points: Dict) -> List[Dict]:
    """
    Match control points from both sources

    Args:
        s01_points: Dict from parse_s01_file
        base_points: Dict from parse_base_csv

    Returns:
        List of control point dicts with keys: line, shotpoint, x, y, lat, lon
    """
    control_points = []

    for key, (x, y) in s01_points.items():
        if key in base_points:
            line_num, shotpoint = key
            lat, lon = base_points[key]

            control_points.append({
                'line': line_num,
                'shotpoint': shotpoint,
                'x': x,
                'y': y,
                'lat': lat,
                'lon': lon
            })

    return control_points


def select_distributed_points(control_points: List[Dict], target_count: int = 100) -> List[Dict]:
    """
    Select well-distributed control points across the survey area

    Args:
        control_points: All matched control points
        target_count: Target number of points to select

    Returns:
        List of selected control points
    """
    if len(control_points) <= target_count:
        return control_points

    # Sort by line then shotpoint
    sorted_points = sorted(control_points, key=lambda p: (p['line'], p['shotpoint']))

    # Take every nth point to get even distribution
    step = len(sorted_points) // target_count

    selected = []
    for i in range(0, len(sorted_points), step):
        selected.append(sorted_points[i])
        if len(selected) >= target_count:
            break

    return selected


def main():
    """Main extraction script"""
    import argparse

    parser = argparse.ArgumentParser(description='Extract control points for coordinate transformation')
    parser.add_argument('s01_file', help='Path to .s01 file')
    parser.add_argument('base_csv', help='Path to base.csv file')
    parser.add_argument('--output', '-o', default='control_points.csv', help='Output CSV file')
    parser.add_argument('--count', '-n', type=int, default=100, help='Target number of control points')

    args = parser.parse_args()

    print(f"Parsing {args.s01_file}...")
    s01_points = parse_s01_file(args.s01_file)
    print(f"  Found {len(s01_points)} points")

    print(f"\nParsing {args.base_csv}...")
    base_points = parse_base_csv(args.base_csv)
    print(f"  Found {len(base_points)} points")

    print(f"\nMatching control points...")
    matched = match_control_points(s01_points, base_points)
    print(f"  Matched {len(matched)} control points")

    if len(matched) == 0:
        print("ERROR: No matching points found!")
        return 1

    print(f"\nSelecting {args.count} distributed points...")
    selected = select_distributed_points(matched, args.count)
    print(f"  Selected {len(selected)} control points")

    # Calculate spatial extent
    x_vals = [p['x'] for p in selected]
    y_vals = [p['y'] for p in selected]
    lat_vals = [p['lat'] for p in selected]
    lon_vals = [p['lon'] for p in selected]

    print(f"\nSpatial extent:")
    print(f"  X: {min(x_vals):.1f} to {max(x_vals):.1f} ({max(x_vals) - min(x_vals):.1f}m range)")
    print(f"  Y: {min(y_vals):.1f} to {max(y_vals):.1f} ({max(y_vals) - min(y_vals):.1f}m range)")
    print(f"  Lat: {min(lat_vals):.6f} to {max(lat_vals):.6f}")
    print(f"  Lon: {min(lon_vals):.6f} to {max(lon_vals):.6f}")

    # Write to CSV
    print(f"\nWriting to {args.output}...")
    with open(args.output, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['line', 'shotpoint', 'x', 'y', 'lat', 'lon'])
        writer.writeheader()
        writer.writerows(selected)

    print(f"✓ Saved {len(selected)} control points to {args.output}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
