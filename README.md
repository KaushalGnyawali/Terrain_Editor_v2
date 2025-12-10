# Terrain Editor Pro — Quick Start

This repository contains the Streamlit application `terrain_editor.py` for interactive
design of berms, ditches, swales and polygonal basins on local DEMs. The app lets you
draw features on a map, edit cross-sections and compute volumes using multiple methods.

See also: `PROJECT_SUMMARY.md` and `CALCULATION_METHODS.md` for high-level and
calculation-specific documentation.

## Install

Open PowerShell and run:

```powershell
pip install -r requirements.txt
```

If you prefer, install manually:

```powershell
pip install streamlit rasterio numpy pandas folium streamlit-folium shapely plotly pyproj
```

Optional (for shapefile handling):

```powershell
pip install geopandas fiona
```

## Run the app

```powershell
streamlit run terrain_editor.py
```

The app will open in your browser at `http://localhost:8501`.

## Quickstart — folder structure

Place your input files in the `Data/` folder alongside `terrain_editor.py`:

```
project_root/
├─ terrain_editor.py
└─ Data/
   ├─ dem.tif          # required (GeoTIFF)
   ├─ profile.*        # optional: profile.shp (zipped) or profile.kml
   └─ basin/           # optional supporting files
```

## High-level workflow

1. Start the app and choose Design Mode: `Profile Line (Berm/Ditch)` or `Polygon Basin`.
2. Load or upload a DEM (GeoTIFF). If available, the app will auto-load `Data/dem.tif`.
3. Draw or upload a profile line (polyline) for corridor designs or draw a polygon for basin designs.
4. Configure template parameters (berm/ditch/swale) or basin depth/side slope/longitudinal slope.
5. Inspect cross-sections and profile plots, adjust stations/elevations as needed.
6. Calculate volumes using the provided methods and export vector outputs (Shapefile/KML/GeoJSON) or the modified DEM.

## Loading data

- DEM: place `dem.tif` in `Data/` or upload via the app (GeoTIFF required).
- Profile (optional): upload a Shapefile ZIP or KML (polyline). The app will attempt to detect CRS and transform to lat/lon.
- Basin polygon (optional): upload a Shapefile ZIP or KML (polygon) or draw on the map.

## Exporting results

On the map panels and download sections you can export:
- Shapefile (ZIP), KML, GeoJSON for profile lines, basin polygons, and channel lines.
- Modified DEM export available from the Basin Design workflow (GeoTIFF).

## Links
- Calculation details and worked examples: `CALCULATION_METHODS.md`
- Project summary and features: `PROJECT_SUMMARY.md`

## Troubleshooting
- If the app cannot find a DEM, ensure `Data/dem.tif` exists and the working directory is the project root.
- For shapefiles install `geopandas` and `fiona` (optional). If shapefile CRS is not geographic the app attempts to reproject to the analysis CRS.

- Updates automatically with longitudinal slope

🗺️ **Basin Plan View Map**
- Outer polygon (red) - basin boundary
- Inner polygon (blue) - basin bottom projection
- Channel line (green) - flow path (if drawn)
- S0 and S1 station markers (yellow with black borders)
- Auto-zoomed to polygon outer boundary extent

🔄 **Apply Basin to Terrain**
- Click "Compute Basin Cut" to generate modified DEM
- Automatically calculates DEM-based volume with uncertainty analysis
- Export modified DEM at custom resolution

✅ **Result**: Complete basin design visualization with accurate volume estimates

---

### 6. EXPORT - Download Modified DEM

💾 **Configure export**
```
Target Resolution: [2.0] m  ← Choose resolution (0.1-100m)
Current: 1.0 m              ← Original resolution
```

🔄 **Generate modified DEM**
1. Click "🔄 Compute Modified DEM"
2. Wait for processing
3. Click "💾 Download Modified DEM"

📦 **Output**
- File: `terrain_modified_2m.tif`
- Format: GeoTIFF
- CRS: Same as input
- Resolution: As specified

✅ **Result**: Professional GeoTIFF exported!

---

## 🎓 EXAMPLES

### Example 1: Debris Flow Berm (Profile Mode)

**Scenario**: Design 200m berm for debris flow protection

**Step-by-Step:**
1. **Design Mode**: Select "Profile Line (Berm/Ditch)"
2. **Input Data**: Draw 200m line from ridge to valley
3. **Cross-Section Setup**:
   ```
   Stations: 40
   Slope: -2.0%
   Template: Berm + Ditch
   Berm Top: 4m
   Berm Slope: 2:1
   Ditch Bottom: 2m
   Ditch Depth: 1.5m
   Ditch Slope: 3:1
   Ditch Side: Left
   Influence: 20m
   ```
4. **Browse**: Check stations 0, 10, 20, 30, 39
5. **Edit**: 
   - Set gradient slopes at key stations (e.g., -2% at station 0)
   - Adjust individual station elevations using slider or table
   - Only selected station can be edited in table
6. **Profile**: Verify continuous design with gradients applied
7. **Export**: Download at 2m resolution

**Time**: ~5 minutes  
**Result**: Professional terrain modification

---

### Example 2: Debris Storage Basin (Basin Mode)

**Scenario**: Design sediment retention basin

**Step-by-Step:**
1. **Design Mode**: Select "Polygon Basin"
2. **Input Data**: 
   - Draw basin polygon boundary (map auto-zooms to polygon)
   - Optionally draw channel line (green polyline) - S0/S1 markers appear automatically
3. **Basin Design Setup**:
   ```
   Basin Depth: 3.0m
   Side Slope: 1.5 H:1V
   Longitudinal Slope: 2.0%
   ```
