"""
Flask routes for post plot acquisition map
All routes are registered under the /postplot blueprint prefix
"""

from flask import render_template, jsonify, request, session, redirect, url_for
from postplot import postplot_bp
from postplot.models import PostPlotDB
from postplot.utils import validate_source_csv, validate_acquisition_csv
import logging

logger = logging.getLogger(__name__)

# Database helper (imported from main app)
from app import get_postgres_connection, return_postgres_connection

# Initialize database handler
db = PostPlotDB(get_postgres_connection, return_postgres_connection)


@postplot_bp.route("/map")
def map_view():
    """
    Render post plot acquisition map

    URL: /postplot/map
    """
    if 'username' not in session:
        return redirect(url_for('login'))

    return render_template('postplot_map.html', username=session['username'])


@postplot_bp.route("/upload")
def upload_page():
    """
    Render upload management page with statistics

    URL: /postplot/upload
    """
    if 'username' not in session:
        return redirect(url_for('login'))

    try:
        # Get statistics for all swaths
        swath_stats = db.get_all_swath_stats()
        return render_template('upload_postplot.html',
                             swath_stats=swath_stats,
                             username=session['username'])
    except Exception as e:
        logger.error(f"Error loading upload page: {e}", exc_info=True)
        return render_template('upload_postplot.html',
                             swath_stats=[],
                             username=session['username'],
                             error="Error loading statistics")


@postplot_bp.route("/upload_source", methods=["POST"])
def upload_source():
    """
    Upload source shotpoint CSV

    Expected file format: SwathN_Source.csv
    CSV columns: Line, shotpoint, lat, lon

    URL: POST /postplot/upload_source
    """
    if 'username' not in session:
        return jsonify({"error": "Not authenticated"}), 401

    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']
    filename = file.filename

    if not filename:
        return jsonify({"error": "No file selected"}), 400

    # Validate CSV
    success, error_msg, swath_num, data = validate_source_csv(file, filename)

    if not success:
        return jsonify({"error": error_msg}), 400

    # Insert into database
    try:
        row_count = db.insert_source_points(swath_num, data, session['username'])

        return jsonify({
            "success": True,
            "message": f"Successfully uploaded {row_count} source points to Swath {swath_num}",
            "swath": swath_num,
            "count": row_count
        })

    except Exception as e:
        logger.error(f"Error uploading source data: {e}", exc_info=True)
        return jsonify({"error": f"Database error: {str(e)}"}), 500


@postplot_bp.route("/upload_acquisition", methods=["POST"])
def upload_acquisition():
    """
    Upload acquisition data CSV or Excel (row-by-row format: Line, Station)

    Supports: .csv, .xlsx files
    Required columns: Line, Station

    URL: POST /postplot/upload_acquisition
    """
    if 'username' not in session:
        return jsonify({"error": "Not authenticated"}), 401

    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']
    filename = file.filename

    if not filename:
        return jsonify({"error": "No file selected"}), 400

    # Get user-selected swath number from form data
    swath_num = request.form.get('swath')
    if not swath_num:
        return jsonify({"error": "No swath selected. Please select a swath number."}), 400

    try:
        swath_num = int(swath_num)
    except ValueError:
        return jsonify({"error": "Invalid swath number"}), 400

    # Determine file type and validate accordingly
    file_ext = filename.lower().split('.')[-1]

    if file_ext == 'xlsx':
        # Excel file
        from postplot.utils import validate_acquisition_excel
        success, error_msg, swath_num, data, extracted_date = validate_acquisition_excel(file, filename, swath_num)
    elif file_ext == 'csv':
        # CSV file
        success, error_msg, swath_num, data, extracted_date = validate_acquisition_csv(file, filename, swath_num)
    else:
        return jsonify({"error": f"Unsupported file type: .{file_ext}. Please upload .csv or .xlsx files."}), 400

    if not success:
        return jsonify({"error": error_msg}), 400

    # Update database
    try:
        updated_count, not_found_count = db.mark_as_acquired(swath_num, data)

        message = f"Marked {updated_count} shots as acquired in Swath {swath_num}"
        if not_found_count > 0:
            message += f" ({not_found_count} shotpoints not found in source data)"
        if extracted_date:
            message += f" (Date: {extracted_date})"

        return jsonify({
            "success": True,
            "message": message,
            "swath": swath_num,
            "updated": updated_count,
            "not_found": not_found_count,
            "date": extracted_date
        })

    except Exception as e:
        logger.error(f"Error uploading acquisition data: {e}", exc_info=True)
        return jsonify({"error": f"Database error: {str(e)}"}), 500


