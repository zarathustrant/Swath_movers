"""
Utility functions for post plot module
CSV/Excel validation and helper functions
"""

import pandas as pd
import re
from typing import Tuple, List, Dict, Optional
from datetime import datetime


def validate_source_csv(file, filename: str) -> Tuple[bool, str, Optional[int], Optional[List[Dict]]]:
    """
    Validate source CSV file

    Expected format: SwathN_Source.csv
    Columns: Line, shotpoint, lat, lon

    Args:
        file: File object from Flask request.files
        filename: Filename string

    Returns:
        Tuple of (success, error_message, swath_num, data)
        - success: bool
        - error_message: str (empty if success)
        - swath_num: int or None
        - data: List of dicts or None
    """
    # Extract swath number from filename
    match = re.match(r'Swath(\d+)_Source\.csv', filename, re.IGNORECASE)
    if not match:
        return (False, "Invalid filename. Expected format: SwathN_Source.csv (e.g., Swath1_Source.csv)", None, None)

    swath_num = int(match.group(1))
    if swath_num < 1 or swath_num > 8:
        return (False, "Swath number must be between 1 and 8", None, None)

    try:
        # Read CSV
        df = pd.read_csv(file)

        # Validate columns
        required_cols = ['Line', 'shotpoint', 'lat', 'lon']
        missing_cols = [col for col in required_cols if col not in df.columns]

        if missing_cols:
            return (False, f"Missing required columns: {', '.join(missing_cols)}. Required: Line, shotpoint, lat, lon", None, None)

        # Check for empty dataframe
        if df.empty:
            return (False, "CSV file is empty", None, None)

        # Validate data types
        try:
            df['Line'] = df['Line'].astype(int)
            df['shotpoint'] = df['shotpoint'].astype(int)
            df['lat'] = df['lat'].astype(float)
            df['lon'] = df['lon'].astype(float)
        except ValueError as e:
            return (False, f"Invalid data types. All columns must be numeric: {str(e)}", None, None)

        # Check for NaN values
        if df[required_cols].isnull().any().any():
            nan_counts = df[required_cols].isnull().sum()
            nan_cols = [col for col in required_cols if nan_counts[col] > 0]
            return (False, f"Found missing values in columns: {', '.join(nan_cols)}", None, None)

        # Check for duplicates
        duplicates = df.duplicated(subset=['Line', 'shotpoint'])
        if duplicates.any():
            dup_count = duplicates.sum()
            return (False, f"Found {dup_count} duplicate (Line, shotpoint) pairs. Each shot must be unique.", None, None)

        # Validate coordinate ranges (basic sanity check)
        if not (-90 <= df['lat'].min() <= 90 and -90 <= df['lat'].max() <= 90):
            return (False, "Latitude values must be between -90 and 90", None, None)

        if not (-180 <= df['lon'].min() <= 180 and -180 <= df['lon'].max() <= 180):
            return (False, "Longitude values must be between -180 and 180", None, None)

        # Convert to list of dicts
        data = df[required_cols].rename(columns={
            'Line': 'line',
            'shotpoint': 'shotpoint',
            'lat': 'lat',
            'lon': 'lon'
        }).to_dict('records')

        return (True, "", swath_num, data)

    except pd.errors.EmptyDataError:
        return (False, "CSV file is empty or invalid", None, None)
    except pd.errors.ParserError as e:
        return (False, f"CSV parsing error: {str(e)}", None, None)
    except Exception as e:
        return (False, f"Unexpected error while validating CSV: {str(e)}", None, None)


