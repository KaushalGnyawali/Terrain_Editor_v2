import re
import numpy as np
from rasterio.transform import from_origin

# Read the terrain_editor file and extract the three function definitions
with open('terrain_editor.py', 'r', encoding='utf-8') as f:
    src = f.read()

# Patterns for functions to extract
funcs = ['calculate_dem_volume', 'calculate_dem_volume_uncertainty', 'apply_basin_to_dem']
extracted = ''
for func in funcs:
    m = re.search(r"def\s+" + func + r"\s*\([^\)]*\):", src)
    if not m:
        raise SystemExit(f'Could not find function {func} in terrain_editor.py')
    start = m.start()
    # Find end: next \ndef\s+ at column 0 after start
    rest = src[start:]
    # Find next top-level def (start of line)
    match_next = re.search(r"\n(?=def\s+)", rest)
    if match_next:
        end = start + match_next.start()
    else:
        end = len(src)
    extracted += src[start:end] + '\n\n'

# Execute extracted functions in a safe namespace with required imports
ns = {'np': np, '__builtins__': __builtins__}
exec(extracted, ns)

# Create synthetic DEM (flat 100m) with transform: origin at (0, 100), cellsize 1m
width = height = 100
cellsize = 1.0
origin_x, origin_y = 0.0, 100.0
transform = from_origin(origin_x, origin_y, cellsize, cellsize)

original_dem = np.full((height, width), 100.0, dtype=np.float32)

# Define a simple square polygon in projected coords covering central 40x40 cells
minx, miny = 30.0, 30.0
maxx, maxy = 70.0, 70.0
# Polygon as list of (x,y)
poly = [(minx, miny), (minx, maxy), (maxx, maxy), (maxx, miny), (minx, miny)]

# Parameters for basin
depth = 5.0
side_slope = 1.5
longitudinal_slope = 0.0
channel_coords = None

print('Running apply_basin_to_dem...')
new_dem_res = ns['apply_basin_to_dem'](original_dem, transform, None, poly, depth, side_slope, longitudinal_slope, channel_coords)
print('apply_basin_to_dem returned type:', type(new_dem_res))
# Expect tuple (new_dem, cut_volume)
if isinstance(new_dem_res, tuple):
    new_dem, cut_vol = new_dem_res
    print('cut_vol:', cut_vol)
else:
    new_dem = new_dem_res
    print('apply_basin_to_dem returned single object')

print('Running calculate_dem_volume...')
dem_vol = ns['calculate_dem_volume'](original_dem, new_dem, transform, None, poly)
print('DEM difference volume:', dem_vol)

print('Running calculate_dem_volume_uncertainty...')
try:
    unc = ns['calculate_dem_volume_uncertainty'](original_dem, new_dem, transform, None, poly, None, cell_sizes=[1.0, 2.0])
    print('Uncertainty result:', unc)
except Exception as e:
    print(f'Error in uncertainty calculation: {e}')
    import traceback
    traceback.print_exc()
