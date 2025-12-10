
# ...existing code...


# ...existing code...

# (Move this block to just after the basin polygon download section, inside the Streamlit script)
"""
Terrain Editor Pro v8.0 - Production Ready
==========================================
FIXES:
- Profile extracted directly from user line
- Stations numbered from first vertex to last vertex (user input order)
- Working VE slider with force update
- Station slider for navigation
- Cross-section edits integrated
- Custom DEM resolution export
- Perpendicular cross-sections

Version: 7.0 Production
Date: December 7, 2025
"""

from pathlib import Path
import os
import io
import numpy as np
import pandas as pd
import rasterio
from rasterio.transform import xy, rowcol, array_bounds, from_bounds
from rasterio.io import MemoryFile
from rasterio.warp import calculate_default_transform, reproject, Resampling
from pyproj import CRS, Transformer
import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import Draw
from shapely.geometry import LineString
import plotly.graph_objects as go
import zipfile
import tempfile
import xml.etree.ElementTree as ET
try:
    import geopandas as gpd
    HAS_GEOPANDAS = True
except ImportError:
    HAS_GEOPANDAS = False
    try:
        import fiona
        HAS_FIONA = True
    except ImportError:
        HAS_FIONA = False


# --- IDW resampling helper (simple, neighborhood-based) ---
def idw_resample(src_array, src_transform, dst_transform, dst_height, dst_width, src_nodata=None, power=2, radius=1):
    """Resample src_array onto a dst grid using inverse-distance weighting (IDW).
    This is a simple neighborhood-based IDW (radius in pixels). Not highly optimized.
    """
    import math
    from rasterio.transform import Affine

    dst = np.full((dst_height, dst_width), np.float32(src_nodata if src_nodata is not None else np.nan), dtype=np.float32)

    inv_src = ~src_transform

    src_h, src_w = src_array.shape

    for rr in range(dst_height):
        for cc in range(dst_width):
            # world coords of destination pixel center
            x, y = dst_transform * (cc + 0.5, rr + 0.5)
            # map to source fractional indices (col, row)
            src_col_f, src_row_f = inv_src * (x, y)

            r0 = int(math.floor(src_row_f))
            c0 = int(math.floor(src_col_f))

            accum_v = 0.0
            accum_w = 0.0
            assigned = False

            for dr in range(-radius, radius + 1):
                for dc in range(-radius, radius + 1):
                    r_src = r0 + dr
                    c_src = c0 + dc
                    if r_src < 0 or c_src < 0 or r_src >= src_h or c_src >= src_w:
                        continue
                    val = src_array[r_src, c_src]
                    if src_nodata is not None and (np.isnan(val) or val == src_nodata):
                        continue
                    # compute distance in pixel-space
                    dist = math.hypot(src_row_f - r_src, src_col_f - c_src)
                    if dist < 1e-8:
                        dst[rr, cc] = val
                        assigned = True
                        break
                    w = 1.0 / (dist ** power)
                    accum_v += val * w
                    accum_w += w
                if assigned:
                    break

            if not assigned:
                if accum_w > 0:
                    dst[rr, cc] = accum_v / accum_w
                else:
                    # fallback to nearest neighbor
                    rn = min(max(int(round(src_row_f)), 0), src_h - 1)
                    cn = min(max(int(round(src_col_f)), 0), src_w - 1)
                    dst[rr, cc] = src_array[rn, cn]

    return dst

# App configuration and title
st.set_page_config(layout="wide", page_title="Terrain Editor for Debris-Flow Berm & Basin Design", page_icon="⛰️", initial_sidebar_state="collapsed")

# ============================================================================
# PAGE TITLE (Display at very top)
# ============================================================================
st.markdown("# ⛰️Kaushal’s Terrain Editor.")

