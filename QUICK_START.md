# Terrain Editor Pro v25 - Quick Start

## 🚀 Application Setup

### Install Dependencies

**Option 1: Using requirements.txt (Recommended)**
```bash
pip install -r requirements.txt
```

**Option 2: Manual Installation**
```bash
pip install streamlit rasterio numpy pandas folium streamlit-folium shapely plotly pyproj geopandas fiona scipy
```

### Run the Application

```bash
streamlit run terrain_editor.py
```

The application will open in your default web browser at `http://localhost:8501`

---

## 📁 Folder Structure

```
your_project/
├── terrain_editor.py
├── README.md
├── QUICK_START.md
├── VOLUME_CALCULATION_METHODS.md
├── PROJECT_SUMMARY.md
└── Data/
    ├── dem.tif          ← Your DEM file (optional - can upload)
    └── Profile.zip      ← Optional profile shapefile (only in folder mode)
```

---

## 🎯 Quick Start Guide

### 1. Choose Data Source & Design Mode

**Data Source (Default: Upload Files)**
- **Upload Files**: Upload all data through the UI (recommended)
- **Use Folder**: Load from Data/ folder automatically

**Design Mode**
- **Profile Line (Berm/Ditch)**: For linear corridor design
- **Polygon Basin**: For debris storage basin design

### 2. Load Data

**Upload Files Mode (Default):**
- Upload DEM (GeoTIFF) - Required
- Upload Profile Line (ZIP, KML, or KMZ) - Optional
- Upload Contours (ZIP, KML, or KMZ) - Optional for visualization
- Upload Vector Layers (ZIP, KML, KMZ, or GeoJSON) - Optional for visualization
  - **Note**: When uploading contours or vector layers, the map automatically zooms to their full extent
  - Symbology controls (opacity, labels, colors) appear directly in the upload tile

**Use Folder Mode:**
- Place `dem.tif` in `Data/` folder
- Place `Profile.zip` (or `profile.zip`) in `Data/` folder - optional
- Profile auto-loads only in folder mode

**Important Notes:**
- Uploading a new profile clears all previous profile data and regenerates stations
- KMZ files are fully supported (automatically extracted and parsed)
- Map zooms to uploaded data extent immediately

### 3. Visualize Optional Layers

**Contours (Optional):**
- Upload contour shapefile (ZIP), KML, or KMZ
- Map automatically zooms to contour extent
- Adjust symbology directly in upload tile:
  - Layer opacity
  - Show/hide labels (index contours only)
  - Label field selection
  - Label size, opacity, and background
  - Index interval for highlighting major contours
- Labels appear parallel to contour lines with tight white backgrounds

**Vector Layers (Optional):**
- Upload vector data (ZIP, KML, KMZ, GeoJSON)
- Map automatically zooms to layer extent
- Adjust symbology directly in upload tile:
  - Layer opacity
  - Show/hide labels
  - Label field selection
  - Label size, opacity, and background
- Polygon labels centered inside features
- Multiple layers supported

### 4. Draw Geometry

**Profile Mode:**
- Draw profile line on map using polyline tool
- Map zooms to profile line extent automatically
- Stations (S0, S1, S2...) appear immediately at each vertex

**Basin Mode:**
- Draw basin polygon on map using polygon tool (map auto-zooms to polygon)
- Optionally draw channel line using green polyline tool
  - Channel line persists after first draw
  - S0 (upstream) and S1 (downstream) markers appear automatically

### 5. Configure Parameters

**Profile Mode:**
- Set number of stations
- Choose template (Berm+Ditch or Swale)
- Configure template parameters
- Set influence width

**Basin Mode:**
- Set basin depth (default: 3.0m)
- Set side slope (default: 1.5 H:1V)
- Set longitudinal slope (default: 0.0%)
- Click "Compute Basin Cut" to generate modified DEM and calculate volumes
- Review both geometric and DEM-difference volumes with uncertainty analysis

### 6. Review & Export

- Review cross-sections (Profile Mode) or basin metrics (Basin Mode)
- Edit elevations if needed (Profile Mode)
- Compute modified DEM
- Download modified DEM at custom resolution

