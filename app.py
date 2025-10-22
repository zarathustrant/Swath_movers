from flask import Flask, request, render_template_string, jsonify, redirect, url_for, render_template, send_from_directory,session, send_file
import pandas as pd
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import secrets
from shapely.geometry import LineString
import json
from math import radians, degrees, atan2, cos, sin
from shapely.geometry import Polygon






app = Flask(__name__)
# Change from relative to absolute path
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
SWATH_FOLDER = os.path.join(PROJECT_DIR, "swaths")
DB_FILE = os.path.join(PROJECT_DIR, "swath_movers.db")
BASE_COORDS_CSV = os.path.join(PROJECT_DIR, "base.csv")
app.secret_key = "f6e3a4b5e1c2d89a345e2a3c9bd0a5f4"
os.makedirs(SWATH_FOLDER, exist_ok=True)

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

# === MIGRATION SCRIPT ===
def migrate_csv_to_sqlite():
    if not os.path.exists(BASE_COORDS_CSV):
        print("❌ base_coordinates.csv not found.")
        return

    df = pd.read_csv(BASE_COORDS_CSV)
    required_cols = {"Line", "Shotpoint", "Latitude", "Longitude", "Type", "_id"}
    if not required_cols.issubset(set(df.columns)):
        print("❌ CSV is missing required columns.")
        return

    with sqlite3.connect(DB_FILE) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS coordinates (
                Line INTEGER,
                Shotpoint INTEGER,
                Latitude REAL,
                Longitude REAL,
                Type TEXT,
                _id TEXT PRIMARY KEY
            )
        ''')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_line_shot ON coordinates (Line, Shotpoint)')

        for _, row in df.iterrows():
            try:
                conn.execute('''
                    INSERT OR REPLACE INTO coordinates (Line, Shotpoint, Latitude, Longitude, Type, _id)
                    VALUES (?, ?, ?, ?, ?, ?)
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
    print("✅ Coordinates loaded into SQLite.")
    

def load_users_from_csv(csv_file="users.csv", db_file="swath_movers.db"):
    df = pd.read_csv(csv_file)
    with sqlite3.connect(db_file) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL
            )
        ''')
        for _, row in df.iterrows():
            username = row["username"].strip()
            password = row["password"].strip()
            hashed = generate_password_hash(password)
            try:
                conn.execute("INSERT OR REPLACE INTO users (username, password_hash) VALUES (?, ?)", (username, hashed))
                print(f"✅ Added user: {username}")
            except Exception as e:
                print(f"⚠️ Skipped user {username}: {e}")

# === FAST COORDINATE LOOKUP ===
def get_coordinate_lookup():
    coords = {}
    with sqlite3.connect(DB_FILE) as conn:
        result = conn.execute("SELECT Line, Shotpoint, Latitude, Longitude FROM coordinates").fetchall()
        for line, shot, lat, lon in result:
            coords[(line, shot)] = (lat, lon)
    return coords

# === BASIC APP FUNCTIONALITY ===
def init_swath_table(swath):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(f'''
            CREATE TABLE IF NOT EXISTS "{swath}" (
                Line INTEGER,
                Shotpoint INTEGER,
                DeploymentType TEXT,
                Username TEXT,
                Timestamp TEXT,
                PRIMARY KEY (Line, Shotpoint)
            )
        ''')
        
def init_global_deployments_table():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS global_deployments (
                Line INTEGER,
                Shotpoint INTEGER,
                DeploymentType TEXT,
                Username TEXT,
                Timestamp TEXT,
                PRIMARY KEY (Line, Shotpoint)
            )
        ''')
def run_migrations_once():
    LOCK_FILE = "migration.lock"
    if os.path.exists(LOCK_FILE):
        print("✅ Migrations already run. Skipping.")
        return

    migrate_csv_to_sqlite()
    load_users_from_csv()
    init_global_deployments_table()
    
    with open(LOCK_FILE, "w") as f:
        f.write(datetime.now().isoformat())
    print("✅ Migrations done.")
        
