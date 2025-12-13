# Terrain Editor Pro v25 — Project Summary

## Purpose
Terrain Editor Pro is an interactive Streamlit application for designing small engineered terrain features (berms, ditches, swales, and polygonal basins) on a local DEM. It provides drawing tools, cross‑section sampling, and three independent methods to estimate earthwork volumes and areas with professional cartographic visualization capabilities.

## Main Features

### Core Functionality
- Interactive map drawing (polyline for profile, polygon for basin) via Folium + Draw plugin
- Profile-based corridor design (berm/ditch/swale templates) with station-based editing
- Basin design workflow with optional channel line for longitudinal slope definition
- Three volume estimation methods: Geometric (frustum-based), Mesh/TIN (conceptual TIN with geometric core), and DEM differencing (raster comparison with uncertainty analysis)
- Export options for designed vectors: Shapefile (ZIP), KML, GeoJSON; export modified DEM as GeoTIFF
- Session-state persistence for incremental editing

### Visualization & Cartography (v25)
- **KMZ File Support**: Upload Google Earth KMZ files for profiles, contours, and vector layers (automatic extraction)
- **In-Tile Symbology Controls**: All layer styling options appear directly in upload tiles for immediate access
- **Professional Label Cartography**:
  - Index contours only with labels parallel to contour lines
  - Polygon labels centered inside features using geometric centroids
  - Point and line labels with optimal placement
  - Tight white backgrounds (minimal padding) for clean appearance
- **Auto-Zoom Behavior**: Maps automatically zoom to uploaded data extent (contours, vectors, profiles) with 10% buffer
- **Multiple Layer Support**: Upload and visualize multiple vector layers simultaneously with independent symbology controls

### Data Management (v25)
- **Dual Data Source Modes**:
  - Upload Files (Default): Upload all data through UI, no auto-loading, full control
  - Use Folder: Traditional file-based workflow with auto-loading from Data/ folder
- **Smart Data Handling**:
  - Profile upload clears old station data automatically
  - No auto-load in Upload mode (prevents unwanted data loading)
  - Immediate station display after profile upload
- **File Format Support**:
  - DEM: GeoTIFF (.tif)
  - Vectors: Shapefile (.zip), KML (.kml), KMZ (.kmz), GeoJSON (.geojson)
  - Automatic CRS detection and transformation

### Volume Calculation
- **Geometric Method**: Frustum-based calculation with support for longitudinal slopes
- **DEM Differencing**: Raster comparison with multi-resolution uncertainty analysis
  - Reports mean ± standard deviation
  - Provides [min, max] range across cell sizes (0.5-5 m)
  - Cell-size sensitivity analysis for robust volume estimation
- **TIN Method**: Conceptual mesh-based approach (uses geometric core)

## What's New in v25

1. **KMZ File Support**: Automatic extraction and parsing of Google Earth KMZ files
2. **In-Tile Symbology**: Layer controls moved into upload tiles for better UX
3. **Enhanced Cartography**:
   - Index-only contour labels parallel to lines
   - Centered polygon labels
   - Tight white backgrounds on all labels
4. **Auto-Zoom**: Immediate zoom to uploaded data extent
5. **Upload Mode Default**: "Upload Files" is now the default data source
6. **Smart Data Clearing**: Old profile data automatically cleared on new upload
7. **No Auto-Load in Upload Mode**: Folder auto-loading only in "Use Folder" mode

## Technical Architecture

### Single-File Application
- Main file: `terrain_editor.py` (comprehensive Streamlit app)
- Version control: `_versions/` folder for rollback capability
- Resources: `Data/` folder for optional file-based inputs

### Dependencies
- **Core**: streamlit, rasterio, numpy, pandas
- **Mapping**: folium, streamlit-folium
- **Geometry**: shapely, geopandas, fiona
- **Visualization**: plotly
- **Projection**: pyproj
- **Analysis**: scipy (for uncertainty calculations)

### CRS Handling
- Local raster reprojection and resampling
- Automatic CRS detection for shapefiles
- Transform between geographic (EPSG:4326) and projected CRS
- Distance/area calculations in analysis CRS (meters)

## Use Cases

### Profile Mode
- **Debris Flow Berms**: Linear protection structures with berm+ditch template
- **Drainage Swales**: Sunken channels for water conveyance
- **Road Corridors**: Linear earthwork with elevation control
- **Utility Trenches**: Cut corridors with specified dimensions

### Basin Mode
- **Debris Storage Basins**: Sediment retention with volume calculations
- **Retention Ponds**: Water storage with longitudinal slopes
- **Excavation Planning**: Polygon-based cut planning with uncertainty
- **Mine Planning**: Small-scale excavation design

### Visualization
- **Context Mapping**: Overlay contours for topographic context
- **Boundary Verification**: Check against property boundaries (cadastre)
- **Infrastructure Clearance**: Verify against existing roads/buildings
- **Regulatory Compliance**: Export professional maps for permits

## Quality Assurance

### Accuracy
- DEM-based volumes include uncertainty analysis
- Multi-resolution testing (0.5-5 m cell sizes)
- Geometric validation against known formulas
- Coordinate transformation testing

### Robustness
- Handles invalid geometries gracefully
- Nodata value management in rasters
- Buffer operation fallbacks for degenerate cases
- Session state persistence for stability

### User Experience
- Immediate visual feedback on uploads
- Auto-zoom to relevant data
- In-context symbology controls
- Clear error messages and troubleshooting

## Where to Find More

- **Detailed calculation methods and worked examples**: `VOLUME_CALCULATION_METHODS.md`
- **Quick start, installation, and workflow**: `QUICK_START.md`
- **Complete feature guide and examples**: `README.md`

## System Requirements

- **Python**: 3.8 or higher
- **Memory**: 4GB RAM minimum (8GB recommended for large DEMs)
- **Storage**: Depends on DEM size (typically 100MB-2GB)
- **Browser**: Modern browser (Chrome, Firefox, Edge, Safari)

## Version Information

- **Current Version**: 25
- **Status**: Production Ready
- **Date**: December 2025
- **Stability**: Tested for geotechnical research and professional use
- **License**: Contact repository owner for licensing information

## Notes

This repository provides a professional-grade terrain editing tool with emphasis on:
- Accurate volume calculations with uncertainty quantification
- Professional cartographic output
- Flexible data input (upload or folder-based)
- Modern, responsive user interface
- Comprehensive documentation