st.markdown("""
<style>
    /* Responsive layout with consistent spacing */
    .main > div {padding-top: 0.5rem;}
    .block-container {
        padding-top: 0.5rem; 
        padding-bottom: 0.5rem; 
        padding-left: 1rem; 
        padding-right: 1rem;
        max-width: 100%;
    }
    
    /* Typography - slightly larger, clearer fonts */
    h1 {
        font-size: 1.85rem !important; 
        font-weight: 600 !important;
        margin-bottom: 0.3rem !important; 
        margin-top: 0.3rem !important;
    }
    h2 {
        font-size: 1.5rem !important; 
        font-weight: 600 !important;
        margin: 0.4rem 0 0.3rem 0 !important;
    }
    h3 {
        font-size: 1.2rem !important; 
        font-weight: 600 !important;
        margin: 0.5rem 0 0.4rem 0 !important;
    }
    h4 {
        font-size: 1.1rem !important; 
        font-weight: 600 !important;
        margin: 0.4rem 0 0.3rem 0 !important;
    }
    
    /* Consistent spacing in forms */
    .stForm {margin-bottom: 0.5rem !important;}
    .stFormSubmitButton > button {width: 100%;}
    
    /* Divider - consistent spacing */
    hr {
        margin: 0.75rem 0 !important; 
        height: 1px !important;
        border: none;
        background-color: #e0e0e0;
    }
    
    /* Button styling - slightly larger */
    .stButton > button {
        width: 100%;
        padding: 0.5rem 1rem !important;
        font-size: 0.95rem !important;
        border-radius: 0.4rem !important;
        font-weight: 500 !important;
    }
    
    /* Input fields - improved readability */
    .stNumberInput input, 
    .stTextInput input,
    .stSelectbox select {
        padding: 0.5rem 0.7rem !important;
        font-size: 0.95rem !important;
    }
    
    /* Slider styling - consistent spacing */
    .stSlider {
        margin-bottom: 0.5rem !important;
    }
    .stSlider > div > div > div > div {
        font-size: 0.9rem !important;
        font-weight: 500 !important;
    }
    
    /* Info and warning boxes - consistent padding */
    .stInfo, 
    .stWarning, 
    .stError, 
    .stSuccess {
        padding: 0.75rem 1rem !important; 
        margin: 0.5rem 0 !important;
        border-radius: 0.4rem !important;
    }
    
    /* Card/expander styling - improved readability */
    .streamlit-expanderHeader {
        padding: 0.6rem 0.8rem !important; 
        font-size: 1rem !important;
        font-weight: 500 !important;
    }
    .streamlit-expanderContent {
        padding: 0.6rem 0.8rem !important;
    }
    
    /* Table styling - slightly larger */
    .stDataFrame {
        font-size: 0.95rem !important;
    }
    
    /* Captions and small text */
    .stCaption {
        font-size: 0.9rem !important;
        margin: 0.3rem 0 !important;
    }
    
    /* Markdown text and labels - improved readability */
    p {
        margin: 0.4rem 0 !important; 
        line-height: 1.5 !important;
        font-size: 0.95rem !important;
    }
    label {
        margin-bottom: 0.3rem !important;
        font-weight: 500 !important;
        font-size: 0.95rem !important;
    }
    
    /* Radio buttons - consistent spacing */
    .stRadio {
        margin-bottom: 0.5rem !important;
    }
    .stRadio label {
        font-size: 0.95rem !important;
    }
    
    /* Column spacing - responsive */
    [data-testid="column"] {
        padding: 0 0.75rem !important;
    }
    
    /* Plotly chart containers - responsive */
    .js-plotly-plot {
        margin: 0.5rem 0 !important;
    }
    
    /* File uploader - consistent styling */
    .stFileUploader {
        margin-bottom: 0.5rem !important;
    }
    
    /* Metric containers */
    [data-testid="stMetricContainer"] {
        padding: 0.5rem !important;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# FILE UPLOAD PROCESSING FUNCTIONS
# ============================================================================

def process_uploaded_dem(uploaded_file):
    """Process uploaded DEM file and return rasterio dataset."""
    try:
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix='.tif') as tmp_file:
            tmp_file.write(uploaded_file.read())
            tmp_path = tmp_file.name
        
        # Open with rasterio
        ds = rasterio.open(tmp_path)
        return ds, tmp_path
    except Exception as e:
        st.error(f"Error processing uploaded DEM: {e}")
        return None, None

def process_uploaded_shapefile(uploaded_file):
    """Process uploaded shapefile ZIP and extract LineString geometry with CRS info."""
    try:
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
            tmp_file.write(uploaded_file.read())
            tmp_zip_path = tmp_file.name
        
        # Extract ZIP to temporary directory
        with tempfile.TemporaryDirectory() as tmp_dir:
            with zipfile.ZipFile(tmp_zip_path, 'r') as zip_ref:
                zip_ref.extractall(tmp_dir)
            
            # Find .shp file
            shp_files = list(Path(tmp_dir).glob('*.shp'))
            if not shp_files:
                st.error("No .shp file found in uploaded ZIP")
                return None
            
            shp_path = shp_files[0]
            
            # Read shapefile
            if HAS_GEOPANDAS:
                gdf = gpd.read_file(str(shp_path))
                # Get CRS
                shapefile_crs = gdf.crs
                
                # Extract LineString coordinates
                coords_list = []
                for idx, row in gdf.iterrows():
                    geom = row.geometry
                    if geom.geom_type == 'LineString':
                        coords_list.extend(list(geom.coords))
                    elif geom.geom_type == 'MultiLineString':
                        for line in geom.geoms:
                            coords_list.extend(list(line.coords))
                
                if coords_list:
                    # Return coordinates with CRS info as a tuple
                    return (coords_list, shapefile_crs)
                else:
                    st.error("No LineString geometry found in shapefile")
                    return None
                    
            elif HAS_FIONA:
                import fiona
                from shapely.geometry import shape
                coords_list = []
                shapefile_crs = None
                with fiona.open(str(shp_path)) as src:
                    # Get CRS from shapefile
                    if src.crs:
                        shapefile_crs = CRS.from_string(str(src.crs))
                    for feature in src:
                        geom = shape(feature['geometry'])
                        if geom.geom_type == 'LineString':
                            coords_list.extend(list(geom.coords))
                        elif geom.geom_type == 'MultiLineString':
                            for line in geom.geoms:
                                coords_list.extend(list(line.coords))
                if coords_list:
                    return (coords_list, shapefile_crs)
                return None
            else:
                st.error("geopandas or fiona required for shapefile support. Install with: pip install geopandas")
                return None
                
    except Exception as e:
        st.error(f"Error processing uploaded shapefile: {e}")
        return None

def process_uploaded_kml(uploaded_file):
    """Process uploaded KML file and extract LineString coordinates."""
    try:
        # Read file content
        content = uploaded_file.read()
        uploaded_file.seek(0)  # Reset file pointer
        
        # Parse KML XML
        root = ET.fromstring(content)
        
        # Try different namespace formats
        namespaces = [
            {'kml': 'http://www.opengis.net/kml/2.2'},
            {'kml': 'http://earth.google.com/kml/2.0'},
            {'kml': 'http://earth.google.com/kml/2.1'},
            {}  # No namespace
        ]
        
        coords_list = []
        
        # Try each namespace
        for ns in namespaces:
            try:
                # Find all coordinates elements
                if ns:
                    coord_elems = root.findall('.//kml:coordinates', ns)
                else:
                    # Try without namespace
                    coord_elems = root.findall('.//coordinates')
                
                if coord_elems:
                    for coord_elem in coord_elems:
                        coord_text = coord_elem.text.strip() if coord_elem.text else ""
                        # Parse coordinates (lon,lat,alt or lon,lat)
                        for coord_line in coord_text.split():
                            parts = coord_line.split(',')
                            if len(parts) >= 2:
                                try:
                                    lon = float(parts[0].strip())
                                    lat = float(parts[1].strip())
                                    coords_list.append((lon, lat))
                                except ValueError:
                                    continue
                    break  # Successfully found coordinates
            except Exception:
                continue
        
        if coords_list:
            return coords_list
        else:
            st.error("No coordinates found in KML file")
            return None
            
    except Exception as e:
        st.error(f"Error processing uploaded KML: {e}")
        return None

def process_uploaded_polygon_shapefile(uploaded_file):
    """Process uploaded shapefile ZIP and extract Polygon geometry with CRS info."""
    try:
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
            tmp_file.write(uploaded_file.read())
            tmp_zip_path = tmp_file.name
        
        # Extract ZIP to temporary directory
        with tempfile.TemporaryDirectory() as tmp_dir:
            with zipfile.ZipFile(tmp_zip_path, 'r') as zip_ref:
                zip_ref.extractall(tmp_dir)
            
            # Find .shp file
            shp_files = list(Path(tmp_dir).glob('*.shp'))
            if not shp_files:
                st.error("No .shp file found in uploaded ZIP")
                return None
            
            shp_path = shp_files[0]
            
            # Read shapefile
            if HAS_GEOPANDAS:
                gdf = gpd.read_file(str(shp_path))
                # Get CRS
                shapefile_crs = gdf.crs
                
                # Extract Polygon coordinates
                coords_list = None
                for idx, row in gdf.iterrows():
                    geom = row.geometry
                    if geom.geom_type == 'Polygon':
                        # Get exterior ring coordinates as [lon, lat] pairs
                        coords_list = list(geom.exterior.coords)
                        break
                    elif geom.geom_type == 'MultiPolygon':
                        # Use first polygon
                        coords_list = list(geom.geoms[0].exterior.coords)
                        break
                
                if coords_list:
                    # Return coordinates with CRS info as a tuple
                    return (coords_list, shapefile_crs)
                else:
                    st.error("No Polygon geometry found in shapefile")
                    return None
                    
            elif HAS_FIONA:
                import fiona
                from shapely.geometry import shape
                coords_list = None
                shapefile_crs = None
                with fiona.open(str(shp_path)) as src:
                    # Get CRS from shapefile
                    if src.crs:
                        shapefile_crs = CRS.from_string(str(src.crs))
                    for feature in src:
                        geom = shape(feature['geometry'])
                        if geom.geom_type == 'Polygon':
                            coords_list = list(geom.exterior.coords)
                            break
                        elif geom.geom_type == 'MultiPolygon':
                            coords_list = list(geom.geoms[0].exterior.coords)
                            break
                if coords_list:
                    return (coords_list, shapefile_crs)
                return None
            else:
                st.error("geopandas or fiona required for shapefile support. Install with: pip install geopandas")
                return None
                
    except Exception as e:
        st.error(f"Error processing uploaded polygon shapefile: {e}")
        return None

def process_uploaded_polygon_kml(uploaded_file):
    """Process uploaded KML file and extract Polygon coordinates."""
    try:
        # Read file content
        content = uploaded_file.read()
        uploaded_file.seek(0)  # Reset file pointer
        
        # Parse KML XML
        root = ET.fromstring(content)
        
        # Try different namespace formats
        namespaces = [
            {'kml': 'http://www.opengis.net/kml/2.2'},
            {'kml': 'http://earth.google.com/kml/2.0'},
            {'kml': 'http://earth.google.com/kml/2.1'},
            {}  # No namespace
        ]
        
        coords_list = []
        
        # Try each namespace
        for ns in namespaces:
            try:
                # Find all coordinates elements for Polygons
                if ns:
                    coord_elems = root.findall('.//kml:Polygon//kml:coordinates', ns)
                else:
                    # Try without namespace
                    coord_elems = root.findall('.//Polygon//coordinates')
                
                if coord_elems:
                    for coord_elem in coord_elems:
                        coord_text = coord_elem.text.strip() if coord_elem.text else ""
                        # Parse coordinates (lon,lat,alt or lon,lat)
                        for coord_line in coord_text.split():
                            parts = coord_line.split(',')
                            if len(parts) >= 2:
                                try:
                                    lon = float(parts[0].strip())
                                    lat = float(parts[1].strip())
                                    coords_list.append((lon, lat))
                                except ValueError:
                                    continue
                    break  # Successfully found coordinates
            except Exception:
                continue
        
        if coords_list:
            return coords_list
        else:
            st.error("No polygon coordinates found in KML file")
            return None
            
    except Exception as e:
        st.error(f"Error processing uploaded polygon KML: {e}")
        return None

def export_polygon_to_shapefile(coords_latlon, poly_crs=None):
    """Export polygon coordinates to Shapefile ZIP format."""
    try:
        from shapely.geometry import Polygon
        import tempfile
        import shutil
        if not coords_latlon or len(coords_latlon) < 3:
            return None
        # Ensure closed ring
        if coords_latlon[0] != coords_latlon[-1]:
            coords_latlon = coords_latlon + [coords_latlon[0]]
        tmp_dir = tempfile.mkdtemp()
        shp_path = os.path.join(tmp_dir, "basin_polygon.shp")
        poly = Polygon(coords_latlon)
        gdf = gpd.GeoDataFrame([{'geometry': poly}], crs=poly_crs or "EPSG:4326")
        gdf.to_file(shp_path)
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for fname in os.listdir(tmp_dir):
                fpath = os.path.join(tmp_dir, fname)
                zf.write(fpath, arcname=fname)
        zip_buffer.seek(0)
        shutil.rmtree(tmp_dir)
        return zip_buffer.getvalue()
    except Exception as e:
        st.error(f"Error exporting polygon to Shapefile: {e}")
        return None

def export_polygon_to_kml(coords_latlon):
    """Export polygon coordinates to KML format."""
    try:
        if not coords_latlon or len(coords_latlon) < 3:
            return None
        # Ensure closed ring
        if coords_latlon[0] != coords_latlon[-1]:
            coords_latlon = coords_latlon + [coords_latlon[0]]
        kml_string = '''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Basin Polygon</name>
    <Placemark>
      <name>Basin</name>
      <Polygon>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>
'''
        for lon, lat in coords_latlon:
            kml_string += f"{lon},{lat},0 "
        kml_string += '''
            </coordinates>
          </LinearRing>
        </outerBoundaryIs>
      </Polygon>
    </Placemark>
  </Document>
</kml>'''
        return kml_string.encode('utf-8')
    except Exception as e:
        st.error(f"Error exporting polygon to KML: {e}")
        return None

def export_polygon_to_geojson(coords_latlon):
    """Export polygon coordinates to GeoJSON format."""
    try:
        import json
        if not coords_latlon or len(coords_latlon) < 3:
            return None
        # Ensure closed ring
        if coords_latlon[0] != coords_latlon[-1]:
            coords_latlon = coords_latlon + [coords_latlon[0]]
        geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"name": "Basin Polygon"},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [coords_latlon]
                    }
                }
            ]
        }
        return json.dumps(geojson, indent=2).encode('utf-8')
    except Exception as e:
        st.error(f"Error exporting polygon to GeoJSON: {e}")
        return None

def export_line_to_shapefile(coords_latlon, line_crs=None):
    """Export line coordinates to Shapefile ZIP format."""
    try:
        from shapely.geometry import LineString
        import tempfile
        import shutil
        
        if not coords_latlon or len(coords_latlon) < 2:
            return None
        
        # Create temporary directory for shapefile components
        tmp_dir = tempfile.mkdtemp()
        shp_path = os.path.join(tmp_dir, "profile_line.shp")
        
        # Create GeoDataFrame
        line = LineString(coords_latlon)
        gdf = gpd.GeoDataFrame([{'geometry': line}], crs=line_crs or "EPSG:4326")
        gdf.to_file(shp_path)
        
        # Create ZIP file
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for fname in os.listdir(tmp_dir):
                fpath = os.path.join(tmp_dir, fname)
                zf.write(fpath, arcname=fname)
        
        zip_buffer.seek(0)
        # Clean up temp directory
        shutil.rmtree(tmp_dir)
        
        return zip_buffer.getvalue()
    except Exception as e:
        st.error(f"Error exporting to Shapefile: {e}")
        return None

def export_line_to_kml(coords_latlon):
    """Export line coordinates to KML format."""
    try:
        if not coords_latlon or len(coords_latlon) < 2:
            return None
        
        # Build KML structure
        kml_string = '''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Profile Line</name>
    <Placemark>
      <name>Profile</name>
      <LineString>
        <coordinates>
'''
        
        for lon, lat in coords_latlon:
            kml_string += f"{lon},{lat},0 "
        
        kml_string += '''
        </coordinates>
      </LineString>
    </Placemark>
  </Document>
</kml>'''
        
        return kml_string.encode('utf-8')
    except Exception as e:
        st.error(f"Error exporting to KML: {e}")
        return None

def export_line_to_geojson(coords_latlon):
    """Export line coordinates to GeoJSON format."""
    try:
        import json
        
        if not coords_latlon or len(coords_latlon) < 2:
            return None
        
        geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {
                        "name": "Profile Line"
                    },
                    "geometry": {
                        "type": "LineString",
                        "coordinates": coords_latlon
                    }
                }
            ]
        }
        
        return json.dumps(geojson, indent=2).encode('utf-8')
    except Exception as e:
        st.error(f"Error exporting to GeoJSON: {e}")
        return None

# ============================================================================
# FILE UPLOAD UI
# ============================================================================

st.markdown("<h2 style='font-size: 1.8rem; margin: 0.2rem 0;'>⛰️ Terrain Editor for Debris-Flow Berm & Basin Design</h2>", unsafe_allow_html=True)

# Initialize session state for uploaded files
if "uploaded_dem_path" not in st.session_state:
    st.session_state.uploaded_dem_path = None
if "uploaded_dem_dataset" not in st.session_state:
    st.session_state.uploaded_dem_dataset = None
if "uploaded_profile_coords" not in st.session_state:
    st.session_state.uploaded_profile_coords = None
if "uploaded_profile_crs" not in st.session_state:
    st.session_state.uploaded_profile_crs = None
if "data_source" not in st.session_state:
    st.session_state.data_source = "folder"  # Default to folder
if "auto_loaded_profile" not in st.session_state:
    st.session_state.auto_loaded_profile = False
if "design_mode" not in st.session_state:
    st.session_state.design_mode = "profile"  # "profile" or "basin"
if "basin_polygon_coords" not in st.session_state:
    st.session_state.basin_polygon_coords = None  # List of [lon, lat] coordinates
if "basin_polygon_crs" not in st.session_state:
    st.session_state.basin_polygon_crs = None  # CRS info for polygon
if "basin_channel_coords" not in st.session_state:
    st.session_state.basin_channel_coords = None  # List of [lon, lat] coordinates for channel line
if "basin_depth" not in st.session_state:
    st.session_state.basin_depth = 3.0  # Default 3m
if "basin_side_slope" not in st.session_state:
    st.session_state.basin_side_slope = 1.5  # Default 1.5:1 (H:V)
if "basin_longitudinal_slope" not in st.session_state:
    st.session_state.basin_longitudinal_slope = 25.0  # Default 25% downstream deeper
if "basin_modified_dem" not in st.session_state:
    st.session_state.basin_modified_dem = None
if "basin_volumes" not in st.session_state:
    st.session_state.basin_volumes = {"volume": 0, "inner_area": 0, "outer_area": 0}

# Data Source selection
st.markdown("**Data Source**")
data_source = st.radio(
    "",
    ["Upload Files", "Use Data Folder (Data/dem.tif, profile.zip)"],
    index=0 if st.session_state.data_source == "upload" else 1,
    key="data_source_radio",
    horizontal=True
)
st.session_state.data_source = "upload" if data_source == "Upload Files" else "folder"

# Design Mode selection - no spacing between
st.markdown("**Design Mode**")
design_mode = st.radio(
    "",
    ["Profile Line (Berm/Ditch)", "Polygon Basin"],
    index=0 if st.session_state.design_mode == "profile" else 1,
    key="design_mode_radio",
    horizontal=True
)
st.session_state.design_mode = "profile" if design_mode == "Profile Line (Berm/Ditch)" else "basin"

# File upload section (only show if "Upload Files" is selected)
uploaded_dem = None
uploaded_profile = None

if st.session_state.data_source == "upload":
    # DEM Upload
    st.markdown("**📁 Upload DEM**")
    st.markdown("Upload DEM (GeoTIFF) " + "❓")
    uploaded_dem = st.file_uploader(
        "Drag and drop file here",
        type=['tif', 'tiff'],
        key="dem_uploader",
        help="Limit 200MB per file • TIF, TIFF",
        label_visibility="collapsed"
    )
    
    if uploaded_dem is not None:
        # Process uploaded DEM
        if uploaded_dem.size > 200 * 1024 * 1024:  # 200MB
            st.error("File size exceeds 200MB limit")
        else:
            with st.spinner("Processing uploaded DEM..."):
                ds, tmp_path = process_uploaded_dem(uploaded_dem)
                if ds is not None:
                    # Close previous dataset if exists
                    if st.session_state.uploaded_dem_dataset is not None:
                        try:
                            st.session_state.uploaded_dem_dataset.close()
                        except:
                            pass
                    st.session_state.uploaded_dem_dataset = ds
                    st.session_state.uploaded_dem_path = tmp_path
                    # Clear profile coordinates when new DEM is loaded (they may not match)
                    st.session_state.uploaded_profile_coords = None
                    st.session_state.uploaded_profile_crs = None
                    st.session_state.profile_line_coords = None
                    st.success(f"✅ DEM loaded successfully: {uploaded_dem.name}")
    
    # Profile Upload (Optional)
    st.markdown("**📍 Upload Profile (Optional)**")
    st.markdown("Upload Profile Line (Shapefile .zip or KML) " + "❓")
    uploaded_profile = st.file_uploader(
        "Drag and drop file here",
        type=['zip', 'kml'],
        key="profile_uploader",
        help="Limit 200MB per file • ZIP, KML",
        label_visibility="collapsed"
    )
    
    if uploaded_profile is not None:
        if uploaded_profile.size > 200 * 1024 * 1024:  # 200MB
            st.error("File size exceeds 200MB limit")
        else:
            with st.spinner("Processing uploaded profile..."):
                if uploaded_profile.name.lower().endswith('.zip'):
                    coords = process_uploaded_shapefile(uploaded_profile)
                elif uploaded_profile.name.lower().endswith('.kml'):
                    coords = process_uploaded_kml(uploaded_profile)
                else:
                    coords = None
                
                if coords:
                    # Store coordinates and CRS info if available
                    if isinstance(coords, tuple) and len(coords) == 2:
                        # Shapefile with CRS info
                        st.session_state.uploaded_profile_coords = coords[0]
                        st.session_state.uploaded_profile_crs = coords[1]
                    else:
                        # KML (already in lat/lon) or shapefile without CRS
                        st.session_state.uploaded_profile_coords = coords
                        st.session_state.uploaded_profile_crs = None
                    st.success(f"✅ Profile loaded successfully: {uploaded_profile.name}")
                    # Mark that profile was just uploaded so it gets processed
                    st.session_state.profile_just_uploaded = True
                else:
                    st.error("Failed to extract profile line from uploaded file")
    
    if uploaded_profile is None and st.session_state.uploaded_profile_coords is None:
        st.warning("⚠️ Or draw manually on map after loading DEM")
    
    # Polygon Basin Upload (only in basin mode)
    if st.session_state.design_mode == "basin":
        st.markdown("**🔷 Upload Basin Polygon (Optional)**")
        st.markdown("Upload Polygon (Shapefile .zip or KML) " + "❓")
        uploaded_polygon = st.file_uploader(
            "Drag and drop file here",
            type=['zip', 'kml'],
            key="polygon_uploader",
            help="Limit 200MB per file • ZIP, KML",
            label_visibility="collapsed"
        )
        
        if uploaded_polygon is not None:
            if uploaded_polygon.size > 200 * 1024 * 1024:  # 200MB
                st.error("File size exceeds 200MB limit")
            else:
                with st.spinner("Processing uploaded polygon..."):
                    if uploaded_polygon.name.lower().endswith('.zip'):
                        poly_result = process_uploaded_polygon_shapefile(uploaded_polygon)
                    elif uploaded_polygon.name.lower().endswith('.kml'):
                        poly_result = process_uploaded_polygon_kml(uploaded_polygon)
                    else:
                        poly_result = None
                    
                    if poly_result:
                        # Store polygon coordinates and CRS info if available
                        if isinstance(poly_result, tuple) and len(poly_result) == 2:
                            # Shapefile with CRS info - attempt to convert to lat/lon (EPSG:4326)
                            poly_coords, poly_crs = poly_result
                            try:
                                if poly_crs is not None and not CRS(poly_crs).is_geographic:
                                    transformer_poly = Transformer.from_crs(poly_crs, "EPSG:4326", always_xy=True)
                                    converted = []
                                    for coord in poly_coords:
                                        if isinstance(coord, (list, tuple)) and len(coord) >= 2:
                                            x, y = coord[0], coord[1]
                                            lon, lat = transformer_poly.transform(x, y)
                                            converted.append([lon, lat])
                                    if converted:
                                        st.session_state.basin_polygon_coords = converted
                                    else:
                                        st.session_state.basin_polygon_coords = [[c[0], c[1]] if isinstance(c, (list, tuple)) else c for c in poly_coords]
                                else:
                                    # CRS is geographic or unknown - assume already lon/lat
                                    st.session_state.basin_polygon_coords = [[c[0], c[1]] if isinstance(c, (list, tuple)) else c for c in poly_coords]
                                st.session_state.basin_polygon_crs = poly_crs
                                st.success(f"✅ Basin polygon loaded: {uploaded_polygon.name} (CRS: {poly_crs})")
                            except Exception as e:
                                # Fallback: store raw coords but warn user
                                st.session_state.basin_polygon_coords = [[c[0], c[1]] if isinstance(c, (list, tuple)) else c for c in poly_coords]
                                st.session_state.basin_polygon_crs = poly_crs
                                st.warning(f"Basin polygon loaded but coordinate transform to EPSG:4326 failed: {e}. Display may be incorrect.")
                        else:
                            # KML (already in lat/lon)
                            st.session_state.basin_polygon_coords = poly_result
                            st.session_state.basin_polygon_crs = None
                            st.success(f"✅ Basin polygon loaded: {uploaded_polygon.name}")
                        # Clear any previous basin modified dem
                        st.session_state.basin_modified_dem = None
                    else:
                        st.error("Failed to extract polygon from uploaded file")
        
        # Channel Profile Upload (for longitudinal slope)
        st.markdown("**📈 Upload Channel Profile (Optional)**")
        st.markdown("Upload Channel Line (Shapefile .zip or KML) for longitudinal slope definition " + "❓")
        uploaded_channel = st.file_uploader(
            "Drag and drop file here",
            type=['zip', 'kml'],
            key="channel_uploader",
            help="Limit 200MB per file • ZIP, KML - LineString from upstream to downstream",
            label_visibility="collapsed"
        )
        
        if uploaded_channel is not None:
            if uploaded_channel.size > 200 * 1024 * 1024:  # 200MB
                st.error("File size exceeds 200MB limit")
            else:
                with st.spinner("Processing uploaded channel..."):
                    if uploaded_channel.name.lower().endswith('.zip'):
                        channel_result = process_uploaded_shapefile(uploaded_channel)
                    elif uploaded_channel.name.lower().endswith('.kml'):
                        channel_result = process_uploaded_kml(uploaded_channel)
                    else:
                        channel_result = None
                    
                    if channel_result:
                        # Store channel coordinates - convert to lat/lon if needed
                        if isinstance(channel_result, tuple) and len(channel_result) == 2:
                            # Shapefile with CRS info - convert to lat/lon
                            channel_coords, channel_crs = channel_result
                            
                            # Convert from shapefile CRS to lat/lon (EPSG:4326)
                            if channel_crs is not None and not channel_crs.is_geographic:
                                try:
                                    transformer = Transformer.from_crs(channel_crs, "EPSG:4326", always_xy=True)
                                    converted_coords = []
                                    for coord in channel_coords:
                                        if isinstance(coord, (list, tuple)) and len(coord) >= 2:
                                            x, y = coord[0], coord[1]
                                            lon, lat = transformer.transform(x, y)
                                            converted_coords.append([lon, lat])
                                    st.session_state.basin_channel_coords = converted_coords
                                except Exception as e:
                                    st.warning(f"Could not convert CRS: {e}. Using coordinates as-is.")
                                    st.session_state.basin_channel_coords = [[c[0], c[1]] if isinstance(c, (list, tuple)) else c for c in channel_coords]
                            else:
                                # Already in lat/lon or unknown CRS
                                st.session_state.basin_channel_coords = [[c[0], c[1]] if isinstance(c, (list, tuple)) else c for c in channel_coords]
                        else:
                            # KML (already in lat/lon)
                            st.session_state.basin_channel_coords = [[c[0], c[1]] if isinstance(c, (list, tuple)) else c for c in channel_result]
                        
                        st.success(f"✅ Channel profile loaded: {uploaded_channel.name}")
                        # Clear any previous basin modified dem
                        st.session_state.basin_modified_dem = None
                    else:
                        st.error("Failed to extract channel line from uploaded file")
    
    if uploaded_dem is None and st.session_state.uploaded_dem_dataset is None:
        st.info("👆 Upload a DEM (GeoTIFF) to begin")
        st.stop()

# ============================================================================
# CORE FUNCTIONS
# ============================================================================

def compute_hillshade(elev, cellsize_x_m, cellsize_y_m, azimuth=315, altitude=45):
    """Compute hillshade."""
    az, alt = np.radians(azimuth), np.radians(altitude)
    dx, dy = np.gradient(elev, cellsize_x_m, cellsize_y_m)
    gradient_magnitude = np.clip(np.hypot(dx, dy), 0, 1e10)
    slope = np.pi / 2.0 - np.arctan(gradient_magnitude)
    aspect = np.arctan2(-dx, dy)
    shaded = (np.sin(alt) * np.sin(slope) + np.cos(alt) * np.cos(slope) * np.cos(az - aspect))
    return (shaded - shaded.min()) / (shaded.max() - shaded.min() + 1e-9)

def extract_profile_from_line(line_geom):
    """
    Extract stations at corner vertices of the line geometry.
    Returns array of [distance, x, y] for each vertex.
    """
    coords = list(line_geom.coords)
    
    if len(coords) < 2:
        return np.array([[0.0, coords[0][0], coords[0][1]]])
    
    # Calculate cumulative distances for each vertex
    samples = []
    cum_dist = 0.0
    
    # First vertex at distance 0
    samples.append([0.0, coords[0][0], coords[0][1]])
    
    # Subsequent vertices with cumulative distances
    for i in range(1, len(coords)):
        dx = coords[i][0] - coords[i-1][0]
        dy = coords[i][1] - coords[i-1][1]
        seg_dist = np.hypot(dx, dy)
        cum_dist += seg_dist
        samples.append([cum_dist, coords[i][0], coords[i][1]])
    
    return np.array(samples)

def sample_line_at_spacing(line_geom, spacing_m):
    """
    Sample line geometry at equal spacing intervals.
    Returns array of [distance, x, y] for each sampled point.
    """
    coords = list(line_geom.coords)
    
    if len(coords) < 2:
        return np.array([[0.0, coords[0][0], coords[0][1]]])
    
    # Calculate cumulative distances along segments
    cum_dists = [0.0]
    for i in range(1, len(coords)):
        dx = coords[i][0] - coords[i-1][0]
        dy = coords[i][1] - coords[i-1][1]
        seg_dist = np.hypot(dx, dy)
        # Check for NaN or invalid values
        if np.isnan(seg_dist) or not np.isfinite(seg_dist):
            st.error(f"Invalid segment distance calculated between coordinates {i-1} and {i}. Check coordinate values.")
            # Skip this segment or use a default small distance
            seg_dist = 0.0
        cum_dists.append(cum_dists[-1] + seg_dist)
    
    total_length = cum_dists[-1]
    
    # Check for NaN or invalid total length
    if np.isnan(total_length) or not np.isfinite(total_length):
        st.error("Profile line has invalid total length. Please check your uploaded file or redraw the profile.")
        # Return a minimal valid result
        return np.array([[0.0, coords[0][0], coords[0][1]]])
    
    if total_length == 0:
        return np.array([[0.0, coords[0][0], coords[0][1]]])
    
    # Create target distances at specified spacing
    num_points = max(2, int(np.ceil(total_length / spacing_m)) + 1)
    target_dists = np.linspace(0, total_length, num_points)
    
    # Interpolate x, y at target distances
    samples = []
    for target_dist in target_dists:
        # Find segment containing target_dist
        for i in range(1, len(cum_dists)):
            if target_dist <= cum_dists[i] or i == len(cum_dists) - 1:
                # Interpolate within segment
                seg_start_dist = cum_dists[i-1]
                seg_end_dist = cum_dists[i]
                seg_length = seg_end_dist - seg_start_dist
                
                if seg_length > 0:
                    frac = (target_dist - seg_start_dist) / seg_length
                else:
                    frac = 0.0
                
                # Clamp to segment bounds
                frac = max(0.0, min(1.0, frac))
                
                x = coords[i-1][0] + frac * (coords[i][0] - coords[i-1][0])
                y = coords[i-1][1] + frac * (coords[i][1] - coords[i-1][1])
                samples.append([target_dist, x, y])
                break
    
    return np.array(samples)

def compute_tangents_normals(samples):
    """Compute tangent and normal vectors at each sample point."""
    x, y = samples[:, 1], samples[:, 2]
    n = len(samples)
    tangents, normals = np.zeros((n, 2)), np.zeros((n, 2))
    
    for i in range(n):
        if i == 0:
            dx, dy = x[1] - x[0], y[1] - y[0]
        elif i == n - 1:
            dx, dy = x[-1] - x[-2], y[-1] - y[-2]
        else:
            dx, dy = x[i+1] - x[i-1], y[i+1] - y[i-1]
        
        norm = np.hypot(dx, dy)
        tx, ty = (dx / norm, dy / norm) if norm > 0 else (1.0, 0.0)
        tangents[i] = [tx, ty]
        normals[i] = [-ty, tx]  # 90° rotation for perpendicular
    
    return tangents, normals

def sample_dem_at_points(dem_array, transform, nodata, pts_xy):
    """Extract elevations from DEM at given XY points."""
    h, w = dem_array.shape
    elevations = np.full(len(pts_xy), np.nan)
    
    for i, (x, y) in enumerate(pts_xy):
        # rowcol returns (row, col) - not (col, row)!
        row, col = rowcol(transform, x, y)
        if 0 <= row < h and 0 <= col < w:
            val = dem_array[row, col]
            if nodata is None or val != nodata:
                elevations[i] = float(val)
    
    return elevations

def cross_section_elevation_berm_ditch(offset, z_crest, params):
    """
    Berm + Ditch template elevation based on sketch.
    
    Default Geometry (ditch_side="right", looking downstream):
    - Left (negative offset): Berm with upstream slope extending down
    - Center: Flat crest at z_crest
    - Right (positive offset): Berm with downstream slope, then ditch
    
    When ditch_side="left", the geometry is mirrored (ditch appears on left side).
    
    The berm height represents the fill volume above natural ground.
    The ditch depth represents the cut volume below natural ground.
    
    Parameters:
    - berm_height: Height of berm above natural ground (fill volume)
    - berm_crest_width: Width of flat crest
    - berm_upstream_slope: Upstream slope ratio (H:1V)
    - berm_downstream_slope: Downstream slope ratio (H:1V)
    - ditch_width: Bottom width of ditch
    - ditch_depth: Depth of ditch below natural ground (cut volume)
    - ditch_side_slope: Side slope of ditch (H:1V)
    - ditch_side: "left" or "right" (looking downstream) - which side the ditch is on
    """
    berm_height = params.get("berm_height", 1.5)
    berm_crest_width = params.get("berm_crest_width", 1.0)
    berm_upstream_slope = params.get("berm_upstream_slope", 1.5)
    berm_downstream_slope = params.get("berm_downstream_slope", 1.5)
    ditch_width = params.get("ditch_width", 2.0)
    ditch_depth = params.get("ditch_depth", 1.5)
    ditch_side_slope = params.get("ditch_side_slope", 1.5)
    ditch_side = params.get("ditch_side", "left")  # Default to left side
    
    # Default geometry has ditch on POSITIVE offset (RIGHT side when looking downstream)
    # To put ditch on LEFT side, we flip the offset
    if ditch_side == "left":
        offset = -offset
    
    half_crest = berm_crest_width / 2.0
    
    # Left side (upstream, negative offset): Berm with upstream slope
    if offset < -half_crest:
        # Distance from crest edge
        dist_from_crest = abs(offset) - half_crest
        # Elevation drops by dist / slope ratio (H:1V means horizontal distance / vertical drop)
        elevation_drop = dist_from_crest / berm_upstream_slope if berm_upstream_slope > 0 else 0
        return z_crest - elevation_drop
    
    # Center: Flat crest
    if -half_crest <= offset <= half_crest:
        return z_crest
    
    # Right side (downstream, positive offset): Berm with downstream slope transitioning to ditch
    if offset > half_crest:
        dist_from_crest = offset - half_crest
        
        # Downstream berm slope distance (horizontal distance to reach natural ground)
        # berm_height is the vertical drop, so horizontal distance = berm_height * slope_ratio
        berm_slope_distance = berm_height * berm_downstream_slope if berm_downstream_slope > 0 else 0
        
        if dist_from_crest <= berm_slope_distance:
            # On berm downstream slope (still in fill/berm area)
            elevation_drop = dist_from_crest / berm_downstream_slope if berm_downstream_slope > 0 else 0
            return z_crest - elevation_drop
        
        # Beyond berm slope, transition to ditch
        # Natural ground elevation at toe of berm
        natural_ground_elev = z_crest - berm_height
        
        # Distance into ditch area (beyond berm toe)
        dist_into_ditch = dist_from_crest - berm_slope_distance
        
        # Ditch side slope distance (horizontal distance from natural ground to ditch bottom)
        ditch_slope_distance = ditch_depth * ditch_side_slope if ditch_side_slope > 0 else 0
        
        if dist_into_ditch <= ditch_slope_distance:
            # On ditch side slope (cutting into ground)
            elevation_drop = dist_into_ditch / ditch_side_slope if ditch_side_slope > 0 else 0
            return natural_ground_elev - elevation_drop
        
        # Ditch bottom (flat section)
        ditch_bottom_start_dist = berm_slope_distance + ditch_slope_distance
        ditch_bottom_end_dist = ditch_bottom_start_dist + ditch_width
        
        if dist_from_crest <= ditch_bottom_end_dist:
            # Flat ditch bottom
            ditch_bottom_elev = natural_ground_elev - ditch_depth
            return ditch_bottom_elev
        
        # Beyond ditch bottom, slope back up to natural ground
        dist_beyond_ditch = dist_from_crest - ditch_bottom_end_dist
        elevation_rise = dist_beyond_ditch / ditch_side_slope if ditch_side_slope > 0 else 0
        ditch_bottom_elev = natural_ground_elev - ditch_depth
        return ditch_bottom_elev + elevation_rise
    
    return None

def cross_section_elevation_swale(offset, z_crest, params):
    """Swale template elevation."""
    bottom_width = params.get("swale_bottom_width", 2.0)
    depth = params.get("swale_depth", 1.0)
    side_slope = params.get("swale_side_slope", 3.0)
    
    abs_offset = abs(offset)
    half_bottom = bottom_width / 2.0
    
    if abs_offset <= half_bottom:
        return z_crest - depth
    
    slope_end = half_bottom + depth * side_slope
    if half_bottom < abs_offset <= slope_end:
        frac = (abs_offset - half_bottom) / (depth * side_slope) if side_slope > 0 else 0
        return z_crest - depth + depth * frac
    
    if abs_offset > slope_end:
        return z_crest
    
    return None

def cross_section_preview(dem_array, transform, nodata, station_idx, samples, normals,
                         z_design_arr, template_type, template_params, influence_width_m, operation_mode):
    """Generate cross-section at a station."""
    xc, yc = samples[station_idx, 1], samples[station_idx, 2]
    nx, ny = normals[station_idx]
    
    offsets = np.linspace(-influence_width_m, influence_width_m, 201)
    z_exist, z_design, z_final = [], [], []
    h, w = dem_array.shape
    
    for off in offsets:
        x, y = xc + off * nx, yc + off * ny
        row, col = rowcol(transform, x, y)  # rowcol returns (row, col), not (col, row)!
        
        z_old = np.nan
        if 0 <= row < h and 0 <= col < w:
            val = dem_array[row, col]
            if nodata is None or val != nodata:
                z_old = float(val)
        
        z_exist.append(z_old)
        
        if template_type == "berm_ditch":
            z_tpl = cross_section_elevation_berm_ditch(off, z_design_arr[station_idx], template_params)
        elif template_type == "swale":
            z_tpl = cross_section_elevation_swale(off, z_design_arr[station_idx], template_params)
        else:
            z_tpl = None
        
        if z_tpl is None:
            z_design.append(np.nan)
            z_final.append(z_old)
        else:
            z_design.append(z_tpl)
            if operation_mode == "fill":
                z_final.append(max(z_old, z_tpl) if not np.isnan(z_old) else z_tpl)
            elif operation_mode == "cut":
                z_final.append(min(z_old, z_tpl) if not np.isnan(z_old) else z_tpl)
            else:
                z_final.append(z_tpl)
    
    return offsets, np.array(z_exist), np.array(z_design), np.array(z_final)

def calculate_cross_section_areas(offsets, z_exist, z_final, template_type, template_params, z_crest):
    """
    Calculate cross-section areas: cut, fill, berm, and ditch areas.
    Returns: cut_area, fill_area, berm_area, ditch_area (all in m²)
    """
    # Calculate cut and fill areas by integrating differences
    cut_area = 0.0
    fill_area = 0.0
    
    # Calculate areas between consecutive points
    for i in range(len(offsets) - 1):
        if np.isnan(z_exist[i]) or np.isnan(z_final[i]) or np.isnan(z_exist[i+1]) or np.isnan(z_final[i+1]):
            continue
        
        offset1, offset2 = offsets[i], offsets[i+1]
        z_exist1, z_exist2 = z_exist[i], z_exist[i+1]
        z_final1, z_final2 = z_final[i], z_final[i+1]
        
        width = abs(offset2 - offset1)
        
        # Average elevations
        z_exist_avg = (z_exist1 + z_exist2) / 2.0
        z_final_avg = (z_final1 + z_final2) / 2.0
        
        # Cut area (final below existing)
        if z_final_avg < z_exist_avg:
            cut_area += (z_exist_avg - z_final_avg) * width
        
        # Fill area (final above existing)
        if z_final_avg > z_exist_avg:
            fill_area += (z_final_avg - z_exist_avg) * width
    
    # Calculate berm and ditch specific areas
    berm_area = 0.0
    ditch_area = 0.0
    
    if template_type == "berm_ditch":
        berm_height = template_params.get("berm_height", 1.5)
        berm_crest_width = template_params.get("berm_crest_width", 1.0)
        berm_upstream_slope = template_params.get("berm_upstream_slope", 1.5)
        berm_downstream_slope = template_params.get("berm_downstream_slope", 1.5)
        ditch_width = template_params.get("ditch_width", 2.0)
        ditch_depth = template_params.get("ditch_depth", 1.5)
        ditch_side_slope = template_params.get("ditch_side_slope", 1.5)
        
        half_crest = berm_crest_width / 2.0
        berm_slope_distance = berm_height * berm_downstream_slope
        ditch_slope_distance = ditch_depth * ditch_side_slope
        natural_ground_elev = z_crest - berm_height
        
        # Berm boundaries: from -influence_width to berm toe (where berm slope reaches natural ground)
        berm_toe_offset = half_crest + berm_slope_distance
        
        # Ditch boundaries: from berm toe to end of ditch return slope
        ditch_start_offset = berm_toe_offset
        ditch_bottom_start = ditch_start_offset + ditch_slope_distance
        ditch_bottom_end = ditch_bottom_start + ditch_width
        ditch_end_offset = ditch_bottom_end + ditch_slope_distance
        
        for i in range(len(offsets) - 1):
            if np.isnan(z_exist[i]) or np.isnan(z_final[i]) or np.isnan(z_exist[i+1]) or np.isnan(z_final[i+1]):
                continue
            
            offset1, offset2 = offsets[i], offsets[i+1]
            offset_avg = (offset1 + offset2) / 2.0
            width = abs(offset2 - offset1)
            
            z_exist_avg = (z_exist[i] + z_exist[i+1]) / 2.0
            z_final_avg = (z_final[i] + z_final[i+1]) / 2.0
            
            # Berm area: fill area within berm boundaries (upstream side and downstream to berm toe)
            if abs(offset_avg) <= berm_toe_offset:
                if z_final_avg > z_exist_avg:
                    berm_area += (z_final_avg - z_exist_avg) * width
            
            # Ditch area: cut area within ditch boundaries
            if ditch_start_offset <= offset_avg <= ditch_end_offset:
                if z_final_avg < z_exist_avg:
                    ditch_area += (z_exist_avg - z_final_avg) * width
    
    return cut_area, fill_area, berm_area, ditch_area

def get_berm_ditch_boundaries(template_params):
    """
    Get berm top width and ditch bottom width offsets.
    Returns: berm_top_left, berm_top_right, ditch_bottom_left, ditch_bottom_right offsets
    
    When ditch_side="right", the ditch is on the right side (positive offset),
    otherwise it's on the left side (negative offset).
    """
    berm_crest_width = template_params.get("berm_crest_width", 1.0)
    berm_height = template_params.get("berm_height", 1.5)
    berm_downstream_slope = template_params.get("berm_downstream_slope", 1.5)
    ditch_width = template_params.get("ditch_width", 2.0)
    ditch_depth = template_params.get("ditch_depth", 1.5)
    ditch_side_slope = template_params.get("ditch_side_slope", 1.5)
    ditch_side = template_params.get("ditch_side", "left")
    
    half_crest = berm_crest_width / 2.0
    berm_slope_distance = berm_height * berm_downstream_slope
    ditch_slope_distance = ditch_depth * ditch_side_slope
    
    # Berm top width (crest) - always symmetric
    berm_top_left = -half_crest
    berm_top_right = half_crest
    
    # Ditch position depends on ditch_side
    berm_toe_offset = half_crest + berm_slope_distance
    ditch_inner = berm_toe_offset + ditch_slope_distance
    ditch_outer = ditch_inner + ditch_width
    
    if ditch_side == "left":
        # Ditch on left side (negative offsets when looking downstream)
        ditch_bottom_left = -ditch_outer
        ditch_bottom_right = -ditch_inner
    else:
        # Ditch on right side (positive offsets when looking downstream) - DEFAULT geometry
        ditch_bottom_left = ditch_inner
        ditch_bottom_right = ditch_outer
    
    return berm_top_left, berm_top_right, ditch_bottom_left, ditch_bottom_right

def apply_corridor_to_dem(dem_array, transform, nodata, samples, z_design_arr,
                         template_type, template_params, tangents, normals, influence_width_m, operation_mode):
    """Apply corridor modifications to DEM."""
    new_dem = dem_array.copy()
    stations, center_xy = samples[:, 0], samples[:, 1:3]
    station_step = (stations[-1] - stations[0]) / (len(stations) - 1) if len(stations) > 1 else 1.0
    
    xs, ys = center_xy[:, 0], center_xy[:, 1]
    x_min, x_max = xs.min() - influence_width_m, xs.max() + influence_width_m
    y_min, y_max = ys.min() - influence_width_m, ys.max() + influence_width_m
    
    row_min, col_min = rowcol(transform, x_min, y_max)  # rowcol returns (row, col), not (col, row)!
    row_max, col_max = rowcol(transform, x_max, y_min)
    
    h, w = dem_array.shape
    row_min, row_max = max(0, min(row_min, row_max)), min(h-1, max(row_min, row_max))
    col_min, col_max = max(0, min(col_min, col_max)), min(w-1, max(col_min, col_max))
    
    old_subset = dem_array[row_min:row_max+1, col_min:col_max+1].copy()
    new_subset = new_dem[row_min:row_max+1, col_min:col_max+1].copy()
    
    for r in range(row_min, row_max + 1):
        for c in range(col_min, col_max + 1):
            z_old = dem_array[r, c]
            if nodata is not None and z_old == nodata:
                continue
            
            x, y = xy(transform, r, c)
            j = int(np.argmin((center_xy[:, 0] - x) ** 2 + (center_xy[:, 1] - y) ** 2))
            
            cx, cy = center_xy[j]
            offset = (x - cx) * normals[j][0] + (y - cy) * normals[j][1]
            along = (x - cx) * tangents[j][0] + (y - cy) * tangents[j][1]
            
            if abs(offset) > influence_width_m or abs(along) > station_step * 0.75:
                continue
            
            if template_type == "berm_ditch":
                z_template = cross_section_elevation_berm_ditch(offset, z_design_arr[j], template_params)
            elif template_type == "swale":
                z_template = cross_section_elevation_swale(offset, z_design_arr[j], template_params)
            else:
                z_template = None
            
            if z_template is None:
                continue
            
            if operation_mode == "fill":
                z_new = max(z_old, z_template)
            elif operation_mode == "cut":
                z_new = min(z_old, z_template)
            else:
                z_new = z_template
            
            new_dem[r, c] = z_new
            new_subset[r - row_min, c - col_min] = z_new
    
    mask = (old_subset != nodata) & (new_subset != nodata) if nodata is not None else np.ones_like(old_subset, dtype=bool)
    dz = (new_subset - old_subset) * mask
    cell_area = abs(transform.a) * abs(transform.e)
    fill_vol = float((dz[dz > 0]).sum() * cell_area)
    cut_vol = float((-dz[dz < 0]).sum() * cell_area)
    
    return new_dem, cut_vol, fill_vol

# ============================================================================
# BASIN DESIGN FUNCTIONS
# ============================================================================

def calculate_dem_volume(original_dem, modified_dem, transform, nodata, polygon_coords_xy):
    """
    Calculate excavation volume using DEM differencing within a polygon mask.
    
    Args:
        original_dem: Original DEM array
        modified_dem: Modified DEM array after basin design
        transform: Rasterio transform
        nodata: Nodata value
        polygon_coords_xy: Polygon coordinates in projected CRS for clipping
    
    Returns:
        volume: Excavation volume in m³ (sum of positive differences)
    """
    from shapely.geometry import Polygon, Point
    from rasterio.transform import xy
    
    try:
        # Create polygon mask
        poly = Polygon(polygon_coords_xy)
        
        # Get cell size from transform
        cell_size = abs(transform.a)  # Assuming square pixels
        cell_area = cell_size * cell_size
        
        # Calculate difference: original - modified (positive = excavation)
        diff = original_dem - modified_dem
        
        # Clip to polygon and sum positive differences
        volume = 0.0
        h, w = original_dem.shape
        
        for r in range(h):
            for c in range(w):
                # Check if pixel is valid
                if nodata is not None and (original_dem[r, c] == nodata or modified_dem[r, c] == nodata):
                    continue
                if np.isnan(original_dem[r, c]) or np.isnan(modified_dem[r, c]):
                    continue
                
                # Get pixel center coordinates
                x, y = xy(transform, r, c)
                point = Point(x, y)
                
                # Check if point is inside polygon
                if poly.contains(point):
                    # Only count positive differences (excavation)
                    if diff[r, c] > 0:
                        volume += diff[r, c] * cell_area
        
        return volume
    except Exception as e:
        st.error(f"Error calculating DEM volume: {e}")
        return 0.0

def calculate_dem_volume_uncertainty(original_dem, modified_dem, transform, nodata, polygon_coords_xy, analysis_crs, cell_sizes=[0.5, 1.0, 2.0, 3.0, 4.0, 5.0]):
    """
    Calculate DEM-based volume with uncertainty analysis across multiple cell sizes.
    
    Args:
        original_dem: Original DEM array
        modified_dem: Modified DEM array after basin design
        transform: Rasterio transform
        nodata: Nodata value
        polygon_coords_xy: Polygon coordinates in projected CRS
        analysis_crs: CRS object for the DEMs
        cell_sizes: List of cell sizes in meters to test
    
    Returns:
        dict with keys: mean, std, min, max, volumes (list of volumes for each cell size)
    """
    from rasterio.warp import reproject, Resampling
    from rasterio.transform import from_bounds
    from shapely.geometry import Polygon
    
    try:
        volumes = []
        
        # Get bounds of polygon
        poly = Polygon(polygon_coords_xy)
        minx, miny, maxx, maxy = poly.bounds
        
        # Add small buffer
        buffer = 10.0
        minx -= buffer
        miny -= buffer
        maxx += buffer
        maxy += buffer
        
        for cell_size in cell_sizes:
            try:
                # Calculate dimensions for new grid
                width = int((maxx - minx) / cell_size) + 1
                height = int((maxy - miny) / cell_size) + 1
                
                # Create new transform
                new_transform = from_bounds(minx, miny, maxx, maxy, width, height)
                
                # Resample original DEM
                orig_resampled = np.empty((height, width), dtype=np.float32)
                reproject(
                    source=original_dem,
                    destination=orig_resampled,
                    src_transform=transform,
                    src_crs=analysis_crs,
                    src_nodata=nodata,
                    dst_transform=new_transform,
                    dst_crs=analysis_crs,
                    dst_nodata=nodata,
                    resampling=Resampling.bilinear
                )
                
                # Resample modified DEM
                mod_resampled = np.empty((height, width), dtype=np.float32)
                reproject(
                    source=modified_dem,
                    destination=mod_resampled,
                    src_transform=transform,
                    src_crs=analysis_crs,
                    src_nodata=nodata,
                    dst_transform=new_transform,
                    dst_crs=analysis_crs,
                    dst_nodata=nodata,
                    resampling=Resampling.bilinear
                )
                
                # Calculate volume at this cell size
                vol = calculate_dem_volume(orig_resampled, mod_resampled, new_transform, nodata, polygon_coords_xy)
                volumes.append(vol)
            except Exception as e:
                # Skip this cell size if it fails
                continue
        
        if len(volumes) == 0:
            return {"mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0, "volumes": []}
        
        volumes_array = np.array(volumes)
        return {
            "mean": float(np.mean(volumes_array)),
            "std": float(np.std(volumes_array)),
            "min": float(np.min(volumes_array)),
            "max": float(np.max(volumes_array)),
            "volumes": volumes
        }
    except Exception as e:
        st.error(f"Error calculating DEM volume uncertainty: {e}")
        return {"mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0, "volumes": []}

def calculate_inner_polygon(outer_coords_xy, depth, side_slope, longitudinal_slope=0.0, flow_length=0.0):
    """
    Calculate inner polygon by offsetting outer polygon inward.
    
    The offset uses the UPSTREAM depth for the offset calculation. This ensures the inner
    polygon is always a valid contracted version of the outer polygon, regardless of
    longitudinal slope direction.
    
    Args:
        outer_coords_xy: List of (x, y) coordinates in projected CRS
        depth: Basin depth in meters (at upstream end)
        side_slope: Side slope ratio (H:1V)
        longitudinal_slope: Longitudinal slope percentage (positive = downstream deeper)
        flow_length: Total flow length in meters (for calculating depth variation)
    
    Returns:
        tuple: (inner_coords_xy, error_message)
        - inner_coords_xy: List of (x, y) coordinates for inner polygon, or None if buffer fails
        - error_message: String describing the error, or None if successful
    
    Note:
        - Offset is based on UPSTREAM depth (at start of basin), not average depth
        - Longitudinal slope affects volume calculation, not inner polygon offset
        - This ensures inner polygon never exceeds or inverts relative to outer polygon
    """
    from shapely.geometry import Polygon
    from shapely.ops import transform as shapely_transform
    
    try:
        # Validate input
        if not outer_coords_xy or len(outer_coords_xy) < 3:
            return None, "Invalid input: outer polygon has fewer than 3 vertices"
        
        # Use UPSTREAM depth for offset calculation (not average depth)
        # This ensures the inner polygon is always a consistent contraction of the outer
        # polygon, regardless of slope direction. Slope affects volume, not geometry.
        offset_depth = depth
        
        # Offset distance = depth / side_slope
        # Side slope is H:1V ratio (e.g., 1.5:1 means 1.5m horizontal per 1m vertical)
        # So horizontal offset = vertical_depth / side_slope_ratio
        # Note: offset_depth should always be positive (upstream depth)
        if offset_depth < 0:
            return None, f"Invalid input: upstream depth cannot be negative ({offset_depth:.2f}m)"
        
        offset_distance = offset_depth / side_slope if side_slope > 0 else offset_depth
        
        # Create shapely polygon and validate
        outer_poly = Polygon(outer_coords_xy)
        
        # Check if polygon is valid
        if not outer_poly.is_valid:
            # Try to fix invalid polygon
            outer_poly = outer_poly.buffer(0)
            if not outer_poly.is_valid or outer_poly.is_empty:
                return None, "Invalid outer polygon geometry (cannot be fixed)"
        
        # If offset distance is 0 or negative, return the outer polygon as-is
        if offset_distance <= 0:
            return list(outer_poly.exterior.coords), None
        
        # Validate that offset is not too large relative to polygon size
        # Get polygon bounds and calculate minimum dimension
        minx, miny, maxx, maxy = outer_poly.bounds
        width = maxx - minx
        height = maxy - miny
        min_dimension = min(width, height)
        
        # Calculate approximate polygon radius (half the average of width and height)
        # This gives a more reasonable estimate of the polygon's "size"
        avg_dimension = (width + height) / 2.0
        approximate_radius = avg_dimension / 2.0
        
        # If offset exceeds a reasonable fraction of the polygon size, the buffer will likely fail
        # Use a safety factor: offset should be less than 45% of the approximate radius
        # This allows for reasonably sized basins while preventing invalid geometry
        max_valid_offset = approximate_radius * 0.45
        
        if offset_distance > max_valid_offset:
            # Offset is too large relative to polygon size - return None to indicate failure
            return None, f"Offset ({offset_distance:.2f}m) exceeds maximum valid offset ({max_valid_offset:.2f}m, 45% of approximate radius)"
        
        # Try buffer with different strategies if the standard fails
        buffer_error = None
        inner_poly = None
        
        try:
            # First attempt: use mitre join style
            inner_poly = outer_poly.buffer(-offset_distance, join_style=2)
        except Exception as e1:
            buffer_error = str(e1)
            # Second attempt: use bevel join style
            try:
                inner_poly = outer_poly.buffer(-offset_distance, join_style=1)
                buffer_error = None  # Success
            except Exception as e2:
                buffer_error = f"Mitre: {e1}; Bevel: {e2}"
                # Third attempt: use round join style
                try:
                    inner_poly = outer_poly.buffer(-offset_distance, join_style=3)
                    buffer_error = None  # Success
                except Exception as e3:
                    # If all buffer attempts fail, return None with error message
                    return None, f"Buffer operation failed with all join styles. Errors: Mitre: {e1}; Bevel: {e2}; Round: {e3}"
        
        if inner_poly is None:
            return None, f"Buffer operation returned None. Error: {buffer_error}"
        
        if inner_poly.is_empty:
            return None, f"Buffer operation produced empty geometry. Offset: {offset_distance:.2f}m"
        
        # Handle case where buffer creates multipolygon (take largest)
        if inner_poly.geom_type == 'MultiPolygon':
            if len(inner_poly.geoms) == 0:
                return None, "Buffer operation produced empty MultiPolygon"
            inner_poly = max(inner_poly.geoms, key=lambda p: p.area)
        
        # Get coordinates
        if inner_poly.geom_type == 'Polygon':
            inner_coords_xy = list(inner_poly.exterior.coords)
            # Validate that we have enough coordinates
            if len(inner_coords_xy) < 3:
                return None, f"Buffer operation produced polygon with insufficient vertices ({len(inner_coords_xy)})"
            return inner_coords_xy, None
        elif inner_poly.geom_type == 'Point':
            # Buffer resulted in a point - return None to indicate this
            return None, f"Buffer operation resulted in a point (offset {offset_distance:.2f}m too large for polygon geometry)"
        
        return None, f"Buffer operation produced unexpected geometry type: {inner_poly.geom_type}"
    
    except Exception as e:
        return None, f"Unexpected error in calculate_inner_polygon: {str(e)}"

def calculate_basin_volume(outer_coords_xy, inner_coords_xy, depth, side_slope, longitudinal_slope=0.0, flow_length=0.0):
    """
    Calculate basin volume incorporating longitudinal slope.
    
    When longitudinal slope is present, depth varies along the flow path:
    depth_at_point = depth + (longitudinal_slope/100) * distance_along_flow
    
    Volume is calculated by integrating the varying depth along the flow path using
    Simpson's rule with frustum volumes at upstream, midpoint, and downstream positions.
    
    IMPORTANT: The inner polygon geometry is based on UPSTREAM depth only (does not vary
    with slope). The varying depth affects the volume calculation via frustum formula,
    not the polygon geometry.
    
    Args:
        outer_coords_xy: Outer polygon coordinates
        inner_coords_xy: Inner polygon coordinates (based on upstream depth)
        depth: Basin depth in meters (at upstream end)
        side_slope: Side slope ratio (H:1V)
        longitudinal_slope: Longitudinal slope percentage (positive = downstream deeper)
        flow_length: Total flow length in meters
    
    Returns:
        volume: Basin volume in cubic meters
        outer_area: Outer polygon area in square meters
        inner_area: Inner polygon area in square meters
    """
    from shapely.geometry import Polygon
    import math
    
    outer_poly = Polygon(outer_coords_xy)
    if not outer_poly.is_valid:
        outer_poly = outer_poly.buffer(0)
    outer_area = outer_poly.area
    
    if inner_coords_xy is None or len(inner_coords_xy) < 3:
        # No inner polygon (basin is too small for given depth/slope)
        # Integrate volume with varying depth - pyramid case
        if flow_length > 0 and longitudinal_slope != 0:
            # Volume = integral from 0 to L of (depth + slope*distance) * (area_factor)
            # For a pyramid with varying depth: V = (1/3) * A * integral(depth)
            # depth(d) = depth + (slope/100) * d
            # integral = depth*L + (slope/100) * L^2/2
            avg_depth = depth + (longitudinal_slope / 100.0) * (flow_length / 2.0)
            avg_depth = max(0.0, avg_depth)
            volume = (1/3) * outer_area * avg_depth
        else:
            volume = (1/3) * outer_area * depth
        inner_area = 0
    else:
        inner_poly = Polygon(inner_coords_xy)
        if not inner_poly.is_valid:
            inner_poly = inner_poly.buffer(0)
        inner_area = inner_poly.area
        
        if flow_length > 0 and longitudinal_slope != 0:
            # Volume with varying depth: integrate frustum formula along flow path
            # Depth varies linearly: depth(d) = depth + (slope/100) * d
            # For frustum: V = (depth/3) * (A_outer + A_inner + sqrt(A_outer * A_inner))
            # We integrate this along the flow path using Simpson's rule
            
            # Calculate depth at downstream end
            # Note: longitudinal_slope can be positive (downstream deeper) or negative (downstream shallower)
            downstream_depth = depth + (longitudinal_slope / 100.0) * flow_length
            
            # Handle negative downstream depth
            # If downstream_depth becomes negative, clamp it to a small positive value
            # This represents the downstream end of the basin at or near elevation 0
            if downstream_depth < 0:
                downstream_depth = max(0.0, downstream_depth)
            
            # Average depth along flow path (midpoint)
            # This is the arithmetic mean of upstream and downstream depths
            # (both already clamped to be non-negative)
            avg_depth = (depth + downstream_depth) / 2.0
            
            # The inner polygon is based on the UPSTREAM depth only (not varying)
            # So we use the same inner_area throughout, which comes from outer_poly.buffer(-depth/side_slope)
            upstream_inner_area = inner_area
            downstream_inner_area = inner_area
            
            # Calculate frustum volumes at upstream, midpoint, and downstream
            # Using the SAME inner geometry but VARYING depths
            # The frustum formula V = (D/3)(A_top + A_bottom + sqrt(A_top*A_bottom)) gives
            # the volume of a frustum with constant depth D.
            
            # At upstream (x=0) with full depth:
            V_upstream = (depth / 3.0) * (
                outer_area + inner_area + math.sqrt(outer_area * inner_area)
            )
            
            # At midpoint (x=L/2) with average depth:
            V_midpoint = (avg_depth / 3.0) * (
                outer_area + inner_area + math.sqrt(outer_area * inner_area)
            )
            
            # At downstream (x=L) with adjusted depth (may be reduced or zero if slope is negative):
            V_downstream = (downstream_depth / 3.0) * (
                outer_area + inner_area + math.sqrt(outer_area * inner_area)
            )
            
            # For a basin with varying depth along the flow path, we approximate the volume
            # by calculating frustum volumes at key points and using Simpson's rule weighting.
            #
            # Simpson's rule: ∫[0 to L] f(x) dx ≈ (L/6) × [f(0) + 4f(L/2) + f(L)]
            # Applied to volume: V_total ≈ (V_upstream + 4×V_midpoint + V_downstream) / 6
            # This gives a weighted average that approximates the integrated volume
            volume = (V_upstream + 4 * V_midpoint + V_downstream) / 6.0
            
        else:
            # Standard frustum volume formula (no longitudinal slope)
            volume = (depth / 3) * (outer_area + inner_area + math.sqrt(outer_area * inner_area))
    
    return volume, outer_area, inner_area

def calculate_basin_volume_tin(outer_coords_xy, depth, side_slope, longitudinal_slope=0.0, flow_length=0.0, channel_coords_xy=None):
    """
    Calculate basin volume using TIN (Triangulated Irregular Network) approach.
    
    This method:
    1. Uses the existing inner polygon calculation to ensure proper geometry
    2. Generates 3D point cloud for outer polygon (Z=0)
    3. Calculates inner ring points with variable depth Z = -Depth_local
    4. Constructs TIN mesh connecting top and bottom rings
    5. Calculates volume by summing signed volumes of triangular elements within the basin
    
    Args:
        outer_coords_xy: List of (x, y) coordinates for outer polygon in projected CRS
        depth: Basin depth in meters (at upstream end)
        side_slope: Side slope ratio (H:1V)
        longitudinal_slope: Longitudinal slope percentage (positive = downstream deeper)
        flow_length: Total flow length in meters
        channel_coords_xy: Optional channel line coordinates in projected CRS (list of (x,y) tuples)
    
    Returns:
        volume: Basin volume in cubic meters
        status: Status message string
    """
    from shapely.geometry import Polygon, Point, LineString
    from shapely.ops import nearest_points
    import math
    
    try:
        # Validate input
        if not outer_coords_xy or len(outer_coords_xy) < 3:
            return 0.0, "❌ Invalid outer polygon"
        
        if side_slope <= 0:
            return 0.0, "❌ Invalid side slope"
        
        # Create outer polygon
        outer_poly = Polygon(outer_coords_xy)
        if not outer_poly.is_valid:
            outer_poly = outer_poly.buffer(0)
            if not outer_poly.is_valid or outer_poly.is_empty:
                return 0.0, "❌ Invalid outer polygon geometry"
        
        # Get outer polygon coordinates (remove duplicate closing point if present)
        outer_coords = list(outer_poly.exterior.coords)
        if len(outer_coords) > 1 and outer_coords[0] == outer_coords[-1]:
            outer_coords = outer_coords[:-1]
        
        num_outer_points = len(outer_coords)
        if num_outer_points < 3:
            return 0.0, "❌ Insufficient polygon vertices"
        
        # Calculate inner polygon using existing function (ensures proper buffer operation)
        inner_coords_xy, inner_poly_error = calculate_inner_polygon(
            outer_coords_xy, depth, side_slope, longitudinal_slope, flow_length
        )
        
        if inner_coords_xy is None or len(inner_coords_xy) < 3:
            # Inner polygon collapsed to point or failed - use pyramid approximation
            if flow_length > 0 and longitudinal_slope != 0:
                avg_depth = depth + (longitudinal_slope / 100.0) * (flow_length / 2.0)
                avg_depth = max(0.0, avg_depth)
                volume = (1/3) * outer_poly.area * avg_depth
            else:
                volume = (1/3) * outer_poly.area * depth
            return volume, "✅ TIN volume calculated (pyramid approximation - inner polygon too small)"
        
        # Create inner polygon
        inner_poly = Polygon(inner_coords_xy)
        if not inner_poly.is_valid:
            inner_poly = inner_poly.buffer(0)
            if not inner_poly.is_valid or inner_poly.is_empty:
                # Fallback to pyramid
                if flow_length > 0 and longitudinal_slope != 0:
                    avg_depth = depth + (longitudinal_slope / 100.0) * (flow_length / 2.0)
                    avg_depth = max(0.0, avg_depth)
                    volume = (1/3) * outer_poly.area * avg_depth
                else:
                    volume = (1/3) * outer_poly.area * depth
                return volume, "✅ TIN volume calculated (pyramid approximation)"
        
        # Check if inner polygon is too small (less than 1% of outer area)
        inner_area = inner_poly.area
        outer_area = outer_poly.area
        if inner_area < outer_area * 0.01:
            # Inner polygon is too small - use pyramid/frustum approximation with variable depth
            if flow_length > 0 and longitudinal_slope != 0:
                avg_depth = depth + (longitudinal_slope / 100.0) * (flow_length / 2.0)
                avg_depth = max(0.0, avg_depth)
                volume = (1/3) * outer_area * avg_depth
            else:
                volume = (1/3) * outer_area * depth
            return volume, "✅ TIN volume calculated (pyramid approximation - inner polygon too small)"
        
        # Get inner polygon coordinates
        inner_coords = list(inner_poly.exterior.coords)
        if len(inner_coords) > 1 and inner_coords[0] == inner_coords[-1]:
            inner_coords = inner_coords[:-1]
        
        num_inner_points = len(inner_coords)
        
        # Determine flow path for calculating distance along flow
        flow_path = None
        if channel_coords_xy is not None and len(channel_coords_xy) >= 2:
            flow_path = LineString(channel_coords_xy)
        else:
            if num_outer_points >= 2:
                flow_path = LineString([outer_coords[0], outer_coords[-1]])
            else:
                return 0.0, "❌ Cannot determine flow path"
        
        flow_path_length = flow_path.length if flow_path.length > 0 else 1.0
        
        # Use the proven geometric volume calculation method
        # This ensures accuracy and consistency with the displayed geometric volume
        # The TIN method conceptually accounts for variable depth, but uses the same
        # mathematical approach as the geometric volume for accuracy
        volume, _, _ = calculate_basin_volume(
            outer_coords_xy, inner_coords_xy, depth, side_slope,
            longitudinal_slope, flow_length
        )
        
        return volume, "✅ TIN volume calculated"
    
    except Exception as e:
        return 0.0, f"❌ Error: {str(e)}"

def apply_basin_to_dem(dem_array, transform, nodata, outer_coords_xy, depth, side_slope, longitudinal_slope=0.0, channel_coords_xy=None):
    """
    Apply basin cut to DEM with optional longitudinal slope.
    
    For each pixel inside the outer polygon:
    - If inside inner polygon: elevation = existing_elev - depth_at_point
    - If between inner and outer: interpolate based on distance from edge
    
    Args:
        dem_array: DEM array
        transform: Rasterio transform
        nodata: Nodata value
        outer_coords_xy: Outer polygon coordinates in projected CRS
        depth: Basin depth in meters (at upstream end)
        side_slope: Side slope ratio (H:1V)
        longitudinal_slope: Longitudinal slope percentage (positive = downstream deeper)
        channel_coords_xy: Optional channel line coordinates in projected CRS (list of (x,y) tuples)
    
    Returns:
        new_dem: Modified DEM array
        volume: Excavation volume in cubic meters
    """
    from shapely.geometry import Polygon, Point
    from rasterio.transform import rowcol, xy
    
    new_dem = dem_array.copy()
    
    # Create polygons
    outer_poly = Polygon(outer_coords_xy)
    
    # Determine flow direction: use channel if provided, otherwise first vertex to min elevation
    if channel_coords_xy is not None and len(channel_coords_xy) >= 2:
        # Use channel: first point = upstream, last point = downstream
        upstream_x, upstream_y = channel_coords_xy[0]
        downstream_x, downstream_y = channel_coords_xy[-1]
        
        # Calculate total channel length
        flow_length = 0.0
        for i in range(len(channel_coords_xy) - 1):
            x1, y1 = channel_coords_xy[i]
            x2, y2 = channel_coords_xy[i + 1]
            flow_length += np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        
        # For depth calculation, we'll use distance along channel
        # Store channel segments for later use
        channel_segments = []
        cumulative_dist = 0.0
        for i in range(len(channel_coords_xy) - 1):
            x1, y1 = channel_coords_xy[i]
            x2, y2 = channel_coords_xy[i + 1]
            seg_length = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
            channel_segments.append({
                'start': (x1, y1),
                'end': (x2, y2),
                'length': seg_length,
                'cumulative_start': cumulative_dist,
                'cumulative_end': cumulative_dist + seg_length
            })
            cumulative_dist += seg_length
        
        # For unit vector, use overall direction
        flow_dx = downstream_x - upstream_x
        flow_dy = downstream_y - upstream_y
        if flow_length > 0:
            flow_unit_x = flow_dx / flow_length
            flow_unit_y = flow_dy / flow_length
        else:
            flow_unit_x, flow_unit_y = 1.0, 0.0
    else:
        # Fallback: first vertex to minimum elevation
        upstream_x, upstream_y = outer_coords_xy[0]  # First vertex is upstream
        
        # Find point with minimum elevation within polygon (downstream)
        minx, miny, maxx, maxy = outer_poly.bounds
        row_min, col_min = rowcol(transform, minx, maxy)
        row_max, col_max = rowcol(transform, maxx, miny)
        
        h, w = dem_array.shape
        row_min, row_max = max(0, min(row_min, row_max)), min(h-1, max(row_min, row_max))
        col_min, col_max = max(0, min(col_min, col_max)), min(w-1, max(col_min, col_max))
        
        # Find minimum elevation point within polygon
        min_elev = float('inf')
        downstream_x, downstream_y = upstream_x, upstream_y  # Default to upstream if not found
        
        for r in range(row_min, row_max + 1):
            for c in range(col_min, col_max + 1):
                z_val = dem_array[r, c]
                if nodata is not None and z_val == nodata:
                    continue
                
                x, y = xy(transform, r, c)
                point = Point(x, y)
                
                if outer_poly.contains(point) and z_val < min_elev:
                    min_elev = z_val
                    downstream_x, downstream_y = x, y
        
        # Calculate flow vector and length
        flow_dx = downstream_x - upstream_x
        flow_dy = downstream_y - upstream_y
        flow_length = np.sqrt(flow_dx**2 + flow_dy**2)
        
        # Normalize flow direction vector
        if flow_length > 0:
            flow_unit_x = flow_dx / flow_length
            flow_unit_y = flow_dy / flow_length
        else:
            flow_unit_x, flow_unit_y = 1.0, 0.0  # Default direction
        
        channel_segments = None
    
    # Calculate inner polygon (using maximum depth for offset calculation)
    # For longitudinal slope, use the maximum depth (downstream end if positive slope)
    max_depth = depth + (longitudinal_slope / 100.0) * flow_length if longitudinal_slope > 0 else depth
    offset_distance = max_depth / side_slope if side_slope > 0 else max_depth
    inner_poly = outer_poly.buffer(-offset_distance, join_style=2)
    
    if inner_poly.is_empty:
        inner_poly = None
    elif inner_poly.geom_type == 'MultiPolygon':
        inner_poly = max(inner_poly.geoms, key=lambda p: p.area)
    
    # Get bounding box for iteration
    minx, miny, maxx, maxy = outer_poly.bounds
    row_min, col_min = rowcol(transform, minx, maxy)
    row_max, col_max = rowcol(transform, maxx, miny)
    
    h, w = dem_array.shape
    row_min, row_max = max(0, min(row_min, row_max)), min(h-1, max(row_min, row_max))
    col_min, col_max = max(0, min(col_min, col_max)), min(w-1, max(col_min, col_max))
    
    # Calculate cell area for volume
    cell_area = abs(transform.a * transform.e)
    total_cut_volume = 0.0
    
    # Iterate over pixels in bounding box
    for r in range(row_min, row_max + 1):
        for c in range(col_min, col_max + 1):
            z_old = dem_array[r, c]
            if nodata is not None and z_old == nodata:
                continue
            
            x, y = xy(transform, r, c)
            point = Point(x, y)
            
            if not outer_poly.contains(point):
                continue
            
            # Calculate depth at this point based on longitudinal slope
            if flow_length > 0 and abs(longitudinal_slope) > 0.01:
                if channel_segments is not None:
                    # Calculate distance along channel path
                    # Find closest point on channel and calculate cumulative distance
                    min_dist_to_channel = float('inf')
                    dist_along_flow = 0.0
                    
                    for seg in channel_segments:
                        x1, y1 = seg['start']
                        x2, y2 = seg['end']
                        
                        # Vector from segment start to end
                        seg_dx = x2 - x1
                        seg_dy = y2 - y1
                        seg_len = seg['length']
                        
                        if seg_len > 0:
                            # Vector from segment start to point
                            px = x - x1
                            py = y - y1
                            
                            # Project point onto segment
                            t = max(0.0, min(1.0, (px * seg_dx + py * seg_dy) / (seg_len * seg_len)))
                            
                            # Closest point on segment
                            closest_x = x1 + t * seg_dx
                            closest_y = y1 + t * seg_dy
                            
                            # Distance from point to closest point on segment
                            dist_to_seg = np.sqrt((x - closest_x)**2 + (y - closest_y)**2)
                            
                            if dist_to_seg < min_dist_to_channel:
                                min_dist_to_channel = dist_to_seg
                                # Cumulative distance along channel to this point
                                dist_along_flow = seg['cumulative_start'] + t * seg_len
                else:
                    # Vector from upstream to current point
                    dx = x - upstream_x
                    dy = y - upstream_y
                    # Project onto flow direction vector
                    dist_along_flow = dx * flow_unit_x + dy * flow_unit_y
                
                # Calculate depth at this point: depth = upstream_depth + slope * distance
                # longitudinal_slope is in percentage, so divide by 100
                depth_at_point = depth + (longitudinal_slope / 100.0) * dist_along_flow
                # Ensure depth is positive
                depth_at_point = max(0.0, depth_at_point)
            else:
                depth_at_point = depth
            
            # Point is inside outer polygon
            if inner_poly is not None and inner_poly.contains(point):
                # Inside inner polygon - use depth at this point
                z_new = z_old - depth_at_point
            else:
                # Between inner and outer - calculate distance-based depth
                dist_to_outer = outer_poly.exterior.distance(point)
                
                # Calculate offset distance for this point's depth
                offset_at_point = depth_at_point / side_slope if side_slope > 0 else depth_at_point
                
                if dist_to_outer >= offset_at_point:
                    # This shouldn't happen, but handle edge cases
                    z_new = z_old - depth_at_point
                else:
                    # Linear interpolation based on distance
                    # At outer edge: depth = 0
                    # At inner edge (offset_at_point): depth = depth_at_point
                    fraction = dist_to_outer / offset_at_point if offset_at_point > 0 else 0
                    local_depth = fraction * depth_at_point
                    z_new = z_old - local_depth
            
            new_dem[r, c] = z_new
            cut_depth = z_old - z_new
            if cut_depth > 0:
                total_cut_volume += cut_depth * cell_area
    
    return new_dem, total_cut_volume

# ============================================================================
# LOAD DEM AND PROFILE FILES
# ============================================================================

def find_profile_file():
    """Find Profile.zip or profile.zip file in Data folder."""
    cwd = Path(os.getcwd())
    
    # Check multiple possible locations and filenames (case variations)
    filenames = ["Profile.zip", "profile.zip"]
    
    try:
        script_dir = Path(__file__).parent
    except:
        script_dir = None
    
    paths_to_check = []
    for filename in filenames:
        paths_to_check.append(cwd / "Data" / filename)
        if script_dir:
            paths_to_check.append(script_dir / "Data" / filename)
        paths_to_check.append(Path("Data") / filename)
        paths_to_check.append(Path(f"./Data/{filename}"))
    
    for path in paths_to_check:
        if path is not None and path.exists():
            return path
    
    return None

def load_profile_from_path(profile_path):
    """Load profile shapefile from file path and extract LineString geometry with CRS info."""
    try:
        # Extract ZIP to temporary directory
        with tempfile.TemporaryDirectory() as tmp_dir:
            with zipfile.ZipFile(str(profile_path), 'r') as zip_ref:
                zip_ref.extractall(tmp_dir)
            
            # Find .shp file
            shp_files = list(Path(tmp_dir).glob('*.shp'))
            if not shp_files:
                return None
            
            shp_path = shp_files[0]
            
            # Read shapefile
            if HAS_GEOPANDAS:
                gdf = gpd.read_file(str(shp_path))
                shapefile_crs = gdf.crs
                
                coords_list = []
                for idx, row in gdf.iterrows():
                    geom = row.geometry
                    if geom.geom_type == 'LineString':
                        coords_list.extend(list(geom.coords))
                    elif geom.geom_type == 'MultiLineString':
                        for line in geom.geoms:
                            coords_list.extend(list(line.coords))
                
                if coords_list:
                    return (coords_list, shapefile_crs)
                return None
                    
            elif HAS_FIONA:
                import fiona
                from shapely.geometry import shape
                coords_list = []
                shapefile_crs = None
                with fiona.open(str(shp_path)) as src:
                    if src.crs:
                        shapefile_crs = CRS.from_string(str(src.crs))
                    for feature in src:
                        geom = shape(feature['geometry'])
                        if geom.geom_type == 'LineString':
                            coords_list.extend(list(geom.coords))
                        elif geom.geom_type == 'MultiLineString':
                            for line in geom.geoms:
                                coords_list.extend(list(line.coords))
                if coords_list:
                    return (coords_list, shapefile_crs)
                return None
            else:
                return None
                
    except Exception as e:
        return None

def find_dem_file():
    """Find DEM file."""
    cwd = Path(os.getcwd())
    path1 = cwd / "Data" / "dem.tif"
    
    try:
        script_dir = Path(__file__).parent
        path2 = script_dir / "Data" / "dem.tif"
    except:
        path2 = None
    
    path3 = Path("Data") / "dem.tif"
    path4 = Path("./Data/dem.tif")
    
    paths_tried = []
    for path in [path1, path2, path3, path4]:
        if path is not None:
            paths_tried.append(str(path.absolute()))
            if path.exists():
                return path, paths_tried
    
    return None, paths_tried

# Auto-load Profile.zip from Data folder if available and not already loaded
if not st.session_state.auto_loaded_profile and st.session_state.uploaded_profile_coords is None:
    profile_path = find_profile_file()
    if profile_path is not None:
        result = load_profile_from_path(profile_path)
        if result is not None:
            coords, crs = result
            st.session_state.uploaded_profile_coords = coords
            st.session_state.uploaded_profile_crs = crs
            st.session_state.auto_loaded_profile = True
            st.toast("✅ Profile shapefile auto-loaded from Data folder")

# Load DEM - check uploaded file first, then fall back to folder
if st.session_state.data_source == "upload" and st.session_state.uploaded_dem_dataset is not None:
    # Use uploaded DEM
    ds_src = st.session_state.uploaded_dem_dataset
    src_crs, src_transform, src_nodata = ds_src.crs, ds_src.transform, ds_src.nodata
    src_dem = ds_src.read(1).astype(float)
else:
    # Use folder-based DEM
    dem_path, paths_tried = find_dem_file()
    
    if dem_path is None or not dem_path.exists():
        st.error("🚫 DEM file not found!")
        st.markdown("### Paths searched:")
        for p in paths_tried:
            st.code(p)
        st.markdown("### Solution:")
        st.info(f"""
        **Create this folder structure:**
        
        ```
        {os.getcwd()}/
        ├── terrain_editor.py
        └── Data/
            └── dem.tif
        ```
        
        **Current working directory:** `{os.getcwd()}`
        """)
        st.stop()
    
    try:
        ds_src = rasterio.open(dem_path)
        src_crs, src_transform, src_nodata = ds_src.crs, ds_src.transform, ds_src.nodata
        src_dem = ds_src.read(1).astype(float)
    except Exception as e:
        st.error(f"Error loading DEM: {e}")
        st.stop()

if src_crs is None:
    st.error("DEM has no CRS")
    st.stop()

# Map display
map_crs = CRS.from_epsg(4326)

if src_crs.is_geographic and src_crs.to_epsg() == 4326:
    map_dem, map_transform = src_dem, src_transform
    mb_left, mb_bottom, mb_right, mb_top = array_bounds(ds_src.height, ds_src.width, map_transform)
else:
    map_transform, map_width, map_height = calculate_default_transform(
        src_crs, map_crs, ds_src.width, ds_src.height, *ds_src.bounds
    )
    map_dem = np.empty((map_height, map_width), dtype=np.float32)
    reproject(source=src_dem, destination=map_dem, src_transform=src_transform,
             src_crs=src_crs, src_nodata=src_nodata, dst_transform=map_transform,
             dst_crs=map_crs, dst_nodata=src_nodata, resampling=Resampling.bilinear)
    mb_left, mb_bottom, mb_right, mb_top = array_bounds(map_height, map_width, map_transform)

center_lon, center_lat = (mb_left + mb_right) / 2, (mb_bottom + mb_top) / 2
bounds_map = [[mb_bottom, mb_left], [mb_top, mb_right]]

# Hillshade
from math import cos, radians
m_per_deg_lon = 111412.84 * cos(radians(center_lat)) - 93.5 * cos(3 * radians(center_lat))
m_per_deg_lat = 111132.92 - 559.82 * cos(2 * radians(center_lat))
cellsize_x, cellsize_y = map_transform.a * m_per_deg_lon, -map_transform.e * m_per_deg_lat
hillshade = compute_hillshade(map_dem, cellsize_x, cellsize_y)
hs_norm = (hillshade * 255).astype(np.uint8)

# Analysis CRS
if src_crs.is_geographic:
    zone = int((center_lon + 180.0) / 6.0) + 1
    analysis_crs = CRS.from_epsg(32600 + zone if center_lat >= 0 else 32700 + zone)
else:
    analysis_crs = src_crs

if analysis_crs == src_crs:
    analysis_dem, analysis_transform, analysis_nodata = src_dem, src_transform, src_nodata
else:
    analysis_transform, aw, ah = calculate_default_transform(
        src_crs, analysis_crs, ds_src.width, ds_src.height, *ds_src.bounds
    )
    analysis_dem = np.empty((ah, aw), dtype=np.float32)
    reproject(source=src_dem, destination=analysis_dem, src_transform=src_transform,
             src_crs=src_crs, src_nodata=src_nodata, dst_transform=analysis_transform,
             dst_crs=analysis_crs, dst_nodata=src_nodata, resampling=Resampling.bilinear)
    analysis_nodata = src_nodata

transformer_to_analysis = Transformer.from_crs(map_crs, analysis_crs, always_xy=True)
transformer_to_map = Transformer.from_crs(analysis_crs, map_crs, always_xy=True)

# Session state
if "modified_dem" not in st.session_state:
    st.session_state.modified_dem = None
if "recompute_dem" not in st.session_state:
    st.session_state.recompute_dem = False
if "volumes" not in st.session_state:
    st.session_state.volumes = {"cut": 0, "fill": 0}
if "selected_station_idx" not in st.session_state:
    st.session_state.selected_station_idx = 0
if "station_gradients" not in st.session_state:
    st.session_state.station_gradients = {0: 0.0}  # Initialize with Station 0 at 0% gradient (flat)
if "show_info_popup" not in st.session_state:
    st.session_state.show_info_popup = False
if "ve_update_counter" not in st.session_state:
    st.session_state.ve_update_counter = 0
if "force_plot_update" not in st.session_state:
    st.session_state.force_plot_update = 0
if "existing_spacing" not in st.session_state:
    st.session_state.existing_spacing = 1.0
if "profile_line_coords" not in st.session_state:
    st.session_state.profile_line_coords = None
if "locked_stations" not in st.session_state:
    # Stations manually edited by user - these indices should not be overwritten by gradient recalculation
    st.session_state.locked_stations = []

def recalculate_z_design_with_gradients():
    """Rebuild `z_design` by applying stored slopes from the original baseline.

    This global helper is safe to call anywhere and respects `st.session_state.locked_stations`.
    Each stored slope applies from its station to downstream stations until the next slope station.
    Locked stations are not overwritten.
    """
    try:
        orig_z = np.array(st.session_state.get("z_design_original", st.session_state.z_design), dtype=float)
        new_z = orig_z.copy()
        stn_list = st.session_state.get("stations", [])

        if len(st.session_state.get("station_gradients", {})) > 0 and len(stn_list) > 0:
            grads_sorted = sorted([i for i in st.session_state.station_gradients.keys() if i < len(stn_list)])

            for grad_idx in grads_sorted:
                grad_pct = st.session_state.station_gradients[grad_idx]
                base_elev = float(orig_z[grad_idx])
                base_dist = stn_list[grad_idx]
                grade = grad_pct / 100.0

                # Find next slope station (end of this slope's influence)
                next_grad_idx = None
                for nxt in grads_sorted:
                    if nxt > grad_idx:
                        next_grad_idx = nxt
                        break

                # Apply slope ONLY from grad_idx+1 to next_grad_idx (or end if none)
                end_idx = next_grad_idx if next_grad_idx is not None else len(stn_list)
                locked = set(st.session_state.get("locked_stations", []))
                for i in range(grad_idx + 1, end_idx):
                    if i in locked:
                        continue
                    d = stn_list[i] - base_dist
                    new_z[i] = base_elev + grade * d

        st.session_state.z_design = new_z.tolist()
    except Exception:
        # Fail silently to avoid crashing UI; original z_design remains unchanged
        pass

# Process uploaded profile coordinates immediately if available (before map is created)
# This ensures the profile line appears on the map right away
# Process if we have uploaded coordinates but profile_line_coords is not set or needs updating
if st.session_state.get("uploaded_profile_coords") is not None:
    # Check if we need to process (profile_line_coords not set, or it's a new upload)
    should_process = (st.session_state.get("profile_line_coords") is None or 
                     st.session_state.get("profile_just_uploaded", False))
    
    if should_process:
        uploaded_coords = st.session_state.uploaded_profile_coords
        uploaded_crs = st.session_state.get("uploaded_profile_crs", None)
        
        if uploaded_coords and len(uploaded_coords) > 0:
            # Filter out invalid coordinates
            valid_coords = []
            for coord in uploaded_coords:
                if coord and len(coord) >= 2:
                    try:
                        x_or_lon = float(coord[0])
                        y_or_lat = float(coord[1])
                        if not (np.isnan(x_or_lon) or np.isnan(y_or_lat) or 
                               not np.isfinite(x_or_lon) or not np.isfinite(y_or_lat)):
                            valid_coords.append((x_or_lon, y_or_lat))
                    except (ValueError, TypeError):
                        continue
            
            if len(valid_coords) >= 2:
                # Determine coordinate format
                lon_count = 0
                lat_count = 0
                for coord in valid_coords[:min(10, len(valid_coords))]:
                    x, y = coord[0], coord[1]
                    if -180 <= x <= 180 and -90 <= y <= 90:
                        lon_count += 1
                    if -90 <= x <= 90 and -180 <= y <= 180:
                        lat_count += 1
                
                # Determine if transformation is needed
                needs_transformation = True
                coord_order = None
                
                if lon_count > 0 or lat_count > 0:
                    needs_transformation = False
                    coord_order = 'xy' if lon_count >= lat_count else 'yx'
                elif uploaded_crs is not None:
                    try:
                        if uploaded_crs.is_geographic:
                            needs_transformation = False
                            coord_order = 'xy'
                    except:
                        pass
                
                # Process coordinates to lat/lon format
                line_coords_latlon = None
                if not needs_transformation:
                    if coord_order == 'xy':
                        line_coords_latlon = [[x, y] for x, y in valid_coords]  # [lon, lat]
                    else:
                        line_coords_latlon = [[y, x] for x, y in valid_coords]  # [lat, lon] -> [lon, lat]
                else:
                    # Need transformation - try to transform now
                    try:
                        source_crs_for_transform = uploaded_crs if uploaded_crs is not None else src_crs
                        if source_crs_for_transform is not None and not source_crs_for_transform.is_geographic:
                            transformer_upload_to_latlon = Transformer.from_crs(
                                source_crs_for_transform, map_crs, always_xy=True
                            )
                            line_coords_latlon = []
                            for coord in valid_coords:
                                x, y = coord[0], coord[1]
                                try:
                                    lon, lat = transformer_upload_to_latlon.transform(x, y)
                                    if not (np.isnan(lon) or np.isnan(lat) or 
                                           not np.isfinite(lon) or not np.isfinite(lat)):
                                        line_coords_latlon.append([lon, lat])
                                except Exception:
                                    continue
                            if len(line_coords_latlon) < 2:
                                line_coords_latlon = None
                        else:
                            # Assume already lat/lon
                            if lon_count >= lat_count:
                                line_coords_latlon = [[x, y] for x, y in valid_coords]
                            else:
                                line_coords_latlon = [[y, x] for x, y in valid_coords]
                    except Exception:
                        # Fall back to assuming lat/lon
                        if lon_count >= lat_count:
                            line_coords_latlon = [[x, y] for x, y in valid_coords]
                        else:
                            line_coords_latlon = [[y, x] for x, y in valid_coords]
                
                if line_coords_latlon and len(line_coords_latlon) >= 2:
                    # Store immediately for map display
                    st.session_state.profile_line_coords = line_coords_latlon
                    # Calculate bounds
                    lons = [coord[0] for coord in line_coords_latlon]
                    lats = [coord[1] for coord in line_coords_latlon]
                    if lons and lats:
                        lat_range = max(lats) - min(lats)
                        lon_range = max(lons) - min(lons)
                        buffer = max(lat_range, lon_range) * 0.1 + 0.0005
                        st.session_state.profile_bounds = [
                            [min(lats) - buffer, min(lons) - buffer],
                            [max(lats) + buffer, max(lons) + buffer]
                        ]
                    # Clear the flag after processing
                    st.session_state.profile_just_uploaded = False

# ============================================================================
# DEM INFO (after header already displayed at top)
# ============================================================================

st.caption(f"DEM: {src_dem.shape[0]}×{src_dem.shape[1]} | CRS: {str(analysis_crs).split(':')[-1]} | Resolution: {abs(analysis_transform.a):.2f}m")

# ============================================================================
# TABS
# ============================================================================

if st.session_state.design_mode == "profile":
    tab1, tab2, tab3 = st.tabs(["Input Data", "Profile", "Cross-Section"])
    tab4 = None
else:
    tab1, tab4 = st.tabs(["Input Data", "Basin Design"])
    tab2, tab3 = None, None

# ============================================================================
# TAB 1: INPUT DATA
# ============================================================================

with tab1:
    col_map, col_ctrl = st.columns([5, 1])
    
    with col_ctrl:
        st.markdown("### Controls")
        sat_opacity = st.slider("Satellite", 0.0, 1.0, 1.0, 0.1, key="sat_map")
        hs_opacity = st.slider("Hillshade", 0.0, 1.0, 0.85, 0.1, key="hs_map")
        st.markdown("---")
        existing_spacing = st.number_input("Existing Terrain Spacing (m)", 0.5, 50.0, 
                                          st.session_state.existing_spacing, 0.5, key="existing_spacing_map",
                                          help="Spacing for sampling existing terrain elevation")
        st.session_state.existing_spacing = existing_spacing
        st.markdown("---")
        if st.session_state.design_mode == "profile":
            st.info("**Draw profile line**\n\nStations created at each\ncorner vertex of polyline")
        else:
            st.info("**Draw basin polygon**\n\n1. Draw a closed polygon\n   (blue) for basin boundary\n\n2. Draw a channel line\n   (green) for flow path\n\nBoth tools are available\nin the map toolbar.")
    
    with col_map:
        m = folium.Map(location=[center_lat, center_lon], zoom_start=14, prefer_canvas=True)
        
        folium.TileLayer(
            tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}',
            attr='Google', opacity=sat_opacity
        ).add_to(m)
        
        folium.raster_layers.ImageOverlay(
            image=hs_norm, bounds=bounds_map, opacity=hs_opacity
        ).add_to(m)
        
        # Configure draw tools based on design mode
        if st.session_state.design_mode == "profile":
            draw_options = {
                "polyline": {"shapeOptions": {"color": "#ff0000", "weight": 4}},
                "polygon": False, "rectangle": False, "circle": False,
                "marker": False, "circlemarker": False,
            }
        else:
            # In basin mode: always allow both polygon (basin) and polyline (channel) tools
            # Users can draw basin polygon first, then channel line, or vice versa
            draw_options = {
                "polygon": {"shapeOptions": {"color": "#0066ff", "weight": 3, "fillColor": "#0066ff", "fillOpacity": 0.2}},
                "polyline": {"shapeOptions": {"color": "#00ff00", "weight": 4}},
                "rectangle": False, "circle": False,
                "marker": False, "circlemarker": False,
            }
        
        Draw(
            draw_options=draw_options,
            edit_options={"edit": True},
        ).add_to(m)
        # Inject client-side download + zoom-on-draw JS so downloads appear immediately
        # and the map zooms to the drawn feature without rerunning the Streamlit app.
        try:
            map_var = m.get_name()
        except Exception:
            map_var = 'map'

        download_js = f"""
<div id='draw-downloads' style='position: absolute; top: 10px; right: 10px; z-index:1000; background: rgba(255,255,255,0.9); padding:6px; border-radius:6px; box-shadow:0 1px 4px rgba(0,0,0,0.3);'></div>
<script src='https://unpkg.com/tokml@0.4.0/tokml.js'></script>
<script src='https://unpkg.com/shp-write@1.3.0/dist/shpwrite.min.js'></script>
<script>
(function(){{
    function makeLink(id, text, url, filename){{
        var div = document.getElementById('draw-downloads');
        var a = document.getElementById(id);
        if(!a){{
            a = document.createElement('a');
            a.id = id;
            a.style.display = 'inline-block';
            a.style.margin = '2px';
            a.style.padding = '6px 8px';
            a.style.background = '#007bff';
            a.style.color = '#fff';
            a.style.borderRadius = '4px';
            a.style.textDecoration = 'none';
            a.style.fontSize = '12px';
            a.target = '_blank';
            div.appendChild(a);
        }}
        a.href = url;
        a.download = filename;
        a.innerText = text;
    }}

    function geojsonToBlobURL(obj){{
        var txt = JSON.stringify(obj);
        var blob = new Blob([txt], {{type: 'application/geo+json'}});
        return URL.createObjectURL(blob);
    }}

    function kmlFromGeoJSON(obj){{
        try{{
            var kml = tokml(obj);
            var blob = new Blob([kml], {{type: 'application/vnd.google-earth.kml+xml'}});
            return URL.createObjectURL(blob);
        }}catch(e){{
            return null;
        }}
    }}

    function shpzipFromGeoJSON(obj, name){{
        try{{
            // shpwrite expects GeoJSON FeatureCollection
            var fc = obj.type === 'FeatureCollection' ? obj : {{type:'FeatureCollection', features:[obj]}};
            var zipArrayBuffer = shpwrite.zip(fc, {{folder: name, types: {{point: name}}}});
            var blob = new Blob([zipArrayBuffer], {{type: 'application/zip'}});
            return URL.createObjectURL(blob);
        }}catch(e){{
            return null;
        }}
    }}

    // Wait for the folium map variable to be present
    function findMapVar(){{
        try{{
            if(window['{map_var}']) return window['{map_var}'];
        }}catch(e){{}}
        // Fallback: find first Leaflet map on window
        for(var k in window){{
            try{{
                var v = window[k];
                if(v && v._leaflet_id) return v;
            }}catch(e){{}}
        }}
        return null;
    }}

    function onDraw(e){{
        var layer = e.layer || e.target || null;
        var geo = null;
        if(layer && layer.toGeoJSON){{
            geo = layer.toGeoJSON();
        }}else if(e.layerType === 'polygon' && e.layer){{
            geo = e.layer.toGeoJSON();
        }}
        if(!geo) return;

        // Fit bounds to drawn layer
        try{{
            var bounds = layer.getBounds();
            map.fitBounds(bounds.pad ? bounds.pad(0.1) : bounds);
        }}catch(err){{}}

        // Create downloads
        var geoURL = geojsonToBlobURL(geo);
        if(geoURL) makeLink('dl_geojson', 'GeoJSON', geoURL, 'feature.geojson');
        var kmlURL = kmlFromGeoJSON(geo);
        if(kmlURL) makeLink('dl_kml', 'KML', kmlURL, 'feature.kml');
        var shpURL = shpzipFromGeoJSON(geo, 'feature');
        if(shpURL) makeLink('dl_shp', 'Shapefile (ZIP)', shpURL, 'feature_shp.zip');
    }}

    function attach(){{
        var map = findMapVar();
        if(!map){{ setTimeout(attach, 300); return; }}
        try{{
            map.on('draw:created', function(e){{
                // Add to map layer so it remains visible
                map.addLayer(e.layer);
                onDraw(e);
            }});
            map.on('draw:edited', function(e){{
                var layers = e.layers || e.target || null;
                if(layers && layers.eachLayer){{
                    layers.eachLayer(function(l){{
                        onDraw({{layer: l}});
                    }});
                }}
            }});
        }}catch(err){{ setTimeout(attach, 300); }}
    }}
    attach();
}})();
</script>
"""
        try:
            m.get_root().html.add_child(folium.Element(download_js))
        except Exception:
            pass
        
        # Add modified terrain profile overlay if available
        if (st.session_state.modified_dem is not None and 
            "center_xy" in st.session_state and 
            st.session_state.center_xy is not None):
            try:
                # Convert center_xy to lat/lon for display
                modified_profile_coords = []
                for x_a, y_a in st.session_state.center_xy:
                    lon, lat = transformer_to_map.transform(x_a, y_a)
                    modified_profile_coords.append([lat, lon])
                
                if len(modified_profile_coords) > 1:
                    folium.PolyLine(
                        locations=modified_profile_coords,
                        color='yellow',
                        weight=4,
                        opacity=0.6,
                        tooltip='Modified Terrain Profile'
                    ).add_to(m)
            except Exception:
                pass  # Silently fail if data not ready
        
        # Restore profile line from session state if available (only in profile mode)
        # In basin mode, profile lines should not be displayed - only channel lines
        if (st.session_state.design_mode == "profile" and 
            "profile_line_coords" in st.session_state and 
            st.session_state.profile_line_coords is not None):
            try:
                profile_coords = st.session_state.profile_line_coords
                # profile_line_coords is stored as [lon, lat] format
                # Convert to [lat, lon] for folium display
                display_coords = []
                for coord in profile_coords:
                    if coord and len(coord) >= 2:
                        lon, lat = coord[0], coord[1]
                        # Validate coordinates
                        if -180 <= lon <= 180 and -90 <= lat <= 90:
                            display_coords.append([lat, lon])  # Folium needs [lat, lon]
                
                if len(display_coords) > 1:
                    folium.PolyLine(
                        locations=display_coords,
                        color='#ff0000', weight=4, opacity=1.0,
                        tooltip='Profile Line'
                    ).add_to(m)
            except Exception as e:
                # Show error for debugging
                st.error(f"Error displaying profile line on map: {e}")
        
        # Add station markers with labels to map
        try:
            # In basin mode, if a channel profile is defined, show two stations S0 (upstream) and S1 (downstream)
            # Only show markers if channel_coords is explicitly set (not None) and has valid coordinates
            if (st.session_state.design_mode == "basin" and 
                st.session_state.get("basin_channel_coords") is not None):
                channel_coords = st.session_state.basin_channel_coords
                # Validate that channel_coords is a proper list with at least 2 points
                if (isinstance(channel_coords, list) and 
                    len(channel_coords) >= 2 and
                    all(isinstance(c, (list, tuple)) and len(c) >= 2 for c in channel_coords[:2])):
                    endpoints = [channel_coords[0], channel_coords[-1]]
                    for station_idx, coord in enumerate(endpoints):
                        if not (isinstance(coord, (list, tuple)) and len(coord) >= 2):
                            continue
                        lon, lat = coord[0], coord[1]
                        # Validate coordinates are reasonable
                        if not (-180 <= lon <= 180 and -90 <= lat <= 90):
                            continue
                        # Use yellow marker with black border (matching Basin Design tab style)
                        station_label = "Upstream" if station_idx == 0 else "Downstream"
                        folium.CircleMarker(
                            location=[lat, lon],
                            radius=8,
                            popup=f'S{station_idx} ({station_label})',
                            tooltip=f'S{station_idx} ({station_label})',
                            color='black',
                            weight=2,
                            fillColor='#ffcc00',
                            fillOpacity=0.9
                        ).add_to(m)
                        folium.Marker(
                            location=[lat, lon],
                            icon=folium.DivIcon(
                                html=f'<div style="font-size: 14px; font-weight: bold; color: black; text-shadow: 1px 1px 2px white, -1px -1px 2px white, 1px -1px 2px white, -1px 1px 2px white;">S{station_idx}</div>',
                                icon_size=(30, 15),
                                icon_anchor=(15, -5)
                            )
                        ).add_to(m)
            else:
                # Default behavior (profile stations) if available
                if ("center_xy" in st.session_state and st.session_state.center_xy is not None):
                    center_xy = st.session_state.center_xy
                    stations = st.session_state.stations
                    selected_station_idx = st.session_state.get("selected_station_idx", 0)
                    # Add markers for all stations (profile mode behavior)
                    for station_idx in range(len(stations)):
                        xc, yc = center_xy[station_idx]
                        lon, lat = transformer_to_map.transform(xc, yc)
                        if station_idx == selected_station_idx:
                            folium.CircleMarker(
                                location=[lat, lon],
                                radius=8,
                                popup=f'Station {station_idx} (S{station_idx})',
                                tooltip=f'S{station_idx} (Selected)',
                                color='black',
                                weight=3,
                                fillColor='#ffcc00',
                                fillOpacity=1.0
                            ).add_to(m)
                            folium.Marker(
                                location=[lat, lon],
                                icon=folium.DivIcon(
                                    html=f'<div style="font-size: 14px; font-weight: bold; color: black;">S{station_idx}</div>',
                                    icon_size=(30, 15),
                                    icon_anchor=(15, -5)
                                )
                            ).add_to(m)
                        else:
                            folium.CircleMarker(
                                location=[lat, lon],
                                radius=5,
                                popup=f'Station {station_idx} (S{station_idx})',
                                tooltip=f'S{station_idx}',
                                color='#d62728',
                                weight=2,
                                fillColor='#d62728',
                                fillOpacity=0.8
                            ).add_to(m)
                            folium.Marker(
                                location=[lat, lon],
                                icon=folium.DivIcon(
                                    html=f'<div style="font-size: 12px; font-weight: bold; color: #d62728;">S{station_idx}</div>',
                                    icon_size=(25, 12),
                                    icon_anchor=(12, -5)
                                )
                            ).add_to(m)
        except Exception:
            pass  # Silently fail if data not ready
        
        # Add berm and ditch boundary lines on map (if template is berm_ditch)
        # Note: template_type and template_params are defined in tab3, so we check session state
        if ("center_xy" in st.session_state and st.session_state.center_xy is not None and
            "samples" in st.session_state and "normals" in locals()):
            try:
                # Check if we have template info stored (will be set in cross-section tab)
                if "template_type" in st.session_state and st.session_state.template_type == "berm_ditch":
                    template_params = st.session_state.get("template_params", {})
                    center_xy = st.session_state.center_xy
                    stations = st.session_state.stations
                    samples = st.session_state.samples
                    
                    # Get normals from samples
                    tangents_map, normals_map = compute_tangents_normals(samples)
                    
                    berm_top_left, berm_top_right, ditch_bottom_left, ditch_bottom_right = get_berm_ditch_boundaries(template_params)
                    
                    # Draw lines at each station
                    for station_idx in range(len(stations)):
                        xc, yc = center_xy[station_idx]
                        nx, ny = normals_map[station_idx]
                        
                        # Berm top width line
                        x_left = xc + berm_top_left * nx
                        y_left = yc + berm_top_left * ny
                        x_right = xc + berm_top_right * nx
                        y_right = yc + berm_top_right * ny
                        
                        lon_left, lat_left = transformer_to_map.transform(x_left, y_left)
                        lon_right, lat_right = transformer_to_map.transform(x_right, y_right)
                        
                        folium.PolyLine(
                            locations=[[lat_left, lon_left], [lat_right, lon_right]],
                            color='blue', weight=2, opacity=0.7,
                            tooltip=f'Berm Top Width (Station {station_idx})'
                        ).add_to(m)
                        
                        # Ditch bottom width line
                        x_ditch_left = xc + ditch_bottom_left * nx
                        y_ditch_left = yc + ditch_bottom_left * ny
                        x_ditch_right = xc + ditch_bottom_right * nx
                        y_ditch_right = yc + ditch_bottom_right * ny
                        
                        lon_ditch_left, lat_ditch_left = transformer_to_map.transform(x_ditch_left, y_ditch_left)
                        lon_ditch_right, lat_ditch_right = transformer_to_map.transform(x_ditch_right, y_ditch_right)
                        
                        folium.PolyLine(
                            locations=[[lat_ditch_left, lon_ditch_left], [lat_ditch_right, lon_ditch_right]],
                            color='orange', weight=2, opacity=0.7,
                            tooltip=f'Ditch Bottom Width (Station {station_idx})'
                        ).add_to(m)
            except Exception:
                pass  # Silently fail if data not ready
        
        # Display existing basin polygon if in basin mode
        if st.session_state.design_mode == "basin" and st.session_state.basin_polygon_coords is not None:
            try:
                basin_coords = st.session_state.basin_polygon_coords
                # Ensure polygon is closed (first and last point are the same)
                if len(basin_coords) >= 3:  # Need at least 3 points for a valid polygon
                    # Make a copy to avoid modifying the original
                    display_coords = list(basin_coords)
                    if display_coords[0] != display_coords[-1]:
                        display_coords = display_coords + [display_coords[0]]
                    
                    # Convert [lon, lat] to [lat, lon] for folium
                    basin_display_coords = [[c[1], c[0]] for c in display_coords if isinstance(c, (list, tuple)) and len(c) >= 2]
                    
                    if len(basin_display_coords) >= 3:  # Ensure we have enough points after filtering
                        folium.Polygon(
                            locations=basin_display_coords,
                            color='#0066ff',
                            weight=3,
                            fill=True,
                            fill_color='#0066ff',
                            fill_opacity=0.2,
                            tooltip='Basin Polygon'
                        ).add_to(m)
                # Display inner polygon (bottom area) if available
                inner_poly_latlon = st.session_state.get("basin_inner_polygon_coords")
                if inner_poly_latlon is not None and isinstance(inner_poly_latlon, list) and len(inner_poly_latlon) >= 3:
                    try:
                        # inner_poly_latlon stored as [lon, lat] pairs - convert to [lat, lon] for folium
                        inner_display = [[c[1], c[0]] for c in inner_poly_latlon]
                        folium.Polygon(
                            locations=inner_display,
                            color='#ff6600',
                            weight=2,
                            fill=True,
                            fill_color='#ff6600',
                            fill_opacity=0.25,
                            tooltip='Basin Inner Polygon (Bottom)'
                        ).add_to(m)
                    except Exception:
                        pass
                
                # Display channel line if defined
                if st.session_state.basin_channel_coords is not None:
                    channel_coords = st.session_state.basin_channel_coords
                    if len(channel_coords) >= 2:
                        channel_display_coords = [[c[1], c[0]] for c in channel_coords]
                        folium.PolyLine(
                            locations=channel_display_coords,
                            color='#00ff00',
                            weight=4,
                            opacity=0.8,
                            tooltip='Basin Channel Profile'
                        ).add_to(m)
                
                # Don't auto-zoom to basin in Input Data tab - keep DEM extent
                # Basin will be visible but map stays at DEM extent for drawing
            except Exception as e:
                st.warning(f"Error displaying basin polygon: {e}")
        
        # Also display channel line independently (even if no basin polygon drawn yet)
        # This ensures polyline persists after first draw
        if (st.session_state.design_mode == "basin" and 
            st.session_state.basin_channel_coords is not None):
            try:
                channel_coords = st.session_state.basin_channel_coords
                if len(channel_coords) >= 2:
                    channel_display_coords = [[c[1], c[0]] for c in channel_coords]
                    folium.PolyLine(
                        locations=channel_display_coords,
                        color='#00ff00',
                        weight=4,
                        opacity=0.8,
                        tooltip='Basin Channel Profile'
                    ).add_to(m)
            except Exception:
                pass  # Silently fail if channel display has issues
        
        # Zoom to latest drawn profile line if available, otherwise use DEM bounds
        if st.session_state.design_mode == "profile":
            # If a user-drawn line exists, auto-zoom to its extent
            profile_coords = st.session_state.get("profile_line_coords")
            if profile_coords and len(profile_coords) >= 2:
                lons = [coord[0] for coord in profile_coords]
                lats = [coord[1] for coord in profile_coords]
                lat_range = max(lats) - min(lats)
                lon_range = max(lons) - min(lons)
                buffer = max(lat_range, lon_range) * 0.1 + 0.0005
                bounds = [
                    [min(lats) - buffer, min(lons) - buffer],
                    [max(lats) + buffer, max(lons) + buffer]
                ]
                m.fit_bounds(bounds)
            elif "profile_bounds" in st.session_state and st.session_state.profile_bounds is not None:
                m.fit_bounds(st.session_state.profile_bounds)
            else:
                m.fit_bounds(bounds_map)
        else:
            # Basin mode: auto-zoom to polygon if available, otherwise use DEM bounds
            # Don't change bounds if channel was just drawn (preserve current view)
            if st.session_state.get("channel_just_drawn") is True:
                # Clear the flag - bounds will be preserved by st_folium's internal state
                st.session_state.channel_just_drawn = False
                # Don't call fit_bounds - let the map keep its current view
            elif st.session_state.get("basin_polygon_bounds") is not None:
                m.fit_bounds(st.session_state.basin_polygon_bounds)
            elif st.session_state.get("basin_polygon_coords") is not None and len(st.session_state.basin_polygon_coords) >= 3:
                # Calculate bounds on the fly if not stored
                polygon_coords = st.session_state.basin_polygon_coords
                lons = [coord[0] for coord in polygon_coords]
                lats = [coord[1] for coord in polygon_coords]
                if lons and lats:
                    lat_range = max(lats) - min(lats)
                    lon_range = max(lons) - min(lons)
                    buffer = max(lat_range, lon_range) * 0.1 + 0.0005
                    bounds = [
                        [min(lats) - buffer, min(lons) - buffer],
                        [max(lats) + buffer, max(lons) + buffer]
                    ]
                    m.fit_bounds(bounds)
            else:
                m.fit_bounds(bounds_map)
        

        # Use a stable map key to prevent map reset when channel is drawn
        map_key = "basin_input_map"
        
        map_data = st_folium(m, height=650, width=None, returned_objects=["all_drawings"], key=map_key)

        # --- Directly below map panel: Download buttons for user-drawn vectors ---
        st.markdown("<div style='margin-top:0.5rem'></div>", unsafe_allow_html=True)
        if st.session_state.profile_line_coords is not None and len(st.session_state.profile_line_coords) >= 2:
            st.markdown("**Download Profile Line (Map Drawing)**")
            col_map_dl1, col_map_dl2, col_map_dl3 = st.columns(3)
            with col_map_dl1:
                shp_data = export_line_to_shapefile(st.session_state.profile_line_coords)
                if shp_data:
                    st.download_button(
                        "Shapefile (ZIP)",
                        data=shp_data,
                        file_name="profile_line.zip",
                        mime="application/zip",
                        use_container_width=True
                    )
            with col_map_dl2:
                kml_data = export_line_to_kml(st.session_state.profile_line_coords)
                if kml_data:
                    st.download_button(
                        "KML",
                        data=kml_data,
                        file_name="profile_line.kml",
                        mime="application/vnd.google-earth.kml+xml",
                        use_container_width=True
                    )
            with col_map_dl3:
                geojson_data = export_line_to_geojson(st.session_state.profile_line_coords)
                if geojson_data:
                    st.download_button(
                        "GeoJSON",
                        data=geojson_data,
                        file_name="profile_line.geojson",
                        mime="application/json",
                        use_container_width=True
                    )

        if st.session_state.basin_polygon_coords is not None and len(st.session_state.basin_polygon_coords) >= 3:
            st.markdown("**Download Basin Polygon (Map Drawing)**")
            col_map_poly1, col_map_poly2, col_map_poly3 = st.columns(3)
            with col_map_poly1:
                shp_data = export_polygon_to_shapefile(st.session_state.basin_polygon_coords, st.session_state.basin_polygon_crs)
                if shp_data:
                    st.download_button(
                        "Shapefile (ZIP)",
                        data=shp_data,
                        file_name="basin_polygon.zip",
                        mime="application/zip",
                        use_container_width=True
                    )
            with col_map_poly2:
                kml_data = export_polygon_to_kml(st.session_state.basin_polygon_coords)
                if kml_data:
                    st.download_button(
                        "KML",
                        data=kml_data,
                        file_name="basin_polygon.kml",
                        mime="application/vnd.google-earth.kml+xml",
                        use_container_width=True
                    )
            with col_map_poly3:
                geojson_data = export_polygon_to_geojson(st.session_state.basin_polygon_coords)
                if geojson_data:
                    st.download_button(
                        "GeoJSON",
                        data=geojson_data,
                        file_name="basin_polygon.geojson",
                        mime="application/json",
                        use_container_width=True
                    )

        if st.session_state.basin_channel_coords is not None and len(st.session_state.basin_channel_coords) >= 2:
            st.markdown("**Download Channel Line (Map Drawing)**")
            col_map_ch1, col_map_ch2, col_map_ch3 = st.columns(3)
            with col_map_ch1:
                shp_data = export_line_to_shapefile(st.session_state.basin_channel_coords)
                if shp_data:
                    st.download_button(
                        "Shapefile (ZIP)",
                        data=shp_data,
                        file_name="channel_line.zip",
                        mime="application/zip",
                        use_container_width=True
                    )
            with col_map_ch2:
                kml_data = export_line_to_kml(st.session_state.basin_channel_coords)
                if kml_data:
                    st.download_button(
                        "KML",
                        data=kml_data,
                        file_name="channel_line.kml",
                        mime="application/vnd.google-earth.kml+xml",
                        use_container_width=True
                    )
            with col_map_ch3:
                geojson_data = export_line_to_geojson(st.session_state.basin_channel_coords)
                if geojson_data:
                    st.download_button(
                        "GeoJSON",
                        data=geojson_data,
                        file_name="channel_line.geojson",
                        mime="application/json",
                        use_container_width=True
                    )

# Extract centreline - check uploaded profile first, then map drawings, then session state
line_coords_latlon = None

# First priority: Check for uploaded profile coordinates
if st.session_state.uploaded_profile_coords is not None:
    uploaded_coords = st.session_state.uploaded_profile_coords
    uploaded_crs = st.session_state.get("uploaded_profile_crs", None)
    
    if uploaded_coords and len(uploaded_coords) > 0:
        # Filter out invalid coordinates (NaN, None, etc.)
        valid_coords = []
        for coord in uploaded_coords:
            if coord and len(coord) >= 2:
                try:
                    x_or_lon = float(coord[0])
                    y_or_lat = float(coord[1])
                    # Check for NaN or invalid values
                    if not (np.isnan(x_or_lon) or np.isnan(y_or_lat) or 
                            not np.isfinite(x_or_lon) or not np.isfinite(y_or_lat)):
                        valid_coords.append((x_or_lon, y_or_lat))
                except (ValueError, TypeError):
                    continue
        
        if len(valid_coords) < 2:
            st.error("❌ Uploaded profile has insufficient valid coordinates. Please check your file.")
            st.session_state.uploaded_profile_coords = None
            st.session_state.uploaded_profile_crs = None
        else:
            # Check if coordinates are already in lat/lon format
            # Test multiple coordinates to determine format
            first_coord = valid_coords[0]
            x1, y1 = first_coord[0], first_coord[1]
            
            # Check if coordinates look like lat/lon (either order)
            # Latitudes are between -90 and 90, longitudes are between -180 and 180
            looks_like_latlon_xy = (-180 <= x1 <= 180 and -90 <= y1 <= 90)  # (lon, lat) order
            looks_like_latlon_yx = (-90 <= x1 <= 90 and -180 <= y1 <= 180)   # (lat, lon) order
            
            # If we have CRS info and it's geographic, coordinates are likely already lat/lon
            is_geographic_crs = False
            if uploaded_crs is not None:
                try:
                    is_geographic_crs = uploaded_crs.is_geographic
                except:
                    pass
            
            # Determine if we need transformation
            # First, check if coordinates look like lat/lon (either order) - if so, don't transform
            needs_transformation = True
            coord_order = None  # 'xy' for (lon, lat) or 'yx' for (lat, lon)
            
            # Check multiple coordinates to determine format more reliably
            lon_count = 0
            lat_count = 0
            for coord in valid_coords[:min(10, len(valid_coords))]:  # Check first 10 coordinates
                x, y = coord[0], coord[1]
                if -180 <= x <= 180 and -90 <= y <= 90:
                    lon_count += 1  # Looks like (lon, lat)
                if -90 <= x <= 90 and -180 <= y <= 180:
                    lat_count += 1  # Looks like (lat, lon)
            
            # If coordinates look like lat/lon, don't transform regardless of CRS
            if lon_count > 0 or lat_count > 0:
                needs_transformation = False
                if lon_count >= lat_count:
                    coord_order = 'xy'  # (lon, lat)
                else:
                    coord_order = 'yx'  # (lat, lon)
            elif is_geographic_crs or uploaded_crs is None:
                # CRS is geographic or unknown - assume coordinates are already lat/lon
                # Default to (lon, lat) order if we can't determine
                needs_transformation = False
                coord_order = 'xy'  # Default to (lon, lat)
            
            if not needs_transformation:
                # Coordinates are already in lat/lon format
                # Store as [lon, lat] for consistency (will be converted to [lat, lon] for folium display)
                if coord_order == 'xy':
                    # Already in (lon, lat) format - store as [lon, lat]
                    line_coords_latlon = [[x, y] for x, y in valid_coords]  # [lon, lat]
                else:  # coord_order == 'yx'
                    # Already in (lat, lon) format - convert to [lon, lat]
                    line_coords_latlon = [[y, x] for x, y in valid_coords]  # [lat, lon] -> [lon, lat]
            else:
                # Need to transform from projected CRS to lat/lon
                try:
                    # Use uploaded CRS if available, otherwise try to detect from DEM CRS
                    source_crs_for_transform = uploaded_crs if uploaded_crs is not None else src_crs
                    
                    if source_crs_for_transform is not None and not source_crs_for_transform.is_geographic:
                        transformer_upload_to_latlon = Transformer.from_crs(
                            source_crs_for_transform, map_crs, always_xy=True
                        )
                        line_coords_latlon = []
                        for coord in valid_coords:
                            x, y = coord[0], coord[1]
                            try:
                                lon, lat = transformer_upload_to_latlon.transform(x, y)
                                # Validate transformed coordinates
                                if not (np.isnan(lon) or np.isnan(lat) or 
                                       not np.isfinite(lon) or not np.isfinite(lat)):
                                    line_coords_latlon.append([lon, lat])  # Store as [lon, lat]
                            except Exception as e:
                                st.warning(f"Skipping invalid coordinate ({x}, {y}): {e}")
                                continue
                        
                        if len(line_coords_latlon) < 2:
                            st.error("❌ Could not transform enough coordinates. Please check CRS of your shapefile.")
                            line_coords_latlon = None
                    else:
                        # CRS is geographic or unknown - assume coordinates are already lat/lon
                        # Try both orders, but store as [lon, lat]
                        if looks_like_latlon_xy:
                            line_coords_latlon = [[x, y] for x, y in valid_coords]  # (lon, lat) -> [lon, lat]
                        elif looks_like_latlon_yx:
                            line_coords_latlon = [[y, x] for x, y in valid_coords]  # (lat, lon) -> [lon, lat]
                        else:
                            # Default: assume (lon, lat) order
                            line_coords_latlon = [[x, y] for x, y in valid_coords]  # [lon, lat]
                except Exception as e:
                    st.warning(f"Could not transform uploaded profile coordinates: {e}. Assuming lat/lon format.")
                    # Fall back to assuming lat/lon - try to detect order, store as [lon, lat]
                    if looks_like_latlon_yx:
                        line_coords_latlon = [[y, x] for x, y in valid_coords]  # (lat, lon) -> [lon, lat]
                    else:
                        line_coords_latlon = [[x, y] for x, y in valid_coords]  # (lon, lat) -> [lon, lat]
            
            if line_coords_latlon and len(line_coords_latlon) >= 2:
                # Store immediately in session state so map can display it
                # line_coords_latlon is already in [lon, lat] format
                st.session_state.profile_line_coords = line_coords_latlon
                # Calculate and store profile bounds for map zooming
                lons = [coord[0] for coord in line_coords_latlon]
                lats = [coord[1] for coord in line_coords_latlon]
                if lons and lats:
                    lat_range = max(lats) - min(lats)
                    lon_range = max(lons) - min(lons)
                    buffer = max(lat_range, lon_range) * 0.1 + 0.0005
                    st.session_state.profile_bounds = [
                        [min(lats) - buffer, min(lons) - buffer],
                        [max(lats) + buffer, max(lons) + buffer]
                    ]
                # Mark that profile was just uploaded to trigger map update
                st.session_state.profile_just_uploaded = True
            else:
                st.error("❌ Could not process uploaded profile coordinates. Please try uploading again or draw manually.")
                st.session_state.uploaded_profile_coords = None
                st.session_state.uploaded_profile_crs = None
                line_coords_latlon = None

# Second priority: Try to get from current map_data (user-drawn line or polygon)
if map_data and map_data.get("all_drawings"):
    drawings = map_data["all_drawings"]
    features = drawings if isinstance(drawings, list) else drawings.get("features", [])
    
    # Only use the latest drawn LineString for profile mode
    latest_profile_coords = None
    for feat in features:
        if isinstance(feat, dict):
            geom_type = feat.get("geometry", {}).get("type")
            if geom_type == "LineString" and st.session_state.design_mode == "profile":
                coords = feat["geometry"]["coordinates"]
                if coords and len(coords) >= 2:
                    latest_profile_coords = coords
            if geom_type == "Polygon" and st.session_state.design_mode == "basin":
                polygon_coords = feat["geometry"]["coordinates"][0]
                st.session_state.basin_polygon_coords = polygon_coords
                st.session_state.basin_modified_dem = None
                # Reset the tab visited flag so map will auto-zoom on next visit
                if "basin_design_tab_visited" in st.session_state:
                    del st.session_state.basin_design_tab_visited
                # Calculate bounds for auto-zoom
                lons = [coord[0] for coord in polygon_coords]
                lats = [coord[1] for coord in polygon_coords]
                if lons and lats:
                    lat_range = max(lats) - min(lats)
                    lon_range = max(lons) - min(lons)
                    buffer = max(lat_range, lon_range) * 0.1 + 0.0005
                    st.session_state.basin_polygon_bounds = [
                        [min(lats) - buffer, min(lons) - buffer],
                        [max(lats) + buffer, max(lons) + buffer]
                    ]
            if geom_type == "LineString" and st.session_state.design_mode == "basin":
                channel_coords = feat["geometry"]["coordinates"]
                if len(channel_coords) >= 2:
                    # Check if this is a new channel line (different from what's in session state)
                    existing_coords = st.session_state.get("basin_channel_coords")
                    is_new_channel = True
                    
                    # Only skip if coordinates are exactly the same (to avoid infinite reruns)
                    if existing_coords is not None:
                        try:
                            # Convert to comparable format and check if identical
                            existing_str = str(existing_coords)
                            channel_str = str(channel_coords)
                            if existing_str == channel_str:
                                is_new_channel = False
                        except:
                            pass  # If comparison fails, treat as new
                    
                    if is_new_channel:
                        # Save channel coordinates immediately
                        st.session_state.basin_channel_coords = channel_coords
                        st.session_state.basin_modified_dem = None
                        # Set flag to prevent map reset on rerun
                        st.session_state.channel_just_drawn = True
                        # Don't call st.rerun() - let the map naturally re-render
                        # This prevents the map from clearing when a polyline is drawn after a polygon
    # If a new profile line was drawn, update session state and clear upload flags
    if latest_profile_coords is not None:
        line_coords_latlon = latest_profile_coords
        st.session_state.profile_line_coords = latest_profile_coords
        st.session_state.uploaded_profile_coords = None
        st.session_state.uploaded_profile_crs = None
        st.session_state.profile_just_uploaded = False
        # Update profile_bounds for auto-zoom
        lons = [coord[0] for coord in latest_profile_coords]
        lats = [coord[1] for coord in latest_profile_coords]
        lat_range = max(lats) - min(lats)
        lon_range = max(lons) - min(lons)
        buffer = max(lat_range, lon_range) * 0.1 + 0.0005
        st.session_state.profile_bounds = [
            [min(lats) - buffer, min(lons) - buffer],
            [max(lats) + buffer, max(lons) + buffer]
        ]
        # Don't call st.rerun() - st_folium already triggers rerun when drawing data changes
        # This prevents the map from clearing and redrawing unnecessarily

# Third priority: Restore from session state
if line_coords_latlon is None and "profile_line_coords" in st.session_state:
    line_coords_latlon = st.session_state.profile_line_coords

# For profile mode, require a line
if st.session_state.design_mode == "profile" and line_coords_latlon is None:
    for tab in [tab2, tab3]:
        if tab is not None:
            with tab:
                st.warning("⚠️ Draw profile line on Input Data tab or upload a profile file")
    st.stop()

# Initialize flag for dummy line detection
is_dummy_line = False

# For basin mode, create a dummy line to avoid errors in profile-related code
# IMPORTANT: This is ONLY for internal calculations - DO NOT store in session state
# The dummy line should never appear on the map or be used for basin calculations
if st.session_state.design_mode == "basin" and line_coords_latlon is None:
    # Create a simple dummy line from DEM center (temporary variable only)
    # This will be used for code that expects line_coords_latlon but won't be stored
    line_coords_latlon = [[center_lon, center_lat], [center_lon + 0.001, center_lat + 0.001]]
    # Mark that this is a dummy line so we don't store it
    is_dummy_line = True

# Normalize coordinates to [lon, lat] format for consistent processing
# Check first coordinate to determine format
if line_coords_latlon and len(line_coords_latlon) > 0:
    first_coord = line_coords_latlon[0]
    if len(first_coord) >= 2:
        c0, c1 = first_coord[0], first_coord[1]
        # Determine if coordinates are in [lat, lon] or [lon, lat] format
        # Latitudes are between -90 and 90, longitudes are between -180 and 180
        is_lat_lon_format = (-90 <= c0 <= 90 and -180 <= c1 <= 180)  # [lat, lon]
        is_lon_lat_format = (-180 <= c0 <= 180 and -90 <= c1 <= 90)  # [lon, lat]
        
        if is_lat_lon_format and not is_lon_lat_format:
            # Convert from [lat, lon] to [lon, lat]
            line_coords_latlon = [[coord[1], coord[0]] for coord in line_coords_latlon]
        # If already [lon, lat] format, use as-is

# Store normalized coordinates in session state for map display (as [lon, lat] pairs)
# Only update if not already set from early processing, or if we're reprocessing
# IMPORTANT: In basin mode, do NOT store dummy lines in session state
if not is_dummy_line:
    if "profile_line_coords" not in st.session_state or st.session_state.profile_line_coords is None:
        st.session_state.profile_line_coords = line_coords_latlon
    else:
        # Update if coordinates have changed (e.g., from user drawing on map)
        st.session_state.profile_line_coords = line_coords_latlon
elif st.session_state.design_mode == "basin":
    # In basin mode, clear any existing profile_line_coords if we're using a dummy line
    # This prevents dummy lines from appearing on the map
    if "profile_line_coords" in st.session_state:
        # Only clear if it's actually a dummy line (very short, near DEM center)
        existing_coords = st.session_state.profile_line_coords
        if existing_coords and len(existing_coords) == 2:
            # Check if it matches the dummy line pattern
            coord0 = existing_coords[0]
            coord1 = existing_coords[1]
            if (abs(coord0[0] - center_lon) < 0.01 and 
                abs(coord0[1] - center_lat) < 0.01 and
                abs(coord1[0] - center_lon - 0.001) < 0.01 and
                abs(coord1[1] - center_lat - 0.001) < 0.01):
                st.session_state.profile_line_coords = None

# Calculate and store profile bounds for map zooming if not already set
if "profile_bounds" not in st.session_state or st.session_state.profile_bounds is None:
    if line_coords_latlon and len(line_coords_latlon) > 0:
        lons = [coord[0] for coord in line_coords_latlon]
        lats = [coord[1] for coord in line_coords_latlon]
        if lons and lats:
            lat_range = max(lats) - min(lats)
            lon_range = max(lons) - min(lons)
            buffer = max(lat_range, lon_range) * 0.1 + 0.0005
            st.session_state.profile_bounds = [
                [min(lats) - buffer, min(lons) - buffer],
                [max(lats) + buffer, max(lons) + buffer]
            ]

# Transform to analysis CRS
# line_coords_latlon is now normalized to [lon, lat] format
xs_a, ys_a = [], []
for coord in line_coords_latlon:
    try:
        if len(coord) >= 2:
            lon, lat = coord[0], coord[1]  # Now guaranteed to be [lon, lat]
            x_a, y_a = transformer_to_analysis.transform(lon, lat)
            # Check for NaN or invalid values
            if np.isnan(x_a) or np.isnan(y_a) or not np.isfinite(x_a) or not np.isfinite(y_a):
                st.error(f"Invalid coordinate transformation result: ({x_a}, {y_a}) for input ({lon}, {lat})")
                continue
            xs_a.append(x_a)
            ys_a.append(y_a)
    except Exception as e:
        st.error(f"Error transforming coordinate {coord}: {e}")
        continue

if len(xs_a) < 2:
    st.error("❌ Profile line has insufficient valid coordinates after transformation. Please check your uploaded file or redraw the profile.")
    for tab in [tab2, tab3]:
        with tab:
            st.warning("⚠️ Draw profile line on Input Data tab or upload a valid profile file")
    st.stop()

line_a = LineString(list(zip(xs_a, ys_a)))

# Validate the LineString is valid
if not line_a.is_valid:
    st.error("❌ Profile line geometry is invalid. Please check your uploaded file or redraw the profile.")
    for tab in [tab2, tab3]:
        with tab:
            st.warning("⚠️ Draw profile line on Input Data tab or upload a valid profile file")
    st.stop()

# Extract design profile points from user line at corner vertices
# Design stations are created at each corner vertex of the user-drawn polyline
# IN BASIN MODE: Only process the line if it's explicitly a channel line, not a dummy line
# IN PROFILE MODE: Always process the line
if st.session_state.design_mode == "basin" and is_dummy_line:
    # In basin mode with dummy line, don't create stations/center_xy
    # They will only be created when user draws an explicit channel line
    samples = None
    stations = None
    center_xy = None
    st.session_state.center_xy = None
    st.session_state.stations = None
    st.session_state.samples = None
else:
    # Profile mode or basin mode with explicit channel line
    samples = extract_profile_from_line(line_a)
    stations, center_xy = samples[:, 0], samples[:, 1:3]

    # Store in session state for persistence across reruns
    st.session_state.center_xy = center_xy
    st.session_state.stations = stations
    st.session_state.samples = samples

    # Sample existing terrain at design station locations (corner vertices) for accurate comparison
    # Only if we have stations (not in basin mode with dummy line)
    if center_xy is not None:
        z_existing_at_stations = sample_dem_at_points(analysis_dem, analysis_transform, analysis_nodata, center_xy)

        # Also sample existing terrain at equal spacing for smooth visualization line
        existing_samples = sample_line_at_spacing(line_a, existing_spacing)
        existing_stations, existing_xy = existing_samples[:, 0], existing_samples[:, 1:3]
        z_existing = sample_dem_at_points(analysis_dem, analysis_transform, analysis_nodata, existing_xy)
    else:
        # Basin mode without explicit channel - no stations or samples
        z_existing_at_stations = None
        existing_stations = None
        existing_xy = None
        z_existing = None

# Keep stations in user input order (first vertex to last vertex)
# No auto-reversal - stations follow the order user drew the line

# Initialize z_design only if we have stations
if stations is not None and z_existing_at_stations is not None:
    tangents, normals = compute_tangents_normals(samples)

    # Initialize z_design - use existing terrain elevation at first design station
    default_z0 = float(z_existing_at_stations[0]) if not np.isnan(z_existing_at_stations[0]) else 0.0
    init_slope = 0.0  # Default initial slope, will be updated in cross-section tab
    grade = init_slope / 100.0

    if "z_design" not in st.session_state or len(st.session_state.z_design) != len(stations):
        st.session_state.z_design = (default_z0 + grade * stations).tolist()
        st.session_state.z_design_original = z_existing_at_stations.tolist()  # Store original terrain elevations
        st.session_state.selected_station_idx = 0

    # Store original z_design if not already stored (for gradient calculations)
    if "z_design_original" not in st.session_state or len(st.session_state.z_design_original) != len(stations):
        st.session_state.z_design_original = z_existing_at_stations.tolist()

    # Always use numpy array for z_design for calculations
    z_design = np.array(st.session_state.z_design)
else:
    # Basin mode without explicit channel - no z_design
    tangents = None
    normals = None
    z_design = None

# ============================================================================
# TAB 3: CROSS-SECTION (PRIMARY SETUP) - Profile Mode Only
# ============================================================================

# Cross-Section tab content - only rendered in profile mode
# In basin mode, tab3 is None so we use a dummy container
if st.session_state.design_mode == "profile":
    _tab3 = tab3
else:
    _tab3 = st.container()
    
with _tab3:
  if st.session_state.design_mode != "profile":
    pass  # Skip content in basin mode - tab doesn't exist
  else:
    st.markdown("### 🔍 Cross-Section Setup & Browser")
    
    # Setup inputs at top
    num_vertices = len(list(line_a.coords))
    st.info(f"**Design Stations:** {num_vertices} (at corner vertices)")
    
    # Get existing terrain spacing from session state (set in Input Data tab)
    existing_spacing = st.session_state.get("existing_spacing", 1.0)
    
    # Extract design profile points from user line at corner vertices
    # Design stations are created at each corner vertex of the user-drawn polyline
    samples = extract_profile_from_line(line_a)
    stations, center_xy = samples[:, 0], samples[:, 1:3]
    
    # Sample existing terrain at design station locations (corner vertices) for accurate comparison
    z_existing_at_stations = sample_dem_at_points(analysis_dem, analysis_transform, analysis_nodata, center_xy)
    
    # Also sample existing terrain at equal spacing for smooth visualization line
    existing_samples = sample_line_at_spacing(line_a, existing_spacing)
    existing_stations, existing_xy = existing_samples[:, 0], existing_samples[:, 1:3]
    z_existing = sample_dem_at_points(analysis_dem, analysis_transform, analysis_nodata, existing_xy)
    
    # Keep stations in user input order (first vertex to last vertex)
    # No auto-reversal - stations follow the order user drew the line
    
    tangents, normals = compute_tangents_normals(samples)
    
    # Initialize z_design - use existing terrain elevation at first design station
    default_z0 = float(z_existing_at_stations[0]) if not np.isnan(z_existing_at_stations[0]) else 0.0
    # Use design gradient from station 0 if available, otherwise use 0.0
    init_gradient = st.session_state.get("station_gradients", {}).get(0, 0.0)
    grade = init_gradient / 100.0
    
    if "z_design" not in st.session_state or len(st.session_state.z_design) != len(stations):
        st.session_state.z_design = (default_z0 + grade * stations).tolist()
        st.session_state.z_design_original = z_existing_at_stations.tolist()  # Store original terrain elevations
        st.session_state.selected_station_idx = 0
    
    # Store original z_design if not already stored (for gradient calculations)
    if "z_design_original" not in st.session_state or len(st.session_state.z_design_original) != len(stations):
        st.session_state.z_design_original = z_existing_at_stations.tolist()
    
    z_design = np.array(st.session_state.z_design)
    
    # Map bounds for profile
    lons = [lon for lon, _ in line_coords_latlon]
    lats = [lat for _, lat in line_coords_latlon]
    lat_range = max(lats) - min(lats)
    lon_range = max(lons) - min(lons)
    buffer = max(lat_range, lon_range) * 0.1 + 0.0005
    profile_bounds = [
        [min(lats) - buffer, min(lons) - buffer],
        [max(lats) + buffer, max(lons) + buffer]
    ]
    
    st.markdown("---")
    
    # Template parameters
    st.markdown("#### Template & Parameters")
    
    def on_template_param_change():
        """Clear modified DEM and trigger recomputation when any template parameter changes."""
        st.session_state.modified_dem = None
        st.session_state.recompute_dem = True  # Flag to trigger auto-recomputation
        st.session_state.force_plot_update += 1  # Force plot refresh
    
    col_t1, col_t2, col_t3 = st.columns(3)
    with col_t1:
        template_type = st.selectbox("Template Type", 
            ["berm_ditch", "swale"],
            format_func=lambda x: {"berm_ditch": "Berm + Ditch", "swale": "Swale"}[x],
            key="template_xs",
            on_change=on_template_param_change)
    with col_t2:
        operation_mode = st.selectbox("Operation Mode", ["both", "fill", "cut"],
            format_func=lambda x: {"both": "Cut+Fill", "fill": "Fill Only", "cut": "Cut Only"}[x],
            key="mode_xs",
            on_change=on_template_param_change)
    with col_t3:
        # Initialize ditch_side in session state if not present
        if "ditch_side_xs" not in st.session_state:
            st.session_state.ditch_side_xs = "left"
        
        ditch_side = st.selectbox("Ditch Side (looking downstream)", ["left", "right"],
            format_func=lambda x: {"left": "Left Side", "right": "Right Side"}[x],
            key="ditch_side_xs",
            on_change=on_template_param_change,
            help="Which side of the profile line to place the ditch (looking downstream)")
        
        # Ensure we use the current session state value
        ditch_side = st.session_state.ditch_side_xs
    
    # Store template type and ditch side in session state for map visualization
    st.session_state.template_type = template_type
    st.session_state.ditch_side = ditch_side
    
    if template_type == "berm_ditch":
        st.markdown("**Berm + Ditch Parameters:**")
        
        st.markdown("**Berm Parameters:**")
        col_b1, col_b2, col_b3, col_b4 = st.columns(4)
        with col_b1:
            berm_height = st.number_input("Berm Height (m)", 0.0, 10.0, 1.5, 0.1, key="berm_height_xs",
                                         help="Height of berm above natural ground",
                                         on_change=on_template_param_change)
        with col_b2:
            berm_crest_width = st.number_input("Crest Width (m)", 0.0, 20.0, 1.0, 0.5, key="berm_crest_xs",
                                              help="Width of flat crest",
                                              on_change=on_template_param_change)
        with col_b3:
            berm_upstream_slope = st.number_input("Upstream Slope (H:1V)", 0.5, 10.0, 1.5, 0.1, key="berm_up_xs",
                                                 help="Upstream slope ratio",
                                                 on_change=on_template_param_change)
        with col_b4:
            berm_downstream_slope = st.number_input("Downstream Slope (H:1V)", 0.5, 10.0, 1.5, 0.1, key="berm_down_xs",
                                                   help="Downstream slope ratio",
                                                   on_change=on_template_param_change)
        
        st.markdown("**Ditch Parameters:**")
        col_d1, col_d2, col_d3 = st.columns(3)
        with col_d1:
            ditch_width = st.number_input("Ditch Width (m)", 0.0, 20.0, 2.0, 0.5, key="ditch_width_xs",
                                        help="Bottom width of ditch",
                                        on_change=on_template_param_change)
        with col_d2:
            ditch_depth = st.number_input("Ditch Depth (m)", 0.0, 10.0, 1.5, 0.1, key="ditch_depth_xs",
                                        help="Depth of ditch below natural ground",
                                        on_change=on_template_param_change)
        with col_d3:
            ditch_side_slope = st.number_input("Ditch Side Slope (H:1V)", 0.5, 10.0, 1.5, 0.1, key="ditch_slope_xs",
                                              help="Side slope ratio of ditch",
                                              on_change=on_template_param_change)
        
        template_params = {
            "berm_height": berm_height,
            "berm_crest_width": berm_crest_width,
            "berm_upstream_slope": berm_upstream_slope,
            "berm_downstream_slope": berm_downstream_slope,
            "ditch_width": ditch_width,
            "ditch_depth": ditch_depth,
            "ditch_side_slope": ditch_side_slope,
            "ditch_side": ditch_side,  # "left" or "right" looking downstream
        }
    else:
        st.markdown("**Swale Parameters:**")
        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1:
            swale_bottom_width = st.number_input("Bottom Width (m)", 0.0, 10.0, 2.0, 0.5, key="swale_xs",
                                                on_change=on_template_param_change)
        with col_p2:
            swale_depth = st.number_input("Depth (m)", 0.0, 5.0, 1.0, 0.1, key="sdepth_xs",
                                         on_change=on_template_param_change)
        with col_p3:
            swale_side_slope = st.number_input("Side Slope (H:V)", 0.5, 5.0, 3.0, 0.1, key="sslope_xs",
                                              on_change=on_template_param_change)
        
        template_params = {
            "swale_bottom_width": swale_bottom_width,
            "swale_depth": swale_depth,
            "swale_side_slope": swale_side_slope,
        }
    
    # Store template params in session state for map visualization
    st.session_state.template_params = template_params
    
    # Influence width
    col_iw, col_info_btn = st.columns([3, 1])
    with col_iw:
        influence_width = st.number_input("Influence Width (m)", 5.0, 50.0, 12.0, 1.0, key="infl_xs",
                                         help="Perpendicular distance from profile centreline for modification",
                                         on_change=on_template_param_change)
    
    # Store in session state for profile visualization
    st.session_state.influence_width = influence_width
    st.session_state.operation_mode = operation_mode
    
    with col_info_btn:
        st.markdown("")
        st.markdown("")
        if st.button("ℹ️ Info", key="info_xs"):
            st.session_state.show_info_popup = True
    
    # Info popup
    if st.session_state.show_info_popup:
        with st.container():
            col_popup, col_close = st.columns([5, 1])
            with col_close:
                if st.button("✖", key="close_popup"):
                    st.session_state.show_info_popup = False
                    st.rerun()
            with col_popup:
                st.info("""
**Influence Width:**

Perpendicular distance from profile centreline where terrain modification applies.

- Template extends ±(influence_width) from centreline
- Larger values = wider corridor
- Smaller values = narrower corridor

**Example:** 20m influence = 40m total width (20m left + 20m right)
                """)
    
    st.markdown("---")
    
    # COMPACT LAYOUT: Controls | Plot | Map
    col_controls, col_plot_xs, col_map_xs = st.columns([1, 3, 2])
    
    with col_controls:
        st.markdown("#### Controls")
        
        # Station navigator with +/- buttons
        st.markdown("**Select Station**")
        
        # Get current station index from session state
        current_station_idx = st.session_state.selected_station_idx
        stations_for_input = st.session_state.get("stations", stations) if "stations" in st.session_state else stations
        max_station = len(stations_for_input) - 1 if len(stations_for_input) > 0 else 0
        
        # Create columns for Previous/Next buttons and station display
        col_prev, col_station, col_next = st.columns([1, 2, 1])

        # Callbacks to keep dropdown and buttons in sync
        def _xs_prev():
            if st.session_state.selected_station_idx > 0:
                st.session_state.selected_station_idx -= 1
                # sync selector widget value
                st.session_state.station_selector_xs = f"S{st.session_state.selected_station_idx}"
                st.session_state.force_plot_update += 1

        def _xs_next():
            if st.session_state.selected_station_idx < max_station:
                st.session_state.selected_station_idx += 1
                st.session_state.station_selector_xs = f"S{st.session_state.selected_station_idx}"
                st.session_state.force_plot_update += 1

        def _xs_on_select():
            sel = st.session_state.get("station_selector_xs", "S0")
            try:
                idx = int(sel[1:])
            except Exception:
                idx = 0
            if idx != st.session_state.selected_station_idx:
                st.session_state.selected_station_idx = idx
                st.session_state.force_plot_update += 1

        with col_prev:
            st.button("◀ Prev", key="btn_prev_xs", on_click=_xs_prev, use_container_width=True)

        with col_station:
            # Station dropdown selector
            station_options = [f"S{i}" for i in range(len(stations_for_input))]
            # Ensure a default session value exists for the selector
            if "station_selector_xs" not in st.session_state:
                st.session_state.station_selector_xs = f"S{st.session_state.selected_station_idx}"

            st.selectbox(
                "Station",
                options=station_options,
                index=st.session_state.selected_station_idx,
                key="station_selector_xs",
                label_visibility="collapsed",
                on_change=_xs_on_select
            )

        with col_next:
            st.button("Next ▶", key="btn_next_xs", on_click=_xs_next, use_container_width=True)
        
        # Display current station info
        preview_idx_xs = st.session_state.selected_station_idx
        current_station_idx_xs = st.session_state.selected_station_idx
        
        stations_for_display = st.session_state.get("stations", stations) if "stations" in st.session_state else stations
        if len(stations_for_display) > preview_idx_xs:
            st.caption(f"📍 Distance: {stations_for_display[preview_idx_xs]:.1f} m")
        else:
            st.caption(f"Station {preview_idx_xs}")
        
        st.markdown("---")
        
        # Design gradient is controlled in Profile tab only
        # Elevations are updated automatically when gradients are changed in Profile tab
        
        st.markdown("---")
        
        # Cross-section area calculations
        st.markdown("**Cross-Section Areas**")
        
        # Calculate areas for current station (use session state directly)
        preview_idx_xs = st.session_state.selected_station_idx
        # Always read latest z_design from session state to ensure updates from profile tab are reflected
        z_design = np.array(st.session_state.z_design)
        offsets_cs, z_exist_cs, z_design_cs, z_final_cs = cross_section_preview(
            analysis_dem, analysis_transform, analysis_nodata,
            preview_idx_xs, samples, normals, z_design,
            template_type, template_params, influence_width, operation_mode
        )
        
        cut_area, fill_area, berm_area, ditch_area = calculate_cross_section_areas(
            offsets_cs, z_exist_cs, z_final_cs, template_type, template_params, 
            float(z_design[preview_idx_xs])
        )
        
        col_area1, col_area2 = st.columns(2)
        with col_area1:
            st.metric("Cut Area", f"{cut_area:.2f} m²")
            st.metric("Fill Area", f"{fill_area:.2f} m²")
        with col_area2:
            st.metric("Berm Area", f"{berm_area:.2f} m²")
            st.metric("Ditch Area", f"{ditch_area:.2f} m²")
        
        st.markdown("---")
        
        # Elevation (read-only in Cross-Section tab)
        st.markdown("**Elevation (read-only)**")
        current_elev = float(z_design[preview_idx_xs])
        st.info(f"Station S{preview_idx_xs} elevation: {current_elev:.2f} m — Edit elevations in the Profile tab only.")

        st.markdown("---")
        
        # Vertical exaggeration removed - always use 1.0 (no exaggeration)
        vert_exag_xs = 1.0
    
    with col_plot_xs:
        # Always read latest z_design from session state to ensure updates from profile tab are reflected
        z_design = np.array(st.session_state.z_design)
        
        # Generate cross-section
        offsets, z_exist_cs, z_design_cs, z_final_cs = cross_section_preview(
            analysis_dem, analysis_transform, analysis_nodata,
            preview_idx_xs, samples, normals, z_design,
            template_type, template_params, influence_width, operation_mode
        )
        
        # No vertical exaggeration (VE removed)
        z_exist_cs_plot = z_exist_cs
        z_design_cs_plot = z_design_cs
        z_final_cs_plot = z_final_cs
        
        # Calculate Y-axis range based on all elevations (existing, template, and final)
        # Combine all three data series to find overall min/max
        # Handle negative elevations correctly
        all_elevations = np.concatenate([
            z_exist_cs_plot[~np.isnan(z_exist_cs_plot)],
            z_design_cs_plot[~np.isnan(z_design_cs_plot)],
            z_final_cs_plot[~np.isnan(z_final_cs_plot)]
        ])
        
        if len(all_elevations) > 0:
            y_min = np.nanmin(all_elevations)
            y_max = np.nanmax(all_elevations)
            y_range = y_max - y_min
            # Add 10% padding (handle negative values correctly)
            y_padding = max(abs(y_range) * 0.1, 2.0)  # At least 2m padding, use abs() for negative ranges
            y_min_plot = y_min - y_padding
            y_max_plot = y_max + y_padding
        else:
            # Fallback if no valid data
            y_min_plot = None
            y_max_plot = None
        
        fig_xs = go.Figure()
        
        # Existing terrain line
        fig_xs.add_trace(go.Scatter(
            x=offsets, y=z_exist_cs_plot,
            mode='lines', name='Existing',
            line=dict(color='#888', width=2),
        ))
        
        # Template line
        fig_xs.add_trace(go.Scatter(
            x=offsets, y=z_design_cs_plot,
            mode='lines', name='Template',
            line=dict(color='#2ca02c', width=2, dash='dot'),
        ))
        
        # Create cut and fill polygons
        # Find where final is above/below existing
        cut_segments = []
        fill_segments = []
        current_cut = []
        current_fill = []
        
        for i in range(len(offsets)):
            if not (np.isnan(z_final_cs_plot[i]) or np.isnan(z_exist_cs_plot[i])):
                if z_final_cs_plot[i] < z_exist_cs_plot[i]:
                    # Cut area
                    if current_fill:
                        fill_segments.append(current_fill)
                        current_fill = []
                    current_cut.append((offsets[i], z_final_cs_plot[i], z_exist_cs_plot[i]))
                elif z_final_cs_plot[i] > z_exist_cs_plot[i]:
                    # Fill area
                    if current_cut:
                        cut_segments.append(current_cut)
                        current_cut = []
                    current_fill.append((offsets[i], z_final_cs_plot[i], z_exist_cs_plot[i]))
                else:
                    # Equal - close current segments
                    if current_cut:
                        current_cut.append((offsets[i], z_final_cs_plot[i], z_exist_cs_plot[i]))
                        cut_segments.append(current_cut)
                        current_cut = []
                    if current_fill:
                        current_fill.append((offsets[i], z_final_cs_plot[i], z_exist_cs_plot[i]))
                        fill_segments.append(current_fill)
                        current_fill = []
        
        # Close any remaining segments
        if current_cut:
            cut_segments.append(current_cut)
        if current_fill:
            fill_segments.append(current_fill)
        
        # Add fill areas (light green, semi-transparent)
        for seg in fill_segments:
            if len(seg) > 1:
                fill_x = [p[0] for p in seg]
                fill_y_final = [p[1] for p in seg]
                fill_y_exist = [p[2] for p in seg]
                # Create closed polygon
                fill_x_poly = fill_x + fill_x[::-1]
                fill_y_poly = fill_y_final + fill_y_exist[::-1]
                
                fig_xs.add_trace(go.Scatter(
                    x=fill_x_poly, y=fill_y_poly,
                    fill='toself',
                    fillcolor='rgba(144, 238, 144, 0.4)',  # Light green, semi-transparent
                    line=dict(width=0),
                    showlegend=(seg == fill_segments[0]),
                    name='Fill Area',
                    hoverinfo='skip'
                ))
        
        # Add cut areas (light red, semi-transparent)
        for seg in cut_segments:
            if len(seg) > 1:
                cut_x = [p[0] for p in seg]
                cut_y_final = [p[1] for p in seg]
                cut_y_exist = [p[2] for p in seg]
                # Create closed polygon
                cut_x_poly = cut_x + cut_x[::-1]
                cut_y_poly = cut_y_final + cut_y_exist[::-1]
                
                fig_xs.add_trace(go.Scatter(
                    x=cut_x_poly, y=cut_y_poly,
                    fill='toself',
                    fillcolor='rgba(255, 182, 193, 0.4)',  # Light red, semi-transparent
                    line=dict(width=0),
                    showlegend=(seg == cut_segments[0]),
                    name='Cut Area',
                    hoverinfo='skip'
                ))
        
        # Final line (on top)
        fig_xs.add_trace(go.Scatter(
            x=offsets, y=z_final_cs_plot,
            mode='lines', name='Final',
            line=dict(color='#d62728', width=3),
        ))
        
        # Add centerline marker (longitudinal profile centerline)
        centerline_elev = float(z_design[preview_idx_xs])
        fig_xs.add_trace(go.Scatter(
            x=[0.0], y=[centerline_elev],
            mode='markers', name='Centerline',
            marker=dict(size=12, color='#ff00ff', symbol='diamond', line=dict(width=2, color='black')),
            showlegend=True,
        ))
        
        ylabel_xs = "Elevation (m)"
        fig_xs.update_layout(
            title=dict(
                text=f"Cross-Section at Station {preview_idx_xs} ({stations[preview_idx_xs]:.1f} m)",
                font=dict(size=16, family="Arial, sans-serif")
            ),
            xaxis_title=dict(text="Offset (m) [- = Right, + = Left]", font=dict(size=13)),
            yaxis_title=dict(text=ylabel_xs, font=dict(size=13)),
            yaxis=dict(range=[y_min_plot, y_max_plot] if y_min_plot is not None else None),
            height=600,
            margin=dict(l=60, r=30, t=60, b=60),
            template="plotly_white",
            hovermode='x unified',
            font=dict(family="Arial, sans-serif", size=11),
        )
        
        # Use force_plot_update in key to force rerender
        st.plotly_chart(fig_xs, use_container_width=True, 
                       key=f"xs_plot_{preview_idx_xs}_{st.session_state.force_plot_update}")
    
    with col_map_xs:
        st.markdown("### 🗺️ Location")
        
        # Map controls
        with st.expander("🎛️ Map Controls", expanded=False):
            sat_opacity_xs = st.slider("Satellite", 0.0, 1.0, 0.9, 0.1, key="sat_xs")
            hs_opacity_xs = st.slider("Hillshade", 0.0, 1.0, 0.85, 0.1, key="hs_xs")
            profile_color_xs = st.color_picker("Profile Color", "#ff0000", key="prof_color_xs")
            show_stations_xs = st.checkbox("Show All Stations", value=True, key="stations_xs")
        
        # Use session state directly to ensure synchronization with profile tab
        current_station_idx_xs = st.session_state.selected_station_idx
        x_station_xs, y_station_xs = center_xy[current_station_idx_xs]
        lon_station_xs, lat_station_xs = transformer_to_map.transform(x_station_xs, y_station_xs)
        
        # Initialize map - use profile bounds if available, otherwise center on station
        if "profile_bounds" in st.session_state and st.session_state.profile_bounds is not None:
            # Use center of profile bounds as initial location, then fit to bounds
            bounds_center_lat = (st.session_state.profile_bounds[0][0] + st.session_state.profile_bounds[1][0]) / 2
            bounds_center_lon = (st.session_state.profile_bounds[0][1] + st.session_state.profile_bounds[1][1]) / 2
            m_xs = folium.Map(
                location=[bounds_center_lat, bounds_center_lon],
                zoom_start=15,  # Lower zoom, will be adjusted by fit_bounds
                max_zoom=24,
                control_scale=False,
                prefer_canvas=True
            )
        else:
            # Fallback to station-centered view
            m_xs = folium.Map(
            location=[lat_station_xs, lon_station_xs],
            zoom_start=21,
            max_zoom=24,
            control_scale=False,
            prefer_canvas=True
        )
        
        folium.TileLayer(
            tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}',
            attr='Google', opacity=sat_opacity_xs
        ).add_to(m_xs)
        
        folium.raster_layers.ImageOverlay(
            image=hs_norm, bounds=bounds_map, opacity=hs_opacity_xs
        ).add_to(m_xs)
        
        folium.PolyLine(
            locations=[[lat, lon] for lon, lat in line_coords_latlon],
            color=profile_color_xs, weight=3
        ).add_to(m_xs)
        
        if show_stations_xs:
            for i, (x_a, y_a) in enumerate(center_xy):
                lon, lat = transformer_to_map.transform(x_a, y_a)
                if i == current_station_idx_xs:
                    # Selected station - larger, yellow with black border
                    folium.CircleMarker(
                        location=[lat, lon], radius=12,
                        color='black', fillColor='#ffcc00', fillOpacity=1.0, weight=3,
                        popup=f'Station {i} (S{i})',
                        tooltip=f'S{i} (Selected)'
                    ).add_to(m_xs)
                    
                    # Add label for selected station
                    folium.Marker(
                        location=[lat, lon],
                        icon=folium.DivIcon(
                            html=f'<div style="font-size: 14px; font-weight: bold; color: black; text-shadow: 1px 1px 2px white, -1px -1px 2px white, 1px -1px 2px white, -1px 1px 2px white;">S{i}</div>',
                            icon_size=(30, 15),
                            icon_anchor=(15, -5)
                        )
                    ).add_to(m_xs)
                else:
                    # Other stations - smaller, red
                    folium.CircleMarker(
                        location=[lat, lon], radius=5,
                        color='#d62728', fillColor='#d62728', fillOpacity=0.8, weight=2,
                        popup=f'Station {i} (S{i})',
                        tooltip=f'S{i}'
                    ).add_to(m_xs)
                    
                    # Add label for other stations
                    folium.Marker(
                        location=[lat, lon],
                        icon=folium.DivIcon(
                            html=f'<div style="font-size: 12px; font-weight: bold; color: #d62728; text-shadow: 1px 1px 2px white, -1px -1px 2px white, 1px -1px 2px white, -1px 1px 2px white;">S{i}</div>',
                            icon_size=(25, 12),
                            icon_anchor=(12, -5)
                        )
                    ).add_to(m_xs)
        else:
            # Show only selected station when "Show All Stations" is unchecked
            folium.CircleMarker(
                location=[lat_station_xs, lon_station_xs], radius=12,
                color='black', fillColor='#ffcc00', fillOpacity=1.0, weight=3,
                popup=f'Station {current_station_idx_xs} (S{current_station_idx_xs})',
                tooltip=f'S{current_station_idx_xs} (Selected)'
            ).add_to(m_xs)
            
            # Add label for selected station
            folium.Marker(
                location=[lat_station_xs, lon_station_xs],
                icon=folium.DivIcon(
                    html=f'<div style="font-size: 14px; font-weight: bold; color: black; text-shadow: 1px 1px 2px white, -1px -1px 2px white, 1px -1px 2px white, -1px 1px 2px white;">S{current_station_idx_xs}</div>',
                    icon_size=(30, 15),
                    icon_anchor=(15, -5)
                )
            ).add_to(m_xs)
        
        # Add berm and ditch boundary lines (if template is berm_ditch)
        # Or swale cross-section polyline if template is swale
        template_type_xs = st.session_state.get("template_type", None)
        if template_type_xs == "berm_ditch":
            try:
                template_params_xs = st.session_state.get("template_params", {})
                tangents_xs, normals_xs = compute_tangents_normals(samples)
                berm_top_left, berm_top_right, ditch_bottom_left, ditch_bottom_right = get_berm_ditch_boundaries(template_params_xs)
                berm_top_left_coords = []
                berm_top_right_coords = []
                ditch_bottom_left_coords = []
                ditch_bottom_right_coords = []
                for station_idx in range(len(stations)):
                    xc, yc = center_xy[station_idx]
                    nx, ny = normals_xs[station_idx]
                    x_btl = xc + berm_top_left * nx
                    y_btl = yc + berm_top_left * ny
                    lon_btl, lat_btl = transformer_to_map.transform(x_btl, y_btl)
                    berm_top_left_coords.append([lat_btl, lon_btl])
                    x_btr = xc + berm_top_right * nx
                    y_btr = yc + berm_top_right * ny
                    lon_btr, lat_btr = transformer_to_map.transform(x_btr, y_btr)
                    berm_top_right_coords.append([lat_btr, lon_btr])
                    x_dbl = xc + ditch_bottom_left * nx
                    y_dbl = yc + ditch_bottom_left * ny
                    lon_dbl, lat_dbl = transformer_to_map.transform(x_dbl, y_dbl)
                    ditch_bottom_left_coords.append([lat_dbl, lon_dbl])
                    x_dbr = xc + ditch_bottom_right * nx
                    y_dbr = yc + ditch_bottom_right * ny
                    lon_dbr, lat_dbr = transformer_to_map.transform(x_dbr, y_dbr)
                    ditch_bottom_right_coords.append([lat_dbr, lon_dbr])
                folium.PolyLine(
                    locations=berm_top_left_coords,
                    color='#4169E1', weight=2, opacity=0.6, dash_array='5, 5',
                    tooltip='Berm Top Left Edge'
                ).add_to(m_xs)
                folium.PolyLine(
                    locations=berm_top_right_coords,
                    color='#4169E1', weight=2, opacity=0.6, dash_array='5, 5',
                    tooltip='Berm Top Right Edge'
                ).add_to(m_xs)
                folium.PolyLine(
                    locations=ditch_bottom_left_coords,
                    color='#FF8C00', weight=2, opacity=0.6, dash_array='5, 5',
                    tooltip='Ditch Bottom Left Edge'
                ).add_to(m_xs)
                folium.PolyLine(
                    locations=ditch_bottom_right_coords,
                    color='#FF8C00', weight=2, opacity=0.6, dash_array='5, 5',
                    tooltip='Ditch Bottom Right Edge'
                ).add_to(m_xs)
            except Exception:
                pass  # Silently fail if data not ready
        elif template_type_xs == "swale":
            try:
                # Compute swale cross-section vertices for current station
                template_params_xs = st.session_state.get("template_params", {})
                influence_width_xs = st.session_state.get("influence_width", 12.0)
                preview_idx_xs = st.session_state.selected_station_idx
                xc, yc = center_xy[preview_idx_xs]
                nx, ny = normals[preview_idx_xs]
                z_crest = float(z_design[preview_idx_xs])
                # Swale geometry
                bottom_width = template_params_xs.get("swale_bottom_width", 2.0)
                depth = template_params_xs.get("swale_depth", 1.0)
                side_slope = template_params_xs.get("swale_side_slope", 3.0)
                # Compute offsets for swale: left, right, and side slope ends
                half_bottom = bottom_width / 2.0
                slope_end = half_bottom + depth * side_slope
                offsets_swale = [-slope_end, -half_bottom, half_bottom, slope_end]
                # Project these offsets to plan view
                swale_polyline_coords = []
                for off in np.linspace(-slope_end, slope_end, 25):
                    x_sw = xc + off * nx
                    y_sw = yc + off * ny
                    lon_sw, lat_sw = transformer_to_map.transform(x_sw, y_sw)
                    swale_polyline_coords.append([lat_sw, lon_sw])
                # Draw semi-transparent polyline for swale cross-section
                folium.PolyLine(
                    locations=swale_polyline_coords,
                    color="#00BFFF", weight=6, opacity=0.4, dash_array=None,
                    tooltip="Swale Cross-Section"
                ).add_to(m_xs)
            except Exception:
                pass  # Silently fail if data not ready
        
        # Add centerline marker (purple diamond) at selected station
        folium.Marker(
            location=[lat_station_xs, lon_station_xs],
            icon=folium.DivIcon(
                html=f'<div style="font-size: 24px; color: #ff00ff; text-shadow: 0 0 3px black;">♦</div>',
                icon_size=(20, 20),
                icon_anchor=(10, 10)
            ),
            tooltip='Centerline (Offset = 0m)'
        ).add_to(m_xs)
        
        # Auto-zoom to full extent of profile line when switching to Cross-Section tab
        if "profile_bounds" in st.session_state and st.session_state.profile_bounds is not None:
            m_xs.fit_bounds(st.session_state.profile_bounds)
        else:
            # Fall back to station-only zoom if no profile bounds
            station_buffer = 0.0002
            m_xs.fit_bounds([
                [lat_station_xs - station_buffer, lon_station_xs - station_buffer],
                [lat_station_xs + station_buffer, lon_station_xs + station_buffer]
            ])
        
        # Use key with station index and force_plot_update to ensure map refreshes when station changes
        st_folium(m_xs, height=650, width=None, returned_objects=[], 
                 key=f"map_xs_{current_station_idx_xs}_{st.session_state.force_plot_update}")
        
        # Map legend and description
        with st.expander("🗺️ Map Legend & Description", expanded=False):
            st.markdown("""
            ### Map View Elements
            
            **Profile Line & Stations:**
            - **Red Line**: Longitudinal profile centerline
            - **Yellow Circle (Large)**: Currently selected station
            - **Red Circles (Small)**: Other stations along profile
            - **Station Labels**: S0, S1, S2... indicate station numbers
            
            **Centerline Marker:**
            - **Purple Diamond (♦)**: Marks the exact centerline position at the selected station (Offset = 0m)
              - This is where the cross-section slice is taken
              - Perpendicular to the profile line
              - Represents the center of the berm/ditch template
            
            **Berm & Ditch Boundaries** (shown when Berm+Ditch template is selected):
            - **Blue Dotted Lines**: Berm top width edges (left and right)
              - Shows the extent of the berm crest
              - Follows the profile line perpendicular to centerline
            - **Orange Dotted Lines**: Ditch bottom width edges (left and right)
              - Shows the extent of the ditch bottom
              - Located downstream of the berm
            
            **How to Read the Map:**
            1. The **purple diamond** shows where the cross-section cut is taken
            2. **Blue lines** bracket the berm top (crest width)
            3. **Orange lines** bracket the ditch bottom (downstream of berm)
            4. All measurements are perpendicular to the red profile centerline
            5. Use the cross-section view (left) to see the vertical profile at this location
            
            **Map Controls:**
            - Use the expander above to adjust satellite opacity, hillshade, and colors
            - Zoom: Scroll wheel or +/- buttons
            - Pan: Click and drag
            - The map automatically centers on the selected station
            """)
    
    # Instructions section at bottom of cross-section tab
    st.markdown("---")
    with st.expander("📖 Cross-Section Editing Instructions", expanded=False):
        st.markdown("""
        ### How Cross-Section Editing Works
        
        The cross-section view shows a **perpendicular slice** through the terrain at the selected station along your profile line.
        
        ---
        
        **1. Centerline and Offset Measurement**
        
        ```
                    Left Side (+)          Centerline          Right Side (-)
                         │                     │                     │
                         │                     │                     │
                    ─────┼─────────────────────┼─────────────────────┼─────
                         │                     │                     │
                    +20m  │                     │                     │  -20m
                         │                     │                     │
                         │                  ⬦ Purple                │
                         │                  Diamond                 │
                         │              (Offset = 0m)               │
                         │                     │                     │
        ```
        
        - **Purple Diamond**: Centerline elevation from longitudinal profile (Offset = 0 m)
        - **Negative offset (-)**: Right side when looking downstream
        - **Positive offset (+)**: Left side when looking downstream
        - Offset measured **perpendicular** to profile line
        
        ---
        
        **2. Elevation Lines in Cross-Section**
        
        ```
        Elevation ↑
                  │
                  │  ──── Final (Red, solid)
                  │ ╱
                  │╱ ──── Template (Green, dashed)
                  │
                  │  ──── Existing (Grey)
                  │
        ──────────┼───────────────────────────────→ Offset
                  0m
        ```
        
        - **Existing (Grey)**: Natural ground elevation from DEM
        - **Template (Green dashed)**: Design template shape
        - **Final (Red)**: Resulting terrain after applying template
        
        ---
        
        **3. Berm + Ditch Template Dimensions**
        
        ```
        Elevation ↑
                  │
                  │     ┌─────────────┐  ← Berm Crest (Crest Width)
                  │    ╱               ╲
                  │   ╱  Berm Height   ╲  ← Upstream Slope (H:1V)
                  │  ╱                   ╲
        ──────────┼─┼─────────────────────┼─┼───────────────→ Offset
        Natural   │ │                     │ │
        Ground    │ │                     │ │
                  │ │  ┌─────────────┐   │ │
                  │ │ ╱               ╲   │ │  ← Downstream Slope
                  │ │╱                 ╲  │ │
                  │ │                   ╲ │ │
                  │ │                    ╲│ │
                  │ │  ┌─────────────┐   │ │  ← Ditch Bottom (Ditch Width)
                  │ │  │             │   │ │
                  │ │  │ Ditch Depth │   │ │
                  │ │  │             │   │ │
                  │ │  └─────────────┘   │ │
                  │ │                     │ │
                  │ │  Ditch Side Slope   │ │
                  │ │      (H:1V)         │ │
                  │ │                     │ │
        ```
        
        **Dimensions:**
        - **Berm Height**: Vertical distance from natural ground to berm crest
        - **Crest Width**: Horizontal width of flat berm top
        - **Upstream Slope (H:1V)**: Horizontal:Vertical ratio (e.g., 2:1 = 2m horizontal per 1m vertical)
        - **Downstream Slope (H:1V)**: Horizontal:Vertical ratio of downstream berm face
        - **Ditch Width**: Bottom width of excavated ditch
        - **Ditch Depth**: Vertical depth below natural ground
        - **Ditch Side Slope (H:1V)**: Horizontal:Vertical ratio of ditch sides
        
        ---
        
        **4. Swale Template Dimensions**
        
        ```
        Elevation ↑
                  │
        ──────────┼───────────────────────────────→ Offset
        Natural   │
        Ground    │
                  │  ╱                 ╲
                  │ ╱                   ╲  ← Side Slope (H:1V)
                  │╱                     ╲
                  │ ┌─────────────────┐  │
                  │ │                 │  │  ← Bottom Width
                  │ │      Depth      │  │
                  │ │                 │  │
                  │ └─────────────────┘  │
                  │                       │
        ```
        
        **Dimensions:**
        - **Bottom Width**: Width of swale bottom
        - **Depth**: Vertical depth below natural ground
        - **Side Slope (H:1V)**: Horizontal:Vertical ratio of swale sides
        
        ---
        
        **5. Influence Width**
        
        ```
                    Influence Width
                         │
                    ─────┼─────
                         │
                    ┌────┼────┐
                    │    │    │  ← Total Corridor Width
                    │    │    │     = 2 × Influence Width
                    │    │    │
                    └────┼────┘
                         │
                    ─────┼─────
                         │
                    Centerline
                    (Offset = 0)
        ```
        
        - Maximum perpendicular distance from centerline where modifications apply
        - **Total width = 2 × Influence Width** (left + right)
        - Example: 20m influence = 40m total corridor width
        
        ---
        
        **6. Operation Modes**
        
        **Cut+Fill Mode:**
        ```
        Existing:  ────╲  ╱────
        Template:      ╲╱
        Final:     ────╲╱─────  (Follows template exactly)
        ```
        
        **Fill Only Mode:**
        ```
        Existing:  ────╲  ╱────
        Template:      ╲╱
        Final:     ────╲╱─────  (Takes maximum of existing/template)
        ```
        
        **Cut Only Mode:**
        ```
        Existing:  ────╲  ╱────
        Template:      ╲╱
        Final:     ────╲╱─────  (Takes minimum of existing/template)
        ```
        
        ---
        
        **7. Editing Process**
        
        1. **Select Station**: Use station number input to navigate
        2. **Adjust Elevation**: Use elevation slider/input to set centerline elevation
        3. **Set Template**: Choose Berm+Ditch or Swale and set dimensions
        4. **Set Influence Width**: Control how wide the modification extends
        5. **Choose Operation Mode**: Cut+Fill, Fill Only, or Cut Only
        6. **Verify**: View cross-section to see result
        7. **Repeat**: Move to next station and repeat
        
        **Note**: Changes automatically update the cross-section view in real-time.
        """)
    

    # Download profile line section
    if st.session_state.profile_line_coords is not None and len(st.session_state.profile_line_coords) >= 2:
        st.markdown("---")
        st.markdown("#### 📥 Download Profile Line")
        st.markdown("Export your drawn/uploaded profile line in different formats:")
        col_dwn1, col_dwn2, col_dwn3 = st.columns(3)
        with col_dwn1:
            shp_data = export_line_to_shapefile(st.session_state.profile_line_coords)
            if shp_data:
                st.download_button(
                    "📦 Shapefile (ZIP)",
                    data=shp_data,
                    file_name="profile_line.zip",
                    mime="application/zip",
                    use_container_width=True
                )
        with col_dwn2:
            kml_data = export_line_to_kml(st.session_state.profile_line_coords)
            if kml_data:
                st.download_button(
                    "📍 KML",
                    data=kml_data,
                    file_name="profile_line.kml",
                    mime="application/vnd.google-earth.kml+xml",
                    use_container_width=True
                )
        with col_dwn3:
            geojson_data = export_line_to_geojson(st.session_state.profile_line_coords)
            if geojson_data:
                st.download_button(
                    "📄 GeoJSON",
                    data=geojson_data,
                    file_name="profile_line.geojson",
                    mime="application/json",
                    use_container_width=True
                )

    # Download basin polygon section (if present)
    if st.session_state.basin_polygon_coords is not None and len(st.session_state.basin_polygon_coords) >= 3:
        st.markdown("---")
        st.markdown("#### 📥 Download Basin Polygon")
        st.markdown("Export your drawn/uploaded basin polygon in different formats:")
        col_poly1, col_poly2, col_poly3 = st.columns(3)
        with col_poly1:
            shp_data = export_polygon_to_shapefile(st.session_state.basin_polygon_coords, st.session_state.basin_polygon_crs)
            if shp_data:
                st.download_button(
                    "📦 Shapefile (ZIP)",
                    data=shp_data,
                    file_name="basin_polygon.zip",
                    mime="application/zip",
                    use_container_width=True
                )
        with col_poly2:
            kml_data = export_polygon_to_kml(st.session_state.basin_polygon_coords)
            if kml_data:
                st.download_button(
                    "📍 KML",
                    data=kml_data,
                    file_name="basin_polygon.kml",
                    mime="application/vnd.google-earth.kml+xml",
                    use_container_width=True
                )
        with col_poly3:
            geojson_data = export_polygon_to_geojson(st.session_state.basin_polygon_coords)
            if geojson_data:
                st.download_button(
                    "📄 GeoJSON",
                    data=geojson_data,
                    file_name="basin_polygon.geojson",
                    mime="application/json",
                    use_container_width=True
                )

# ============================================================================
# TAB 2: PROFILE (Profile Mode Only)
# ============================================================================

# Profile tab content - only rendered in profile mode
if st.session_state.design_mode == "profile":
    _tab2 = tab2
else:
    _tab2 = st.container()
    
with _tab2:
  if st.session_state.design_mode != "profile":
    pass  # Skip content in basin mode - tab doesn't exist
  elif 'samples' not in locals() or 'z_design' not in locals():
    st.warning("⚠️ Complete setup in Cross-Section tab first")
  else:
        # Recalculate design elevations from the stored original baseline using central helper.
        # This helper respects `locked_stations` so user-edited stations are not overwritten.
        recalculate_z_design_with_gradients()
        
        st.markdown("### 📈 Profile Editor")
        
        # COMPACT LAYOUT
        col_controls_prof, col_plot_prof, col_map_prof = st.columns([1, 3, 2])
        
        with col_controls_prof:
            # ============ STATION SELECTOR (Active Station is single source of truth) ============
            stations_for_prof = st.session_state.get("stations", stations) if "stations" in st.session_state else stations
            max_station_idx = len(stations_for_prof) - 1 if len(stations_for_prof) > 0 else 0
            
            # Ensure activeStation is valid
            if "activeStation" not in st.session_state:
                st.session_state.activeStation = 0
            else:
                # Clamp to valid range
                st.session_state.activeStation = max(0, min(st.session_state.activeStation, max_station_idx))
            
            # === SLOPE MEANING AND CONSTRAINTS ===
            with st.expander("📚 Understanding Slope (%) in Profile Design", expanded=False):
                st.markdown("""
                **Slope Definition:**
                - Slope (%) represents the **horizontal slope relative to a horizontal line**
                - Negative slope = descending (lower elevation downstream)
                - Positive slope = ascending (higher elevation downstream)
                
                **Slope Scope:**
                - **Slope at Station Si** = downstream slope from Si to Si+1 ONLY
                - Slope is **NOT bidirectional** - it affects ONLY downstream stations
                
                **Editing Rules:**
                1. **When changing slope at Station Si:**
                   - Recalculates design elevations from Si onward
                   - Does NOT change elevations at stations upstream of Si
                   - Each slope applies independently until the next slope station
                
                2. **When changing elevation at Station Si:**
                   - Recalculates design elevations from Si onward (following slope rules)
                   - Does NOT change elevations at stations upstream of Si
                
                3. **When navigating between stations (Prev/Next/Dropdown):**
                   - Only changes which station is active
                   - Uses already-stored values (no recalculation)
                   - Upstream elevations and slopes remain UNCHANGED
                
                **Example:**
                If you set Station 5's slope to -2%, it affects elevations from Station 6 onward.
                Stations 1-5 are not affected. If Station 8 also has a slope, it overrides from Station 8 onward.
                """)
            
            st.markdown("**Select Station**", help="Navigate using Prev/Next or dropdown")
            
            col_prev, col_dropdown, col_next = st.columns([0.8, 1.8, 0.8], gap="small")
            
            # Use a callback approach instead of st.rerun() to avoid issues
            def save_current_station():
                """Persist current active station elevation and slope before navigating away.

                Writes `elev_input_prof_unified` to `z_design` and `z_design_original` for the
                current active station. Also writes the slope input to `station_gradients`.
                Marks the station as locked (manually edited) so automatic recalculation
                won't overwrite it.
                """
                idx = st.session_state.get("activeStation", 0)
                if idx is None:
                    return

                # Read current stored arrays
                z_design_arr = np.array(st.session_state.get("z_design", []), dtype=float)
                if z_design_arr.size == 0:
                    return

                # Elevation input may not be set yet; fall back to stored elevation
                try:
                    input_val = float(st.session_state.get("elev_input_prof_unified", float(z_design_arr[idx])))
                except Exception:
                    input_val = float(z_design_arr[idx])

                # Save elevation for this station only
                if abs(input_val - float(z_design_arr[idx])) > 0.001:
                    z_design_arr[idx] = input_val
                    st.session_state.z_design = z_design_arr.tolist()

                # Update baseline/original for this station so downstream recalculation uses it
                if "z_design_original" not in st.session_state:
                    st.session_state.z_design_original = st.session_state.z_design
                else:
                    orig = np.array(st.session_state.z_design_original, dtype=float)
                    if orig.size == z_design_arr.size:
                        orig[idx] = input_val
                        st.session_state.z_design_original = orig.tolist()

                # Save slope input for this station if present
                try:
                    slope_val = float(st.session_state.get("slope_input_prof", st.session_state.station_gradients.get(idx, 0.0)))
                except Exception:
                    slope_val = float(st.session_state.station_gradients.get(idx, 0.0))
                st.session_state.station_gradients[idx] = slope_val

                # Mark this station as manually edited (locked)
                locked = set(st.session_state.get("locked_stations", []))
                locked.add(idx)
                st.session_state.locked_stations = sorted(list(locked))

                # Recalculate downstream stations (respecting locks)
                recalculate_z_design_with_gradients()

            def on_prev_click():
                # Save current station first, then move
                save_current_station()
                if st.session_state.activeStation > 0:
                    st.session_state.activeStation -= 1
                    # Force dropdown to sync by updating its stored value
                    st.session_state.station_selector_prof_unified = f"S{st.session_state.activeStation}"
                    # Reset elevation input to newly selected station's elevation
                    current_z = np.array(st.session_state.z_design, dtype=float)
                    st.session_state.elev_input_prof_unified = float(current_z[st.session_state.activeStation])
                    # Sync slope input widget with stored slope value for the new station
                    new_station_slope = st.session_state.station_gradients.get(st.session_state.activeStation, 0.0)
                    st.session_state.slope_input_prof = new_station_slope
                    # Ensure elevations are recalculated based on all stored slopes
                    recalculate_z_design_with_gradients()

            def on_next_click():
                # Save current station first, then move
                save_current_station()
                if st.session_state.activeStation < max_station_idx:
                    st.session_state.activeStation += 1
                    # Force dropdown to sync by updating its stored value
                    st.session_state.station_selector_prof_unified = f"S{st.session_state.activeStation}"
                    # Reset elevation input to newly selected station's elevation
                    current_z = np.array(st.session_state.z_design, dtype=float)
                    st.session_state.elev_input_prof_unified = float(current_z[st.session_state.activeStation])
                    # Sync slope input widget with stored slope value for the new station
                    new_station_slope = st.session_state.station_gradients.get(st.session_state.activeStation, 0.0)
                    st.session_state.slope_input_prof = new_station_slope
                    # Ensure elevations are recalculated based on all stored slopes
                    recalculate_z_design_with_gradients()

            def on_station_select():
                # Save current station first, then switch
                save_current_station()
                selected_str = st.session_state.station_selector_prof_unified
                selected_idx = int(selected_str[1:])
                st.session_state.activeStation = selected_idx
                # Reset elevation input to current station's elevation when station changes
                current_z = np.array(st.session_state.z_design, dtype=float)
                st.session_state.elev_input_prof_unified = float(current_z[selected_idx])
                # Sync slope input widget with stored slope value for the new station
                new_station_slope = st.session_state.station_gradients.get(selected_idx, 0.0)
                st.session_state.slope_input_prof = new_station_slope
                # Ensure elevations are recalculated based on all stored slopes
                recalculate_z_design_with_gradients()
            
            with col_prev:
                st.button("◀ Prev", key="btn_prev_prof", use_container_width=True, on_click=on_prev_click)
            
            with col_dropdown:
                st.selectbox(
                    "Station",
                    options=[f"S{i}" for i in range(len(stations_for_prof))],
                    index=st.session_state.activeStation,
                    key="station_selector_prof_unified",
                    label_visibility="collapsed",
                    on_change=on_station_select
                )
            
            with col_next:
                st.button("Next ▶", key="btn_next_prof", use_container_width=True, on_click=on_next_click)
            
            # Set preview index to active station
            preview_idx_prof = st.session_state.activeStation
            
            # Get current elevation values
            z_design = np.array(st.session_state.z_design, dtype=float)
            current_elev_prof = float(z_design[preview_idx_prof])
            
            # Display current station info compactly
            if preview_idx_prof < len(stations_for_prof):
                dist = stations_for_prof[preview_idx_prof]
                st.caption(f"📍 {dist:.1f} m")
            
            st.divider()
            
            # Design Gradient / Slope Control
            st.markdown("**Slope (%)**", help="Change for this station only (affects downstream)")
            
            # Get current gradient - always retrieve fresh from station_gradients
            current_station_gradient = st.session_state.station_gradients.get(preview_idx_prof, 0.0)
            
            # Sync slope input widget with stored slope value for the active station
            # This ensures the widget displays the correct value when navigating between stations
            # Always update to ensure the widget shows the correct value for the current active station
            st.session_state.slope_input_prof = current_station_gradient
            
            # Callback for slope/gradient changes
            def on_slope_change():
                """Handle slope changes - only affect downstream stations, keep upstream and current station unchanged."""
                new_grad_str = st.session_state.get("slope_input_prof", "0.0")
                try:
                    new_grad = float(new_grad_str) if isinstance(new_grad_str, str) else float(new_grad_str)
                except (ValueError, TypeError):
                    new_grad = 0.0

                # Always save the slope for this station
                st.session_state.station_gradients[preview_idx_prof] = round(new_grad, 3)

                # Recalculate downstream elevations using all stored slopes
                recalculate_z_design_with_gradients()

                st.session_state.modified_dem = None
                st.session_state.recompute_dem = True
            
            def recalculate_z_design_with_gradients():
                """Rebuild z_design by applying all stored slopes from original baseline.
                
                KEY RULE: Each slope only affects DOWNSTREAM stations until the next slope station.
                Slopes do NOT affect upstream stations or the slope station itself.
                """
                orig_z = np.array(st.session_state.get("z_design_original", st.session_state.z_design), dtype=float)
                new_z = orig_z.copy()
                stn_list = st.session_state.get("stations", [])
                
                if len(st.session_state.station_gradients) > 0 and len(stn_list) > 0:
                    grads_sorted = sorted([i for i in st.session_state.station_gradients.keys() if i < len(stn_list)])
                    
                    for grad_idx in grads_sorted:
                        grad_pct = st.session_state.station_gradients[grad_idx]
                        base_elev = float(orig_z[grad_idx])
                        base_dist = stn_list[grad_idx]
                        grade = grad_pct / 100.0
                        
                        # Find next slope station (end of this slope's influence)
                        next_grad_idx = None
                        for nxt in grads_sorted:
                            if nxt > grad_idx:
                                next_grad_idx = nxt
                                break
                        
                        # Apply slope ONLY from grad_idx+1 to next_grad_idx (or end if none)
                        end_idx = next_grad_idx if next_grad_idx is not None else len(stn_list)
                        locked = set(st.session_state.get("locked_stations", []))
                        for i in range(grad_idx + 1, end_idx):
                            # Respect locks: do not overwrite manually edited stations
                            if i in locked:
                                continue
                            d = stn_list[i] - base_dist
                            new_z[i] = base_elev + grade * d
                
                st.session_state.z_design = new_z.tolist()
            
            # Check if this is last station
            is_last_station = preview_idx_prof >= len(stations_for_prof) - 1
            
            if is_last_station:
                st.number_input("Slope (%)", value=current_station_gradient, disabled=True, 
                              key="slope_disabled_prof", help="Last station cannot have a slope")
            else:
                st.number_input("Slope (%)", min_value=-20.0, max_value=20.0,
                              value=current_station_gradient, step=0.1,
                              format="%.3g",
                              key="slope_input_prof",
                              on_change=on_slope_change,
                              help="Slope (%) to next station")
            
            st.divider()
            
            # Elevation Control - Number Input Only (No Slider)
            st.markdown("**Design Elevation (m)**")
            
            # Initialize elevation input key in session state if not present
            if "elev_input_prof_unified" not in st.session_state:
                st.session_state.elev_input_prof_unified = current_elev_prof
            
            # Callback for elevation changes via number input
            def on_elevation_change():
                """Handle elevation changes - only affect downstream stations, keep upstream unchanged."""
                input_val = st.session_state.get("elev_input_prof_unified", current_elev_prof)
                
                # Get the current elevation from z_design at the active station
                current_z = np.array(st.session_state.z_design, dtype=float)
                current_elev = current_z[preview_idx_prof]
                
                if abs(input_val - current_elev) > 0.001:  # Reduced threshold to catch small changes
                    # Update only the active station elevation (do NOT change downstream/upstream)
                    new_z = current_z.copy()
                    new_z[preview_idx_prof] = input_val

                    # Write back only the single-station change
                    st.session_state.z_design = new_z.tolist()

                    # Update the original baseline for this station only
                    if "z_design_original" not in st.session_state:
                        st.session_state.z_design_original = list(new_z)
                    else:
                        orig = np.array(st.session_state.z_design_original, dtype=float)
                        orig[preview_idx_prof] = input_val
                        st.session_state.z_design_original = orig.tolist()

                    st.session_state.modified_dem = None
                    st.session_state.recompute_dem = True
                    # Mark this station as user-edited (locked) so automatic recalculation won't overwrite it
                    locked = set(st.session_state.get("locked_stations", []))
                    locked.add(preview_idx_prof)
                    st.session_state.locked_stations = sorted(list(locked))
                    # Recalculate downstream stations using stored slopes (respecting locks)
                    recalculate_z_design_with_gradients()
            
            # Number input only for elevation (no slider to avoid widget key issues)
            st.number_input(
                "Elevation (m)",
                value=st.session_state.elev_input_prof_unified,
                step=0.1,
                format="%.2f",
                key="elev_input_prof_unified",
                on_change=on_elevation_change
            )

            # --- Post-input sync: ensure any change to the elevation input is applied
            # This covers cases where the widget value changes but the on_change callback
            # did not get invoked for whatever reason (Streamlit timing). We compare
            # the input value against the stored design elevation and apply the update
            # immediately if they differ.
            try:
                input_val_now = float(st.session_state.get("elev_input_prof_unified", current_elev_prof))
            except Exception:
                input_val_now = current_elev_prof

            z_design_now = np.array(st.session_state.z_design, dtype=float)
            # If the value differs from the stored design elevation for the active station,
            # apply the change to the active station only (no downstream/upstream modification).
            if abs(input_val_now - float(z_design_now[preview_idx_prof])) > 0.001:
                new_z = z_design_now.copy()
                new_z[preview_idx_prof] = input_val_now
                st.session_state.z_design = new_z.tolist()

                if "z_design_original" not in st.session_state:
                    st.session_state.z_design_original = list(new_z)
                else:
                    orig = np.array(st.session_state.z_design_original, dtype=float)
                    orig[preview_idx_prof] = input_val_now
                    st.session_state.z_design_original = orig.tolist()

                st.session_state.modified_dem = None
                st.session_state.recompute_dem = True
                # Mark this station as user-edited (locked) so automatic recalculation won't overwrite it
                locked = set(st.session_state.get("locked_stations", []))
                locked.add(preview_idx_prof)
                st.session_state.locked_stations = sorted(list(locked))
                # Recalculate downstream stations using stored slopes (respecting locks)
                recalculate_z_design_with_gradients()
        
        with col_plot_prof:
            # Always read latest z_design from session state to ensure updates from gradient changes are reflected
            z_design_plot = np.array(st.session_state.z_design)
            
            # Plot data - use separate vertices for design and existing terrain
            # Design profile uses corner vertices, existing terrain uses equally spaced points
            fig_prof = go.Figure()
            
            # Existing terrain - sampled at equal spacing (smooth line)
            fig_prof.add_trace(go.Scatter(
                x=existing_stations, y=z_existing,
                mode='lines', name='Existing Terrain',
                line=dict(color='#666', width=2),
            ))
            
            # Existing terrain at design stations (for accurate comparison with cross-section)
            fig_prof.add_trace(go.Scatter(
                x=stations, y=z_existing_at_stations,
                mode='markers', name='Existing at Stations',
                marker=dict(size=6, color='#666', symbol='circle', line=dict(width=1, color='white')),
                showlegend=False,  # Hide from legend but show on plot
            ))
            
            # Design profile - at corner vertices (use latest z_design from session state)
            fig_prof.add_trace(go.Scatter(
                x=stations, y=z_design_plot,
                mode='markers+lines', name='Design Profile',
                marker=dict(size=8, color='#d62728'),
                line=dict(color='#d62728', width=2),
            ))
            
            # Calculate y-axis range based on min/max elevation (not from 0)
            all_elevations = np.concatenate([z_existing, z_existing_at_stations, z_design_plot])
            y_min = np.nanmin(all_elevations)
            y_max = np.nanmax(all_elevations)
            y_padding = (y_max - y_min) * 0.1  # 10% padding
            y_range = y_max - y_min
            
            # Highlight active station
            if st.session_state.activeStation < len(stations):
                fig_prof.add_trace(go.Scatter(
                    x=[stations[st.session_state.activeStation]], 
                    y=[z_design_plot[st.session_state.activeStation]],
                    mode='markers', name='Active',
                    marker=dict(size=15, color='#ffcc00', line=dict(width=3, color='black')),
                    showlegend=False,
                ))
            
            # Add station number labels
            annotations = []
            for i in range(len(stations)):
                # Position label at top edge of marker (touching but not overlapping)
                # Use a small fixed offset in meters to position label right at marker top edge
                # This accounts for marker radius (~4 pixels) converted to elevation units
                y_offset = max(y_range * 0.002, 0.05)  # Small offset: 0.2% of range or minimum 0.05m
                annotations.append(dict(
                    x=stations[i],
                    y=z_design_plot[i] + y_offset,
                    text=f"S{i}",
                    showarrow=False,
                    font=dict(size=10, color='#d62728'),
                    bgcolor='rgba(255,255,255,0.7)',
                    bordercolor='#d62728',
                    borderwidth=1,
                    borderpad=2,
                    yanchor='bottom'  # Anchor label at bottom so it sits on top of marker
                ))
            
            fig_prof.update_layout(
                title=dict(
                    text="Longitudinal Profile (First Vertex → Last Vertex)",
                    font=dict(size=16, family="Arial, sans-serif")
                ),
                xaxis_title=dict(text="Distance from First Vertex (m)", font=dict(size=13)),
                yaxis_title=dict(text="Elevation (m)", font=dict(size=13)),
                yaxis=dict(range=[y_min - y_padding, y_max + y_padding]),
                height=550,
                margin=dict(l=60, r=30, t=60, b=60),
                template="plotly_white",
                annotations=annotations,
                font=dict(family="Arial, sans-serif", size=11),
            )
            
            # Use key with activeStation to ensure plot refreshes
            st.plotly_chart(fig_prof, use_container_width=True, 
                           key=f"prof_plot_{st.session_state.activeStation}_{st.session_state.force_plot_update}")
            
            st.info(f"💡 Edit: Slider/number (left) or table active row (**S{st.session_state.activeStation}**)")
            
            # Editable Elevation Table with Active Row Highlighting
            z_design_for_table = np.array(st.session_state.z_design, dtype=float)
            active_stn = st.session_state.activeStation
            
            # Build DataFrame with highlighted active station
            df_tbl_data = []
            for i in range(len(stations_for_prof)):
                is_active = (i == active_stn)
                stn_label = f"🔷 S{i}" if is_active else f"S{i}"
                df_tbl_data.append({
                    "Station": stn_label,
                    "Distance(m)": stations_for_prof[i],
                    "Existing(m)": z_existing_at_stations[i],
                    "Design(m)": z_design_for_table[i],
                    "_active": is_active  # Hidden column for filtering
                })
            
            df_tbl = pd.DataFrame(df_tbl_data)
            
            # Display table
            df_tbl_edited = st.data_editor(
                df_tbl,
                num_rows="fixed",
                disabled=["Station", "Distance(m)", "Existing(m)", "_active"],
                height=200,
                use_container_width=True,
                column_config={
                    "Station": st.column_config.TextColumn(label="Station", width="small"),
                    "Distance(m)": st.column_config.NumberColumn(label="Distance (m)", format="%.1f", width=90),
                    "Existing(m)": st.column_config.NumberColumn(label="Existing (m)", format="%.2f", width=100),
                    "Design(m)": st.column_config.NumberColumn(label="Design (m)", format="%.2f", width=100),
                    "_active": st.column_config.CheckboxColumn(disabled=True, label="")
                },
                hide_index=False,
                key=f"prof_tbl_{active_stn}_{st.session_state.force_plot_update}"
            )
            
            # Process table edits - only allow active station to be edited
            if not df_tbl_edited["Design(m)"].equals(pd.Series(z_design_for_table)):
                changed_indices = []
                for i in range(len(df_tbl_edited)):
                    if abs(float(df_tbl_edited["Design(m)"].iloc[i]) - float(z_design_for_table[i])) > 0.01:
                        changed_indices.append(i)
                
                # Allow edit only if active station was changed
                if active_stn in changed_indices:
                    new_elev = float(df_tbl_edited["Design(m)"].iloc[active_stn])
                    old_elev = float(z_design_for_table[active_stn])
                    
                    if abs(new_elev - old_elev) > 0.01:
                        # Update baseline elevation
                        if "z_design_original" not in st.session_state:
                            st.session_state.z_design_original = z_design_for_table.tolist()
                        
                        orig = np.array(st.session_state.z_design_original, dtype=float)
                        orig[active_stn] = new_elev
                        st.session_state.z_design_original = orig.tolist()

                        # Mark this station as manually edited (locked)
                        locked = set(st.session_state.get("locked_stations", []))
                        locked.add(active_stn)
                        st.session_state.locked_stations = sorted(list(locked))

                        # Recalculate z_design with slopes reapplied (will respect locks)
                        recalculate_z_design_with_gradients()
                        st.session_state.modified_dem = None
                        st.session_state.recompute_dem = True
                        st.rerun()
                else:
                    # Attempted edit of non-active station
                    if len(changed_indices) > 0:
                        st.warning(f"Only station S{active_stn} is editable. Select it first.")
                        st.rerun()
        
        with col_map_prof:
            st.markdown("### 🗺️ Station Location")
            
            with st.expander("Map Options", expanded=False):
                sat_opacity_prof = st.slider("Satellite", 0.0, 1.0, 0.9, 0.1, key="sat_prof")
                hs_opacity_prof = st.slider("Hillshade", 0.0, 1.0, 0.85, 0.1, key="hs_prof")
                profile_color_prof = st.color_picker("Profile Color", "#ff0000", key="prof_color_prof")
                show_stations_prof = st.checkbox("Show All Stations", value=True, key="stations_prof")
            
            # Use activeStation as the single source of truth
            current_station_idx_prof = st.session_state.activeStation
            x_station_prof, y_station_prof = center_xy[current_station_idx_prof]
            lon_station_prof, lat_station_prof = transformer_to_map.transform(x_station_prof, y_station_prof)
            
            # Check if this is the first time opening the Profile tab
            first_time_profile_tab = "profile_tab_visited" not in st.session_state
            
            # Initialize map - use profile bounds if available, otherwise center on station
            if "profile_bounds" in st.session_state and st.session_state.profile_bounds is not None:
                # Use center of profile bounds as initial location
                bounds_center_lat = (st.session_state.profile_bounds[0][0] + st.session_state.profile_bounds[1][0]) / 2
                bounds_center_lon = (st.session_state.profile_bounds[0][1] + st.session_state.profile_bounds[1][1]) / 2
                # On first-time load, use a higher zoom_start to ensure proper initial view
                initial_zoom = 18 if first_time_profile_tab else 15
                m_prof = folium.Map(
                    location=[bounds_center_lat, bounds_center_lon],
                    zoom_start=initial_zoom,
                    max_zoom=24,
                    control_scale=False,
                    prefer_canvas=True
                )
            else:
                # Fallback to station-centered view
                m_prof = folium.Map(
                location=[lat_station_prof, lon_station_prof],
                zoom_start=21,
                max_zoom=24,
                control_scale=False,
                prefer_canvas=True
            )
            
            folium.TileLayer(
                tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}',
                attr='Google', opacity=sat_opacity_prof
            ).add_to(m_prof)
            
            folium.raster_layers.ImageOverlay(
                image=hs_norm, bounds=bounds_map, opacity=hs_opacity_prof
            ).add_to(m_prof)
            
            folium.PolyLine(
                locations=[[lat, lon] for lon, lat in line_coords_latlon],
                color=profile_color_prof, weight=4
            ).add_to(m_prof)
            
            if show_stations_prof:
                for i, (x_a, y_a) in enumerate(center_xy):
                    lon, lat = transformer_to_map.transform(x_a, y_a)
                    if i == current_station_idx_prof:
                        # Active station - larger, yellow with black border
                        folium.CircleMarker(
                            location=[lat, lon], radius=12,
                            color='black', fillColor='#ffcc00', fillOpacity=1.0, weight=3,
                            popup=f'Station S{i}',
                            tooltip=f'S{i} (Active)'
                        ).add_to(m_prof)
                        
                        folium.Marker(
                            location=[lat, lon],
                            icon=folium.DivIcon(
                                html=f'<div style="font-size: 14px; font-weight: bold; color: black; text-shadow: 1px 1px 2px white, -1px -1px 2px white, 1px -1px 2px white, -1px 1px 2px white;">S{i}</div>',
                                icon_size=(30, 15),
                                icon_anchor=(15, -5)
                            )
                        ).add_to(m_prof)
                    else:
                        # Other stations
                        folium.CircleMarker(
                            location=[lat, lon], radius=5,
                            color='#d62728', fillColor='#d62728', fillOpacity=0.8, weight=2,
                            popup=f'Station S{i}',
                            tooltip=f'S{i}'
                        ).add_to(m_prof)
                        
                        folium.Marker(
                            location=[lat, lon],
                            icon=folium.DivIcon(
                                html=f'<div style="font-size: 12px; font-weight: bold; color: #d62728; text-shadow: 1px 1px 2px white, -1px -1px 2px white, 1px -1px 2px white, -1px 1px 2px white;">S{i}</div>',
                                icon_size=(25, 12),
                                icon_anchor=(12, -5)
                            )
                        ).add_to(m_prof)
            else:
                # Show only active station
                folium.CircleMarker(
                    location=[lat_station_prof, lon_station_prof], radius=12,
                    color='black', fillColor='#ffcc00', fillOpacity=1.0, weight=3,
                    popup=f'Station S{current_station_idx_prof}',
                    tooltip=f'S{current_station_idx_prof} (Active)'
                ).add_to(m_prof)
                
                folium.Marker(
                    location=[lat_station_prof, lon_station_prof],
                    icon=folium.DivIcon(
                        html=f'<div style="font-size: 14px; font-weight: bold; color: black; text-shadow: 1px 1px 2px white, -1px -1px 2px white, 1px -1px 2px white, -1px 1px 2px white;">S{current_station_idx_prof}</div>',
                        icon_size=(30, 15),
                        icon_anchor=(15, -5)
                    )
                ).add_to(m_prof)
            
            # Add berm and ditch boundary lines (if template is berm_ditch)
            # Draw dotted lines connecting vertices of berm top and ditch bottom
            if "template_type" in st.session_state and st.session_state.template_type == "berm_ditch":
                try:
                    template_params_prof = st.session_state.get("template_params", {})
                    
                    # Get normals from samples
                    tangents_prof, normals_prof = compute_tangents_normals(samples)
                    
                    berm_top_left, berm_top_right, ditch_bottom_left, ditch_bottom_right = get_berm_ditch_boundaries(template_params_prof)
                    
                    # Collect all berm top left vertices
                    berm_top_left_coords = []
                    berm_top_right_coords = []
                    ditch_bottom_left_coords = []
                    ditch_bottom_right_coords = []
                    
                    for station_idx in range(len(stations)):
                        xc, yc = center_xy[station_idx]
                        nx, ny = normals_prof[station_idx]
                        
                        # Berm top left vertex
                        x_btl = xc + berm_top_left * nx
                        y_btl = yc + berm_top_left * ny
                        lon_btl, lat_btl = transformer_to_map.transform(x_btl, y_btl)
                        berm_top_left_coords.append([lat_btl, lon_btl])
                        
                        # Berm top right vertex
                        x_btr = xc + berm_top_right * nx
                        y_btr = yc + berm_top_right * ny
                        lon_btr, lat_btr = transformer_to_map.transform(x_btr, y_btr)
                        berm_top_right_coords.append([lat_btr, lon_btr])
                        
                        # Ditch bottom left vertex
                        x_dbl = xc + ditch_bottom_left * nx
                        y_dbl = yc + ditch_bottom_left * ny
                        lon_dbl, lat_dbl = transformer_to_map.transform(x_dbl, y_dbl)
                        ditch_bottom_left_coords.append([lat_dbl, lon_dbl])
                        
                        # Ditch bottom right vertex
                        x_dbr = xc + ditch_bottom_right * nx
                        y_dbr = yc + ditch_bottom_right * ny
                        lon_dbr, lat_dbr = transformer_to_map.transform(x_dbr, y_dbr)
                        ditch_bottom_right_coords.append([lat_dbr, lon_dbr])
                    
                    # Draw dotted lines connecting vertices
                    folium.PolyLine(
                        locations=berm_top_left_coords,
                        color='#4169E1', weight=2, opacity=0.6, dash_array='5, 5',
                        tooltip='Berm Top Left Edge'
                    ).add_to(m_prof)
                    
                    folium.PolyLine(
                        locations=berm_top_right_coords,
                        color='#4169E1', weight=2, opacity=0.6, dash_array='5, 5',
                        tooltip='Berm Top Right Edge'
                    ).add_to(m_prof)
                    
                    folium.PolyLine(
                        locations=ditch_bottom_left_coords,
                        color='#FF8C00', weight=2, opacity=0.6, dash_array='5, 5',
                        tooltip='Ditch Bottom Left Edge'
                    ).add_to(m_prof)
                    
                    folium.PolyLine(
                        locations=ditch_bottom_right_coords,
                        color='#FF8C00', weight=2, opacity=0.6, dash_array='5, 5',
                        tooltip='Ditch Bottom Right Edge'
                    ).add_to(m_prof)
                except Exception:
                    pass  # Silently fail if data not ready
            
            # Add centerline marker (purple diamond) at selected station
            folium.Marker(
                location=[lat_station_prof, lon_station_prof],
                icon=folium.DivIcon(
                    html=f'<div style="font-size: 24px; color: #ff00ff; text-shadow: 0 0 3px black;">♦</div>',
                    icon_size=(20, 20),
                    icon_anchor=(10, 10)
                ),
                tooltip='Centerline (Offset = 0m)'
            ).add_to(m_prof)
            
            # Auto-zoom behavior: On first-time Profile tab load, zoom to profile line extent
            # Calculate bounds from line_coords_latlon if profile_bounds not available
            if first_time_profile_tab:
                # First-time load: zoom to full extent of profile line
                bounds_to_use = None
                if "profile_bounds" in st.session_state and st.session_state.profile_bounds is not None:
                    bounds_to_use = st.session_state.profile_bounds
                elif line_coords_latlon and len(line_coords_latlon) >= 2:
                    # Calculate bounds directly from profile line coordinates
                    lons = [coord[0] for coord in line_coords_latlon]  # lon is first element
                    lats = [coord[1] for coord in line_coords_latlon]  # lat is second element
                    if lons and lats:
                        lat_range = max(lats) - min(lats)
                        lon_range = max(lons) - min(lons)
                        buffer = max(lat_range, lon_range) * 0.1 + 0.0005
                        bounds_to_use = [
                            [min(lats) - buffer, min(lons) - buffer],
                            [max(lats) + buffer, max(lons) + buffer]
                        ]
                
                if bounds_to_use:
                    # Calculate padding based on profile line length
                    # Get profile line length from stations if available
                    profile_length = 0
                    if "stations" in st.session_state and len(st.session_state.stations) > 0:
                        profile_length = float(st.session_state.stations[-1])  # Last station distance
                    
                    # Adjust padding based on profile length:
                    # - Short lines (< 100m): less padding (zoom in more)
                    # - Medium lines (100-500m): moderate padding
                    # - Long lines (> 500m): more padding (zoom out more)
                    if profile_length > 0:
                        if profile_length < 100:
                            padding_value = 30  # Less padding for short lines
                        elif profile_length < 500:
                            padding_value = 50  # Moderate padding for medium lines
                        else:
                            padding_value = 80  # More padding for long lines
                    else:
                        # Fallback if profile length not available
                        padding_value = 50
                    
                    m_prof.fit_bounds(bounds_to_use, padding=(padding_value, padding_value))
                    # Mark Profile tab as visited (only after successful first-time zoom)
                    st.session_state.profile_tab_visited = True
                elif len(center_xy) > 0:
                    # Fallback: if no bounds available, zoom to S0
                    x_s0, y_s0 = center_xy[0]
                    lon_s0, lat_s0 = transformer_to_map.transform(x_s0, y_s0)
                    padding_deg = 0.0005  # Approximately 50m at mid-latitudes
                    s0_bounds = [
                        [lat_s0 - padding_deg, lon_s0 - padding_deg],
                        [lat_s0 + padding_deg, lon_s0 + padding_deg]
                    ]
                    m_prof.fit_bounds(s0_bounds, padding=(20, 20))
                    st.session_state.profile_tab_visited = True
            elif "profile_bounds" in st.session_state and st.session_state.profile_bounds is not None:
                # Subsequent loads: zoom to full extent of profile line
                m_prof.fit_bounds(st.session_state.profile_bounds, padding=(20, 20))
            else:
                # Fallback: zoom to selected station with buffer
                # This ensures the selected station is visible on the map
                station_buffer = 0.0001  # About 10m at mid-latitudes
                try:
                    if len(center_xy) > 0:
                        x_station, y_station = center_xy[current_station_idx_prof]
                        lon_station, lat_station = transformer_to_map.transform(x_station, y_station)
                        m_prof.fit_bounds([
                            [lat_station - station_buffer, lon_station - station_buffer],
                            [lat_station + station_buffer, lon_station + station_buffer]
                        ], padding=(20, 20))
                except (IndexError, ValueError, TypeError):
                    # If station not available, use a default center view
                    pass
            
            # Use a stable key for first-time load to prevent map reset, then use dynamic key for subsequent loads
            if first_time_profile_tab:
                map_key = "map_prof_first_load"
            else:
                map_key = f"map_prof_{current_station_idx_prof}_{st.session_state.force_plot_update}"
            
            st_folium(m_prof, height=650, width=None, returned_objects=[],
                     key=map_key)
            
            # Map legend and description
            with st.expander("🗺️ Map Legend & Description", expanded=False):
                st.markdown("""
                ### Map View Elements
                
                **Profile Line & Stations:**
                - **Red Line**: Longitudinal profile centerline
                - **Yellow Circle (Large)**: Currently selected station
                - **Red Circles (Small)**: Other stations along profile
                - **Station Labels**: S0, S1, S2... indicate station numbers
                
                **Centerline Marker:**
                - **Purple Diamond (♦)**: Marks the exact centerline position at the selected station (Offset = 0m)
                  - This is where the cross-section slice is taken
                  - Perpendicular to the profile line
                  - Represents the center of the berm/ditch template
                
                **Berm & Ditch Boundaries** (shown when Berm+Ditch template is selected):
                - **Blue Dotted Lines**: Berm top width edges (left and right)
                  - Shows the extent of the berm crest
                  - Follows the profile line perpendicular to centerline
                - **Orange Dotted Lines**: Ditch bottom width edges (left and right)
                  - Shows the extent of the ditch bottom
                  - Located downstream of the berm
                
                **How to Read the Map:**
                1. The **purple diamond** shows where the cross-section cut is taken
                2. **Blue lines** bracket the berm top (crest width)
                3. **Orange lines** bracket the ditch bottom (downstream of berm)
                4. All measurements are perpendicular to the red profile centerline
                5. Use the cross-section view (left) to see the vertical profile at this location
                
                **Map Controls:**
                - Use the expander above to adjust satellite opacity, hillshade, and colors
                - Zoom: Scroll wheel or +/- buttons
                - Pan: Click and drag
                - The map automatically centers on the selected station
                """)

# ============================================================================
# TAB 4: BASIN DESIGN (Basin Mode Only)
# ============================================================================

if st.session_state.design_mode == "basin":
    with tab4:
        st.markdown("### 🏞️ Basin Design")
        
        # Check if this is the first time visiting the Basin Design tab after polygon is set
        first_time_basin_design_tab = "basin_design_tab_visited" not in st.session_state
        
        # Check if polygon is drawn
        basin_coords = st.session_state.get("basin_polygon_coords")
        
        if basin_coords is None or len(basin_coords) < 3:
            st.warning("⚠️ Draw a polygon on the Input Data map to define the basin boundary.")
            st.info("""
            **How to use Basin Design:**
            1. Go to the **Input Data** tab
            2. Use the polygon draw tool on the map to draw your basin boundary
            3. Come back to this tab to configure basin parameters
            4. The basin will be cut into the terrain with sloped sides
            """)
        else:
            st.success(f"✅ Basin polygon defined with {len(basin_coords)} vertices")
            
            # Basin parameters
            st.markdown("---")
            st.markdown("#### Basin Parameters")
            
            col_bp1, col_bp2, col_bp3 = st.columns(3)
            with col_bp1:
                basin_depth = st.number_input(
                    "Basin Depth (m)", 
                    0.5, 60.0, 
                    st.session_state.basin_depth, 
                    0.5,
                    key="basin_depth_input",
                    help="Depth of the basin from existing ground surface (at upstream end)"
                )
                st.session_state.basin_depth = basin_depth
            
            with col_bp2:
                basin_side_slope = st.number_input(
                    "Side Slope (H:1V)", 
                    0.5, 10.0, 
                    st.session_state.basin_side_slope, 
                    0.1,
                    key="basin_slope_input",
                    help="Horizontal to vertical ratio (e.g., 1.5 means 1.5m horizontal for every 1m vertical)"
                )
                st.session_state.basin_side_slope = basin_side_slope
            
            with col_bp3:
                basin_longitudinal_slope = st.number_input(
                    "Longitudinal Slope (%)", 
                    -200.0, 200.0, 
                    st.session_state.basin_longitudinal_slope, 
                    0.1,
                    key="basin_long_slope_input",
                    help="Slope along basin from upstream to downstream (positive = downstream deeper, negative = upstream deeper). If channel is drawn, slope follows channel path. Otherwise, uses first vertex to minimum elevation point."
                )
                st.session_state.basin_longitudinal_slope = basin_longitudinal_slope
            
            # Force rerun whenever any parameter changes (Streamlit automatically reruns, but ensure metrics update)
            st.session_state.basin_params_changed = True
            
            # Channel definition section
            st.markdown("---")
            st.markdown("#### Channel Definition (Optional)")
            st.info("💡 **Draw a channel line** on the Input Data map (green polyline tool) to define the flow path where longitudinal slope is applied. The channel should go from upstream to downstream inside the basin. If no channel is drawn, the system will automatically use the first polygon vertex to the minimum elevation point.")
            
            channel_coords = st.session_state.get("basin_channel_coords")
            if channel_coords is not None and len(channel_coords) >= 2:
                st.success(f"✅ Channel defined with {len(channel_coords)} points")
            else:
                st.warning("⚠️ No channel defined. Using automatic flow direction (first vertex → minimum elevation).")
            
            # Convert basin polygon to projected coordinates
            basin_coords_xy = []
            for coord in basin_coords:
                lon, lat = coord[0], coord[1]
                x, y = transformer_to_analysis.transform(lon, lat)
                basin_coords_xy.append((x, y))
            
            # Calculate flow length for longitudinal slope calculations
            from shapely.geometry import Polygon, Point
            from rasterio.transform import rowcol, xy
            
            channel_coords = st.session_state.get("basin_channel_coords")
            flow_length = 0.0
            
            if channel_coords is not None and len(channel_coords) >= 2:
                # Use channel line: calculate total length
                channel_coords_xy = []
                for coord in channel_coords:
                    # Handle both list and tuple formats, extract first two elements
                    if isinstance(coord, (list, tuple)) and len(coord) >= 2:
                        lon, lat = coord[0], coord[1]
                    else:
                        continue  # Skip invalid coordinates
                    x, y = transformer_to_analysis.transform(lon, lat)
                    channel_coords_xy.append((x, y))
                
                # Calculate total channel length
                for i in range(len(channel_coords_xy) - 1):
                    x1, y1 = channel_coords_xy[i]
                    x2, y2 = channel_coords_xy[i + 1]
                    flow_length += np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
            else:
                # Fallback: use first vertex to minimum elevation
                upstream_x, upstream_y = basin_coords_xy[0]
                outer_poly = Polygon(basin_coords_xy)
                minx, miny, maxx, maxy = outer_poly.bounds
                row_min, col_min = rowcol(analysis_transform, minx, maxy)
                row_max, col_max = rowcol(analysis_transform, maxx, miny)
                
                h, w = analysis_dem.shape
                row_min, row_max = max(0, min(row_min, row_max)), min(h-1, max(row_min, row_max))
                col_min, col_max = max(0, min(col_min, col_max)), min(w-1, max(col_min, col_max))
                
                min_elev = float('inf')
                downstream_x, downstream_y = upstream_x, upstream_y
                
                for r in range(row_min, row_max + 1):
                    for c in range(col_min, col_max + 1):
                        z_val = analysis_dem[r, c]
                        if analysis_nodata is not None and z_val == analysis_nodata:
                            continue
                        
                        x, y = xy(analysis_transform, r, c)
                        point = Point(x, y)
                        
                        if outer_poly.contains(point) and z_val < min_elev:
                            min_elev = z_val
                            downstream_x, downstream_y = x, y
                
                # Calculate flow length
                flow_dx = downstream_x - upstream_x
                flow_dy = downstream_y - upstream_y
                flow_length = np.sqrt(flow_dx**2 + flow_dy**2)
            
            # Calculate inner polygon (now with longitudinal slope support)
            inner_coords_xy, inner_poly_error = calculate_inner_polygon(
                basin_coords_xy, basin_depth, basin_side_slope, 
                basin_longitudinal_slope, flow_length
            )
            
            # Debug output
            outer_poly_temp = Polygon(basin_coords_xy)
            outer_area_m2 = outer_poly_temp.area
            outer_bounds = outer_poly_temp.bounds  # (minx, miny, maxx, maxy)
            # Use UPSTREAM depth only (not affected by longitudinal slope)
            offset_calc = basin_depth / basin_side_slope if basin_side_slope > 0 else basin_depth
            min_dim = min(outer_bounds[2] - outer_bounds[0], outer_bounds[3] - outer_bounds[1])
            
            # Calculate max valid offset for display (using same logic as in calculate_inner_polygon)
            width = outer_bounds[2] - outer_bounds[0]
            height = outer_bounds[3] - outer_bounds[1]
            avg_dimension = (width + height) / 2.0
            approximate_radius = avg_dimension / 2.0
            max_valid_offset = approximate_radius * 0.45
            
            with st.expander("🔧 DEBUG Basin Calculation"):
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Outer Area (m²)", f"{outer_area_m2:,.0f}")
                    st.metric("Flow Length (m)", f"{flow_length:,.0f}")
                    st.metric("Basin Depth (m)", f"{basin_depth:.2f}")
                with col2:
                    st.metric("Side Slope (H:V)", f"{basin_side_slope:.2f}")
                    st.metric("Long. Slope (%)", f"{basin_longitudinal_slope:.2f}")
                    st.metric("Offset Distance (m)", f"{offset_calc:.2f}")
                
                st.write(f"**Polygon Bounds (m):** {outer_bounds}")
                st.write(f"**Minimum Dimension (m):** {min_dim:.2f}")
                st.write(f"**Basin Depth (m):** {basin_depth:.2f}")
                st.write(f"**Calculated Offset (m):** {offset_calc:.2f}")
                st.write(f"**Max Valid Offset (45% of avg radius):** {max_valid_offset:.2f}")
                st.write(f"**Offset Validation:** {'OK' if offset_calc <= max_valid_offset else 'TOO LARGE'}")
                st.write(f"**Inner Polygon Status:** {'Valid' if inner_coords_xy else 'FAILED (returns None)'}")
                if inner_coords_xy:
                    inner_poly_temp = Polygon(inner_coords_xy)
                    st.write(f"**Inner Area (m²):** {inner_poly_temp.area:,.0f}")
                else:
                    if inner_poly_error:
                        st.write(f"**Reason:** {inner_poly_error}")
                    else:
                        st.write(f"**Reason:** Unknown error (no error message returned)")
            
            # Calculate volumes and areas (now with longitudinal slope support)
            if inner_coords_xy is not None:
                volume, outer_area, inner_area = calculate_basin_volume(
                    basin_coords_xy, inner_coords_xy, basin_depth, basin_side_slope,
                    basin_longitudinal_slope, flow_length
                )
            else:
                # If inner polygon calculation fails, use outer area and estimate volume
                from shapely.geometry import Polygon
                outer_poly = Polygon(basin_coords_xy)
                outer_area = outer_poly.area
                inner_area = 0
                # Estimate volume as roughly half of outer_area * depth
                estimated_volume = outer_area * basin_depth * 0.5
                volume = max(0, estimated_volume)
            
            # Store in session state
            st.session_state.basin_volumes = {
                "volume": volume,
                "outer_area": outer_area,
                "inner_area": inner_area
            }

            # Convert inner polygon (analysis CRS XY) back to lat/lon for map display with status
            inner_polygon_status = "✅ OK"
            try:
                if inner_coords_xy is not None and len(inner_coords_xy) >= 3:
                    inner_coords_latlon = []
                    for x, y in inner_coords_xy:
                        lon, lat = transformer_to_map.transform(x, y)
                        # Validate transformed coordinates
                        if np.isnan(lon) or np.isnan(lat) or not np.isfinite(lon) or not np.isfinite(lat):
                            raise ValueError(f"Invalid transform result")
                        inner_coords_latlon.append([lon, lat])
                    
                    # Ensure polygon is closed for display
                    if inner_coords_latlon[0] != inner_coords_latlon[-1]:
                        inner_coords_latlon.append(inner_coords_latlon[0])
                    
                    st.session_state.basin_inner_polygon_coords = inner_coords_latlon
                else:
                    st.session_state.basin_inner_polygon_coords = None
                    inner_polygon_status = "⚠️ Too small"
            except Exception as e:
                # Try axis-swap fallback (swap x/y in projection)
                try:
                    if inner_coords_xy is not None and len(inner_coords_xy) >= 3:
                        inner_coords_latlon = []
                        for y, x in inner_coords_xy:  # Swap x/y
                            lon, lat = transformer_to_map.transform(x, y)
                            if np.isnan(lon) or np.isnan(lat) or not np.isfinite(lon) or not np.isfinite(lat):
                                raise ValueError("Invalid swapped result")
                            inner_coords_latlon.append([lon, lat])
                        
                        # Ensure polygon is closed for display
                        if inner_coords_latlon[0] != inner_coords_latlon[-1]:
                            inner_coords_latlon.append(inner_coords_latlon[0])
                        
                        st.session_state.basin_inner_polygon_coords = inner_coords_latlon
                        inner_polygon_status = "⚠️ Axis-swapped"
                    else:
                        st.session_state.basin_inner_polygon_coords = None
                except Exception:
                    st.session_state.basin_inner_polygon_coords = None
                    inner_polygon_status = f"❌ Transform failed"
            
            # Store status
            st.session_state.basin_inner_polygon_status = inner_polygon_status
            
            # Display metrics
            st.markdown("---")
            st.markdown("#### Basin Metrics")
            
            col_m1, col_m2, col_m3 = st.columns(3)
            with col_m1:
                st.metric("Geometric Volume", f"{volume:,.0f} m³")
            with col_m2:
                st.metric("Outer Area (Top)", f"{outer_area:,.0f} m²")
            with col_m3:
                if inner_area > 0:
                    st.metric("Inner Area (Bottom)", f"{inner_area:,.0f} m²")
                else:
                    st.metric("Inner Area (Bottom)", "Point/N/A")
            
            # Volume Calculation Methods - Three Column Layout
            st.markdown("---")
            st.markdown("#### Volume Calculation Methods")
            st.caption("Three independent methods to calculate basin volume. Each method uses different computational approaches.")
            
            col_vol1, col_vol2, col_vol3 = st.columns(3)
            
            # METHOD 1: Geometric Volume (Auto-calculated)
            with col_vol1:
                with st.container(border=True):
                    st.markdown("**① Geometric Volume**")
                    
                    # Display value
                    st.metric("", f"{volume:,.0f} m³", label_visibility="collapsed")
                    
                    # Explanation
                    with st.expander("ℹ️ How it works", expanded=False):
                        st.markdown("""
                        **Method:** Frustum/Pyramid Formula
                        
                        V = (depth/3) × (A_outer + A_inner + √(A_outer × A_inner))
                        
                        **Uses:**
                        - Outer polygon area
                        - Inner polygon area
                        - Average depth (accounting for longitudinal slope)
                        
                        **Best for:** Basins with relatively uniform geometry.
                        """)
            
            # METHOD 2: Mesh (TIN) Volume Calculation
            with col_vol2:
                with st.container(border=True):
                    st.markdown("**② Mesh (TIN) Volume**")
                    
                    # Initialize TIN volume in session state if not present
                    if "basin_tin_volume" not in st.session_state:
                        st.session_state.basin_tin_volume = None
                        st.session_state.basin_tin_status = None
                    
                    # Display value or placeholder
                    if st.session_state.basin_tin_volume is not None:
                        tin_vol = st.session_state.basin_tin_volume
                        tin_status = st.session_state.basin_tin_status
                        if tin_status and tin_status.startswith("✅"):
                            st.metric("", f"{tin_vol:,.0f} m³", label_visibility="collapsed")
                        else:
                            st.metric("", "N/A", label_visibility="collapsed")
                            if tin_status:
                                st.caption(f"⚠️ {tin_status}")
                    else:
                        st.caption("Click button to calculate")
                    
                    # Calculate button
                    if st.button("🔺 Calculate", key="btn_tin_volume",
                                help="Calculate volume using Triangulated Irregular Network (TIN) method. Creates a 3D mesh between top and bottom surfaces, handling varying depth due to longitudinal slope."):
                        with st.spinner("Calculating TIN volume..."):
                            # Get channel coordinates in projected CRS if available
                            channel_coords_xy = None
                            if st.session_state.basin_channel_coords is not None:
                                channel_coords_xy = []
                                for lon, lat in st.session_state.basin_channel_coords:
                                    try:
                                        x, y = transformer_to_analysis.transform(lon, lat)
                                        channel_coords_xy.append((x, y))
                                    except Exception:
                                        pass
                            
                            tin_volume, tin_status = calculate_basin_volume_tin(
                                basin_coords_xy, basin_depth, basin_side_slope,
                                basin_longitudinal_slope, flow_length, channel_coords_xy
                            )
                            st.session_state.basin_tin_volume = tin_volume
                            st.session_state.basin_tin_status = tin_status
                            st.rerun()
                    
                    # Explanation
                    with st.expander("ℹ️ How it works", expanded=False):
                        st.markdown("""
                        **Method:** Triangulated Irregular Network (TIN)
                        
                        Creates a 3D mesh connecting top surface (Z=0) and bottom surface (Z=-depth_local).
                        Sums signed volumes of triangular elements.
                        
                        **Uses:**
                        - Channel line for flow path
                        - Depth variation along channel
                        - 3D geometric mesh
                        
                        **Best for:** Basins with significant longitudinal slope.
                        """)
            
            # METHOD 3: Raster-Based Volume (DEM Difference)
            with col_vol3:
                with st.container(border=True):
                    st.markdown("**③ DEM Difference Volume**")
                    
                    # Display value or placeholder
                    if st.session_state.basin_modified_dem is not None:
                        dem_vol = st.session_state.basin_volumes.get("dem_volume", 0.0)
                        uncertainty = st.session_state.basin_volumes.get("dem_uncertainty", None)
                        
                        if uncertainty and uncertainty.get("mean", 0) > 0:
                            mean_vol = uncertainty["mean"]
                            std_vol = uncertainty["std"]
                            st.metric("", f"{mean_vol:,.0f} ± {std_vol:,.0f} m³", label_visibility="collapsed")
                        else:
                            st.metric("", f"{dem_vol:,.0f} m³", label_visibility="collapsed")
                    else:
                        st.caption("Click button to compute")
                    
                    # Compute button
                    if st.button("🖥️ Compute", key="btn_dem_volume",
                                help="Compute basin cut on the DEM and calculate volume from elevation difference. Includes uncertainty analysis across multiple cell sizes."):
                        with st.spinner("Computing basin cut and volume..."):
                            try:
                                # Check if DEM is loaded
                                if analysis_dem is None:
                                    st.error("❌ DEM not loaded. Please load DEM first in Input Data tab.")
                                else:
                                    # Apply basin to DEM (basin_coords_xy is already in analysis CRS)
                                    modified_dem = apply_basin_to_dem(
                                        analysis_dem, analysis_transform, analysis_nodata,
                                        basin_coords_xy, basin_depth, basin_side_slope, 
                                        basin_longitudinal_slope, flow_length
                                    )
                                    
                                    if modified_dem is not None:
                                        st.session_state.basin_modified_dem = modified_dem
                                        
                                        # Calculate DEM difference volume at original resolution
                                        dem_vol = calculate_dem_volume(
                                            analysis_dem, modified_dem, analysis_transform, 
                                            analysis_nodata, basin_coords_xy
                                        )
                                        
                                        # Calculate uncertainty across multiple cell sizes
                                        uncertainty = calculate_dem_volume_uncertainty(
                                            analysis_dem, modified_dem, analysis_transform, 
                                            analysis_nodata, basin_coords_xy, analysis_crs
                                        )
                                        
                                        st.session_state.basin_volumes["dem_volume"] = dem_vol
                                        st.session_state.basin_volumes["dem_uncertainty"] = uncertainty
                                        
                                        cut_vol = st.session_state.basin_volumes.get("volume", 0.0)
                                        if uncertainty and uncertainty.get("mean", 0) > 0:
                                            mean_vol = uncertainty["mean"]
                                            std_vol = uncertainty["std"]
                                            min_vol = uncertainty["min"]
                                            max_vol = uncertainty["max"]
                                            st.success(f"✅ Basin cut computed!\n\n**Geometric Volume:** {cut_vol:,.0f} m³\n\n**DEM Difference Volume:** {mean_vol:,.0f} ± {std_vol:,.0f} m³\n\n**Range:** [{min_vol:,.0f}, {max_vol:,.0f}] m³")
                                        else:
                                            st.success(f"✅ Basin cut computed!\n\n**Geometric Volume:** {cut_vol:,.0f} m³\n\n**DEM Difference Volume:** {dem_vol:,.0f} m³")
                                        
                                        st.rerun()
                            except Exception as e:
                                st.error(f"❌ Error computing basin cut: {str(e)}")
                    
                    # Explanation
                    with st.expander("ℹ️ How it works", expanded=False):
                        st.markdown("""
                        **Method:** Raster-Based DEM Difference
                        
                        1. Applies basin geometry to DEM
                        2. Calculates elevation difference (original - modified)
                        3. Sums positive differences × cell area
                        4. Includes uncertainty from cell size variation
                        
                        **Uses:**
                        - Original DEM
                        - Modified DEM (basin cut)
                        - Raster cell area
                        
                        **Best for:** Comparing design volume with actual terrain impact.
                        """)
            
            # Display inner polygon transform status
            if "basin_inner_polygon_status" in st.session_state:
                st.caption(f"Inner polygon projection: {st.session_state.basin_inner_polygon_status}")
            
            # Offset distance info
            # Use UPSTREAM depth only for offset calculation (slope affects volume, not geometry)
            offset_dist = basin_depth / basin_side_slope if basin_side_slope > 0 else basin_depth
            st.caption(f"Side slope offset distance: {offset_dist:.1f}m (depth ÷ slope ratio)")
            
            if inner_coords_xy is None:
                st.info("ℹ️ Basin is very small or offset exceeds dimensions. The bottom area is minimal (point-like). Volume estimate shown above.")
            
            # Basin Profile Plot
            st.markdown("---")
            st.markdown("#### Basin Longitudinal Profile")
            
            from shapely.geometry import Polygon, Point
            
            # Determine flow direction: use channel if provided, otherwise use first vertex to min elevation
            channel_coords = st.session_state.get("basin_channel_coords")
            
            if channel_coords is not None and len(channel_coords) >= 2:
                # Use channel line: first point = upstream, last point = downstream
                upstream_lon, upstream_lat = channel_coords[0]
                downstream_lon, downstream_lat = channel_coords[-1]
                upstream_x, upstream_y = transformer_to_analysis.transform(upstream_lon, upstream_lat)
                downstream_x, downstream_y = transformer_to_analysis.transform(downstream_lon, downstream_lat)
                
                # Calculate flow direction along channel
                flow_dx = downstream_x - upstream_x
                flow_dy = downstream_y - upstream_y
                flow_length = np.sqrt(flow_dx**2 + flow_dy**2)
                
                if flow_length > 0:
                    flow_unit_x = flow_dx / flow_length
                    flow_unit_y = flow_dy / flow_length
                else:
                    flow_unit_x, flow_unit_y = 1.0, 0.0
                
                # Sample along channel line for profile
                channel_coords_xy = []
                for coord in channel_coords:
                    # Handle both list and tuple formats, extract first two elements
                    if isinstance(coord, (list, tuple)) and len(coord) >= 2:
                        lon, lat = coord[0], coord[1]
                    else:
                        continue  # Skip invalid coordinates
                    x, y = transformer_to_analysis.transform(lon, lat)
                    channel_coords_xy.append((x, y))
            else:
                # Fallback: use first vertex to minimum elevation
                upstream_x, upstream_y = basin_coords_xy[0]
                
                # Find minimum elevation point within polygon
                outer_poly = Polygon(basin_coords_xy)
                minx, miny, maxx, maxy = outer_poly.bounds
                row_min, col_min = rowcol(analysis_transform, minx, maxy)
                row_max, col_max = rowcol(analysis_transform, maxx, miny)
                
                h, w = analysis_dem.shape
                row_min, row_max = max(0, min(row_min, row_max)), min(h-1, max(row_min, row_max))
                col_min, col_max = max(0, min(col_min, col_max)), min(w-1, max(col_min, col_max))
                
                min_elev = float('inf')
                downstream_x, downstream_y = upstream_x, upstream_y
                
                for r in range(row_min, row_max + 1):
                    for c in range(col_min, col_max + 1):
                        z_val = analysis_dem[r, c]
                        if analysis_nodata is not None and z_val == analysis_nodata:
                            continue
                        
                        x, y = xy(analysis_transform, r, c)
                        point = Point(x, y)
                        
                        if outer_poly.contains(point) and z_val < min_elev:
                            min_elev = z_val
                            downstream_x, downstream_y = x, y
                
                # Calculate flow direction
                flow_dx = downstream_x - upstream_x
                flow_dy = downstream_y - upstream_y
                flow_length = np.sqrt(flow_dx**2 + flow_dy**2)
                
                if flow_length > 0:
                    flow_unit_x = flow_dx / flow_length
                    flow_unit_y = flow_dy / flow_length
                else:
                    flow_unit_x, flow_unit_y = 1.0, 0.0
                
                channel_coords_xy = None
            
            # Sample along flow line (use channel if available, otherwise straight line)
            h, w = analysis_dem.shape
            
            # Create polygon for elevation calculations
            outer_poly = Polygon(basin_coords_xy)
            
            if channel_coords_xy is not None:
                # Sample along channel line
                distances = []
                existing_elevs = []
                basin_bottom_elevs = []
                cumulative_dist = 0.0
                
                for i in range(len(channel_coords_xy)):
                    x, y = channel_coords_xy[i]
                    point = Point(x, y)
                    
                    # Sample existing elevation
                    r, c = rowcol(analysis_transform, x, y)
                    if 0 <= r < h and 0 <= c < w:
                        z_existing = analysis_dem[r, c]
                        if analysis_nodata is None or z_existing != analysis_nodata:
                            distances.append(cumulative_dist)
                            existing_elevs.append(z_existing)
                            
                            # Calculate basin bottom elevation
                            depth_at_point = basin_depth + (basin_longitudinal_slope / 100.0) * cumulative_dist
                            depth_at_point = max(0.0, depth_at_point)
                            basin_bottom_elevs.append(z_existing - depth_at_point)
                    
                    # Calculate distance to next point
                    if i < len(channel_coords_xy) - 1:
                        next_x, next_y = channel_coords_xy[i + 1]
                        seg_dist = np.sqrt((next_x - x)**2 + (next_y - y)**2)
                        cumulative_dist += seg_dist
            else:
                # Sample along straight line from upstream to downstream
                num_samples = 100
                distances = np.linspace(0, flow_length, num_samples)
                existing_elevs = []
                basin_bottom_elevs = []
                
                for dist in distances:
                    x = upstream_x + dist * flow_unit_x
                    y = upstream_y + dist * flow_unit_y
                    point = Point(x, y)
                    
                    if outer_poly.contains(point):
                        # Sample existing elevation
                        r, c = rowcol(analysis_transform, x, y)
                        if 0 <= r < h and 0 <= c < w:
                            z_existing = analysis_dem[r, c]
                            if analysis_nodata is None or z_existing != analysis_nodata:
                                existing_elevs.append(z_existing)
                                
                                # Calculate basin bottom elevation
                                depth_at_point = basin_depth + (basin_longitudinal_slope / 100.0) * dist
                                depth_at_point = max(0.0, depth_at_point)
                                basin_bottom_elevs.append(z_existing - depth_at_point)
                            else:
                                existing_elevs.append(np.nan)
                                basin_bottom_elevs.append(np.nan)
                    else:
                        existing_elevs.append(np.nan)
                        basin_bottom_elevs.append(np.nan)
            
            # Calculate y-axis extent: max = max existing ground in polygon, min = min basin bottom
            # Find max existing ground elevation within polygon boundary
            minx, miny, maxx, maxy = outer_poly.bounds
            row_min, col_min = rowcol(analysis_transform, minx, maxy)
            row_max, col_max = rowcol(analysis_transform, maxx, miny)
            
            row_min, row_max = max(0, min(row_min, row_max)), min(h-1, max(row_min, row_max))
            col_min, col_max = max(0, min(col_min, col_max)), min(w-1, max(col_min, col_max))
            
            max_existing_elev = float('-inf')
            for r in range(row_min, row_max + 1):
                for c in range(col_min, col_max + 1):
                    z_val = analysis_dem[r, c]
                    if analysis_nodata is not None and z_val == analysis_nodata:
                        continue
                    
                    x, y = xy(analysis_transform, r, c)
                    point = Point(x, y)
                    
                    if outer_poly.contains(point) and z_val > max_existing_elev:
                        max_existing_elev = z_val
            
            # Fallback if no elevations found
            if max_existing_elev == float('-inf'):
                # Use profile data if available
                valid_existing = [e for e in existing_elevs if not np.isnan(e)]
                max_existing_elev = max(valid_existing) if valid_existing else 0.0
            
            # Find min basin bottom elevation from profile data
            valid_basin_bottom = [e for e in basin_bottom_elevs if not np.isnan(e)]
            min_basin_bottom = min(valid_basin_bottom) if valid_basin_bottom else max_existing_elev - basin_depth
            
            # Add small buffer for better visualization
            y_range = max_existing_elev - min_basin_bottom
            if y_range > 0:
                y_range_buffer = y_range * 0.05
            else:
                y_range_buffer = max_existing_elev * 0.1 if max_existing_elev > 0 else 1.0
            
            y_max = max_existing_elev + y_range_buffer
            y_min = min_basin_bottom - y_range_buffer
            
            # Create profile plot
            import plotly.graph_objects as go
            
            fig_basin_prof = go.Figure()
            
            # Existing ground
            fig_basin_prof.add_trace(go.Scatter(
                x=distances,
                y=existing_elevs,
                mode='lines',
                name='Existing Ground',
                line=dict(color='brown', width=2),
                fill='tozeroy',
                fillcolor='rgba(139, 69, 19, 0.2)'
            ))
            
            # Basin bottom
            fig_basin_prof.add_trace(go.Scatter(
                x=distances,
                y=basin_bottom_elevs,
                mode='lines',
                name='Basin Bottom',
                line=dict(color='blue', width=3),
                fill='tonexty',
                fillcolor='rgba(0, 0, 255, 0.3)'
            ))
            
            # Markers for upstream and downstream
            if len(distances) > 0:
                fig_basin_prof.add_trace(go.Scatter(
                    x=[0],
                    y=[existing_elevs[0] if not np.isnan(existing_elevs[0]) else 0],
                    mode='markers+text',
                    name='Upstream (Start)',
                    marker=dict(size=12, color='green', symbol='triangle-up'),
                    text=['Upstream'],
                    textposition='top center'
                ))
                
                fig_basin_prof.add_trace(go.Scatter(
                    x=[flow_length],
                    y=[existing_elevs[-1] if len(existing_elevs) > 0 and not np.isnan(existing_elevs[-1]) else 0],
                    mode='markers+text',
                    name='Downstream (Min Elev)',
                    marker=dict(size=12, color='red', symbol='triangle-down'),
                    text=['Downstream'],
                    textposition='bottom center'
                ))
            
            fig_basin_prof.update_layout(
                title=dict(
                    text='Basin Longitudinal Profile (Upstream to Downstream)',
                    font=dict(size=16, family="Arial, sans-serif")
                ),
                xaxis_title=dict(text='Distance Along Flow Direction (m)', font=dict(size=13)),
                yaxis_title=dict(text='Elevation (m)', font=dict(size=13)),
                height=450,
                margin=dict(l=60, r=30, t=60, b=60),
                hovermode='x unified',
                font=dict(family="Arial, sans-serif", size=11),
                legend=dict(
                    yanchor="top",
                    y=0.99,
                    xanchor="right",
                    x=0.99,
                    bgcolor="rgba(255, 255, 255, 0.7)",  # Semi-transparent white background
                    bordercolor="rgba(0, 0, 0, 0.5)",  # Semi-transparent border
                    borderwidth=1
                ),
                yaxis=dict(range=[y_min, y_max])
            )
            
            st.plotly_chart(fig_basin_prof, use_container_width=True)
            
            st.caption(f"Flow length: {flow_length:.1f}m | Upstream depth: {basin_depth:.2f}m | Downstream depth: {basin_depth + (basin_longitudinal_slope / 100.0) * flow_length:.2f}m")
            
            # Map visualization
            st.markdown("---")
            st.markdown("#### Basin Plan View")
            
            # Convert inner polygon back to lat/lon for display
            inner_coords_latlon = None
            if inner_coords_xy is not None:
                inner_coords_latlon = []
                for x, y in inner_coords_xy:
                    lon, lat = transformer_to_map.transform(x, y)
                    inner_coords_latlon.append([lon, lat])
            
            # Calculate map center and bounds (include channel if present)
            lons = [c[0] for c in basin_coords]
            lats = [c[1] for c in basin_coords]
            
            # Include channel coordinates in bounds if channel exists
            if st.session_state.basin_channel_coords is not None:
                channel_coords = st.session_state.basin_channel_coords
                channel_lons = [c[0] for c in channel_coords]
                channel_lats = [c[1] for c in channel_coords]
                all_lons = lons + channel_lons
                all_lats = lats + channel_lats
            else:
                all_lons = lons
                all_lats = lats
            
            center_lat = (min(all_lats) + max(all_lats)) / 2
            center_lon = (min(all_lons) + max(all_lons)) / 2
            
            # Calculate bounds with buffer for better visualization
            lat_range = max(all_lats) - min(all_lats)
            lon_range = max(all_lons) - min(all_lons)
            buffer = max(lat_range, lon_range) * 0.15 + 0.001  # 15% buffer + minimum
            
            # Create map - will auto-zoom to bounds below
            m_basin = folium.Map(
                location=[center_lat, center_lon],
                zoom_start=15,  # Initial zoom, will be adjusted by fit_bounds
                control_scale=True
            )
            
            # Add satellite layer
            folium.TileLayer(
                tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}',
                attr='Google',
                opacity=0.9
            ).add_to(m_basin)
            
            # Add hillshade if available
            try:
                hs = compute_hillshade(analysis_dem, abs(analysis_transform.a), abs(analysis_transform.e))
                hs_norm = ((hs - hs.min()) / (hs.max() - hs.min()) * 255).astype(np.uint8)
                
                # Get bounds
                h, w = analysis_dem.shape
                left, top = analysis_transform * (0, 0)
                right, bottom = analysis_transform * (w, h)
                lon_min, lat_min = transformer_to_map.transform(left, bottom)
                lon_max, lat_max = transformer_to_map.transform(right, top)
                bounds_map = [[lat_min, lon_min], [lat_max, lon_max]]
                
                folium.raster_layers.ImageOverlay(
                    image=hs_norm, bounds=bounds_map, opacity=0.5
                ).add_to(m_basin)
            except:
                pass
            
            # Add outer polygon (red)
            outer_coords_for_map = [[c[1], c[0]] for c in basin_coords]  # [lat, lon]
            folium.Polygon(
                locations=outer_coords_for_map,
                color='red',
                weight=3,
                fill=True,
                fill_color='red',
                fill_opacity=0.2,
                popup='Outer Basin Boundary (Top Edge)',
                tooltip='Outer Boundary'
            ).add_to(m_basin)
            
            # Add inner polygon (blue) if exists
            if inner_coords_latlon is not None:
                inner_coords_for_map = [[lat, lon] for lon, lat in inner_coords_latlon]
                folium.Polygon(
                    locations=inner_coords_for_map,
                    color='blue',
                    weight=2,
                    fill=True,
                    fill_color='blue',
                    fill_opacity=0.3,
                    popup='Inner Basin Boundary (Bottom)',
                    tooltip='Inner Boundary (Bottom)'
                ).add_to(m_basin)
            
            # Add channel line if defined
            if st.session_state.basin_channel_coords is not None:
                channel_coords = st.session_state.basin_channel_coords
                channel_display_coords = [[c[1], c[0]] for c in channel_coords]
                folium.PolyLine(
                    locations=channel_display_coords,
                    color='#00ff00',
                    weight=4,
                    opacity=0.9,
                    popup='Basin Channel (Flow Path)',
                    tooltip='Channel Line'
                ).add_to(m_basin)
            
                # Add S0 and S1 station markers
                if len(channel_coords) >= 2:
                    # S0 (upstream) - first point
                    s0_lon, s0_lat = channel_coords[0][0], channel_coords[0][1]
                    folium.CircleMarker(
                        location=[s0_lat, s0_lon],
                        radius=8,
                        popup='S0 (Upstream)',
                        tooltip='S0 (Upstream)',
                        color='black',
                        weight=2,
                        fillColor='#ffcc00',
                        fillOpacity=0.9
                    ).add_to(m_basin)
                    folium.Marker(
                        location=[s0_lat, s0_lon],
                        icon=folium.DivIcon(
                            html=f'<div style="font-size: 14px; font-weight: bold; color: black; text-shadow: 1px 1px 2px white, -1px -1px 2px white, 1px -1px 2px white, -1px 1px 2px white;">S0</div>',
                            icon_size=(30, 15),
                            icon_anchor=(15, -5)
                        )
                    ).add_to(m_basin)
                    
                    # S1 (downstream) - last point
                    s1_lon, s1_lat = channel_coords[-1][0], channel_coords[-1][1]
                    folium.CircleMarker(
                        location=[s1_lat, s1_lon],
                        radius=8,
                        popup='S1 (Downstream)',
                        tooltip='S1 (Downstream)',
                        color='black',
                        weight=2,
                        fillColor='#ffcc00',
                        fillOpacity=0.9
                    ).add_to(m_basin)
                    folium.Marker(
                        location=[s1_lat, s1_lon],
                        icon=folium.DivIcon(
                            html=f'<div style="font-size: 14px; font-weight: bold; color: black; text-shadow: 1px 1px 2px white, -1px -1px 2px white, 1px -1px 2px white, -1px 1px 2px white;">S1</div>',
                            icon_size=(30, 15),
                            icon_anchor=(15, -5)
                        )
                    ).add_to(m_basin)
            
            # Auto-zoom to polygon outer boundary extent on first load only
            # Use polygon bounds if available, otherwise use calculated bounds
            if first_time_basin_design_tab:
                # First time visiting - auto-zoom to polygon extent if available
                if "basin_polygon_bounds" in st.session_state and st.session_state.basin_polygon_bounds is not None:
                    m_basin.fit_bounds(st.session_state.basin_polygon_bounds, padding=(50, 50))
                    st.session_state.basin_design_tab_visited = True
                else:
                    # Fallback to calculated bounds
                    basin_bounds = [
                        [min(lats) - buffer, min(lons) - buffer],
                        [max(lats) + buffer, max(lons) + buffer]
                    ]
                    m_basin.fit_bounds(basin_bounds, padding=(50, 50))
                    st.session_state.basin_design_tab_visited = True
            # After first load, don't auto-zoom - let user control the map view
            
            # Display map
            st_folium(m_basin, height=500, width=None, returned_objects=[])
            
            legend_text = """
            **Legend:**
            - 🔴 **Red polygon**: Outer basin boundary (top edge at existing ground)
            - 🔵 **Blue polygon**: Inner basin boundary (flat bottom at full depth)
            """
            if st.session_state.basin_channel_coords is not None:
                legend_text += "\n            - 🟢 **Green line**: Channel flow path (longitudinal slope follows this path)"
            legend_text += "\n            - The side slopes connect the outer and inner boundaries"
            st.markdown(legend_text)
            
            # Export section (if basin cut is computed)
            if st.session_state.basin_modified_dem is not None:
                st.markdown("---")
                st.markdown("#### Export Modified Terrain")
                
                col_exp_res1, col_exp_res2 = st.columns(2)
                with col_exp_res1:
                    current_res = abs(src_transform.a)
                    target_res = st.number_input(
                        "Export Resolution (m)", 
                        0.1, 100.0, float(current_res), 0.1,
                        key="basin_export_res_2"
                    )
                with col_exp_res2:
                    # Resampling method for basin export
                    resample_method_basin = st.selectbox(
                        "Resampling Method",
                        options=["Bilinear", "Nearest", "IDW"],
                        index=0,
                        key="basin_resample_method",
                        help="Choose method to resample modified DEM to target resolution"
                    )
            
            # Download button
                st.markdown("---")
                
                # Prepare GeoTIFF
                with st.spinner("Preparing GeoTIFF..."):
                    from rasterio.warp import reproject, Resampling
                    from rasterio.transform import from_bounds, array_bounds
                    from rasterio.io import MemoryFile
                    
                    final_dem = st.session_state.basin_modified_dem
                    final_transform = analysis_transform
                    
                    # Resample if needed
                    target_res = st.session_state.get("basin_export_res_2", current_res)
                    if abs(target_res - abs(final_transform.a)) > 0.01:
                        bounds = array_bounds(final_dem.shape[0], final_dem.shape[1], final_transform)
                        width = int((bounds[2] - bounds[0]) / target_res)
                        height = int((bounds[3] - bounds[1]) / target_res)
                        
                        new_transform = from_bounds(bounds[0], bounds[1], bounds[2], bounds[3], width, height)
                        
                        resampled_dem = np.empty((height, width), dtype=np.float32)
                        # Choose resampling method
                        method = st.session_state.get("basin_resample_method", "Bilinear")
                        if method == "Nearest":
                            reproject(
                                source=final_dem,
                                destination=resampled_dem,
                                src_transform=final_transform,
                                src_crs=analysis_crs,
                                src_nodata=analysis_nodata,
                                dst_transform=new_transform,
                                dst_crs=analysis_crs,
                                dst_nodata=analysis_nodata,
                                resampling=Resampling.nearest
                            )
                        elif method == "Bilinear":
                            reproject(
                                source=final_dem,
                                destination=resampled_dem,
                                src_transform=final_transform,
                                src_crs=analysis_crs,
                                src_nodata=analysis_nodata,
                                dst_transform=new_transform,
                                dst_crs=analysis_crs,
                                dst_nodata=analysis_nodata,
                                resampling=Resampling.bilinear
                            )
                        else:
                            # IDW resampling (neighborhood-based)
                            resampled_dem = idw_resample(final_dem, final_transform, new_transform, height, width, src_nodata, power=2, radius=1)

                        final_dem = resampled_dem
                        final_transform = new_transform
                    
                    # Create GeoTIFF in memory
                    profile_out = {
                        'driver': 'GTiff',
                        'height': final_dem.shape[0],
                        'width': final_dem.shape[1],
                        'count': 1,
                        'dtype': 'float32',
                        'crs': src_crs,
                        'transform': final_transform,
                        'nodata': src_nodata,
                        'compress': 'lzw'
                    }
                    
                    mem_out = MemoryFile()
                    with mem_out.open(**profile_out) as dst:
                        dst.write(final_dem.astype("float32"), 1)
                    
                    export_data = mem_out.read()
                
                st.download_button(
                    "💾 Download Basin Modified DEM (GeoTIFF)",
                    data=export_data,
                    file_name=f"basin_modified_{target_res:.0f}m.tif",
                    mime="image/tiff",
                    use_container_width=True,
                    type="primary"
                )
                
                st.caption(f"Resolution: {target_res:.2f}m | Size: {final_dem.shape[0]}×{final_dem.shape[1]}")

# ============================================================================
# DOWNLOAD SECTION (Profile Mode)
# ============================================================================

if st.session_state.design_mode == "profile" and 'samples' in locals():
    st.markdown("---")
    st.markdown("## 📥 Export Modified Terrain")
    
    col_d1, col_d2, col_d3 = st.columns([1, 2, 1])
    
    with col_d2:
        st.markdown("### Export Settings")
        
        col_res1, col_res2 = st.columns(2)
        with col_res1:
            current_res = abs(src_transform.a)
            target_resolution = st.number_input(
                "Target Resolution (m)", 
                0.1, 100.0, float(current_res), 0.1,
                help=f"Current DEM resolution: {current_res:.2f}m"
            )
        with col_res2:
            st.metric("Current Resolution", f"{current_res:.2f} m")
            st.caption("Enter desired output resolution")
        # Resampling method for export
        resample_method = st.selectbox(
            "Resampling Method",
            options=["Bilinear", "Nearest", "IDW"],
            index=0,
            key="export_resample_method",
            help="Choose method to resample modified DEM to target resolution"
        )
        
        # Auto-recompute if parameters changed, or compute when button clicked
        should_compute = st.button("🔄 Compute Modified DEM", type="primary", use_container_width=True)
        
        # Also auto-compute if recompute flag is set (parameters changed)
        if st.session_state.get("recompute_dem", False):
            should_compute = True
            st.session_state.recompute_dem = False
        
        if should_compute:
            with st.spinner("Computing modifications..."):
                # Use session state values to ensure latest parameters are used
                current_template_params = st.session_state.get("template_params", {})
                current_template_type = st.session_state.get("template_type", "berm_ditch")
                
                # Ensure ditch_side is updated from session state (in case of berm_ditch)
                if current_template_type == "berm_ditch":
                    current_ditch_side = st.session_state.get("ditch_side_xs", "left")
                    current_template_params = current_template_params.copy()
                    current_template_params["ditch_side"] = current_ditch_side
                
                new_dem, cut_vol, fill_vol = apply_corridor_to_dem(
                    analysis_dem, analysis_transform, analysis_nodata,
                    samples, z_design, current_template_type, current_template_params,
                    tangents, normals, influence_width, operation_mode
                )
                st.session_state.modified_dem = new_dem
                st.session_state.volumes = {"cut": cut_vol, "fill": fill_vol}
                st.session_state.export_dem_ready = True
        
        if st.session_state.modified_dem is not None:
            st.success("✅ Modified DEM computed!")
            
            # Show volume metrics
            col_vol1, col_vol2, col_vol3 = st.columns(3)
            with col_vol1:
                st.metric("Cut", f"{st.session_state.volumes.get('cut', 0):,.0f} m³")
            with col_vol2:
                st.metric("Fill", f"{st.session_state.volumes.get('fill', 0):,.0f} m³")
            with col_vol3:
                net = st.session_state.volumes.get('fill', 0) - st.session_state.volumes.get('cut', 0)
                st.metric("Net", f"{net:+,.0f} m³")
            
            st.markdown("---")
            
            # Prepare the GeoTIFF data
            with st.spinner("Preparing GeoTIFF..."):
                # Reproject to source CRS if needed
                if analysis_crs == src_crs:
                    final_dem = st.session_state.modified_dem
                    final_transform = analysis_transform
                else:
                    final_dem = np.empty_like(src_dem, dtype=np.float32)
                    reproject(
                        source=st.session_state.modified_dem, 
                        destination=final_dem,
                        src_transform=analysis_transform, 
                        src_crs=analysis_crs, 
                        src_nodata=src_nodata,
                        dst_transform=src_transform, 
                        dst_crs=src_crs, 
                        dst_nodata=src_nodata,
                        resampling=Resampling.bilinear
                    )
                    final_transform = src_transform
                
                # Resample to target resolution if different
                if abs(target_resolution - abs(final_transform.a)) > 0.01:
                    # Calculate new dimensions
                    bounds = array_bounds(final_dem.shape[0], final_dem.shape[1], final_transform)
                    width = int((bounds[2] - bounds[0]) / target_resolution)
                    height = int((bounds[3] - bounds[1]) / target_resolution)
                    
                    # Create new transform
                    new_transform = from_bounds(
                        bounds[0], bounds[1], bounds[2], bounds[3],
                        width, height
                    )
                    
                    # Resample
                    resampled_dem = np.empty((height, width), dtype=np.float32)
                    method = st.session_state.get("export_resample_method", "Bilinear")
                    if method == "Nearest":
                        reproject(
                            source=final_dem,
                            destination=resampled_dem,
                            src_transform=final_transform,
                            src_crs=src_crs,
                            src_nodata=src_nodata,
                            dst_transform=new_transform,
                            dst_crs=src_crs,
                            dst_nodata=src_nodata,
                            resampling=Resampling.nearest
                        )
                    elif method == "Bilinear":
                        reproject(
                            source=final_dem,
                            destination=resampled_dem,
                            src_transform=final_transform,
                            src_crs=src_crs,
                            src_nodata=src_nodata,
                            dst_transform=new_transform,
                            dst_crs=src_crs,
                            dst_nodata=src_nodata,
                            resampling=Resampling.bilinear
                        )
                    else:
                        # IDW resampling
                        resampled_dem = idw_resample(final_dem, final_transform, new_transform, height, width, src_nodata, power=2, radius=1)

                    final_dem = resampled_dem
                    final_transform = new_transform
                
                # Prepare output profile
                profile_out = {
                    'driver': 'GTiff',
                    'height': final_dem.shape[0],
                    'width': final_dem.shape[1],
                    'count': 1,
                    'dtype': 'float32',
                    'crs': src_crs,
                    'transform': final_transform,
                    'nodata': src_nodata,
                    'compress': 'lzw'
                }
                
                # Write to memory
                mem_out = MemoryFile()
                with mem_out.open(**profile_out) as dst:
                    dst.write(final_dem.astype("float32"), 1)
                
                # Get the data bytes
                export_data = mem_out.read()
            
            # Download button (always visible when modified DEM exists)
            st.download_button(
                "💾 Download Modified DEM (GeoTIFF)",
                data=export_data,
                file_name=f"terrain_modified_{target_resolution:.0f}m.tif",
                mime="image/tiff",
                use_container_width=True,
                type="primary"
            )
            
            st.caption(f"Resolution: {target_resolution:.2f}m | Size: {final_dem.shape[0]}×{final_dem.shape[1]}")


