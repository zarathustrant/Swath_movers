# Post Plot Acquisition Map - Implementation Complete

## Overview

The Post Plot Acquisition Map feature has been successfully implemented as a self-contained Flask Blueprint module. This feature allows you to track source shot acquisition status with a two-stage CSV upload system.

## What Was Implemented

### Directory Structure
```
postplot/
├── __init__.py              # Blueprint registration
├── routes.py                # All routes (7 endpoints)
├── models.py                # Database operations (PostPlotDB class)
├── utils.py                 # CSV validation helpers
├── templates/
│   ├── postplot_map.html   # Interactive Leaflet map
│   └── upload_postplot.html # Upload management interface
└── schema/
    └── postplot_schema.sql  # Database schema (8 tables)
```

### Database Tables Created

8 new tables were created successfully:
- `post_plot_swath_1_sources` through `post_plot_swath_8_sources`

Each table has the following structure:
- `line` (INTEGER) - Line number
- `shotpoint` (INTEGER) - Shotpoint number
- `latitude` (DECIMAL) - Latitude coordinate
- `longitude` (DECIMAL) - Longitude coordinate
- `is_acquired` (BOOLEAN) - Acquisition status (default: FALSE = RED, TRUE = GREEN)
- `uploaded_by` (TEXT) - Username who uploaded the source data
- `uploaded_at` (TIMESTAMP) - When source data was uploaded
- `acquired_at` (TIMESTAMP) - When marked as acquired

Primary Key: (line, shotpoint)
Indexes: line, is_acquired

### Routes Available

All routes are under the `/postplot` prefix:

1. **GET /postplot/map** - Interactive map view
2. **GET /postplot/upload** - Upload management page
3. **POST /postplot/upload_source** - Upload source CSV (SwathN_Source.csv)
4. **POST /postplot/upload_acquisition** - Upload acquisition CSV (SwathN_Acquisition.csv)
5. **GET /postplot/geojson/source_points?swaths=1,2,3** - GeoJSON data endpoint
6. **POST /postplot/clear_swath** - Clear all data for a swath
7. **GET /postplot/stats/<swath_num>** - Get statistics for a swath

## How to Use

### Step 1: Access the Application

Your application is running on **port 8080**:
```
http://your-server-ip:8080/postplot/map
http://your-server-ip:8080/postplot/upload
```

If accessing locally:
```
http://localhost:8080/postplot/map
http://localhost:8080/postplot/upload
```

### Step 2: Upload Source Data

1. Navigate to **http://localhost:8080/postplot/upload**
2. Click "Upload Source Swath Data" section
3. Prepare CSV files with this format:

**File naming**: `Swath1_Source.csv`, `Swath2_Source.csv`, ... `Swath8_Source.csv`

**CSV format**:
```csv
Line,shotpoint,lat,lon
5000,100,5.123456,7.654321
5000,101,5.123457,7.654322
5000,102,5.123458,7.654323
5001,100,5.124456,7.655321
```

4. Select your CSV file and click "Upload Source Data"
5. All source points will appear as **RED markers** on the map

### Step 3: Upload Acquisition Data

1. On the same upload page, go to "Upload Acquisition Data" section
2. Prepare acquisition CSV files:

**File naming**: `Swath1_Acquisition.csv`, `Swath2_Acquisition.csv`, ... `Swath8_Acquisition.csv`

**CSV format** (one shotpoint per row):
```csv
Line,Station
5000,100
5000,101
5001,100
```

3. Select your CSV file and click "Upload Acquisition Data"
4. Acquired shots will turn **GREEN** on the map

### Step 4: View the Map

1. Navigate to **http://localhost:8080/postplot/map**
2. You'll see:
   - **Blue lines**: Receiver lines (from existing coordinates data)
   - **Red dots**: Source points not yet acquired
   - **Green dots**: Source points that have been acquired
3. Use the swath checkboxes to filter which swaths to display
4. Click on any point to see details (line, shotpoint, status, acquisition time)

## Features

