-- Post Plot Source Tables for Swaths 1-8
-- Tracks planned source shots and their acquisition status

-- Helper function to create post plot tables dynamically
CREATE OR REPLACE FUNCTION create_post_plot_swath_table(swath_num INTEGER)
RETURNS void AS $$
BEGIN
    EXECUTE format('
        CREATE TABLE IF NOT EXISTS post_plot_swath_%s_sources (
            line INTEGER NOT NULL,
            shotpoint INTEGER NOT NULL,
            latitude DECIMAL(10, 8) NOT NULL,
            longitude DECIMAL(11, 8) NOT NULL,
            is_acquired BOOLEAN DEFAULT FALSE,
            uploaded_by TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            acquired_at TIMESTAMP,
            PRIMARY KEY (line, shotpoint)
        )', swath_num);

    EXECUTE format('CREATE INDEX IF NOT EXISTS idx_post_plot_swath_%s_line
                    ON post_plot_swath_%s_sources(line)', swath_num, swath_num);
    EXECUTE format('CREATE INDEX IF NOT EXISTS idx_post_plot_swath_%s_acquired
                    ON post_plot_swath_%s_sources(is_acquired)', swath_num, swath_num);

    RAISE NOTICE 'Created post_plot_swath_%_sources table', swath_num;
END;
$$ LANGUAGE plpgsql;

-- Create all 8 swath tables
DO $$
BEGIN
    FOR i IN 1..8 LOOP
        PERFORM create_post_plot_swath_table(i);
    END LOOP;
END $$;

-- Grant permissions to user
DO $$
BEGIN
    FOR i IN 1..8 LOOP
        EXECUTE format('GRANT ALL PRIVILEGES ON TABLE post_plot_swath_%s_sources TO aerys', i);
    END LOOP;
END $$;

-- Verification query - show all created tables
SELECT
    tablename,
    schemaname
FROM pg_tables
WHERE tablename LIKE 'post_plot_swath_%_sources'
ORDER BY tablename;

-- Show table structures
DO $$
DECLARE
    tbl TEXT;
BEGIN
    FOR i IN 1..8 LOOP
        tbl := 'post_plot_swath_' || i || '_sources';
        RAISE NOTICE 'Table: %', tbl;
    END LOOP;
END $$;
