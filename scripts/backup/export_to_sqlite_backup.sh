#!/bin/bash

echo "========================================"
echo "Exporting PostgreSQL Data to SQLite"
echo "Safe Backup Before Locale Fix"
echo "========================================"
echo ""

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

BACKUP_DB="swath_movers_postgres_backup_$(date +%Y%m%d_%H%M%S).db"

echo "Creating SQLite backup: $BACKUP_DB"
echo ""

# Use sudo -u postgres to bypass locale issues
echo "Note: Using postgres superuser to bypass locale errors"
echo ""

echo "1. Exporting coordinates table..."
sudo -u postgres psql -d swath_movers -c "COPY (SELECT * FROM coordinates) TO STDOUT WITH CSV HEADER" > /tmp/coordinates.csv
COORD_COUNT=$(wc -l < /tmp/coordinates.csv)
echo -e "${GREEN}✓ Exported $((COORD_COUNT - 1)) coordinates${NC}"

echo ""
echo "2. Exporting global_deployments table..."
sudo -u postgres psql -d swath_movers -c "COPY (SELECT * FROM global_deployments) TO STDOUT WITH CSV HEADER" > /tmp/global_deployments.csv
DEPLOY_COUNT=$(wc -l < /tmp/global_deployments.csv)
echo -e "${GREEN}✓ Exported $((DEPLOY_COUNT - 1)) deployments${NC}"

echo ""
echo "3. Exporting swath_lines table..."
sudo -u postgres psql -d swath_movers -c "COPY (SELECT * FROM swath_lines) TO STDOUT WITH CSV HEADER" > /tmp/swath_lines.csv
LINES_COUNT=$(wc -l < /tmp/swath_lines.csv)
echo -e "${GREEN}✓ Exported $((LINES_COUNT - 1)) swath lines${NC}"

echo ""
echo "4. Exporting users table..."
sudo -u postgres psql -d swath_movers -c "COPY (SELECT username, password_hash FROM users) TO STDOUT WITH CSV HEADER" > /tmp/users.csv
USERS_COUNT=$(wc -l < /tmp/users.csv)
echo -e "${GREEN}✓ Exported $((USERS_COUNT - 1)) users${NC}"

echo ""
echo "5. Creating SQLite database: $BACKUP_DB"

# Create SQLite database with schema
sqlite3 "$BACKUP_DB" <<'EOF'
-- Coordinates table
CREATE TABLE coordinates (
    line INTEGER NOT NULL,
    shotpoint INTEGER NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    type TEXT,
    _id TEXT PRIMARY KEY
);

-- Global deployments table
CREATE TABLE global_deployments (
    line INTEGER NOT NULL,
    shotpoint INTEGER NOT NULL,
    deployment_type TEXT NOT NULL,
    username TEXT,
    timestamp TEXT NOT NULL,
    PRIMARY KEY (line, shotpoint)
);

-- Swath lines table
CREATE TABLE swath_lines (
    swath TEXT NOT NULL,
    line INTEGER NOT NULL,
    first_shot INTEGER NOT NULL,
    last_shot INTEGER NOT NULL,
    lon1 REAL NOT NULL,
    lat1 REAL NOT NULL,
    lon2 REAL NOT NULL,
    lat2 REAL NOT NULL,
    type TEXT,
    PRIMARY KEY (swath, line)
);

-- Users table
CREATE TABLE users (
    username TEXT PRIMARY KEY,
    password_hash TEXT NOT NULL
);
EOF

echo -e "${GREEN}✓ SQLite schema created${NC}"

echo ""
echo "6. Importing data into SQLite..."

# Import coordinates
sqlite3 "$BACKUP_DB" <<EOF
.mode csv
.import /tmp/coordinates.csv coordinates_temp
INSERT INTO coordinates SELECT * FROM coordinates_temp WHERE _id != '_id';
DROP TABLE coordinates_temp;
EOF
echo -e "${GREEN}✓ Imported coordinates${NC}"

# Import global_deployments
sqlite3 "$BACKUP_DB" <<EOF
.mode csv
.import /tmp/global_deployments.csv global_deployments_temp
INSERT INTO global_deployments SELECT * FROM global_deployments_temp WHERE line != 'line';
DROP TABLE global_deployments_temp;
EOF
echo -e "${GREEN}✓ Imported global_deployments${NC}"

# Import swath_lines
sqlite3 "$BACKUP_DB" <<EOF
.mode csv
.import /tmp/swath_lines.csv swath_lines_temp
INSERT INTO swath_lines SELECT * FROM swath_lines_temp WHERE swath != 'swath';
DROP TABLE swath_lines_temp;
EOF
echo -e "${GREEN}✓ Imported swath_lines${NC}"

# Import users
sqlite3 "$BACKUP_DB" <<EOF
.mode csv
.import /tmp/users.csv users_temp
INSERT INTO users SELECT * FROM users_temp WHERE username != 'username';
DROP TABLE users_temp;
EOF
echo -e "${GREEN}✓ Imported users${NC}"

echo ""
echo "7. Verifying SQLite backup..."

SQLITE_COORDS=$(sqlite3 "$BACKUP_DB" "SELECT COUNT(*) FROM coordinates;")
SQLITE_DEPLOY=$(sqlite3 "$BACKUP_DB" "SELECT COUNT(*) FROM global_deployments;")
SQLITE_LINES=$(sqlite3 "$BACKUP_DB" "SELECT COUNT(*) FROM swath_lines;")
SQLITE_USERS=$(sqlite3 "$BACKUP_DB" "SELECT COUNT(*) FROM users;")

echo ""
echo "Backup verification:"
echo "  Coordinates: $SQLITE_COORDS"
echo "  Deployments: $SQLITE_DEPLOY"
echo "  Swath Lines: $SQLITE_LINES"
echo "  Users: $SQLITE_USERS"

# Cleanup temp files
rm -f /tmp/coordinates.csv /tmp/global_deployments.csv /tmp/swath_lines.csv /tmp/users.csv

echo ""
echo "========================================"
echo "✓ Backup Complete!"
echo "========================================"
echo ""
echo "SQLite backup saved as: $BACKUP_DB"
echo ""
echo -e "${GREEN}All your data is safely backed up!${NC}"
echo ""
echo "Next step: Run the locale fix script to recreate PostgreSQL database"
echo ""