### Map Features
- ✅ Interactive Leaflet map with OpenTopo base layer
- ✅ Receiver lines displayed in blue
- ✅ Source points: Red (not acquired) / Green (acquired)
- ✅ Swath filtering with checkboxes (multi-select)
- ✅ Real-time statistics panel (total/acquired/pending)
- ✅ Click on points for detailed popup information
- ✅ Line number labels on receiver lines
- ✅ Canvas renderer for high performance with large datasets

### Upload Features
- ✅ Two-stage upload: Source data → Acquisition data
- ✅ CSV validation with detailed error messages
- ✅ File naming validation (SwathN_Source.csv, SwathN_Acquisition.csv)
- ✅ Duplicate detection
- ✅ Coordinate range validation
- ✅ Per-swath statistics table with progress bars
- ✅ Clear data functionality (per swath)
- ✅ Auto-reload after successful upload

### Data Management
- ✅ Replace source data (clears existing, inserts new)
- ✅ Acquisition updates (marks existing shots as acquired)
- ✅ Tracks who uploaded and when
- ✅ Warns if acquisition data doesn't match source data

## Integration with Main App

The post plot module was integrated into app.py with just **2 lines of code**:

```python
# Register post plot blueprint
from postplot import postplot_bp
app.register_blueprint(postplot_bp, url_prefix='/postplot')
```

This keeps the main application clean while adding complete new functionality.

## CSV Format Examples

### Source CSV (SwathN_Source.csv)

Required columns: `Line, shotpoint, lat, lon`

```csv
Line,shotpoint,lat,lon
5000,100,5.12345678,7.65432101
5000,101,5.12345679,7.65432102
5000,102,5.12345680,7.65432103
5001,100,5.12346678,7.65433101
5001,101,5.12346679,7.65433102
```

**Rules**:
- All columns must be numeric
- No missing values
- No duplicate (Line, shotpoint) pairs
- Latitude: -90 to 90
- Longitude: -180 to 180

### Acquisition CSV (SwathN_Acquisition.csv)

Required columns: `Line, Station`

```csv
Line,Station
5000,100
5000,101
5000,102
```

**Rules**:
- All columns must be integers
- One shotpoint per row (Station = shotpoint number)
- Can upload multiple times (idempotent - safe to re-upload)
- Only updates shots that exist in source data

## Restarting the Service

The application needs to be restarted to load the new blueprint. You have two options:

### Option 1: Reload Gunicorn (Graceful)
```bash
sudo systemctl reload gunicorn
```

### Option 2: Restart Gunicorn (Full restart)
```bash
sudo systemctl restart gunicorn
```

### Option 3: Manual restart via process (if no systemd service)
```bash
pkill -HUP gunicorn  # Send HUP signal to reload workers
```

## Verification

### Check if Tables Exist
```bash
PGPASSWORD='aerys123' psql -U aerys -d swath_movers -c "SELECT tablename FROM pg_tables WHERE tablename LIKE 'post_plot_%' ORDER BY tablename;"
```

Expected output:
```
         tablename
---------------------------
 post_plot_swath_1_sources
 post_plot_swath_2_sources
 post_plot_swath_3_sources
 post_plot_swath_4_sources
 post_plot_swath_5_sources
 post_plot_swath_6_sources
 post_plot_swath_7_sources
 post_plot_swath_8_sources
(8 rows)
```

### Test Blueprint Import
```bash
cd /home/aerys/Documents/ANTAN3D
/home/aerys/Documents/ANTAN3D/swathenv/bin/python3 -c "import app; print('✓ App loaded successfully')"
```

### Check Application Logs
```bash
tail -f /home/aerys/Documents/ANTAN3D/logs/gunicorn-error.log
```

Look for:
- "Swath Movers application starting..."
- "Worker initialized successfully"
- No import errors related to postplot

## Troubleshooting

### Issue: "Module postplot not found"
**Solution**: Make sure you're in the correct directory and the postplot folder exists:
```bash
ls -la /home/aerys/Documents/ANTAN3D/postplot/
```

