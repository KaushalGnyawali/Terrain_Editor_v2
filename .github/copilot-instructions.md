# Copilot Instructions for Terrain Editor Pro v8.0

## Project Overview
- **Purpose:** Interactive Streamlit app for geotechnical terrain modification—designing debris-flow berms, ditches, swales, and polygonal basins on DEMs.
- **Entry Point:** `terrain_editor.py` (Streamlit app, all logic in one file)
- **Data Directory:** All persistent data (input DEM, shapefiles, etc.) is in `Data/`.

## Key Workflows
- **Run the app:**
  ```bash
  pip install streamlit rasterio numpy pandas folium streamlit-folium shapely plotly pyproj
  streamlit run terrain_editor.py
  ```
- **DEM Input:** Place `dem.tif` in `Data/` or upload via UI. App expects GeoTIFF.
- **Profile/Basin Input:**
  - Draw interactively on map, or
  - Upload as Shapefile (.zip) or KML (line for profile, polygon for basin)
- **Design Modes:**
  - "Profile Line (Berm/Ditch)": Linear corridor design, station-based editing
  - "Polygon Basin": Basin with polygon boundary, optional channel line for flow
- **Export:** Generates modified DEM as GeoTIFF with user-specified resolution

## Code Structure & Patterns
- **Single-file Streamlit app:** All UI, logic, and helpers in `terrain_editor.py`
- **Session State:** Uses `st.session_state` for all user/session data
- **File Uploads:** Handled via Streamlit, processed with `rasterio`, `geopandas`, or `fiona` (if available)
- **Geometry:** Heavy use of `shapely` for geometric operations, `pyproj` for CRS transforms
- **DEM Processing:**
  - Resampling, cross-section extraction, and corridor application are custom numpy routines
  - No external GIS servers/services—everything is local
- **UI:**
  - Streamlit widgets for all user input
  - Folium map for drawing/uploading features
  - Plotly for profile/cross-section plots

## Conventions & Tips
- **Profile lines:** Always processed upstream→downstream (station 0 = upstream/highest)
- **Basin polygons:** First vertex = upstream; channel line (if present) defines flow path
- **Station editing:** Only one station editable at a time in table; all edits update plots/DEM live
- **No test suite or build system:** Manual testing via app UI
- **No external APIs:** All computation is local, no cloud dependencies

## Integration Points
- **Dependencies:** See install command above; `geopandas`/`fiona` optional for shapefile support
- **Data I/O:** Only reads/writes from `Data/` and user uploads/downloads
- **No background jobs or async:** All processing is synchronous in the Streamlit event loop

## Examples
- See `README.md` for detailed user workflows and parameter explanations
- Key functions: DEM resampling, cross-section extraction, basin volume calculation, file export helpers

---
For more details, see `README.md` and comments in `terrain_editor.py`.
