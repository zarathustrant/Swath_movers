#!/usr/bin/env python3
"""
Database operations test script for PostgreSQL
"""

import os
import sys
from datetime import datetime

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import (
    get_postgres_connection,
    return_postgres_connection,
    init_swath_table,
    init_global_deployments_table,
    migrate_csv_to_postgres,
    load_users_from_csv,
    get_coordinate_lookup,
    load_global_deployments
)

def test_database_connection():
    """Test basic database connection"""
    print("🧪 Testing database connection...")
    conn = None
    try:
        conn = get_postgres_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
            print(f"✅ Connected to PostgreSQL: {version[:50]}...")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False
    finally:
        if conn:
            return_postgres_connection(conn)

def test_table_initialization():
    """Test table initialization"""
    print("🧪 Testing table initialization...")
    try:
        init_global_deployments_table()
        init_swath_table('1')
        init_swath_table('2')
        print("✅ Tables initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Table initialization failed: {e}")
        return False

def test_coordinate_lookup():
    """Test coordinate lookup functionality"""
    print("🧪 Testing coordinate lookup...")
    try:
        coords = get_coordinate_lookup()
        if coords:
            print(f"✅ Coordinate lookup successful: {len(coords)} coordinates loaded")
            # Show a sample
            sample_key = list(coords.keys())[0] if coords else None
            if sample_key:
                print(f"   Sample: {sample_key} -> {coords[sample_key]}")
        else:
            print("⚠️ No coordinates found (this may be expected if no data is loaded)")
        return True
    except Exception as e:
        print(f"❌ Coordinate lookup failed: {e}")
        return False

def test_global_deployments():
    """Test global deployments loading"""
    print("🧪 Testing global deployments...")
    try:
        deployments = load_global_deployments()
        print(f"✅ Global deployments loaded: {len(deployments)} deployments")
        return True
    except Exception as e:
        print(f"❌ Global deployments test failed: {e}")
        return False

def test_data_migration():
    """Test data migration functions"""
    print("🧪 Testing data migration...")
    try:
        # Test user loading
        if os.path.exists('users.csv'):
            success = load_users_from_csv()
            if success:
                print("✅ User migration successful")
            else:
                print("⚠️ User migration failed or no users.csv found")
        else:
            print("⚠️ No users.csv found, skipping user migration test")

        # Test coordinate migration
        if os.path.exists('base.csv'):
            success = migrate_csv_to_postgres()
            if success:
                print("✅ Coordinate migration successful")
            else:
                print("❌ Coordinate migration failed")
                return False
        else:
            print("⚠️ No base.csv found, skipping coordinate migration test")

        return True
    except Exception as e:
        print(f"❌ Data migration test failed: {e}")
        return False

def run_all_tests():
    """Run all database tests"""
    print("🚀 Starting PostgreSQL database tests...")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 50)

    tests = [
        test_database_connection,
        test_table_initialization,
        test_coordinate_lookup,
        test_global_deployments,
        test_data_migration
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            if test():
                passed += 1
            print()
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            print()

    print("=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed!")
        return True
    else:
        print("⚠️ Some tests failed. Check the output above.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
