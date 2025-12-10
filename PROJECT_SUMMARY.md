# Terrain Editor Pro — Project Summary

Purpose
-------
Terrain Editor Pro is an interactive Streamlit application for designing small engineered terrain features (berms, ditches, swales, and polygonal basins) on a local DEM. It provides drawing tools, cross‑section sampling, and three independent methods to estimate earthwork volumes and areas.

Main features
-------------
- Interactive map drawing (polyline for profile, polygon for basin) via Folium + Draw plugin.
- Profile-based corridor design (berm/ditch/swale templates) with station-based editing.
- Basin design workflow with optional channel line for longitudinal slope definition.
- Three volume estimation methods: Geometric (frustum-based), Mesh/TIN (conceptual TIN with geometric core), and DEM differencing (raster comparison).
- Export options for designed vectors: Shapefile (ZIP), KML, GeoJSON; export modified DEM as GeoTIFF.
- Session-state persistence for incremental editing.

Where to find more
-------------------
- Detailed calculation methods and worked examples: `CALCULATION_METHODS.md`
- Quick start, installation, and workflow: `README.md`

Notes
-----
This repository is a single-file Streamlit app (`terrain_editor.py`) plus resources in `Data/`. The app performs local raster reprojection and resampling. For robust shapefile support install the optional packages `geopandas` and `fiona` (listed in `requirements.txt`).
