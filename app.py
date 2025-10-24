from flask import Flask, request, render_template, jsonify, redirect, url_for, send_from_directory, session, send_file
from flask_compress import Compress
import pandas as pd
import psycopg2
import psycopg2.extras
import os
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import secrets
from shapely.geometry import LineString
import json
from math import radians, degrees, atan2, cos, sin
from shapely.geometry import Polygon
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()






app = Flask(__name__)
# Change from relative to absolute path
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
SWATH_FOLDER = os.path.join(PROJECT_DIR, "swaths")
BASE_COORDS_CSV = os.path.join(PROJECT_DIR, "base.csv")
# DB_FILE = os.path.join(PROJECT_DIR, "swath_movers.db")  # Legacy SQLite file (no longer used)

# Database configuration - PostgreSQL
DB_CONFIG = {
    'dbname': os.getenv('DB_NAME', 'swath_movers'),
    'user': os.getenv('DB_USER', 'aerys'),
    'password': os.getenv('DB_PASSWORD', ''),
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432')
}

# Connection pooling for better performance
from psycopg2.pool import ThreadedConnectionPool

# Initialize connection pool
connection_pool = ThreadedConnectionPool(
    minconn=2,
    maxconn=20,
    dbname=DB_CONFIG['dbname'],
    user=DB_CONFIG['user'],
    password=DB_CONFIG['password'],
    host=DB_CONFIG['host'],
    port=DB_CONFIG['port']
)

def get_postgres_connection():
    """Get PostgreSQL connection from pool"""
    return connection_pool.getconn()

def return_postgres_connection(conn):
    """Return PostgreSQL connection to pool"""
    connection_pool.putconn(conn)
app.secret_key = os.getenv('FLASK_SECRET_KEY', "f6e3a4b5e1c2d89a345e2a3c9bd0a5f4")
os.makedirs(SWATH_FOLDER, exist_ok=True)

# Enable compression
Compress(app)

DEPLOYMENT_TYPES = [
    "NODES DEPLOYED", "SM10 GEOPHONES DEPLOYED", "MARSH GEOPHONES DEPLOYED", "HYDROPHONES DEPLOYED",
    "FORBIDDEN BUSH", "OFFSETS", "NODES RETRIEVED", "SM10 GEOPHONES RETRIEVED", "MARSH GEOPHONES RETRIEVED", "HYDROPHONES RETRIEVED"
]

DEPLOYMENT_COLORS = {
    "NODES DEPLOYED": "#f6ee02", "SM10 GEOPHONES DEPLOYED": "#f18807", "MARSH GEOPHONES DEPLOYED": "#057af0",
    "HYDROPHONES DEPLOYED": "#95cef0", "FORBIDDEN BUSH": "#f50303", "OFFSETS": "#f309df",
    "NODES RETRIEVED": "#06e418", "SM10 GEOPHONES RETRIEVED": "#8255219c", "MARSH GEOPHONES RETRIEVED": "#f4d1a4",
    "HYDROPHONES RETRIEVED": "#345d09"
}

# === DATABASE CONNECTION HELPERS ===
def get_postgres_connection():
    """Get PostgreSQL connection from pool"""
    try:
        return connection_pool.getconn()
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        raise

def return_postgres_connection(conn):
    """Return PostgreSQL connection to pool"""
    try:
        connection_pool.putconn(conn)
    except Exception as e:
        print(f"❌ Error returning connection to pool: {e}")

def get_coordinate_lookup():
    """Get coordinate lookup with error handling"""
    coords = {}
    conn = None
    try:
        conn = get_postgres_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT line, shotpoint, latitude, longitude FROM coordinates")
            result = cursor.fetchall()
            for line, shot, lat, lon in result:
                coords[(line, shot)] = (lat, lon)
    except Exception as e:
        print(f"❌ Error loading coordinates: {e}")
        coords = {}
    finally:
        if conn:
            return_postgres_connection(conn)
    return coords