def load_deployments(swath):
    init_swath_table(swath)
    with sqlite3.connect(DB_FILE) as conn:
        result = conn.execute(f"SELECT Line, Shotpoint, DeploymentType FROM \"{swath}\"").fetchall()
    return {(row[0], row[1]): row[2] for row in result}

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
    with sqlite3.connect(DB_FILE) as conn:
        result = conn.execute("SELECT Line, Shotpoint, DeploymentType FROM global_deployments").fetchall()
    return {(row[0], row[1]): row[2] for row in result}

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

    return render_template_string(TEMPLATE,
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

    init_swath_table(swath)  # Ensure table exists

    with sqlite3.connect(DB_FILE) as conn:
        if deploy == "":
            # 🔴 If user clears the selection, delete it from DB
            conn.execute(f'''
                DELETE FROM "{swath}"
                WHERE Line = ? AND Shotpoint = ?
            ''', (line, shot))
            
            conn.execute('''
                DELETE FROM global_deployments
                WHERE Line = ? AND Shotpoint = ?
            ''', (line, shot))
            
            status = "deleted"
        else:
            # 🟢 Save normally
            conn.execute(f'''
                INSERT INTO "{swath}" (Line, Shotpoint, DeploymentType, Username, Timestamp)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(Line, Shotpoint) DO UPDATE SET
                    DeploymentType=excluded.DeploymentType,
                    Username=excluded.Username,
                    Timestamp=excluded.Timestamp
            ''', (line, shot, deploy, username, timestamp))
            
            conn.execute('''
                INSERT INTO global_deployments (Line, Shotpoint, DeploymentType, Username, Timestamp)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(Line, Shotpoint) DO UPDATE SET
                    DeploymentType=excluded.DeploymentType,
                    Username=excluded.Username,
                    Timestamp=excluded.Timestamp
            ''', (line, shot, deploy, username, timestamp))
            
            status = "saved"

    return jsonify({"status": status, "user": username, "timestamp": timestamp})

@app.route("/geojson")
def get_all_shotpoints():
    coords_lookup = get_coordinate_lookup()
    features = []
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        for table in tables:
            try:
                result = conn.execute(f"SELECT Line, Shotpoint, DeploymentType FROM \"{table}\"").fetchall()
                for line, shot, deploy in result:
                    if (line, shot) in coords_lookup:
                        lat, lon = coords_lookup[(line, shot)]
                        features.append({
                            "type": "Feature",
                            "geometry": {"type": "Point", "coordinates": [lon, lat]},
                            "properties": {
                                "line": line,
                                "shotpoint": shot,
                                "type": deploy,
                                "swath": table
                            }
                        })
            except Exception:
                continue
    return jsonify({"type": "FeatureCollection", "features": features})

@app.route("/geojson_lines")
def geojson_lines():
    grouped_by_swath = {}
    labeled_lines = set()  # Track which line numbers have already been labeled

    with sqlite3.connect(DB_FILE) as conn:
        # Ensure tables exist
        conn.execute("""
            CREATE TABLE IF NOT EXISTS swath_boxes (
                swath TEXT PRIMARY KEY,
                coordinates TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS swath_lines (
                swath TEXT,
                line INTEGER,
                first_shot INTEGER,
                last_shot INTEGER,
                lon1 REAL,
                lat1 REAL,
                lon2 REAL,
                lat2 REAL,
                type TEXT,
                PRIMARY KEY (swath, line)
            )
        """)
        coord_rows = conn.execute("SELECT Line, Shotpoint, Latitude, Longitude, Type FROM coordinates").fetchall()
        coord_lookup = {
            (line, shot): (lat, lon, typ) for line, shot, lat, lon, typ in coord_rows
        }

    for filename in os.listdir(SWATH_FOLDER):
        if not filename.endswith(".csv"):
            continue

        swath_name = filename.replace(".csv", "")
        features = []

        # Load existing cached lines if available
        with sqlite3.connect(DB_FILE) as conn:
            existing_lines = conn.execute(
                "SELECT line, first_shot, last_shot, lon1, lat1, lon2, lat2, type FROM swath_lines WHERE swath = ?",
                (swath_name,)
            ).fetchall()

        if existing_lines:
            print(f"📦 Loaded cached lines for swath: {swath_name}")
            for line, first, last, lon1, lat1, lon2, lat2, typ in existing_lines:
                # Generate extended points for existing cached lines
                extended_points = []
                dx = lon2 - lon1
                dy = lat2 - lat1
                norm = (dx ** 2 + dy ** 2) ** 0.5
                length_factor = 0.00005
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
                with sqlite3.connect(DB_FILE) as conn:
                    conn.executemany("""
                        INSERT OR REPLACE INTO swath_lines
                        (swath, line, first_shot, last_shot, lon1, lat1, lon2, lat2, type)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, line_rows)
                    print(f"💾 Saved {len(line_rows)} lines to DB for swath: {swath_name}")

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
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("DELETE FROM swath_lines")
        conn.execute("DELETE FROM swath_boxes")
        conn.commit()
    return jsonify({"status": "success", "message": "Line cache cleared. Lines will be regenerated on next map view."})

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
    
def load_users_from_csv(csv_file="users.csv", db_file="swath_movers.db"):
    df = pd.read_csv(csv_file)
    with sqlite3.connect(db_file) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL
            )
        ''')
        for _, row in df.iterrows():
            username = row["username"].strip()
            password = row["password"].strip()
            hashed = generate_password_hash(password)
            try:
                conn.execute("INSERT OR REPLACE INTO users (username, password_hash) VALUES (?, ?)", (username, hashed))
                print(f"✅ Added user: {username}")
            except Exception as e:
                print(f"⚠️ Skipped user {username}: {e}")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        with sqlite3.connect(DB_FILE) as conn:
            user = conn.execute("SELECT password_hash FROM users WHERE username=?", (username,)).fetchone()
            if user and check_password_hash(user[0], password):
                session["can_edit"] = True
                session["username"] = username
                return redirect(request.args.get("next") or url_for("index"))
        return render_template_string("<p>❌ Invalid credentials.</p><a href='/login'>Try again</a>")

    return render_template_string('''
        <form method="post" style="max-width:300px;margin:auto;padding:40px;font-family:sans-serif;">
            <h3>Login</h3>
            <input type="text" name="username" placeholder="Username" required style="width:100%;padding:10px;margin-bottom:10px;">
            <input type="password" name="password" placeholder="Password" required style="width:100%;padding:10px;margin-bottom:10px;">
            <button type="submit" style="padding:10px;width:100%;background:#2c3e50;color:white;border:none;">Login</button>
        </form>
    ''')
    
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


    


TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap" rel="stylesheet">
    <link rel="icon" href="{{ url_for('static', filename='favicon.png') }}" type="image/png">
    <link rel="shortcut icon" href="{{ url_for('static', filename='favicon.png') }}" type="image/png">
    <title>Swath Movers</title>
    <style>
        body { font-family: Poppins, sans-serif; padding-top: 50px; }
        table { border-collapse: collapse; width: 100%; font-size: 12px; }
        th, td { border: 1px solid #ccc; padding: 4px; text-align: center; }
        th { background: #2c3e50; color: white; position: sticky; top: 50px; z-index: 10; }
        select {
            appearance: none; border: 1px solid #ccc; padding: 3px; font-size: 12px;
            -webkit-appearance: none; -moz-appearance: none;
        }
        .select-wrapper { position: relative; }
        .fill-handle {
            position: absolute; right: -3px; bottom: 2px;
            width: 6px; height: 6px; background: #3498db;
            border-radius: 2px; cursor: crosshair; display: none;
        }
        .select-wrapper:hover .fill-handle { display: block; }
        .shot-cell { font-weight: bold; }
        #zoom-panel {
            position: fixed; top: 0; left: 0; right: 0;
            background: white; padding: 8px; z-index: 999;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            display: flex; align-items: center; gap: 10px;
        }
        #zoom-panel button { padding: 3px 8px; font-size: 14px; }
        
        ::selection {
            background: transparent;
            color: inherit;
        }
        
        label[for="swathSelect"] {
            font-weight: 600;
            color: black;
        }

        select#swathSelect option:checked {
            color: blue;
            font-weight: bold;
        }
        #statsPopup {
            position: fixed;
            top: 70px;
            right: 20px;
            width: 420px;
            max-height: 60vh;
            overflow: hidden;
            background: rgba(255, 255, 255, 0.95);
            border: 1px solid #ccc;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            z-index: 1000;
            font-size: 11px;
            backdrop-filter: blur(6px);
            resize: both;
            overflow: auto;
        }

        #statsHeader {
            background: #2c3e50;
            color: white;
            padding: 8px;
            font-weight: bold;
            cursor: move;
            border-top-left-radius: 12px;
            border-top-right-radius: 12px;
        }

        #statsContent {
            padding: 10px;
        }

    </style>
    <script>
        const deploymentColors = {{ colors | tojson }};
        const canEdit = {{ 'true' if session.get('can_edit') else 'false' }};
        let dragging = false, startSelect = null;

        function showToast(message) {
            const toast = document.getElementById("toast");
            toast.innerText = message;
            toast.style.display = "block";
            setTimeout(() => { toast.style.display = "none"; }, 3000);
        }

        function updateDeployment(select, line, shot) {
            const color = deploymentColors[select.value] || '#ffffff';
            const cell = document.getElementById(`cell-${line}-${shot}`);
            if (cell) cell.style.backgroundColor = color;

            if (!canEdit) {
                showToast("🔒 Not saved — viewer mode only.");
                return;
            }

            fetch('/save/{{ swath }}', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ line: line, shotpoint: shot, deployment: select.value })
            });
        }

        function startFill(handle) {
            dragging = true;
            startSelect = handle.previousElementSibling;
            document.body.classList.add("dragging");
            document.addEventListener('mouseup', stopFill);
            document.addEventListener('mousemove', performFill);
        }

        function stopFill() {
            dragging = false;
            startSelect = null;
            document.body.classList.remove("dragging");
            document.removeEventListener('mouseup', stopFill);
            document.removeEventListener('mousemove', performFill);
        }

        function performFill(e) {
            if (!dragging || !startSelect) return;
            const y = e.clientY;
            const allSelects = document.querySelectorAll(`select[data-line="${startSelect.dataset.line}"]`);
            let startIndex = Array.from(allSelects).findIndex(sel => sel.dataset.shot === startSelect.dataset.shot);
            for (let i = startIndex + 1; i < allSelects.length; i++) {
                const sel = allSelects[i];
                const rect = sel.getBoundingClientRect();
                if (y >= rect.top && y <= rect.bottom) {
                    sel.value = startSelect.value;
                    const line = parseInt(sel.dataset.line);
                    const shot = parseInt(sel.dataset.shot);
                    const color = deploymentColors[sel.value] || '#ffffff';
                    const cell = document.getElementById(`cell-${line}-${shot}`);
                    if (cell) cell.style.backgroundColor = color;
                    updateDeployment(sel, line, shot);
                }
            }
        }

        let zoomLevel = 100;
        function applyZoom() {
            document.body.style.zoom = zoomLevel + '%';
            document.getElementById('zoomDisplay').innerText = zoomLevel + '%';
        }
        function zoomIn() { if (zoomLevel < 200) { zoomLevel += 10; applyZoom(); } }
        function zoomOut() { if (zoomLevel > 50) { zoomLevel -= 10; applyZoom(); } }

        function toggleStats() {
            const statsBox = document.getElementById("statsPopup");
            statsBox.style.display = (statsBox.style.display === "none") ? "block" : "none";
        }

        function clearLineCache() {
            if (confirm("Clear line cache and regenerate all map lines from scratch?")) {
                fetch('/clear_line_cache', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'}
                })
                .then(response => response.json())
                .then(data => {
                    showToast("✅ " + data.message);
                })
                .catch(error => {
                    showToast("❌ Error clearing cache");
                });
            }
        }

        // === Make statsPopup draggable ===
        const popup = document.getElementById("statsPopup");
        const header = document.getElementById("statsHeader");
        let offsetX = 0, offsetY = 0, isDragging = false;

        header.onmousedown = (e) => {
            isDragging = true;
            offsetX = e.clientX - popup.offsetLeft;
            offsetY = e.clientY - popup.offsetTop;
            document.onmousemove = drag;
            document.onmouseup = () => { isDragging = false; document.onmousemove = null; };
        };

        function drag(e) {
            if (!isDragging) return;
            popup.style.top = (e.clientY - offsetY) + "px";
            popup.style.left = (e.clientX - offsetX) + "px";
            popup.style.right = "auto";  // disable fixed right when moving
        }
    </script>
</head>
<body>
    <div id="toast" style="
        position: fixed;
        bottom: 20px;
        right: 20px;
        background: rgba(0, 0, 0, 0.85);
        color: white;
        padding: 10px 16px;
        border-radius: 6px;
        font-size: 13px;
        font-family: Poppins, sans-serif;
        display: none;
        z-index: 9999;
        box-shadow: 0 2px 6px rgba(0,0,0,0.3);
    ">
        Not saved — viewer mode only.
    </div>
    <div id="zoom-panel">
        
        
        <label for="swathSelect" style="font-weight: bold; color: black; font-family: 'Poppins', sans-serif;">Swath:</label>
        <select id="swathSelect" onchange="location.href='/swath/' + this.value"
                style="font-family: 'Poppins', sans-serif; font-weight: bold; color: red;">
            {% for s in swath_list %}
                <option value="{{ s }}" {% if s == swath %}selected{% endif %}>{{ s }}</option>
            {% endfor %}
        </select>
        
        <span>Zoom:</span>
        <button onclick="zoomOut()">−</button>
        <span id="zoomDisplay">100%</span>
        <button onclick="zoomIn()">+</button>
        <button onclick="toggleStats()">📊 Stats</button>
        <button onclick="clearLineCache()">🔄 Regenerate Lines</button>
        <button onclick="location.href='/map'">🗺 Map</button>
        {% if session.get('can_edit') %}
            <button onclick="location.href='/logout'">🔒 Logout</button>
        {% else %}
            <button onclick="location.href='/login'">🔓 Login</button>
        {% endif %}

    </div>
    <table>
        <thead>
            <tr>{% for line in line_numbers %}<th>{{ line }}</th><th>Deployment/Retrieval</th>{% endfor %}</tr>
        </thead>
        <tbody>
            {% for entry in table_data %}
                <tr>
                {% for line in line_numbers %}
                    {% if entry.row[line].value %}
                        <td id="cell-{{ line }}-{{ entry.shot }}" class="shot-cell" style="background-color: {{ entry.row[line].color }}">{{ entry.row[line].value }}</td>
                        <td>
                            <div class="select-wrapper">
                                <select onchange="updateDeployment(this, {{ line }}, {{ entry.shot }})" data-line="{{ line }}" data-shot="{{ entry.shot }}">
                                    <option value="">--</option>
                                    {% for option in deployment_types %}
                                        <option value="{{ option }}" {% if entry.row[line].deploy == option %}selected{% endif %}>{{ option }}</option>
                                    {% endfor %}
                                </select>
                                <div class="fill-handle" onmousedown="startFill(this)"></div>
                            </div>
                        </td>
                    {% else %}
                        <td></td><td></td>
                    {% endif %}
                {% endfor %}
                </tr>
            {% endfor %}
        </tbody>
    </table>
    
    <div id="statsPopup" style="display:none;">
        <div id="statsHeader">📊 Stats <span style="float:right; cursor:pointer;" onclick="toggleStats()">✖</span></div>
        <div id="statsContent">
            <table>
                <thead>
                    <tr>
                        <th>Deployment/Retrieval Type</th>
                        {% for line in line_numbers %}
                            <th>{{ line }}</th>
                        {% endfor %}
                        <th style="background:#333;">Total</th> <!-- Row total -->
                    </tr>
                </thead>
                <tbody>
                    {% for dtype in deployment_types %}
                    <tr>
                        <td><strong>{{ dtype }}</strong></td>
                        {% set ns = namespace(row_total=0) %}
                        {% for line in line_numbers %}
                            {% set count = stats[dtype][line] %}
                            {% set ns.row_total = ns.row_total + count %}
                            {% set maxc = max_count[dtype] %}
                            {% set intensity = 255 - (count / maxc * 180) if maxc > 0 else 255 %}
                            {% set base = colors.get(dtype, "#ffffff") %}
                            {% set r = base[1:3] | int(base=16) %}
                            {% set g = base[3:5] | int(base=16) %}
                            {% set b = base[5:7] | int(base=16) %}
                            {% set rr = (r * (intensity / 255)) | round(0, 'floor') %}
                            {% set gg = (g * (intensity / 255)) | round(0, 'floor') %}
                            {% set bb = (b * (intensity / 255)) | round(0, 'floor') %}
                            {% set brightness = (rr * 0.299 + gg * 0.587 + bb * 0.114) %}
                            {% set text_color = 'white' if brightness < 128 else 'black' %}
                            <td style="background-color: rgb({{ rr }}, {{ gg }}, {{ bb }}); color: {{ text_color }};">
                                {{ count }}
                            </td>
                        {% endfor %}
                        <td style="background:#eee; font-weight:bold;">{{ ns.row_total }}</td> <!-- Row total cell -->
                    </tr>
                    {% endfor %}
                </tbody>
                <tfoot>
                    <tr>
                        <th>Total</th>
                        {% set grand = namespace(total=0) %}
                        {% for line in line_numbers %}
                            {% set col = namespace(total=0) %}
                            {% for dt in deployment_types %}
                                {% if stats[dt][line] is defined %}
                                    {% set col.total = col.total + stats[dt][line] %}
                                {% endif %}
                            {% endfor %}
                            {% set grand.total = grand.total + col.total %}
                            <th style="background:#eee; color:black; font-weight:bold;">{{ col.total }}</th>
                        {% endfor %}
                        <th style="background:#333; color:white; font-weight:bold;">{{ grand.total }}</th>
                    </tr>
                </tfoot>
            </table>
        </div>
    </div>
    <div id="mapOverlay">
        <div id="mapFullscreen">
            <div id="map"></div>
        </div>
    </div>
    
    
</body>
</html>
'''
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)

run_migrations_once()



