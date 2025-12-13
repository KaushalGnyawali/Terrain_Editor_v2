# Terrain Editor Pro v25 — Complete Guide

This repository contains the Streamlit application `terrain_editor.py` for interactive
design of berms, ditches, swales and polygonal basins on local DEMs. The app lets you
draw features on a map, edit cross-sections and compute volumes using multiple methods.

See also: `PROJECT_SUMMARY.md` and `VOLUME_CALCULATION_METHODS.md` for high-level and
calculation-specific documentation.

## What's New in v25

**Cartography & Visualization:**
- ✅ **KMZ File Support**: Upload Google Earth KMZ files for profiles, contours, and vector layers
- ✅ **In-Tile Symbology Controls**: All layer styling options appear directly in upload tiles
- ✅ **Improved Label Cartography**:
  - Index contours only with labels parallel to contour lines
  - Polygon labels centered inside features
  - Tight white backgrounds (no extra padding)
- ✅ **Auto-Zoom to Data**: Maps automatically zoom to uploaded data extent (contours, vectors, profiles)
- ✅ **Upload Files Default**: "Upload Files" is now the default data source mode

**Technical Improvements:**
- ✅ **Profile Upload Cleanup**: Uploading new profiles clears old station data automatically
- ✅ **No Auto-Load in Upload Mode**: Data folder auto-load only works in "Use Folder" mode
- ✅ **Immediate Station Display**: Profile stations appear on map immediately after upload

## Install

Open PowerShell or terminal and run:

```powershell
pip install -r requirements.txt
```

If you prefer, install manually:

```powershell
pip install streamlit rasterio numpy pandas folium streamlit-folium shapely plotly pyproj geopandas fiona scipy
```

## Run the app

```powershell
streamlit run terrain_editor.py
```

The app will open in your browser at `http://localhost:8501`.

## Quickstart — folder structure

```
project_root/
├─ terrain_editor.py
├─ _versions/            # Saved versions for rollback
│  └─ terrain_editor_v25.py
└─ Data/
   ├─ dem.tif            # optional (can upload via UI)
   └─ profile.*          # optional: only loads in "Use Folder" mode
```

## High-level workflow

1. **Choose Data Source**: Select "Upload Files" (default, recommended) or "Use Folder"
2. **Choose Design Mode**: `Profile Line (Berm/Ditch)` or `Polygon Basin`
3. **Load DEM**: Upload GeoTIFF via UI (Upload mode) or use `Data/dem.tif` (Folder mode)
4. **Upload Optional Layers** (Upload mode):
   - Profile line: Shapefile ZIP, KML, or **KMZ** (polyline)
   - Contours: Shapefile ZIP, KML, or **KMZ** (for visualization)
   - Vector layers: Shapefile ZIP, KML, KMZ, or GeoJSON
   - All layers auto-zoom map to their extent on upload
   - Symbology controls appear directly in upload tiles
5. **Draw or Upload Geometry**: Profile line (polyline) or basin polygon
6. **Configure Parameters**: Template settings (berm/ditch/swale) or basin depth/slope
7. **Review & Edit**: Cross-sections, profiles, adjust elevations
8. **Calculate Volumes**: Geometric and DEM-based methods with uncertainty analysis
9. **Export**: Modified DEM (GeoTIFF) or vector data (Shapefile/KML/GeoJSON)

## Loading data

### Data Source Modes

**Upload Files Mode (Default, Recommended):**
- Upload all data through the web interface
- No auto-loading from Data folder
- KMZ files fully supported
- Map auto-zooms to uploaded data
- Symbology controls in upload tiles

**Use Folder Mode:**
- Loads `dem.tif` from Data folder
- Auto-loads `profile.zip` if available
- Traditional file-based workflow

### File Types Supported

**DEM:**
- GeoTIFF (.tif) required
- Upload via UI or place in `Data/` folder
- Should be in projected CRS with meter units