4. **Review Metrics**: 
   - Geometric Volume: 4,934 m³
   - DEM Difference Volume: 4,856 ± 124 m³ (after computing basin cut)
   - Outer/Inner areas displayed
5. **Compute Basin Cut**: Click "Compute Basin Cut" button
   - Generates modified DEM
   - Calculates DEM-based volume with uncertainty analysis
   - Shows volume with mean ± std dev and [min, max] range
6. **View Profile**: Verify longitudinal profile with S0/S1 markers
7. **View Map**: Basin Plan View shows polygon, channel, and S0/S1 stations
8. **Export**: Download modified DEM at custom resolution

**Time**: ~5 minutes  
**Result**: Complete basin design with accurate volume calculations (geometric and DEM-based with uncertainty)

---

## 💡 TIPS & TRICKS

### Design Mode
- ✅ **Profile Line Mode**: Linear corridor design (berm/ditch/swale)
- ✅ **Basin Mode**: Polygon-based debris storage basin design

### Profile Line (Profile Mode)
- ✅ Draw in any direction
- ✅ System auto-corrects to upstream→downstream
- ✅ Station 0 = always upstream (high)

### Basin Polygon (Basin Mode)
- ✅ Draw closed polygon for basin boundary
- ✅ Optional channel line for flow path definition
- ✅ First vertex = upstream, minimum elevation = downstream

### Number of Stations
- Few (10-20): Quick, rough design
- Medium (50-100): Standard projects
- Many (200-500): Detailed, precise work

### Vertical Exaggeration
- VE=1.0: True scale (flat terrain)
- VE=2.0-3.0: Good for most terrain
- VE=5.0-10.0: Subtle slopes visible

### Elevation Editing
- **Gradient Slope**: Set slope relative to horizontal for downstream stations
  - 0% = flat line (same elevation as gradient station)
  - Positive % = rising slope (downstream higher)
  - Negative % = falling slope (downstream lower)
  - Slope is relative to horizontal, not previous station
- **Slider**: Quick adjustments (±10m range)
- **Table**: Precise values (only selected station editable)
- All methods update immediately and work together seamlessly
- Gradient slopes are recalculated when station elevations are edited

### Export Resolution
- Same as input: No resampling
- Higher (e.g., 5m): Smaller file
- Lower (e.g., 0.5m): More detail

### Basin Design
- Longitudinal slope: Positive = downstream deeper, negative = upstream deeper
- Channel line: Optional - defines exact flow path for slope application
  - Channel persists after first draw (no app reset)
  - S0 (upstream) and S1 (downstream) markers shown on both Input Data and Basin Design maps
- Volume calculation: 
  - Geometric volume: From designed geometry formulas
  - DEM difference volume: From raster elevation subtraction with uncertainty analysis
  - Uncertainty reported as mean ± std dev with [min, max] range across cell sizes (0.5-5 m)
- Inner area: Updates based on average depth considering longitudinal slope
- Map auto-zoom: Basin Plan View automatically zooms to polygon outer boundary

---

## ⚠️ COMMON ISSUES

### "DEM file not found"
**Solution**: Put `dem.tif` in `Data/` folder

### "Draw profile line first"
**Solution**: Go to Map tab, use polyline tool

### "VE slider not updating"
**Solution**: Move slider, wait 1 second, should update

### "Next/Prev buttons not working"
**Solution**: Check you have drawn profile and set up stations

### "Edits not in exported DEM"
**Solution**: Click "Compute Modified DEM" before downloading

---

## 📚 KEY CONCEPTS

### Upstream vs Downstream
- **Upstream**: High elevation (Station 0)
- **Downstream**: Low elevation (Station N)
- Profile always goes upstream→downstream

### Cross-Section
- **Perpendicular**: 90° to profile line
- **Offset**: Distance from centreline
  - Negative (-): Right side
  - Positive (+): Left side

### Influence Width
- Half-width of corridor
- 20m influence = 40m total width
- ±20m from centreline

### Template Types
- **Berm+Ditch**: Raised berm with channel (left or right side)
- **Swale**: Sunken drainage channel
- **Basin**: Polygon-based debris storage basin with varying depth

### Volume Calculation Methods (Basin Mode)
- **Geometric Volume**: Calculated using geometric formulas based on basin parameters (outer polygon area, inner polygon area, depth, and slopes). Assumes perfect geometric shapes.
- **DEM Difference Volume**: Calculated by differencing original and modified DEMs, clipping both to basin polygon, and summing positive differences (excavation) × cell area. Includes uncertainty analysis across cell sizes (0.5-5 m). Reported as mean ± standard deviation with [min, max] range.

### Operation Mode
- **Cut+Fill**: Both operations
- **Fill Only**: Only raise terrain
- **Cut Only**: Only lower terrain

---

## 🆘 SUPPORT

**All features working?**
✓ Profile from user line
✓ Upstream→downstream
✓ VE slider
✓ Next/Prev buttons
✓ Elevation editing
✓ Custom resolution export

**Still having issues?**
Check CHANGES_v7.0.md for technical details

---

**STATUS**: Production Ready v8.0  
**DATE**: December 2025  
**READY**: For geotechnical research and professional use  
**FEATURES**: 
- Profile Line Design (Berm/Ditch/Swale)
- Polygon Basin Design with dual volume calculation methods
- DEM-based volume with uncertainty analysis (cell-size sensitivity)
- Longitudinal Slope support
- Channel Flow Path with S0/S1 station markers
- Improved UI with modern styling and responsive layout
- Auto-zoom functionality for maps