# === BASIC APP FUNCTIONALITY ===
def init_swath_table(swath):
    """Initialize swath table in PostgreSQL"""
    conn = None
    try:
        conn = get_postgres_connection()
        with conn.cursor() as cursor:
            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS swath_{swath} (
                    line INTEGER NOT NULL,
                    shotpoint INTEGER NOT NULL,
                    deployment_type TEXT NOT NULL,
                    username TEXT,
                    timestamp TIMESTAMP NOT NULL,
                    PRIMARY KEY (line, shotpoint)
                )
            ''')
            # Create indexes for better performance
            cursor.execute(f'CREATE INDEX IF NOT EXISTS idx_swath_{swath}_type ON swath_{swath} (deployment_type)')
            cursor.execute(f'CREATE INDEX IF NOT EXISTS idx_swath_{swath}_user ON swath_{swath} (username)')
            cursor.execute(f'CREATE INDEX IF NOT EXISTS idx_swath_{swath}_timestamp ON swath_{swath} (timestamp)')
        conn.commit()
        print(f"✅ Swath table {swath} initialized successfully")
    except Exception as e:
        print(f"❌ Error initializing swath table {swath}: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            return_postgres_connection(conn)

def init_global_deployments_table():
    """Initialize global deployments table in PostgreSQL"""
    conn = None
    try:
        conn = get_postgres_connection()
        with conn.cursor() as cursor:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS global_deployments (
                    line INTEGER NOT NULL,
                    shotpoint INTEGER NOT NULL,
                    deployment_type TEXT NOT NULL,
                    username TEXT,
                    timestamp TIMESTAMP NOT NULL,
                    PRIMARY KEY (line, shotpoint)
                )
            ''')
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_global_deployments_type ON global_deployments (deployment_type)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_global_deployments_user ON global_deployments (username)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_global_deployments_timestamp ON global_deployments (timestamp)')
        conn.commit()
        print("✅ Global deployments table initialized successfully")
    except Exception as e:
        print(f"❌ Error initializing global deployments table: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            return_postgres_connection(conn)

def migrate_csv_to_postgres():
    """Migrate coordinates from CSV to PostgreSQL"""
    if not os.path.exists(BASE_COORDS_CSV):
        print("❌ base_coordinates.csv not found.")
        return False

    df = pd.read_csv(BASE_COORDS_CSV)
    required_cols = {"Line", "Shotpoint", "Latitude", "Longitude", "Type", "_id"}
    if not required_cols.issubset(set(df.columns)):
        print("❌ CSV is missing required columns.")
        return False

    conn = None
    try:
        conn = get_postgres_connection()
        with conn.cursor() as cursor:
            # Create coordinates table if it doesn't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS coordinates (
                    line INTEGER NOT NULL,
                    shotpoint INTEGER NOT NULL,
                    latitude DECIMAL(10, 8) NOT NULL,
                    longitude DECIMAL(11, 8) NOT NULL,
                    type TEXT,
                    _id TEXT PRIMARY KEY
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_coordinates_line_shot ON coordinates (line, shotpoint)')

            # Insert data
            for _, row in df.iterrows():
                try:
                    cursor.execute('''
                        INSERT INTO coordinates (line, shotpoint, latitude, longitude, type, _id)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (_id) DO UPDATE SET
                            line = EXCLUDED.line,
                            shotpoint = EXCLUDED.shotpoint,
                            latitude = EXCLUDED.latitude,
                            longitude = EXCLUDED.longitude,
                            type = EXCLUDED.type
                    ''', (
                        int(row['Line']),
                        int(row['Shotpoint']),
                        float(row['Latitude']),
                        float(row['Longitude']),
                        row['Type'],
                        row['_id']
                    ))
                except Exception as e:
                    print(f"⚠️ Skipping row due to error: {e}")
        conn.commit()
        print("✅ Coordinates loaded into PostgreSQL.")
        return True
    except Exception as e:
        print(f"❌ Error migrating coordinates: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            return_postgres_connection(conn)

def load_users_from_csv(csv_file="users.csv"):
    """Load users from CSV to PostgreSQL"""
    if not os.path.exists(csv_file):
        print(f"❌ {csv_file} not found.")
        return False

    df = pd.read_csv(csv_file)
    conn = None
    try:
        conn = get_postgres_connection()
        with conn.cursor() as cursor:
            # Create users table if it doesn't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            for _, row in df.iterrows():
                username = row["username"].strip()
                password = row["password"].strip()
                hashed = generate_password_hash(password)
                try:
                    cursor.execute("""
                        INSERT INTO users (username, password_hash)
                        VALUES (%s, %s)
                        ON CONFLICT (username) DO UPDATE SET
                            password_hash = EXCLUDED.password_hash,
                            updated_at = CURRENT_TIMESTAMP
                    """, (username, hashed))
                    print(f"✅ Added/updated user: {username}")
                except Exception as e:
                    print(f"⚠️ Skipped user {username}: {e}")
        conn.commit()
        print("✅ Users loaded into PostgreSQL.")
        return True
    except Exception as e:
        print(f"❌ Error loading users: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            return_postgres_connection(conn)

def run_migrations_once():
    """Run migrations once with proper error handling"""
    LOCK_FILE = "migration.lock"
    if os.path.exists(LOCK_FILE):
        print("✅ Migrations already run. Skipping.")
        return

    print("🚀 Starting PostgreSQL migrations...")
    success = True

    # Migrate coordinates
    if not migrate_csv_to_postgres():
        success = False

    # Load users
    if not load_users_from_csv():
        success = False

    # Initialize tables
    try:
        init_global_deployments_table()
        # Initialize swath tables 1-8
        for swath in range(1, 9):
            init_swath_table(str(swath))
    except Exception as e:
        print(f"❌ Error initializing tables: {e}")
        success = False

    if success:
        with open(LOCK_FILE, "w") as f:
            f.write(datetime.now().isoformat())
        print("✅ All migrations completed successfully.")
    else:
        print("❌ Some migrations failed.")
        raise Exception("Migration failed")

def load_deployments(swath):
    """Load deployments for a specific swath with error handling"""
    try:
        init_swath_table(swath)
        conn = get_postgres_connection()
        with conn.cursor() as cursor:
            cursor.execute(f"SELECT line, shotpoint, deployment_type FROM swath_{swath}")
            result = cursor.fetchall()
        return_postgres_connection(conn)
        return {(row[0], row[1]): row[2] for row in result}
    except Exception as e:
        print(f"❌ Error loading deployments for swath {swath}: {e}")
        return {}

@app.route("/")
def index():
    swaths = sorted(
        [f.split(".")[0] for f in os.listdir(SWATH_FOLDER) if f.endswith(".csv")]
    )
    last_swath = session.get("last_swath")
    if last_swath in swaths:
        return redirect(url_for('show_table', swath=last_swath))
    return redirect(url_for('show_table', swath=swaths[0] if swaths else '1'))

def load_global_deployments():
    conn = None
    try:
        conn = get_postgres_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT line, shotpoint, deployment_type FROM global_deployments")
            result = cursor.fetchall()
        return {(row[0], row[1]): row[2] for row in result}
    except Exception as e:
        print(f"❌ Error loading global deployments: {e}")
        return {}
    finally:
        if conn:
            return_postgres_connection(conn)

@app.route("/api/swath/<swath>")
def api_swath_data(swath):
    """API endpoint that returns JSON data for a swath"""

    csv_path = os.path.join(SWATH_FOLDER, f"{swath}.csv")
    if not os.path.exists(csv_path):
        return jsonify({"error": f"Swath file {swath}.csv not found."})

    swath_files = sorted(
        [f.split(".")[0] for f in os.listdir(SWATH_FOLDER) if f.endswith(".csv")]
    )

    df = pd.read_csv(csv_path, header=None, names=['Line', 'FirstShot', 'LastShot'])
    line_data = {}
    for _, row in df.iterrows():
        line = int(row['Line'])
        line_data[line] = list(range(int(row['FirstShot']), int(row['LastShot']) + 1))

    all_shotpoints = sorted(set(sp for points in line_data.values() for sp in points))
    line_numbers = sorted(line_data.keys())

    # 🔧 Load from GLOBAL deployments, not per-swath, for visual consistency
    deployments = load_global_deployments()

    table_data = []
    for shot in all_shotpoints:
        row = {}
        for line in line_numbers:
            if shot in line_data[line]:
                key = (line, shot)
                deploy = deployments.get(key, '')
                row[line] = {
                    'value': str(shot),
                    'deploy': deploy,
                    'color': DEPLOYMENT_COLORS.get(deploy, '#ffffff')
                }
            else:
                row[line] = {'value': '', 'deploy': '', 'color': '#ffffff'}
        table_data.append({'shot': shot, 'row': row})
    table_data.sort(key=lambda x: x['shot'], reverse=True)

    stats = {dtype: {line: 0 for line in line_numbers} for dtype in DEPLOYMENT_TYPES}
    for (line, shot), dtype in deployments.items():
        if dtype in stats and line in stats[dtype]:
            stats[dtype][line] += 1

    max_count = {
        dtype: max(counts.values()) if counts else 1
        for dtype, counts in stats.items()
    }

    return jsonify({
        'swath': swath,
        'swath_list': swath_files,
        'stats': stats,
        'table_data': table_data,
        'max_count': max_count,
        'line_numbers': line_numbers,
        'deployment_types': DEPLOYMENT_TYPES,
        'colors': DEPLOYMENT_COLORS,
        'can_edit': session.get('can_edit', False)
    })

@app.route("/swath/<swath>")
def show_table(swath):

    # 🔑 Store this swath in session
    session["last_swath"] = swath

    csv_path = os.path.join(SWATH_FOLDER, f"{swath}.csv")
    if not os.path.exists(csv_path):
        return f"Swath file {swath}.csv not found."

    swath_files = sorted(
        [f.split(".")[0] for f in os.listdir(SWATH_FOLDER) if f.endswith(".csv")]
    )

    df = pd.read_csv(csv_path, header=None, names=['Line', 'FirstShot', 'LastShot'])
    line_data = {}
    for _, row in df.iterrows():
        line = int(row['Line'])
        line_data[line] = list(range(int(row['FirstShot']), int(row['LastShot']) + 1))

    all_shotpoints = sorted(set(sp for points in line_data.values() for sp in points))
    line_numbers = sorted(line_data.keys())

    # 🔧 Load from GLOBAL deployments, not per-swath, for visual consistency
    deployments = load_global_deployments()

    table_data = []
    for shot in all_shotpoints:
        row = {}
        for line in line_numbers:
            if shot in line_data[line]:
                key = (line, shot)
                deploy = deployments.get(key, '')
                row[line] = {
                    'value': str(shot),
                    'deploy': deploy,
                    'color': DEPLOYMENT_COLORS.get(deploy, '#ffffff')
                }
            else:
                row[line] = {'value': '', 'deploy': '', 'color': '#ffffff'}
        table_data.append({'shot': shot, 'row': row})
    table_data.sort(key=lambda x: x['shot'], reverse=True)

    swath_files = sorted(
    [f.split(".")[0] for f in os.listdir(SWATH_FOLDER) if f.endswith(".csv")],
)

    stats = {dtype: {line: 0 for line in line_numbers} for dtype in DEPLOYMENT_TYPES}
    for (line, shot), dtype in deployments.items():
        if dtype in stats and line in stats[dtype]:
            stats[dtype][line] += 1

    max_count = {
        dtype: max(counts.values()) if counts else 1
        for dtype, counts in stats.items()
    }

    return render_template('table.html',
        swath=swath,
        swath_list=swath_files,
        stats=stats,
        table_data=table_data,
        max_count=max_count,
        line_numbers=line_numbers,
        deployment_types=DEPLOYMENT_TYPES,
        colors=DEPLOYMENT_COLORS
    )

@app.route("/map")
def map_page():
    # Default map view
    map_view = {"lat": 5.5, "lng": 7.0, "zoom": 16}
    view_file = os.path.join(SWATH_FOLDER, "map_view.json")
    if os.path.exists(view_file):
        with open(view_file) as f:
            map_view = json.load(f)

    return render_template("map.html", colors=DEPLOYMENT_COLORS, map_view=map_view)


@app.route("/save_map_view", methods=["POST"])
def save_map_view():
    data = request.get_json()
    view_file = os.path.join(SWATH_FOLDER, "map_view.json")

    with open(view_file, "w") as f:
        json.dump(data, f)

    return jsonify({"status": "saved"})


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, 'static'),
        'favicon.png',  
        mimetype='image/png'
    )


@app.route("/save/<swath>", methods=["POST"])
def save_deployment(swath):
    if not session.get("can_edit"):
        return jsonify({"status": "ignored", "message": "Viewer mode only"})

    data = request.json
    line = int(data['line'])
    shot = int(data['shotpoint'])
    deploy = data['deployment'].strip()
    username = session.get("username", "unknown")
    timestamp = datetime.now().isoformat()

    conn = None
    try:
        conn = get_postgres_connection()
        with conn.cursor() as cursor:
            if deploy == "":
                # 🔴 If user clears the selection, delete it from DB
                cursor.execute(f'DELETE FROM swath_{swath} WHERE line = %s AND shotpoint = %s', (line, shot))
                cursor.execute('DELETE FROM global_deployments WHERE line = %s AND shotpoint = %s', (line, shot))
                status = "deleted"
            else:
                # 🟢 Save normally
                cursor.execute(f'''
                    INSERT INTO swath_{swath} (line, shotpoint, deployment_type, username, timestamp)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (line, shotpoint) DO UPDATE SET
                        deployment_type = EXCLUDED.deployment_type,
                        username = EXCLUDED.username,
                        timestamp = EXCLUDED.timestamp
                ''', (line, shot, deploy, username, timestamp))

                cursor.execute('''
                    INSERT INTO global_deployments (line, shotpoint, deployment_type, username, timestamp)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (line, shotpoint) DO UPDATE SET
                        deployment_type = EXCLUDED.deployment_type,
                        username = EXCLUDED.username,
                        timestamp = EXCLUDED.timestamp
                ''', (line, shot, deploy, username, timestamp))

                status = "saved"
        conn.commit()
        return jsonify({"status": status, "user": username, "timestamp": timestamp})
    except Exception as e:
        print(f"❌ Error saving deployment: {e}")
        if conn:
            conn.rollback()
        return jsonify({"status": "error", "message": "Database error"})
    finally:
        if conn:
            return_postgres_connection(conn)

@app.route("/geojson")
def get_all_shotpoints():
    coords_lookup = get_coordinate_lookup()
    features = []
    seen_points = set()  # Avoid duplicates

    conn = None
    try:
        conn = get_postgres_connection()
        with conn.cursor() as cursor:
            # Get all deployment data from global_deployments only (avoid duplicates from swath tables)
            cursor.execute("SELECT line, shotpoint, deployment_type FROM global_deployments")
            global_deployments = cursor.fetchall()

            # Add global deployments
            for line, shot, deploy in global_deployments:
                key = (line, shot)
                if key in coords_lookup and key not in seen_points:
                    lat, lon = coords_lookup[key]
                    seen_points.add(key)
                    # Simplified structure - removed redundant swath property
                    features.append({
                        "type": "Feature",
                        "geometry": {"type": "Point", "coordinates": [lon, lat]},
                        "properties": {
                            "l": line,  # Shortened property names to reduce payload
                            "s": shot,
                            "t": deploy
                        }
                    })

        response = jsonify({"type": "FeatureCollection", "features": features})
        response.headers['Cache-Control'] = 'public, max-age=300'  # Cache for 5 minutes
        return response
    except Exception as e:
        print(f"❌ Error loading shotpoints: {e}")
        return jsonify({"type": "FeatureCollection", "features": []})
    finally:
        if conn:
            return_postgres_connection(conn)

@app.route("/geojson_lines")
def geojson_lines():
    grouped_by_swath = {}
    labeled_lines = set()  # Track which line numbers have already been labeled

    # Get coordinates from PostgreSQL
    coords_lookup = get_coordinate_lookup()
    coord_lookup = coords_lookup  # Alias for compatibility

    # Use PostgreSQL for cache operations
    conn = None
    try:
        conn = get_postgres_connection()
        with conn.cursor() as cursor:
            # Ensure cache tables exist in PostgreSQL
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS swath_lines (
                    swath TEXT,
                    line INTEGER,
                    first_shot INTEGER,
                    last_shot INTEGER,
                    lon1 DECIMAL(11, 8),
                    lat1 DECIMAL(10, 8),
                    lon2 DECIMAL(11, 8),
                    lat2 DECIMAL(10, 8),
                    type TEXT,
                    PRIMARY KEY (swath, line)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS swath_boxes (
                    swath TEXT PRIMARY KEY,
                    coordinates TEXT
                )
            """)
    except Exception as e:
        print(f"❌ Error initializing cache tables: {e}")
    finally:
        if conn:
            return_postgres_connection(conn)

    for filename in os.listdir(SWATH_FOLDER):
        if not filename.endswith(".csv"):
            continue

        swath_name = filename.replace(".csv", "")
        features = []

        # Load existing cached lines if available from PostgreSQL
        conn = None
        try:
            conn = get_postgres_connection()
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT line, first_shot, last_shot, lon1, lat1, lon2, lat2, type FROM swath_lines WHERE swath = %s",
                    (swath_name,)
                )
                existing_lines = cursor.fetchall()
        except Exception as e:
            print(f"❌ Error loading cached lines for swath {swath_name}: {e}")
            existing_lines = []
        finally:
            if conn:
                return_postgres_connection(conn)

        if existing_lines:
            print(f"📦 Loaded cached lines for swath: {swath_name}")
            for line, first, last, lon1, lat1, lon2, lat2, typ in existing_lines:
                # Generate extended points for existing cached lines
                extended_points = []
                dx = float(lon2) - float(lon1)
                dy = float(lat2) - float(lat1)
                norm = (dx ** 2 + dy ** 2) ** 0.5
                length_factor = 0.00005
                for i in range(1, 11):
                    offset_lon = float(lon2) + (dx / norm) * length_factor * i if norm else float(lon2)
                    offset_lat = float(lat2) + (dy / norm) * length_factor * i if norm else float(lat2)
                    extended_points.append([offset_lon, offset_lat])

                # Check if this line number has already been labeled
                show_label = line not in labeled_lines
                if show_label:
                    labeled_lines.add(line)
                    display_label = f"{line}"
                else:
                    display_label = ""  # No label for duplicate line numbers

                features.append({
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[float(lon1), float(lat1)], [float(lon2), float(lat2)]]
                    },
                    "properties": {
                        "line": line,
                        "line_id": f"{swath_name}_L{line}",  # Unique identifier for backend
                        "display_label": display_label,  # Only show label once per line number
                        "first_shot": first,
                        "last_shot": last,
                        "swath": swath_name,
                        "type": typ,
                        "extended_points": extended_points
                    }
                })
        else:
            swath_path = os.path.join(SWATH_FOLDER, filename)
            df = pd.read_csv(swath_path, header=None, names=["Line", "FirstShot", "LastShot"])
            line_rows = []

            for _, row in df.iterrows():
                line = int(row["Line"])
                first = int(row["FirstShot"])
                last = int(row["LastShot"])
                key1 = (line, first)
                key2 = (line, last)

                if key1 in coord_lookup and key2 in coord_lookup:
                    lat1, lon1, type1 = coord_lookup[key1]
                    lat2, lon2, type2 = coord_lookup[key2]
                    typ = type1 if type1 == type2 else f"{type1}/{type2}"

                    dx = lon2 - lon1
                    dy = lat2 - lat1
                    norm = (dx ** 2 + dy ** 2) ** 0.5
                    length_factor = 0.00005
                    extended_points = []
                    for i in range(1, 11):
                        offset_lon = lon2 + (dx / norm) * length_factor * i if norm else lon2
                        offset_lat = lat2 + (dy / norm) * length_factor * i if norm else lat2
                        extended_points.append([offset_lon, offset_lat])

                    # Check if this line number has already been labeled
                    show_label = line not in labeled_lines
                    if show_label:
                        labeled_lines.add(line)
                        display_label = f"{line}"
                    else:
                        display_label = ""  # No label for duplicate line numbers

                    features.append({
                        "type": "Feature",
                        "geometry": {
                            "type": "LineString",
                            "coordinates": [[lon1, lat1], [lon2, lat2]]
                        },
                        "properties": {
                            "line": line,
                            "line_id": f"{swath_name}_L{line}",  # Unique identifier for backend
                            "display_label": display_label,  # Only show label once per line number
                            "first_shot": first,
                            "last_shot": last,
                            "swath": swath_name,
                            "type": typ,
                            "extended_points": extended_points
                        }
                    })

                    line_rows.append((swath_name, line, first, last, lon1, lat1, lon2, lat2, typ))

            if line_rows:
                # Save to PostgreSQL cache
                conn = None
                try:
                    conn = get_postgres_connection()
                    with conn.cursor() as cursor:
                        cursor.executemany("""
                            INSERT INTO swath_lines
                            (swath, line, first_shot, last_shot, lon1, lat1, lon2, lat2, type)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (swath, line) DO UPDATE SET
                                first_shot = EXCLUDED.first_shot,
                                last_shot = EXCLUDED.last_shot,
                                lon1 = EXCLUDED.lon1,
                                lat1 = EXCLUDED.lat1,
                                lon2 = EXCLUDED.lon2,
                                lat2 = EXCLUDED.lat2,
                                type = EXCLUDED.type
                        """, line_rows)
                        print(f"💾 Saved {len(line_rows)} lines to DB for swath: {swath_name}")
                    conn.commit()
                except Exception as e:
                    print(f"❌ Error saving cache for swath {swath_name}: {e}")
                    if conn:
                        conn.rollback()
                finally:
                    if conn:
                        return_postgres_connection(conn)

        # === Divider Line Calculation ===
        # Find the last line (highest line number) in the swath
        line_features = [f for f in features if f["geometry"]["type"] == "LineString"]

        if line_features:
            # Get the line with the highest line number
            last_line_feature = max(line_features, key=lambda f: f["properties"]["line"])
            last_line_coords = last_line_feature["geometry"]["coordinates"]

            # Calculate the average angle of all lines for consistent orientation
            angles = []
            for f in line_features:
                coords = f["geometry"]["coordinates"]
                if len(coords) >= 2:
                    x1, y1 = coords[0]
                    x2, y2 = coords[-1]
                    dx, dy = x2 - x1, y2 - y1
                    if dx or dy:
                        angle = degrees(atan2(dy, dx))
                        angles.append(angle)

            if angles:
                avg_angle = sum(angles) / len(angles)
                theta = radians(avg_angle)

                # Calculate perpendicular angle for the divider
                perp_theta = theta + radians(90)

                # Use the last line's midpoint as reference
                last_x1, last_y1 = last_line_coords[0]
                last_x2, last_y2 = last_line_coords[1]
                midpoint_x = (last_x1 + last_x2) / 2
                midpoint_y = (last_y1 + last_y2) / 2

                # Calculate line spacing (distance between parallel lines)
                if len(line_features) >= 2:
                    # Sort lines by line number to get consistent spacing
                    sorted_lines = sorted(line_features, key=lambda f: f["properties"]["line"])

                    # Calculate average spacing between consecutive lines
                    spacings = []
                    for i in range(len(sorted_lines) - 1):
                        line1_coords = sorted_lines[i]["geometry"]["coordinates"]
                        line2_coords = sorted_lines[i + 1]["geometry"]["coordinates"]

                        # Get midpoints of both lines
                        mid1_x = (line1_coords[0][0] + line1_coords[1][0]) / 2
                        mid1_y = (line1_coords[0][1] + line1_coords[1][1]) / 2
                        mid2_x = (line2_coords[0][0] + line2_coords[1][0]) / 2
                        mid2_y = (line2_coords[0][1] + line2_coords[1][1]) / 2

                        # Calculate distance between midpoints
                        spacing = ((mid2_x - mid1_x) ** 2 + (mid2_y - mid1_y) ** 2) ** 0.5
                        spacings.append(spacing)

                    avg_spacing = sum(spacings) / len(spacings) if spacings else 0.001
                else:
                    avg_spacing = 0.001  # Default small spacing

                # Position divider one spacing unit beyond the last line
                divider_center_x = midpoint_x + cos(perp_theta) * avg_spacing
                divider_center_y = midpoint_y + sin(perp_theta) * avg_spacing

                # Make divider same length as the survey lines
                line_length = ((last_x2 - last_x1) ** 2 + (last_y2 - last_y1) ** 2) ** 0.5
                half_length = line_length / 2

                # Calculate divider endpoints (parallel to survey lines)
                dx = cos(theta) * half_length
                dy = sin(theta) * half_length

                x0 = divider_center_x - dx
                y0 = divider_center_y - dy
                x1 = divider_center_x + dx
                y1 = divider_center_y + dy

                divider_coords = [[x0, y0], [x1, y1]]



        # === Swath Bounding Box ===
        # Create a rotated bounding box following the direction of the lines
        if line_features:
            # Calculate the average angle of all lines for consistent orientation
            angles = []
            all_coords = []
            for f in line_features:
                coords = f["geometry"]["coordinates"]
                all_coords.extend(coords)
                if len(coords) >= 2:
                    x1, y1 = coords[0]
                    x2, y2 = coords[-1]
                    dx, dy = x2 - x1, y2 - y1
                    if dx or dy:
                        angle = degrees(atan2(dy, dx))
                        angles.append(angle)

            if all_coords and angles:
                # Calculate average angle and convert to radians
                avg_angle = sum(angles) / len(angles)
                theta = radians(avg_angle)

                # Find the center point of all coordinates
                lons = [coord[0] for coord in all_coords]
                lats = [coord[1] for coord in all_coords]
                center_lon = (min(lons) + max(lons)) / 2
                center_lat = (min(lats) + max(lats)) / 2

                # Transform coordinates to a rotated coordinate system
                rotated_coords = []
                for lon, lat in all_coords:
                    # Translate to origin
                    dx = lon - center_lon
                    dy = lat - center_lat
                    # Rotate by -theta to align with axes
                    rot_x = dx * cos(-theta) - dy * sin(-theta)
                    rot_y = dx * sin(-theta) + dy * cos(-theta)
                    rotated_coords.append((rot_x, rot_y))

                # Find bounding box in rotated space
                rot_xs = [coord[0] for coord in rotated_coords]
                rot_ys = [coord[1] for coord in rotated_coords]
                min_rot_x, max_rot_x = min(rot_xs), max(rot_xs)
                min_rot_y, max_rot_y = min(rot_ys), max(rot_ys)

                # Add padding
                padding = 0.0001
                min_rot_x -= padding
                max_rot_x += padding
                min_rot_y -= padding
                max_rot_y += padding

                # Add extra offset to move the bottom edge away from the lines
                bottom_offset = 0.002  # Additional spacing below the lines
                min_rot_y -= bottom_offset

                # Create only the bottom edge of the box in rotated space
                bottom_edge_rot = [
                    (min_rot_x, min_rot_y),  # Bottom-left
                    (max_rot_x, min_rot_y)   # Bottom-right
                ]

                # Transform back to geographic coordinates
                bottom_edge_coords = []
                for rot_x, rot_y in bottom_edge_rot:
                    # Rotate back by theta
                    dx = rot_x * cos(theta) - rot_y * sin(theta)
                    dy = rot_x * sin(theta) + rot_y * cos(theta)
                    # Translate back to original position
                    lon = dx + center_lon
                    lat = dy + center_lat
                    bottom_edge_coords.append([lon, lat])

                features.append({
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": bottom_edge_coords
                    },
                    "properties": {
                        "swath": swath_name,
                        "type": "swath_edge",
                        "name": f"Swath {swath_name}",
                        "rotation_angle": avg_angle
                    }
                })

        grouped_by_swath[swath_name] = {
            "type": "FeatureCollection",
            "features": features
        }

    return jsonify({"swaths": grouped_by_swath})


@app.route("/clear_line_cache", methods=["POST"])
def clear_line_cache():
    """Clear all cached swath line data to force regeneration"""
    conn = None
    try:
        conn = get_postgres_connection()
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM swath_lines")
            cursor.execute("DELETE FROM swath_boxes")
        conn.commit()
        return jsonify({"status": "success", "message": "Line cache cleared. Lines will be regenerated on next map view."})
    except Exception as e:
        print(f"❌ Error clearing line cache: {e}")
        if conn:
            conn.rollback()
        return jsonify({"status": "error", "message": "Database error"})
    finally:
        if conn:
            return_postgres_connection(conn)

@app.route("/load_polygons")
def load_polygons():
    folder = "saved_polygons"
    features = []

    if not os.path.exists(folder):
        os.makedirs(folder)
        return jsonify({"type": "FeatureCollection", "features": []})

    for fname in os.listdir(folder):
        if fname.endswith(".geojson"):
            try:
                with open(os.path.join(folder, fname)) as f:
                    features.append(json.load(f))
            except Exception as e:
                print(f"❌ Error reading {fname}: {e}")

    return jsonify({"type": "FeatureCollection", "features": features})

@app.route("/save_polygon", methods=["POST"])
def save_polygon():
    data = request.get_json()
    label = data.get("properties", {}).get("label", "unnamed")
    safe_label = "".join(c if c.isalnum() else "_" for c in label)

    folder = "saved_polygons"
    if not os.path.exists(folder):
        os.makedirs(folder)

    filepath = os.path.join(folder, f"{safe_label}.geojson")
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

    return jsonify({"status": "success"})

@app.route("/delete_polygon/<label>", methods=["DELETE"])
def delete_polygon(label):
    safe_label = "".join(c if c.isalnum() else "_" for c in label)
    path = os.path.join("saved_polygons", f"{safe_label}.geojson")

    if os.path.exists(path):
        os.remove(path)
        return jsonify({"status": "deleted"})
    else:
        return jsonify({"status": "not found"}), 404
    


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        conn = None
        try:
            conn = get_postgres_connection()
            with conn.cursor() as cursor:
                cursor.execute("SELECT password_hash FROM users WHERE username = %s", (username,))
                user = cursor.fetchone()
                if user and check_password_hash(user[0], password):
                    session["can_edit"] = True
                    session["username"] = username
                    return redirect(request.args.get("next") or url_for("index"))
        except Exception as e:
            print(f"❌ Error during login: {e}")
            error = "Database error occurred."
        finally:
            if conn:
                return_postgres_connection(conn)
        error = "Invalid credentials."

    return render_template('login.html', error=error)
    
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


    



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)

run_migrations_once()