**Profile Lines:**
- Shapefile (as .zip)
- KML (.kml)
- **KMZ (.kmz)** - Google Earth format, automatically extracted

**Contours (Optional):**
- Shapefile (as .zip)
- KML (.kml)
- **KMZ (.kmz)**
- Automatically displays with index contour labels
- Map zooms to contour extent on upload

**Vector Layers (Optional):**
- Shapefile (as .zip)
- KML (.kml)
- **KMZ (.kmz)**
- GeoJSON (.geojson)
- Supports points, lines, and polygons
- Multiple layers can be loaded

### Important Notes

- **Profile Upload**: When uploading a new profile, all previous profile data (stations, elevations, modifications) are **automatically cleared** to ensure clean processing
- **KMZ Files**: Automatically extracted and parsed - no manual extraction needed
- **Auto-Zoom**: Maps automatically fit to uploaded data bounds
- **CRS Detection**: App attempts to detect CRS and transform to lat/lon automatically

## Symbology & Visualization

### Contour Styling (v25)

After uploading contours, symbology controls appear **in the upload tile**:
- **Layer Opacity**: 0-100% transparency
- **Show Labels**: Toggle labels on/off
- **Label Field**: Choose which attribute to display
- **Label Size**: 5-20 pixels
- **Label Opacity**: Label text opacity
- **Label Background**: White background opacity
- **Index Interval**: Highlight every Nth contour with thicker lines

**Label Behavior:**
- Only **index contours** are labeled (divisible by index interval)
- Labels are **parallel to contour lines** (rotated automatically)
- **Tight white backgrounds** with minimal padding
- One label per contour at midpoint

### Vector Layer Styling (v25)

After uploading vector layers, symbology controls appear **in the upload tile**:
- **Layer Opacity**: 0-100% transparency
- **Show Labels**: Toggle labels on/off
- **Label Field**: Choose attribute to display
- **Label Size**: 5-20 pixels
- **Label Opacity**: Label text opacity
- **Label Background**: White background opacity

**Label Behavior:**
- **Points**: Labels positioned at point location
- **Lines**: Labels at line midpoint
- **Polygons**: Labels **centered inside polygon** (using centroid)
- **Tight white backgrounds** on all labels
- Clean, professional cartographic appearance

### Map Auto-Zoom Behavior

**Priority Order:**
1. **Highest**: Just-uploaded contours or vector layers
2. **Second**: Profile line or basin polygon
3. **Fallback**: DEM extent

When you upload contours or vectors, the map immediately zooms to show the full extent with 10% buffer.

## Exporting results

On the map panels and download sections you can export:
- **Shapefile (ZIP)**, **KML**, **GeoJSON** for profile lines, basin polygons, and channel lines
- **Modified DEM** as GeoTIFF with custom resolution (from Basin Design or Profile workflow)

## Links
- Calculation details and worked examples: `VOLUME_CALCULATION_METHODS.md`
- Project summary and features: `PROJECT_SUMMARY.md`
- Quick start guide: `QUICK_START.md`

## Troubleshooting

### General Issues

**"DEM file not found"**
- In "Upload Files" mode: Upload DEM via UI
- In "Use Folder" mode: Ensure `Data/dem.tif` exists and working directory is correct

**"Draw profile line first" or "Draw basin polygon first"**
- Go to **Input Data** tab
- Use the drawing tools on the map (polyline for profile, polygon for basin)

### Upload Issues

**KML/KMZ parsing errors**
- Ensure file is valid KML/KMZ format (Google Earth export)
- Check file size is under 200MB
- For KMZ: App automatically extracts - no manual unzipping needed

**Map not zooming to uploaded data**
- Ensure upload was successful (look for green success message)
- Check that "Upload Files" mode is selected (not "Use Folder")
- Try re-uploading the file

**Old stations showing after profile upload**
- This should not happen in v25 - old data is auto-cleared
- Try refreshing the browser page if issue persists