### Issue: Routes return 404
**Solution**: Restart Gunicorn to load the new blueprint:
```bash
sudo systemctl restart gunicorn
```

### Issue: CSV upload fails with "Invalid filename"
**Solution**: Ensure file is named exactly `Swath1_Source.csv` or `Swath1_Acquisition.csv` (case-insensitive, numbers 1-8)

### Issue: Acquisition data doesn't turn points green
**Solution**:
1. Check that source data was uploaded first
2. Verify (Line, Station) pairs exist in source table
3. Check upload result message for "not found" count

### Issue: Map doesn't show receiver lines
**Solution**: Receiver lines come from existing coordinates table. Make sure:
1. The `/geojson_lines` endpoint is working
2. Coordinates exist in the database with type='R' or 'S/R'
3. Swaths are selected in the checkbox filter

## Statistics Queries

### Check Source Points Count
```sql
SELECT
    'Swath 1' as swath, COUNT(*) as total,
    SUM(CASE WHEN is_acquired THEN 1 ELSE 0 END) as acquired
FROM post_plot_swath_1_sources
UNION ALL
SELECT
    'Swath 2', COUNT(*),
    SUM(CASE WHEN is_acquired THEN 1 ELSE 0 END)
FROM post_plot_swath_2_sources;
-- Continue for swaths 3-8
```

### View Recent Uploads
```sql
SELECT line, shotpoint, is_acquired, uploaded_by, uploaded_at, acquired_at
FROM post_plot_swath_1_sources
ORDER BY uploaded_at DESC
LIMIT 10;
```

## Next Steps

1. **Restart Gunicorn** (if not done already):
   ```bash
   sudo systemctl restart gunicorn
   ```

2. **Access the map**:
   ```
   http://localhost:8080/postplot/map
   ```

3. **Upload test data**:
   - Create a small test CSV (Swath1_Source.csv)
   - Upload via http://localhost:8080/postplot/upload
   - Verify red markers appear on map

4. **Test acquisition**:
   - Create acquisition CSV (Swath1_Acquisition.csv)
   - Upload it
   - Verify markers turn green

5. **Add navigation links** (optional):
   - Edit templates/map.html to add link to `/postplot/map`
   - Edit postplot/templates/postplot_map.html to add link to `/map`

## Architecture Benefits

✅ **Self-contained**: All post plot code in one folder
✅ **No clutter**: Main app.py only +3 lines
✅ **Easy to remove**: Delete folder + 3 lines from app.py
✅ **Reusable**: Can be moved to other Flask projects
✅ **Testable**: Can test blueprint independently
✅ **Isolated**: No risk to existing routes or telegram bot

## Files Created

Total: 7 new files

1. `postplot/__init__.py` - Blueprint registration (18 lines)
2. `postplot/routes.py` - Flask routes (220 lines)
3. `postplot/models.py` - Database operations (240 lines)
4. `postplot/utils.py` - CSV validation (180 lines)
5. `postplot/templates/postplot_map.html` - Map interface (300 lines)
6. `postplot/templates/upload_postplot.html` - Upload page (280 lines)
7. `postplot/schema/postplot_schema.sql` - Database schema (65 lines)

**Total**: ~1,300 lines of new code

## Files Modified

1. `app.py` - Added 3 lines to register blueprint

## No Changes To

- Telegram bot files (untouched)
- Existing templates (untouched)
- Existing routes (untouched)
- Systemd services (untouched)

---

## Summary

The Post Plot Acquisition Map is now fully implemented and ready to use! The feature allows you to:

- Upload source shotpoint data per swath
- Track acquisition status (red → green)
- Visualize on an interactive map with receiver lines
- Filter by swath
- View real-time statistics
- Manage data (upload, clear, re-upload)

All implemented as a clean, self-contained Flask Blueprint that doesn't interfere with your existing application or telegram bot services.

**To get started**: Restart Gunicorn and visit http://localhost:8080/postplot/map

Enjoy! 🎉
