# Terrain Editor Pro v8.0 - Quick Start Guide

## 🚀 SETUP

### Install Dependencies

**Option 1: Using requirements.txt (Recommended)**
```bash
pip install -r requirements.txt
```

**Option 2: Manual Installation**
```bash
pip install streamlit rasterio numpy pandas folium streamlit-folium shapely plotly pyproj geopandas fiona
```

### Run the Application

```bash
streamlit run terrain_editor.py
```

The application will open in your default web browser at `http://localhost:8501`

## 📁 FOLDER STRUCTURE

```
your_project/
├── terrain_editor.py
└── Data/
    └── dem.tif  ← Your DEM file
```

## 🎯 WORKFLOW

### 0. DESIGN MODE SELECTION

**Choose your design mode:**
- **Profile Line (Berm/Ditch)**: Linear corridor design for berms, ditches, and swales
- **Polygon Basin**: Debris storage basin design with polygon boundary

✅ **Result**: Appropriate tabs and tools enabled

---

### 1. INPUT DATA TAB - Draw Profile Line or Basin Polygon

**For Profile Line Mode:**
✏️ **Draw your profile line on the map**
- Click the polyline tool (📏)
- Draw from **any direction** (high→low or low→high)
- System auto-corrects to upstream→downstream

**For Basin Mode:**
✏️ **Draw basin polygon on the map**
- Click the polygon tool (⬟)
- Draw a closed polygon for the basin boundary
- Map auto-zooms to polygon extent after drawing

✏️ **Draw channel line (optional)**
- Click the polyline tool (green)
- Draw from upstream to downstream inside the basin
- Channel line stays visible on first draw (no app reset)
- S0 (upstream) and S1 (downstream) markers appear automatically

✅ **Result**: Profile line or basin polygon on map with S0/S1 markers (if channel drawn)

---

### 2A. PROFILE MODE - Cross-Section Tab Setup

⚙️ **Configure extraction**
```
Number of Stations: [50]     ← How many points (10-500)
Initial Slope: [0.0] %       ← Starting slope (optional)
```

📋 **Choose template**
- **Berm + Ditch**: For debris flow barriers
- **Swale**: For drainage channels

🎛️ **Set parameters**
```
Berm + Ditch:
├─ Berm Top Width: 4.0 m
├─ Berm Side Slope: 2.0 (H:V)
├─ Ditch Bottom Width: 2.0 m
├─ Ditch Depth: 1.5 m
├─ Ditch Side Slope: 3.0 (H:V)
└─ Ditch Side: [Left ▼]    ← Left or Right side

Influence Width: 20.0 m  ← Corridor width (±20m)
```

✅ **Result**: Profile extracted, stations numbered 0→N

---

### 2B. BASIN MODE - Basin Design Tab Setup

⚙️ **Configure basin parameters**
```
Basin Depth: [3.0] m          ← Depth at upstream (0.5-20m)
Side Slope: [1.5] H:1V        ← Side slope ratio (0.5-10)
Longitudinal Slope: [0.0] %   ← Slope along flow path (-50% to +50%)
```

📏 **Optional: Draw channel line**
- Draw green polyline on Input Data map to define flow path
- If not drawn, uses first vertex → minimum elevation

✅ **Result**: Basin metrics calculated (volume, areas)

---

### 3. PROFILE MODE - Cross-Section Tab Browse & Edit

🔍 **Navigate stations**
```
┌──────────────┐
│ ◄ Prev | Next►│  ← Click to browse
├──────────────┤
│  [═══╬═══]   │  ← Or use slider
│  Station 25  │
│  250.5 m     │
└──────────────┘
```

📊 **View cross-section**
- Existing terrain (gray)
- Template design (green)
- Final result (red)

✏️ **Edit elevation**
```
Elev: 245.3 m
[═══╬═══]     ← Drag to adjust ±10m
```

🔬 **Adjust vertical exaggeration**
```
V.E.: 2.5×
[═══╬═══]     ← See slopes clearly
```

✅ **Result**: Cross-section edited at each station

---

### 4. PROFILE MODE - Profile Tab View & Edit

📈 **Full profile view**
- Distance-elevation plot
- Upstream (Station 0) → Downstream (Station N)
- Shows downward slope
- Updates automatically when gradients or elevations change

✏️ **Three editing methods**

**Method 1: Design Gradient Slope**
- Select station with Prev/Next or station number input
- Set gradient slope (%) relative to horizontal
- Gradient applies to all downstream stations until next gradient station
- 0% = flat line (same elevation)
- Positive = rising slope, Negative = falling slope

**Method 2: Elevation Slider**
- Select station with Prev/Next or station number input
- Adjust elevation with slider (±10m range)
- Updates design profile and modified DEM

**Method 3: Elevation Table**
- Only the **selected station** can be edited in the table
- Edit Design_Elev value for the selected station
- Changes update gradients, plot, and modified DEM automatically
- Other stations are protected from editing

✅ **Result**: Design profile verified with gradients and elevations

---

### 5. BASIN MODE - Basin Design Tab Features

📊 **Basin Metrics Display**
```
Geometric Volume: 4,934 m³
Outer Area (Top): 1,853 m²
Inner Area (Bottom): 328 m²

DEM Difference Volume: 4,856 ± 124 m³
Range: [4,623, 5,089] m³
```

**Volume Calculation Methods:**
- **Geometric Volume**: Calculated from designed ditch geometry using geometric formulas
- **DEM Difference Volume**: Calculated by differencing original and modified DEMs, with uncertainty analysis across cell sizes (0.5-5 m)

📈 **Longitudinal Profile Plot**
- Shows existing ground and basin bottom elevation
- Upstream (S0) and downstream (S1) markers
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