def validate_acquisition_csv(file, filename: str, swath_num: Optional[int] = None) -> Tuple[bool, str, Optional[int], Optional[List[Dict]], Optional[str]]:
    """
    Validate acquisition CSV file

    Expected format: SwathN_Acquisition.csv (or any CSV if swath_num provided)
    Columns: Line, Station (where Station = shotpoint number)

    Args:
        file: File object from Flask request.files
        filename: Filename string
        swath_num: Optional user-specified swath number (1-8). If None, extract from filename.

    Returns:
        Tuple of (success, error_message, swath_num, data, date)
        - success: bool
        - error_message: str (empty if success)
        - swath_num: int or None
        - data: List of dicts or None
        - date: str or None (extracted from filename)
    """
    # Extract date from filename
    extracted_date = extract_date_from_filename(filename)

    # If swath_num not provided, extract from filename
    if swath_num is None:
        match = re.match(r'Swath(\d+)_Acquisition\.csv', filename, re.IGNORECASE)
        if not match:
            return (False, "Invalid filename. Expected format: SwathN_Acquisition.csv (e.g., Swath1_Acquisition.csv) or provide swath number", None, None, None)
        swath_num = int(match.group(1))

    # Validate swath number
    if swath_num < 1 or swath_num > 8:
        return (False, "Swath number must be between 1 and 8", None, None, None)

    try:
        # Read CSV
        df = pd.read_csv(file)

        # Validate columns
        required_cols = ['Line', 'Station']
        missing_cols = [col for col in required_cols if col not in df.columns]

        if missing_cols:
            return (False, f"Missing required columns: {', '.join(missing_cols)}. Required: Line, Station", None, None)

        # Check for empty dataframe
        if df.empty:
            return (False, "CSV file is empty", None, None)

        # Validate data types
        try:
            df['Line'] = df['Line'].astype(int)
            df['Station'] = df['Station'].astype(int)
        except ValueError as e:
            return (False, f"Invalid data types. Line and Station must be integers: {str(e)}", None, None)

        # Check for NaN values
        if df[required_cols].isnull().any().any():
            nan_counts = df[required_cols].isnull().sum()
            nan_cols = [col for col in required_cols if nan_counts[col] > 0]
            return (False, f"Found missing values in columns: {', '.join(nan_cols)}", None, None)

        # Convert to list of dicts
        data = df[required_cols].rename(columns={
            'Line': 'line',
            'Station': 'station'
        }).to_dict('records')

        return (True, "", swath_num, data, extracted_date)

    except pd.errors.EmptyDataError:
        return (False, "CSV file is empty or invalid", None, None, None)
    except pd.errors.ParserError as e:
        return (False, f"CSV parsing error: {str(e)}", None, None, None)
    except Exception as e:
        return (False, f"Unexpected error while validating CSV: {str(e)}", None, None, None)


def format_number(num: int) -> str:
    """
    Format number with thousand separators

    Args:
        num: Integer to format

    Returns:
        Formatted string (e.g., 1234 -> "1,234")
    """
    return f"{num:,}"


def format_percentage(value: float, decimals: int = 1) -> str:
    """
    Format percentage value

    Args:
        value: Percentage value (0-100)
        decimals: Number of decimal places

    Returns:
        Formatted string (e.g., 66.7 -> "66.7%")
    """
    return f"{value:.{decimals}f}%"


def validate_s01_file(file, filename: str) -> Tuple[bool, str, Optional[int], Optional[List[Dict]]]:
    """
    Validate .s01 source point file

    Expected format: SwathN-PROJECTNAME.s01 or similar .s01 file
    Format: Fixed-width fields with S (source), Line, Shotpoint, FID, X, Y, Depth

    Args:
        file: File object from Flask request.files
        filename: Filename string

    Returns:
        Tuple of (success, error_message, swath_num, data)
        - success: bool
        - error_message: str (empty if success)
        - swath_num: int or None (extracted from filename)
        - data: List of dicts with keys: line, shotpoint, x, y
    """
    # Try to extract swath number from filename (e.g., swath04-BININ.s01 -> 4)
    match = re.search(r'swath(\d+)', filename, re.IGNORECASE)
    if match:
        swath_num = int(match.group(1))
        if swath_num < 1 or swath_num > 8:
            return (False, f"Swath number {swath_num} out of range (must be 1-8)", None, None)
    else:
        return (False, "Could not extract swath number from filename. Expected format: swathN-*.s01 (e.g., swath04-BININ.s01)", None, None)

    try:
        # Read file content
        file.seek(0)
        content = file.read()

        # Try to decode as text
        try:
            text = content.decode('utf-8')
        except UnicodeDecodeError:
            text = content.decode('latin-1')  # Fallback encoding

        lines = text.splitlines()

        if len(lines) == 0:
            return (False, "File is empty", None, None)

        # Parse .s01 format
        data = []
        parse_errors = 0

        for line_text in lines:
            # Skip empty lines
            if not line_text.strip():
                continue

            # Split by whitespace
            fields = line_text.split()

            if len(fields) < 7:  # Need at least: type, line, sp, fid, x, y, depth
                continue

            try:
                point_type = fields[0]

                # Only process source points
                if point_type != 'S':
                    continue

                line_num = int(fields[1])
                shotpoint = int(fields[2])

                # Extract X, Y coordinates
                # Get all numeric fields after the type/line/shotpoint
                numeric_fields = []
                for field in fields[1:]:
                    try:
                        numeric_fields.append(float(field))
                    except ValueError:
                        pass

                if len(numeric_fields) >= 4:  # line, shotpoint, X, Y minimum
                    x = numeric_fields[-3]  # Third from end (X, Y, Depth)
                    y = numeric_fields[-2]  # Second from end

                    data.append({
                        'line': line_num,
                        'shotpoint': shotpoint,
                        'x': x,
                        'y': y
                    })

            except (ValueError, IndexError):
                parse_errors += 1
                if parse_errors > 100:  # Too many errors, probably wrong format
                    return (False, f"Too many parse errors ({parse_errors}). File may not be valid .s01 format", None, None)
                continue

        if len(data) == 0:
            return (False, "No valid source points found in file", None, None)

        # Validate data ranges
        lines_set = set(d['line'] for d in data)
        shotpoints_set = set(d['shotpoint'] for d in data)

        if len(lines_set) == 0:
            return (False, "No valid line numbers found", None, None)

        # Check for reasonable coordinate ranges (X, Y should be in UTM range)
        x_vals = [d['x'] for d in data]
        y_vals = [d['y'] for d in data]

        min_x, max_x = min(x_vals), max(x_vals)
        min_y, max_y = min(y_vals), max(y_vals)

        # Basic sanity check for UTM coordinates
        if not (100000 <= min_x <= 1000000) or not (100000 <= min_y <= 10000000):
            return (False, f"Coordinates appear invalid. X range: {min_x:.0f}-{max_x:.0f}, Y range: {min_y:.0f}-{max_y:.0f}. Expected UTM coordinates.", None, None)

        return (True, "", swath_num, data)

    except Exception as e:
        return (False, f"Error parsing file: {str(e)}", None, None)


