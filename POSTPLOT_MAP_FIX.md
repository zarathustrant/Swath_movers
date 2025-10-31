# Post Plot Map - Receiver Lines Fix

## Changes Made

### Problem
The post plot map was loading but receiver lines weren't showing up.

### Root Cause
The JavaScript code was using a different approach than the working deployment map (map.html) to process the `/geojson_lines` data structure.

### Solution Implemented

**File Modified**: `/home/aerys/Documents/ANTAN3D/postplot/templates/postplot_map.html`

#### Change 1: Enhanced Receiver Lines Layer (Lines 319-350)
**Added tooltip functionality** to show line information on hover:

```javascript
onEachFeature: function(feature, layer) {
    // Add tooltip with line info
    if (feature.properties.line) {
        layer.bindTooltip(
            `Line ${feature.properties.line}`,
            { permanent: false, direction: 'center', className: 'line-label' }
        );
    }
    // ... existing label code ...
}
```

**Benefit**: Users can now hover over lines to see the line number.

#### Change 2: Improved loadMapData() Function (Lines 386-471)

**Key improvements**:

1. **Better data structure handling**:
   - Changed from `selectedSwaths.forEach()` to `Object.entries(data.swaths).forEach()`
   - This matches the working approach in map.html
   - Properly iterates through all swaths returned by the backend

2. **Added comprehensive logging**:
   ```javascript
   console.log('Loading map data for swaths:', selectedSwaths);
   console.log('Received geojson_lines data:', data);
   console.log(`Processing ${swathName}, features:`, swathData.features.length);
   console.log(`Found ${receiverFeatures.length} receiver lines in ${swathName}`);
   console.log(`Total receiver lines added: ${totalReceiverLines}`);
   ```

3. **Enhanced error handling**:
   - Checks `response.ok` before parsing JSON
   - Validates `data.swaths` exists
   - Shows user-friendly alerts on errors
   - Detailed console error messages

4. **Proper swath filtering**:
   ```javascript
   const swathNum = parseInt(swathName.split('_')[1]);
   if (!selectedSwaths.includes(swathNum)) {
       return; // Skip unselected swaths
   }
   ```

5. **Better feature filtering**:
   ```javascript
   const receiverFeatures = swathData.features.filter(f => {
       return f.geometry.type === 'LineString' &&
              (f.properties.type === 'R' || f.properties.type === 'S/R');
   });
   ```

## How to Test

### Step 1: Restart the Service
```bash
sudo systemctl restart swath-movers.service
```

### Step 2: Clear Browser Cache
- Press `Ctrl+Shift+R` (hard refresh) or
- Press `F12` → Network tab → Check "Disable cache"

### Step 3: Open the Post Plot Map
Navigate to:
```
http://localhost:8080/postplot/map
```

### Step 4: Check Browser Console
Press `F12` to open Developer Tools, then check the Console tab for:

**Expected console output**:
```
Loading map data for swaths: [1, 2, 3, 4, 5, 6, 7, 8]
Received geojson_lines data: {swaths: {...}}
Processing swath_1, features: 15
Found 15 receiver lines in swath_1
Processing swath_2, features: 14
Found 14 receiver lines in swath_2
...
Total receiver lines added: 123
Received source points data: {type: "FeatureCollection", features: []}
```

**What to look for**:
- ✅ "Received geojson_lines data" shows swaths object
- ✅ "Processing swath_X" messages for each swath
- ✅ "Found N receiver lines" with N > 0
- ✅ "Total receiver lines added" with total > 0
- ✅ Blue lines appear on the map
- ✅ Receiver count in stats panel shows > 0

### Step 5: Verify Functionality
- [ ] Blue receiver lines visible on map
- [ ] Hover over lines to see line number tooltip
- [ ] Swath filter checkboxes work
- [ ] Statistics panel shows correct receiver line count
- [ ] No errors in console (ignore source map warnings)

## Debugging

If lines still don't show:

### Check 1: Service Restarted?
```bash
systemctl status swath-movers.service
# Should show "active (running)"

journalctl -u swath-movers.service -n 20
# Should show recent startup logs, no errors
```

### Check 2: /geojson_lines Endpoint Working?
Open in browser or run:
```bash
curl http://localhost:8080/geojson_lines | python3 -m json.tool | head -50
```

Should return JSON with structure:
```json
{
  "swaths": {
    "swath_1": {
      "type": "FeatureCollection",
      "features": [...]
    },
    ...
  }
}
```

### Check 3: Browser Console Logs
Look for specific error messages:
- "No swaths property in data" → Backend issue
- "HTTP error! status: 404" → Route not found (service not restarted)
- "HTTP error! status: 500" → Server error (check logs)

### Check 4: Network Tab
In DevTools → Network tab:
- Find `/geojson_lines` request
- Should be Status: 200
- Preview tab should show swaths data
- Response should not be empty

## Expected Behavior After Fix

### Map Display
- **Blue lines**: Receiver lines from coordinates table
- **Line numbers**: Visible as labels on the lines
- **Tooltips**: Hover over lines to see line number
- **Statistics**: "Receiver Lines: 123" (or whatever count)

### Console Logs
Detailed logging showing:
- Which swaths are being processed
- How many features per swath
- How many receiver lines found
- Total lines added to map

### Error Handling
- Clear error messages in console
- User-friendly alerts on failures
- Graceful handling of missing data

## Technical Details

### Data Flow
1. User loads `/postplot/map`
2. `loadMapData()` called with all swaths
3. Fetches `/geojson_lines` from backend
4. Iterates through `data.swaths` object
5. For each swath:
   - Checks if selected
   - Filters to receiver LineStrings only
   - Adds to receiver lines layer
6. Updates statistics panel
7. Fetches `/postplot/geojson/source_points` (might be empty initially)

### Why This Approach Works
- Matches the proven approach from map.html
- Uses `Object.entries()` to iterate swaths
- Properly filters by geometry type AND property type
- Handles missing data gracefully
- Provides detailed debugging information

## Common Issues & Solutions

### Issue: "Failed to load receiver lines: HTTP error! status: 404"
**Solution**: Service not restarted. Run `sudo systemctl restart swath-movers.service`

### Issue: Lines show but no source points
**Solution**: This is normal if you haven't uploaded source data yet. Go to `/postplot/upload` to upload source CSVs.

### Issue: Console shows "Found 0 receiver lines in swath_X"
**Solution**:
- Check if coordinates table has type='R' records
- Check if swath CSV files are present
- Verify `/geojson_lines` returns data for that swath

### Issue: Source map error about leaflet.js.map
**Solution**: Ignore this - it's a harmless DevTools warning, not an actual error.

## Rollback

If issues persist, the original code can be restored from git:
```bash
git diff postplot/templates/postplot_map.html
# Review changes

git checkout postplot/templates/postplot_map.html
# Restore original if needed
```

---

## Summary

The fix improves the post plot map's receiver line loading by:
1. ✅ Using the proven data iteration approach from map.html
2. ✅ Adding comprehensive console logging for debugging
3. ✅ Improving error handling and user feedback
4. ✅ Adding tooltips for better UX
5. ✅ Properly filtering features by geometry and property types

After restarting the service and clearing browser cache, receiver lines should now display correctly on the post plot map.
