#!/usr/bin/env python3
"""
Data migration script from SQLite to PostgreSQL for Swath Movers
"""

import sqlite3
import psycopg2
import psycopg2.extras
import os
from datetime import datetime

def migrate_data():
    """Migrate all data from SQLite to PostgreSQL"""

    # SQLite connection
    sqlite_path = 'swath_movers.db'
    sqlite_conn = sqlite3.connect(sqlite_path)

    # PostgreSQL connection
    postgres_conn = psycopg2.connect(
        dbname='swath_movers',
        user='oluseyioyetunde',  # Default PostgreSQL user
        password='',  # No password for local development
        host='localhost',
        port='5432'
    )

    postgres_conn.autocommit = True
    postgres_cursor = postgres_conn.cursor()

    print("🚀 Starting data migration from SQLite to PostgreSQL...")

    try:
        # Migrate coordinates table
        print("📍 Migrating coordinates...")
        sqlite_cursor = sqlite_conn.cursor()
        sqlite_cursor.execute("SELECT Line, Shotpoint, Latitude, Longitude, Type, _id FROM coordinates")
        coordinates = sqlite_cursor.fetchall()

        if coordinates:
            psycopg2.extras.execute_values(
                postgres_cursor,
                "INSERT INTO coordinates (line, shotpoint, latitude, longitude, type, _id) VALUES %s ON CONFLICT (_id) DO NOTHING",
                coordinates
            )
            print(f"✅ Migrated {len(coordinates)} coordinate records")

        # Migrate users table
        print("👥 Migrating users...")
        sqlite_cursor.execute("SELECT username, password_hash FROM users")
        users = sqlite_cursor.fetchall()

        if users:
            psycopg2.extras.execute_values(
                postgres_cursor,
                "INSERT INTO users (username, password_hash) VALUES %s ON CONFLICT (username) DO NOTHING",
                users
            )
            print(f"✅ Migrated {len(users)} user records")

        # Migrate global deployments
        print("🌍 Migrating global deployments...")
        sqlite_cursor.execute("SELECT Line, Shotpoint, DeploymentType, Username, Timestamp FROM global_deployments")
        global_deployments = sqlite_cursor.fetchall()

        if global_deployments:
            psycopg2.extras.execute_values(
                postgres_cursor,
                "INSERT INTO global_deployments (line, shotpoint, deployment_type, username, timestamp) VALUES %s ON CONFLICT (line, shotpoint) DO UPDATE SET deployment_type = EXCLUDED.deployment_type, username = EXCLUDED.username, timestamp = EXCLUDED.timestamp",
                global_deployments
            )
            print(f"✅ Migrated {len(global_deployments)} global deployment records")

        # Migrate individual swath tables (check which ones exist)
        existing_swaths = ['1', '2', '3', '4', '5', '8']  # From .tables output
        for table_name in existing_swaths:
            print(f"📊 Migrating swath {table_name}...")

            try:
                sqlite_cursor.execute(f"SELECT Line, Shotpoint, DeploymentType, Username, Timestamp FROM '{table_name}'")
                swath_data = sqlite_cursor.fetchall()

                if swath_data:
                    psycopg2.extras.execute_values(
                        postgres_cursor,
                        f"INSERT INTO swath_{table_name} (line, shotpoint, deployment_type, username, timestamp) VALUES %s ON CONFLICT (line, shotpoint) DO UPDATE SET deployment_type = EXCLUDED.deployment_type, username = EXCLUDED.username, timestamp = EXCLUDED.timestamp",
                        swath_data
                    )
                    print(f"✅ Migrated {len(swath_data)} records for swath {table_name}")
                else:
                    print(f"ℹ️ No data found for swath {table_name}")

            except sqlite3.OperationalError as e:
                print(f"⚠️ Warning: Could not migrate swath {table_name}: {e}")

        # Migrate cache tables
        cache_tables = ['swath_lines', 'swath_boxes', 'swath_edges']
        for table in cache_tables:
            print(f"💾 Migrating {table}...")
            try:
                if table == 'swath_lines':
                    sqlite_cursor.execute("SELECT swath, line, first_shot, last_shot, lon1, lat1, lon2, lat2, type FROM swath_lines")
                    columns = 'swath, line, first_shot, last_shot, lon1, lat1, lon2, lat2, type'
                elif table == 'swath_boxes':
                    sqlite_cursor.execute("SELECT swath, coordinates FROM swath_boxes")
                    columns = 'swath, coordinates'
                elif table == 'swath_edges':
                    sqlite_cursor.execute("SELECT swath, edge_coordinates, rotation_angle FROM swath_edges")
                    columns = 'swath, edge_coordinates, rotation_angle'

                data = sqlite_cursor.fetchall()

                if data:
                    placeholders = ', '.join(['%s'] * len(data[0]))
                    psycopg2.extras.execute_values(
                        postgres_cursor,
                        f"INSERT INTO {table} ({columns}) VALUES %s ON CONFLICT DO NOTHING",
                        data
                    )
                    print(f"✅ Migrated {len(data)} records for {table}")

            except Exception as e:
                print(f"⚠️ Warning: Could not migrate {table}: {e}")

        print("🎉 Data migration completed successfully!")

        # Show summary
        postgres_cursor.execute("SELECT COUNT(*) FROM coordinates")
        coord_count = postgres_cursor.fetchone()[0]

        postgres_cursor.execute("SELECT COUNT(*) FROM global_deployments")
        global_count = postgres_cursor.fetchone()[0]

        postgres_cursor.execute("SELECT COUNT(*) FROM users")
        user_count = postgres_cursor.fetchone()[0]

        print("📊 Migration Summary:")
        print(f"   - Coordinates: {coord_count} records")
        print(f"   - Global Deployments: {global_count} records")
        print(f"   - Users: {user_count} records")

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        sqlite_conn.close()
        postgres_conn.close()

if __name__ == "__main__":
    migrate_data()