def extract_date_from_filename(filename: str) -> Optional[str]:
    """
    Extract date from filename if present

    Supports formats:
    - DDMMYYYY (e.g., "Acquired Shots 25102025.xlsx" -> "25/10/2025")
    - DD-MM-YYYY, DD_MM_YYYY, DDMMYY, etc.

    Args:
        filename: Filename string

    Returns:
        Formatted date string (DD/MM/YYYY) or None if not found
    """
    # Try various date patterns
    patterns = [
        r'(\d{2})(\d{2})(\d{4})',  # DDMMYYYY
        r'(\d{2})[_-](\d{2})[_-](\d{4})',  # DD-MM-YYYY or DD_MM_YYYY
        r'(\d{2})(\d{2})(\d{2})',  # DDMMYY
    ]

    for pattern in patterns:
        match = re.search(pattern, filename)
        if match:
            day, month, year = match.groups()

            # Handle 2-digit year
            if len(year) == 2:
                year = f"20{year}"

            # Validate date
            try:
                date_obj = datetime.strptime(f"{day}/{month}/{year}", "%d/%m/%Y")
                return date_obj.strftime("%d/%m/%Y")
            except ValueError:
                # Invalid date, continue to next pattern
                continue

    return None


def validate_acquisition_excel(file, filename: str, swath_num: int) -> Tuple[bool, str, Optional[int], Optional[List[Dict]], Optional[str]]:
    """
    Validate acquisition Excel file (.xlsx)

    Expected columns: Line, Station (case-insensitive)
    Format: One shotpoint per row

    Args:
        file: File object from Flask request.files
        filename: Filename string
        swath_num: User-selected swath number (1-8)

    Returns:
        Tuple of (success, error_message, swath_num, data, date)
        - success: bool
        - error_message: str (empty if success)
        - swath_num: int or None
        - data: List of dicts with keys: line, station
        - date: str or None (extracted from filename)
    """
    # Validate swath number
    if swath_num < 1 or swath_num > 8:
        return (False, "Swath number must be between 1 and 8", None, None, None)

    # Extract date from filename
    extracted_date = extract_date_from_filename(filename)

    try:
        # Read Excel file
        file.seek(0)
        df = pd.read_excel(file, sheet_name=0)

        # Check for empty dataframe
        if df.empty:
            return (False, "Excel file is empty", None, None, None)

        # Find Line and Station columns (case-insensitive)
        col_mapping = {}
        for col in df.columns:
            col_lower = str(col).lower().strip()
            if col_lower == 'line':
                col_mapping['Line'] = col
            elif col_lower == 'station':
                col_mapping['Station'] = col

        # Check required columns
        if 'Line' not in col_mapping or 'Station' not in col_mapping:
            available_cols = ', '.join(str(c) for c in df.columns[:10])
            return (False, f"Missing required columns. Need: Line, Station. Found: {available_cols}", None, None, None)

        # Extract required columns
        df_subset = df[[col_mapping['Line'], col_mapping['Station']]].copy()
        df_subset.columns = ['Line', 'Station']

        # Remove rows with NaN values
        df_clean = df_subset.dropna()

        if df_clean.empty:
            return (False, "No valid data rows found (all rows have missing Line or Station)", None, None, None)

        # Validate data types
        try:
            df_clean['Line'] = df_clean['Line'].astype(int)
            df_clean['Station'] = df_clean['Station'].astype(int)
        except ValueError as e:
            return (False, f"Invalid data types. Line and Station must be integers: {str(e)}", None, None, None)

        # Convert to list of dicts
        data = df_clean.rename(columns={
            'Line': 'line',
            'Station': 'station'
        }).to_dict('records')

        if len(data) == 0:
            return (False, "No valid acquisition data found after cleaning", None, None, None)

        return (True, "", swath_num, data, extracted_date)

    except pd.errors.EmptyDataError:
        return (False, "Excel file is empty or invalid", None, None, None)
    except Exception as e:
        return (False, f"Error reading Excel file: {str(e)}", None, None, None)
