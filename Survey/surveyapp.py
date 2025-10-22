from flask import Flask, request, jsonify, send_file
import csv
import os
import sqlite3
from datetime import datetime

app = Flask(__name__)
INPUT_FILE = 'input.csv'
DB_FILE = 'zones.db'

# Initialize the SQLite database
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS zones (
                Receiver TEXT,
                Shotpoint TEXT,
                Zone TEXT,
                Color TEXT,
                Latitude TEXT,
                Longitude TEXT,
                Type TEXT,
                _id TEXT,
                SurveyorName TEXT,
                WorkDate TEXT,
                timestamp TEXT,
                PRIMARY KEY (Receiver, Shotpoint)
            )
        ''')
        conn.commit()

# Load initial input data from CSV
def load_input_data():
    input_data = []
    with open(INPUT_FILE, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            input_data.append({
                'Receiver': row['Receiver'],
                'Shotpoint': row['Shotpoint'],
                'Latitude': row['Latitude'],
                'Longitude': row['Longitude'],
                'Type': row['Type'],
                '_id': row['_id']
            })
    return input_data

# Load existing zones and extra metadata from DB
def load_existing_zones():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT Receiver, Shotpoint, Zone, SurveyorName, WorkDate FROM zones")
        return {
            (r[0], r[1]): {
                'Zone': r[2],
                'SurveyorName': r[3],
                'WorkDate': r[4]
            } for r in c.fetchall()
        }

# Zone name to color map
def zone_to_color(zone):
    mapping = {
        'Forest': 'green',
        'Creek': 'blue',
        'Farmland': 'orange',
        'Urban': 'red',
        'Industrial': 'gray',
        'Swamp': 'purple',
        'Mangrove': 'darkgreen',
        'Savanna': 'yellow',
        'Wetland': 'teal',
        'Bushland': 'olive',
        'Grassland': 'lightgreen',
        'Scrubland': 'darkolivegreen',
        'Hilltop': 'brown',
        'Lowland': 'lightblue',
        'Valley': 'lightgray',
        'Residential': 'pink',
        'Commercial': 'gold',
        'School Zone': 'violet',
        'Playground': 'skyblue',
        'Rocky': 'saddlebrown',
        'Dry Area': 'tan',
        'Wet Area': 'aquamarine',
        'Dump Site': 'black',
        'Gas Zone': 'navy',
        'Oil Zone': 'maroon',
        'Protected Area': 'lime',
        'Research Area': 'indigo',
        'Old Pipeline': 'slategray',
        'New Pipeline': 'darkred'
    }
    return mapping.get(zone.strip(), 'gray')

@app.route('/')
def index():
    return send_file('index_ommision.html')

@app.route('/data', methods=['GET'])
def get_data():
    init_db()
    input_rows = load_input_data()
    zone_lookup = load_existing_zones()

    data = []
    for row in input_rows:
        key = (row['Receiver'], row['Shotpoint'])
        zdata = zone_lookup.get(key, {})
        zone = zdata.get('Zone', '')
        surveyor = zdata.get('SurveyorName', '')
        work_date = zdata.get('WorkDate', '')
        color = zone_to_color(zone) if zone else ''
        data.append({
            'Receiver': row['Receiver'],
            'Shotpoint': row['Shotpoint'],
            'Zone': zone,
            'Color': color,
            'Latitude': row['Latitude'],
            'Longitude': row['Longitude'],
            'Type': row['Type'],
            '_id': row['_id'],
            'SurveyorName': surveyor,
            'WorkDate': work_date
        })
    return jsonify(data)

@app.route('/save', methods=['POST'])
def save_data():
    data = request.json
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    init_db()

    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        for row in data:
            zone = row['Zone'].strip()
            color = zone_to_color(zone)
            c.execute('''
                INSERT INTO zones 
                (Receiver, Shotpoint, Zone, Color, Latitude, Longitude, Type, _id, SurveyorName, WorkDate, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(Receiver, Shotpoint) DO UPDATE SET 
                    Zone=excluded.Zone,
                    Color=excluded.Color,
                    Latitude=excluded.Latitude,
                    Longitude=excluded.Longitude,
                    Type=excluded.Type,
                    _id=excluded._id,
                    SurveyorName=excluded.SurveyorName,
                    WorkDate=excluded.WorkDate,
                    timestamp=excluded.timestamp
            ''', (
                row['Receiver'],
                row['Shotpoint'],
                zone,
                color,
                row['Latitude'],
                row['Longitude'],
                row['Type'],
                row['_id'],
                row.get('SurveyorName', ''),
                row.get('WorkDate', ''),
                now
            ))
        conn.commit()
    return 'Saved to database', 200

if __name__ == '__main__':
    init_db()
    app.run(debug=True)