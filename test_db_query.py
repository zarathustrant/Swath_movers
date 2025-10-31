#!/usr/bin/env python3
import psycopg2

# Connect to database
conn = psycopg2.connect(
    host='localhost',
    port=5432,
    user='swath_user',
    password='',
    database='swath_movers_postgres'
)

cursor = conn.cursor()

# Check swath 4 source points
cursor.execute("SELECT COUNT(*) FROM post_plot_swath_4_sources WHERE is_acquired = TRUE")
acquired_count = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM post_plot_swath_4_sources")
total_count = cursor.fetchone()[0]

print(f"Swath 4 - Total source points: {total_count}")
print(f"Swath 4 - Acquired points: {acquired_count}")
print(f"Swath 4 - Pending points: {total_count - acquired_count}")

# Get a sample of acquired points
cursor.execute("""
    SELECT line, shotpoint, latitude, longitude, is_acquired, acquired_at
    FROM post_plot_swath_4_sources
    WHERE is_acquired = TRUE
    LIMIT 5
""")

print("\nSample of acquired points:")
for row in cursor.fetchall():
    print(f"  Line {row[0]}, Shot {row[1]}, Lat/Lon: {row[2]:.6f}/{row[3]:.6f}, Acquired: {row[5]}")

cursor.close()
conn.close()