### Shapefile Support

For shapefile handling, `geopandas` and `fiona` should be installed (in requirements.txt).
If shapefile CRS is not geographic, the app attempts to reproject to the analysis CRS.

---

## WORKFLOW EXAMPLES

### Example 1: Debris Flow Berm (Profile Mode)

**Scenario**: Design 200m berm for debris flow protection

**Step-by-Step:**
1. **Data Source**: Keep default "Upload Files"
2. **Design Mode**: Select "Profile Line (Berm/Ditch)"
3. **Upload DEM**: Click DEM tile, upload GeoTIFF
4. **Optional**: Upload contours for visualization (map auto-zooms)
5. **Input Data**: Draw 200m line from ridge to valley using polyline tool
   - Map auto-zooms to profile
   - Stations (S0, S1, S2...) appear immediately
6. **Cross-Section Setup**:
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
7. **Browse**: Check stations 0, 10, 20, 30, 39
8. **Edit**:
   - Set gradient slopes at key stations
   - Adjust individual station elevations
   - Only selected station editable in table
9. **Profile**: Verify continuous design
10. **Export**: Download modified DEM at 2m resolution

**Time**: ~5 minutes
**Result**: Professional terrain modification with visualization layers

---

### Example 2: Debris Storage Basin with Visualization (Basin Mode)

**Scenario**: Design sediment retention basin with property boundaries and contours

**Step-by-Step:**
1. **Data Source**: Keep default "Upload Files"
2. **Design Mode**: Select "Polygon Basin"
3. **Upload DEM**: Click DEM tile, upload GeoTIFF
4. **Upload Visualization Layers**:
   - Upload contours (KMZ from Google Earth)
     - Map auto-zooms to contours
     - Adjust symbology in upload tile (opacity, labels, index interval)
   - Upload cadastre/property boundaries (Shapefile ZIP)
     - Map auto-zooms to boundaries
     - Adjust symbology (opacity, labels, label field)
5. **Input Data**:
   - Draw basin polygon boundary
     - Map auto-zooms to polygon
   - Optionally draw channel line (green polyline)
     - S0/S1 markers appear automatically
6. **Basin Design Setup**:
   ```
   Basin Depth: 3.0m
   Side Slope: 1.5 H:1V
   Longitudinal Slope: 2.0%
   ```
7. **Review Metrics**:
   - Geometric Volume: 4,934 m³
   - Outer/Inner areas displayed
8. **Compute Basin Cut**: Click "Compute Basin Cut" button
   - Generates modified DEM
   - Calculates DEM-based volume: 4,856 ± 124 m³
   - Shows uncertainty analysis (mean ± std dev, [min, max] range)
9. **View Profile**: Longitudinal profile with S0/S1 markers
10. **View Map**: Basin Plan View shows polygon, channel, S0/S1 stations, contours, and property boundaries
11. **Export**: Download modified DEM at custom resolution

**Time**: ~7 minutes
**Result**: Complete basin design with context layers and accurate volume calculations

---

## TIPS & TRICKS

### Design Mode
- ✅ **Profile Line Mode**: Linear corridor design (berm/ditch/swale)
- ✅ **Basin Mode**: Polygon-based debris storage basin design

### Data Source Selection
- ✅ **Upload Files** (Default): Best for flexibility and visualization layers
- ✅ **Use Folder**: Quick workflow if you have organized Data folder

### File Formats
- ✅ **KMZ Files**: Fully supported - no manual extraction needed
- ✅ **Shapefiles**: Must be zipped (include .shp, .shx, .dbf, .prj)
- ✅ **KML**: Direct upload supported
- ✅ **GeoJSON**: Supported for vector layers

### Visualization Layers
- ✅ Upload contours for topographic context
- ✅ Upload cadastre/property boundaries to check basin location
- ✅ Upload existing infrastructure (roads, buildings) for clearance checks
- ✅ Adjust opacity to overlay multiple layers
- ✅ Toggle labels on/off as needed

