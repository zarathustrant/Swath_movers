-- Coordinate Transformation Table
-- Stores polynomial transformation coefficients for converting XY (UTM) to Lat/Lon

CREATE TABLE IF NOT EXISTS coordinate_transforms (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    description TEXT,

    -- 3rd order polynomial coefficients (10 terms each)
    -- lon = a₀ + a₁X + a₂Y + a₃X² + a₄XY + a₅Y² + a₆X³ + a₇X²Y + a₈XY² + a₉Y³
    coefficients_lon JSONB NOT NULL,  -- Array: [a₀, a₁, a₂, a₃, a₄, a₅, a₆, a₇, a₈, a₉]

    -- lat = b₀ + b₁X + b₂Y + b₃X² + b₄XY + b₅Y² + b₆X³ + b₇X²Y + b₈XY² + b₉Y³
    coefficients_lat JSONB NOT NULL,  -- Array: [b₀, b₁, b₂, b₃, b₄, b₅, b₆, b₇, b₈, b₉]

    -- Accuracy metrics
    rmse_lon DECIMAL(12, 10),  -- Root Mean Square Error in longitude (degrees)
    rmse_lat DECIMAL(12, 10),  -- Root Mean Square Error in latitude (degrees)
    rmse_meters DECIMAL(10, 2), -- Approximate RMSE in meters

    -- Metadata
    control_point_count INTEGER,  -- Number of control points used for calibration
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT valid_coefficients CHECK (
        jsonb_array_length(coefficients_lon) = 10 AND
        jsonb_array_length(coefficients_lat) = 10
    )
);

-- Index for fast lookup by name
CREATE INDEX IF NOT EXISTS idx_transforms_name ON coordinate_transforms(name);

-- Comment
COMMENT ON TABLE coordinate_transforms IS 'Stores 3rd-order polynomial transformation coefficients for converting UTM (X,Y) coordinates to Lat/Lon';
COMMENT ON COLUMN coordinate_transforms.coefficients_lon IS 'Longitude polynomial coefficients [a₀, a₁, a₂, a₃, a₄, a₅, a₆, a₇, a₈, a₉]';
COMMENT ON COLUMN coordinate_transforms.coefficients_lat IS 'Latitude polynomial coefficients [b₀, b₁, b₂, b₃, b₄, b₅, b₆, b₇, b₈, b₉]';