@postplot_bp.route("/upload_s01", methods=["POST"])
def upload_s01():
    """
    Upload .s01 source file and transform coordinates
    """
    # Check authentication
    if 'username' not in session:
        return jsonify({"error": "Not authenticated"}), 401

    from postplot.utils import validate_s01_file
    from postplot.enserv_transform import CoordinateTransform
    import numpy as np

    if 's01_file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['s01_file']
    transformation_name = request.form.get('transformation')

    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    if not transformation_name:
        return jsonify({"error": "No transformation method selected"}), 400

    filename = file.filename

    # Validate .s01 file
    success, error_msg, swath_num, xy_data = validate_s01_file(file, filename)

    if not success:
        return jsonify({"error": error_msg}), 400

    try:
        # Load transformation from database
        conn = get_postgres_connection()
        transform = CoordinateTransform(name=transformation_name, db_conn=conn)

        try:
            transform.load_from_database()
        except ValueError as e:
            return jsonify({"error": f"Transformation not found: {str(e)}"}), 400

        # Transform XY coordinates to Lat/Lon
        xy_array = np.array([[pt['x'], pt['y']] for pt in xy_data])
        latlon_array = transform.transform_batch(xy_array)

        # Combine with line/shotpoint data
        transformed_data = []
        for i, pt in enumerate(xy_data):
            transformed_data.append({
                'line': pt['line'],
                'shotpoint': pt['shotpoint'],
                'lat': float(latlon_array[i, 0]),
                'lon': float(latlon_array[i, 1])
            })

        # Insert to database using the db instance
        num_inserted = db.insert_source_points(swath_num, transformed_data, session['username'])

        return jsonify({
            "success": True,
            "message": f"Successfully uploaded {num_inserted} source points for Swath {swath_num}",
            "swath": swath_num,
            "points": num_inserted,
            "transformation": transformation_name,
            "rmse_meters": transform.rmse_meters
        })

    except Exception as e:
        logger.error(f"Error uploading .s01 file: {e}", exc_info=True)
        return jsonify({"error": f"Upload error: {str(e)}"}), 500


@postplot_bp.route("/transformations")
def get_transformations():
    """
    Get list of available coordinate transformations
    """
    # Check authentication
    if 'username' not in session:
        return jsonify({"error": "Not authenticated"}), 401

    from postplot.enserv_transform import get_all_transformations

    try:
        conn = get_postgres_connection()
        transformations = get_all_transformations(conn)
        return_postgres_connection(conn)

        return jsonify({"transformations": transformations})

    except Exception as e:
        logger.error(f"Error fetching transformations: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@postplot_bp.route("/geojson/source_points")
def geojson_source_points():
    """
    Return source points as GeoJSON, optionally filtered by swaths

    Query parameters:
        swaths: Comma-separated swath numbers (e.g., "1,2,3")
                Default: "1,2,3,4,5,6,7,8" (all swaths)

    URL: GET /postplot/geojson/source_points?swaths=1,2,3

    Returns:
        GeoJSON FeatureCollection with source point features
    """
    swaths_param = request.args.get('swaths', '1,2,3,4,5,6,7,8')

    # Parse swath numbers
    selected_swaths = []
    for s in swaths_param.split(','):
        s = s.strip()
        if s.isdigit():
            swath_num = int(s)
            if 1 <= swath_num <= 8:
                selected_swaths.append(swath_num)

    if not selected_swaths:
        selected_swaths = list(range(1, 9))  # Default to all swaths

    try:
        geojson = db.get_source_points_geojson(selected_swaths)

        response = jsonify(geojson)
        # Reduced cache time since acquisition data changes frequently
        response.headers['Cache-Control'] = 'public, max-age=30'  # 30 seconds cache
        return response

    except Exception as e:
        logger.error(f"Error generating GeoJSON: {e}", exc_info=True)
        return jsonify({"error": f"Failed to generate GeoJSON: {str(e)}"}), 500


@postplot_bp.route("/clear_swath", methods=["POST"])
def clear_swath():
    """
    Clear all post plot data for a swath

    Request JSON:
        {"swath": <swath_number>}

    URL: POST /postplot/clear_swath
    """
    if 'username' not in session:
        return jsonify({"error": "Not authenticated"}), 401

    data = request.get_json()
    if not data or 'swath' not in data:
        return jsonify({"error": "Swath number not provided"}), 400

    swath_num = data.get('swath')

    if not isinstance(swath_num, int) or swath_num < 1 or swath_num > 8:
        return jsonify({"error": "Invalid swath number. Must be 1-8"}), 400

    try:
        deleted_count = db.clear_swath(swath_num)

        return jsonify({
            "success": True,
            "message": f"Cleared {deleted_count} records from Swath {swath_num}",
            "count": deleted_count
        })

    except Exception as e:
        logger.error(f"Error clearing swath data: {e}", exc_info=True)
        return jsonify({"error": f"Database error: {str(e)}"}), 500


@postplot_bp.route("/stats/<int:swath_num>")
def swath_stats(swath_num):
    """
    Get statistics for a specific swath

    URL: GET /postplot/stats/<swath_num>

    Returns:
        JSON with swath statistics
    """
    if swath_num < 1 or swath_num > 8:
        return jsonify({"error": "Invalid swath number. Must be 1-8"}), 400

    try:
        stats = db.get_swath_summary(swath_num)

        if stats is None:
            return jsonify({"error": f"No data found for Swath {swath_num}"}), 404

        return jsonify(stats)

    except Exception as e:
        logger.error(f"Error getting swath stats: {e}", exc_info=True)
        return jsonify({"error": f"Failed to get statistics: {str(e)}"}), 500