### Profile Line (Profile Mode)
- ✅ Draw in any direction - system auto-corrects to upstream→downstream
- ✅ Station 0 = always upstream (high elevation)
- ✅ KMZ files from Google Earth work perfectly

### Basin Polygon (Basin Mode)
- ✅ Draw closed polygon for basin boundary
- ✅ Optional channel line for flow path definition
- ✅ Map auto-zooms to polygon extent
- ✅ S0 (upstream) and S1 (downstream) markers automatically placed

### Number of Stations
- Few (10-20): Quick, rough design
- Medium (50-100): Standard projects
- Many (200-500): Detailed, precise work

### Cartography & Labels
- ✅ **Index Contours Only**: Reduces label clutter
- ✅ **Parallel Labels**: Professional appearance on contours
- ✅ **Centered Polygon Labels**: Easy to read
- ✅ **Tight Backgrounds**: Clean, modern look
- ✅ **Adjustable Label Size**: Match your screen/export needs

### Vertical Exaggeration
- VE=1.0: True scale (flat terrain)
- VE=2.0-3.0: Good for most terrain
- VE=5.0-10.0: Subtle slopes visible

### Elevation Editing
- **Gradient Slope**: Set slope relative to horizontal for downstream stations
  - 0% = flat line (same elevation as gradient station)
  - Positive % = rising slope (downstream higher)
  - Negative % = falling slope (downstream lower)
- **Slider**: Quick adjustments (±10m range)
- **Table**: Precise values (only selected station editable)
- All methods update immediately and work together seamlessly

### Export Resolution
- Same as input: No resampling
- Higher (e.g., 5m): Smaller file size
- Lower (e.g., 0.5m): More detail, larger file

### Basin Design
- **Longitudinal slope**: Positive = downstream deeper, negative = upstream deeper
- **Channel line**: Optional - defines exact flow path
- **Volume calculation**:
  - Geometric: From designed geometry formulas
  - DEM difference: From raster elevation subtraction with uncertainty analysis
- **Uncertainty**: Reported as mean ± std dev with [min, max] range across cell sizes
- **Inner area**: Updates based on average depth considering longitudinal slope

---

## KEY CONCEPTS

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
- **Geometric Volume**: Calculated using geometric formulas (outer polygon area, inner polygon area, depth, and slopes). Assumes perfect geometric shapes.
- **DEM Difference Volume**: Calculated by differencing original and modified DEMs, clipping to basin polygon, and summing positive differences. Includes uncertainty analysis across cell sizes (0.5-5 m). Reported as mean ± standard deviation with [min, max] range.

### Operation Mode
- **Cut+Fill**: Both operations
- **Fill Only**: Only raise terrain
- **Cut Only**: Only lower terrain

---

## SUPPORT

**All features working?**
✓ Profile from user line or upload
✓ KMZ file support
✓ Auto-zoom to uploaded data
✓ Symbology controls in tiles
✓ Upstream→downstream orientation
✓ VE slider
✓ Next/Prev buttons
✓ Elevation editing
✓ Contour and vector layer visualization
✓ Professional label cartography
✓ Custom resolution export

**Still having issues?**
Check QUICK_START.md for troubleshooting tips

---

**STATUS**: Production Ready v25
**DATE**: December 2025
**READY**: For geotechnical research and professional use

**FEATURES**:
- Profile Line Design (Berm/Ditch/Swale)
- Polygon Basin Design with dual volume calculation methods
- DEM-based volume with uncertainty analysis
- KMZ file support for all vector inputs
- In-tile symbology controls
- Professional label cartography (index contours, centered polygons)
- Auto-zoom to uploaded data
- Visualization layer support (contours, cadastre, infrastructure)
- Longitudinal Slope support
- Channel Flow Path with S0/S1 station markers
- Modern UI with responsive layout
