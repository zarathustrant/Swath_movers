import sqlite3
import folium
import random
import math
from datetime import datetime

#fetch zones
# Load all zone points from SQLite
def fetch_points_from_db(db_path="zones.db"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT Receiver, Shotpoint, Zone, Color, Latitude, Longitude, Type FROM zones")
    rows = cursor.fetchall()
    conn.close()

    zone_descriptions = {
        "Forest": ["Thick canopy", "Fallen logs", "Animal trails"],
        "Creek": ["Swampy terrain", "Muddy bank", "Shallow stream"],
        "Farmland": ["Cassava field", "Crop rows", "Footpath crossing"],
        "Urban": ["Concrete edge", "Electric poles"],
        "Industrial": ["Storage area", "Pipeline trench"],
        "Swamp": ["Wet zone", "Reeds", "Waterlogging"]
    }

    points = []
    for r in rows:
        receiver, shotpoint, zone, color, lat, lon, ptype = r
        points.append({
            "receiver": receiver,
            "shotpoint": int(shotpoint),
            "zone": zone,
            "color": color,
            "lat": float(lat),
            "lon": float(lon),
            "type": ptype,
            "desc": random.choice(zone_descriptions.get(zone, ["No description"]))
        })
    return points

# Calculate angle between two lat/lon pairs
def calculate_angle(lat1, lon1, lat2, lon2):
    delta_lon = math.radians(lon2 - lon1)
    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)
    x = math.sin(delta_lon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(delta_lon)
    bearing = math.atan2(x, y)
    return math.degrees(bearing)

# Draw short perpendicular line at a point
def short_perpendicular_line(lat, lon, angle, offset=0.0001):
    perp_angle = math.radians(angle + 90)
    lat1 = lat + offset * math.sin(perp_angle)
    lon1 = lon + offset * math.cos(perp_angle)
    lat2 = lat - offset * math.sin(perp_angle)
    lon2 = lon - offset * math.cos(perp_angle)
    return [(lat1, lon1), (lat2, lon2)]

# Main function
def create_map():
    points = fetch_points_from_db()
    if not points:
        print("No data found in zones.db")
        return

    # Group by zone segments
    segments = {}
    for p in points:
        key = (p["receiver"], p["zone"], p["color"])
        segments.setdefault(key, []).append(p)
    for k in segments:
        segments[k].sort(key=lambda x: x["shotpoint"])

    # Center map
    avg_lat = sum(p['lat'] for p in points) / len(points)
    avg_lon = sum(p['lon'] for p in points) / len(points)
    m = folium.Map(location=[avg_lat, avg_lon], zoom_start=17, tiles="CartoDB dark_matter")

    # Add points by type
    for p in points:
        popup = folium.Popup(
            f"<b>Receiver:</b> {p['receiver']}<br>"
            f"<b>Shotpoint:</b> {p['shotpoint']}<br>"
            f"<b>Zone:</b> {p['zone']}<br>"
            f"<b>Description:</b> {p['desc']}",
            max_width=250
        )

        if p.get('type') == 'R':
            folium.Marker(
                location=[p['lat'], p['lon']],
                icon=folium.DivIcon(html="""
                    <div style="font-size:16px; color:blue;">+</div>
                """),
                popup=popup
            ).add_to(m)
        else:
            folium.CircleMarker(
                location=[p['lat'], p['lon']],
                radius=6,
                color='red',
                fill=False,
                weight=2,
                popup=popup
            ).add_to(m)

    # Add zone segment boundaries and labels
    for (receiver, zone, color), zpoints in segments.items():
        if len(zpoints) < 2:
            continue

        start = zpoints[0]
        end = zpoints[-1]
        angle = calculate_angle(start['lat'], start['lon'], end['lat'], end['lon'])

        # Short perpendicular boundary lines (customized length & angle)
        folium.PolyLine(short_perpendicular_line(start['lat'], start['lon'], angle + 10, offset=0.0002),
                        color=color, weight=3, tooltip=f"{zone} START").add_to(m)

        folium.PolyLine(short_perpendicular_line(end['lat'], end['lon'], angle + 10, offset=0.0002),
                        color=color, weight=3, tooltip=f"{zone} END").add_to(m)

        # ➕ R-type label (above line, original direction)
        r_points = [pt for pt in zpoints if pt['type'] == 'R']
        if len(r_points) >= 2:
            r_mid = r_points[len(r_points) // 2]
            r_angle = angle + 90
            if r_angle > 90 or r_angle < -90:
                r_angle = (r_angle + 180) % 360
                if r_angle > 180:
                    r_angle -= 360
            r_offset_lat = r_mid['lat'] + 0.0006 * math.sin(math.radians(r_angle + 90))
            r_offset_lon = r_mid['lon'] + 0.0006 * math.cos(math.radians(r_angle + 90))
            folium.Marker(
                [r_offset_lat, r_offset_lon],
                icon=folium.DivIcon(html=f"""
                    <div style="transform: rotate({r_angle:.2f}deg);
                                font-size:14px; font-weight:bold;
                                color:{color}; white-space: nowrap;">
                        {zone} 
                    </div>
                """)
            ).add_to(m)

        # 🔴 S-type label (below line, flipped direction)
        s_points = [pt for pt in zpoints if pt['type'] == 'S']
        if len(s_points) >= 2:
            s_mid = s_points[len(s_points) // 2]
            s_angle = (angle + 90) % 360
            if s_angle > 90 or s_angle < -90:
                s_angle = (s_angle + 180) % 360
                if s_angle > 180:
                    s_angle -= 360
            s_offset_lat = s_mid['lat'] + 0.0006 * math.sin(math.radians(s_angle - 90))
            s_offset_lon = s_mid['lon'] + 0.0006 * math.cos(math.radians(s_angle - 90))
            folium.Marker(
                [s_offset_lat, s_offset_lon],
                icon=folium.DivIcon(html=f"""
                    <div style="transform: rotate({s_angle:.2f}deg);
                                font-size:14px; font-weight:bold;
                                color:{color}; white-space: nowrap;">
                        {zone}
                    </div>
                """)
            ).add_to(m)

    # Zone label legend
    legend_html = "<div style='position: fixed; bottom: 20px; left: 20px; background-color: white;" \
                  "padding: 10px; border:2px solid gray; z-index:9999; font-size:14px;'>" \
                  "<b>Zone Legend</b><br>"
    seen = set()
    #for p in points:
        #if p["zone"] not in seen and p["color"]:
            #legend_html += f"<span style='color:{p['color']};'>●</span> {p['zone']}<br>"
            #seen.add(p["zone"])
    #legend_html += "</div>"
    #m.get_root().html.add_child(folium.Element(legend_html))

    # Save file
    filename = f"shotpoint_map_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    m.save(filename)
    print(f"✅ Map saved: {filename}")

# Run
if __name__ == "__main__":
    create_map()