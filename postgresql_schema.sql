-- PostgreSQL schema for Swath Movers application
-- Migration from SQLite to PostgreSQL

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Coordinates table (base shotpoint data)
CREATE TABLE coordinates (
    line INTEGER NOT NULL,
    shotpoint INTEGER NOT NULL,
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    type TEXT,
    _id TEXT PRIMARY KEY
);

-- Create spatial index for coordinates (if using PostGIS later)
CREATE INDEX idx_coordinates_line_shot ON coordinates (line, shotpoint);
CREATE INDEX idx_coordinates_location ON coordinates (latitude, longitude);

-- Users table
CREATE TABLE users (
    username TEXT PRIMARY KEY,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- Note: created_at and updated_at are nullable to allow migration from SQLite

-- Global deployments table
CREATE TABLE global_deployments (
    line INTEGER NOT NULL,
    shotpoint INTEGER NOT NULL,
    deployment_type TEXT NOT NULL,
    username TEXT,
    timestamp TIMESTAMP NOT NULL,
    PRIMARY KEY (line, shotpoint)
);

-- Create indexes for global deployments
CREATE INDEX idx_global_deployments_type ON global_deployments (deployment_type);
CREATE INDEX idx_global_deployments_user ON global_deployments (username);
CREATE INDEX idx_global_deployments_timestamp ON global_deployments (timestamp);

-- Swath lines cache table (for map performance)
CREATE TABLE swath_lines (
    swath TEXT NOT NULL,
    line INTEGER NOT NULL,
    first_shot INTEGER NOT NULL,
    last_shot INTEGER NOT NULL,
    lon1 DECIMAL(11, 8) NOT NULL,
    lat1 DECIMAL(10, 8) NOT NULL,
    lon2 DECIMAL(11, 8) NOT NULL,
    lat2 DECIMAL(10, 8) NOT NULL,
    type TEXT,
    PRIMARY KEY (swath, line)
);

-- Swath boxes cache table
CREATE TABLE swath_boxes (
    swath TEXT PRIMARY KEY,
    coordinates TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Swath edges table
CREATE TABLE swath_edges (
    swath TEXT PRIMARY KEY,
    edge_coordinates TEXT,
    rotation_angle DECIMAL(10, 6),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Individual swath deployment tables (1-8)
-- These will be created dynamically as needed, but here's the template:
-- CREATE TABLE swath_1 (
--     line INTEGER NOT NULL,
--     shotpoint INTEGER NOT NULL,
--     deployment_type TEXT NOT NULL,
--     username TEXT,
--     timestamp TIMESTAMP NOT NULL,
--     PRIMARY KEY (line, shotpoint)
-- );

-- Function to create swath table dynamically
CREATE OR REPLACE FUNCTION create_swath_table(swath_name TEXT)
RETURNS VOID AS $$
BEGIN
    EXECUTE format('
        CREATE TABLE IF NOT EXISTS %I (
            line INTEGER NOT NULL,
            shotpoint INTEGER NOT NULL,
            deployment_type TEXT NOT NULL,
            username TEXT,
            timestamp TIMESTAMP NOT NULL,
            PRIMARY KEY (line, shotpoint)
        )', 'swath_' || swath_name);

    -- Create indexes for the new swath table
    EXECUTE format('CREATE INDEX IF NOT EXISTS idx_%I_type ON %I (deployment_type)', 'swath_' || swath_name, 'swath_' || swath_name);
    EXECUTE format('CREATE INDEX IF NOT EXISTS idx_%I_user ON %I (username)', 'swath_' || swath_name, 'swath_' || swath_name);
    EXECUTE format('CREATE INDEX IF NOT EXISTS idx_%I_timestamp ON %I (timestamp)', 'swath_' || swath_name, 'swath_' || swath_name);
END;
$$ LANGUAGE plpgsql;

-- Create swath tables for existing swaths (1-8)
SELECT create_swath_table('1');
SELECT create_swath_table('2');
SELECT create_swath_table('3');
SELECT create_swath_table('4');
SELECT create_swath_table('5');
SELECT create_swath_table('6');
SELECT create_swath_table('7');
SELECT create_swath_table('8');

-- Create a view for easier querying of all deployment data
CREATE OR REPLACE VIEW all_deployments AS
SELECT 'global' as source, line, shotpoint, deployment_type, username, timestamp
FROM global_deployments
UNION ALL
SELECT 'swath_1' as source, line, shotpoint, deployment_type, username, timestamp
FROM swath_1
UNION ALL
SELECT 'swath_2' as source, line, shotpoint, deployment_type, username, timestamp
FROM swath_2
UNION ALL
SELECT 'swath_3' as source, line, shotpoint, deployment_type, username, timestamp
FROM swath_3
UNION ALL
SELECT 'swath_4' as source, line, shotpoint, deployment_type, username, timestamp
FROM swath_4
UNION ALL
SELECT 'swath_5' as source, line, shotpoint, deployment_type, username, timestamp
FROM swath_5
UNION ALL
SELECT 'swath_6' as source, line, shotpoint, deployment_type, username, timestamp
FROM swath_6
UNION ALL
SELECT 'swath_7' as source, line, shotpoint, deployment_type, username, timestamp
FROM swath_7
UNION ALL
SELECT 'swath_8' as source, line, shotpoint, deployment_type, username, timestamp
FROM swath_8;
