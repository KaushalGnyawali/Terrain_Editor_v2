# Terrain Editor Pro v8.0 - Quick Start

## 🚀 Application Setup

### Install Dependencies

```bash
pip install streamlit rasterio numpy pandas folium streamlit-folium shapely plotly pyproj geopandas fiona
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
├── VISUAL_GUIDE.md
└── Data/
    ├── dem.tif          ← Your DEM file
    └── Profile.zip       ← Optional profile shapefile
```

---

## 🎯 Quick Start Guide

### 1. Choose Design Mode

- **Profile Line (Berm/Ditch)**: For linear corridor design
- **Polygon Basin**: For debris storage basin design

### 2. Load Data

**Option A: Upload Files**
- Upload DEM (GeoTIFF)
- Upload Profile (ZIP shapefile or KML) - optional

**Option B: Use Data Folder**
- Place `dem.tif` in `Data/` folder
- Place `Profile.zip` (or `profile.zip`) in `Data/` folder - optional

### 3. Draw Geometry

**Profile Mode:**
- Draw profile line on map using polyline tool

**Basin Mode:**
- Draw basin polygon on map using polygon tool
- Optionally draw channel line using polyline tool

### 4. Configure Parameters

**Profile Mode:**
- Set number of stations
- Choose template (Berm+Ditch or Swale)
- Configure template parameters
- Set influence width

**Basin Mode:**
- Set basin depth (default: 3.0m)
- Set side slope (default: 1.5 H:1V)
- Set longitudinal slope (default: 0.0%)

### 5. Review & Export

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

### Basin Mode
- ✅ Polygon-based basin design
- ✅ Optional channel line for flow path
- ✅ Longitudinal slope support (-50% to +50%)
- ✅ Accurate volume calculation (accounts for slope)
- ✅ Inner/outer area calculation
- ✅ Basin longitudinal profile plot
- ✅ Basin plan view map

---

## 📚 Documentation

- **README.md**: Complete workflow guide and examples
- **VISUAL_GUIDE.md**: Visual diagrams and parameter guides
- **QUICK_START.md**: This file - quick setup guide

---

## 🆘 Troubleshooting

### "DEM file not found"
- Ensure `dem.tif` is in `Data/` folder
- Or upload DEM file directly

### "Draw profile line first" (Profile Mode)
- Go to Input Data tab
- Use polyline tool to draw line

### "Draw basin polygon first" (Basin Mode)
- Go to Input Data tab
- Use polygon tool to draw closed polygon

### Channel line disappears (Basin Mode)
- Channel should persist after drawing
- Check that you're in Basin Mode
- Try refreshing the page

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

**VERSION**: 8.0  
**STATUS**: ✅ Production Ready  
**LAST UPDATED**: December 2025