---

## 🔧 Key Features

### Profile Mode
- ✅ Linear corridor design
- ✅ Berm + Ditch templates
- ✅ Swale template
- ✅ Ditch side selection (left/right)
- ✅ Design gradient slope (relative to horizontal)
- ✅ Station-by-station elevation editing
- ✅ Table editing (selected station only)
- ✅ Longitudinal profile view with automatic updates
- ✅ KMZ file support for profile uploads
- ✅ Automatic map zoom to profile extent
- ✅ Immediate station display after upload

### Basin Mode
- ✅ Polygon-based basin design
- ✅ Optional channel line for flow path (persists on first draw)
- ✅ S0 and S1 station markers on Input Data and Basin Design maps
- ✅ Longitudinal slope support (-50% to +50%)
- ✅ Dual volume calculation methods:
  - Geometric volume (from design geometry)
  - DEM difference volume (from raster subtraction with uncertainty analysis)
- ✅ Volume uncertainty reporting (mean ± std dev, [min, max] range)
- ✅ Inner/outer area calculation
- ✅ Basin longitudinal profile plot
- ✅ Basin plan view map (auto-zoomed to polygon extent)
- ✅ Apply Basin to Terrain workflow

### Visualization & Cartography (v25)
- ✅ **Contour Labels**: Index contours only, parallel to contour lines, tight white backgrounds
- ✅ **Polygon Labels**: Centered inside polygons with tight white backgrounds
- ✅ **Auto-Zoom**: Maps automatically zoom to uploaded data (contours, vectors, profiles)
- ✅ **In-Tile Symbology**: All layer controls appear directly in upload tiles
- ✅ **KMZ Support**: Full support for Google Earth KMZ files
- ✅ **Upload Mode Default**: "Upload Files" is now the default data source

---

## 📚 Documentation

- **README.md**: Complete workflow guide and examples
- **QUICK_START.md**: This file - quick setup guide
- **VOLUME_CALCULATION_METHODS.md**: Detailed calculation methods
- **PROJECT_SUMMARY.md**: High-level project overview

---

## 🆘 Troubleshooting

### "DEM file not found"
- Ensure `dem.tif` is in `Data/` folder (if using folder mode)
- Or upload DEM file directly (recommended)

### "Draw profile line first" (Profile Mode)
- Go to Input Data tab
- Use polyline tool to draw line

### "Draw basin polygon first" (Basin Mode)
- Go to Input Data tab
- Use polygon tool to draw closed polygon

### Channel line disappears (Basin Mode)
- Channel should persist after first draw (no app reset)
- Check that you're in Basin Mode
- S0 and S1 markers should appear automatically when channel is drawn
- Channel line is displayed in green on both Input Data and Basin Design maps

### Contours or vectors not zooming properly
- Ensure the file is successfully uploaded (check for success message)
- Map should automatically zoom to data extent on upload
- If using folder mode, switch to "Upload Files" mode for auto-zoom

### KML/KMZ upload errors
- Ensure file is a valid KML or KMZ (Google Earth format)
- For KMZ files, the app automatically extracts and parses the KML inside
- Check file size is under 200MB

---

## 📦 Git Setup (Optional)

### Push to GitHub

**Option 1: Using PowerShell Script**
```powershell
.\push_to_github.ps1 YOUR_GITHUB_USERNAME terrain-editor
```

**Option 2: Manual Commands**
```powershell
git remote add origin https://github.com/YOUR_USERNAME/REPO_NAME.git
git push -u origin main
git checkout test
git push -u origin test
git checkout main
```

---

**VERSION**: 25
**STATUS**: ✅ Production Ready
**LAST UPDATED**: December 2025
**NEW FEATURES**:
- KMZ file support with automatic extraction
- Contour and vector layer symbology controls in upload tiles
- Index-only contour labels parallel to contour lines
- Centered polygon labels with tight white backgrounds
- Automatic map zoom to uploaded data extent
- Upload Files mode as default
- Improved label cartography and styling
