# Calculation Methods — Terrain Editor Pro

This document describes the numerical and geometric methods used by the app for
volumes, cross-sections, and area estimates. Units in the app are metric (meters).

Contents
- Volume calculations (Geometric frustum, TIN, DEM differencing)
- Cross-section generation and area integration
- Plan / basin area estimates
- Coordinate systems, nodata handling, and typical error sources
- Worked examples (volume, cross-section, area)

1. Volume calculations
----------------------

All volume computations assume metric units (meters for distance/elevation, m² for areas, m³ for volumes). Volumes are positive for excavation (cut) when calculated using DEM differencing (original minus modified). The app supports three methods; the geometric method is the canonical reference used for consistency across other approaches.

1.1 Geometric method (frustum-based)

Inputs:
- Outer polygon: plan (x,y) coordinates in the analysis CRS (projected meters)
- Inner polygon: offset inward from outer polygon using upstream depth and side slope
- Depth: basin depth at upstream end (m)
- Side slope: horizontal:vertical ratio (H:1V)
- Longitudinal slope: percent change along flow length (percent, e.g. 25 = 25%)
- Flow length: length along channel from upstream to downstream (m)

Procedure:
1. Compute outer polygon area A_o (m²) and inner polygon area A_i (m²). Inner polygon is created by offsetting the outer polygon inward by offset = depth / side_slope (horizontal distance) using shapely.buffer(-offset).
2. If longitudinal slope = 0 (no variation) the frustum formula is used:

   V = (D / 3) * (A_o + A_i + sqrt(A_o * A_i))

   where D is the depth (m).

3. If longitudinal slope ≠ 0 (depth varies linearly from upstream depth D_up to downstream depth D_down), the app computes D_down = D_up + (slope/100) * flow_length, clamps D_down ≥ 0, and approximates the integrated volume along the flow path using Simpson's rule applied to frustum volumes at three stations (upstream, midpoint, downstream):

   V_up = frustum(D_up)
   V_mid = frustum(D_mid)
   V_down = frustum(D_down)

   V_total ≈ (V_up + 4*V_mid + V_down) / 6

   where D_mid = (D_up + D_down)/2, and frustum(D) = (D/3)*(A_o + A_i + sqrt(A_o*A_i)).

Assumptions and notes:
- Inner polygon geometry is based on the upstream depth only. Depth variation along flow affects volume but not the inner polygon geometry.
- If inner polygon calculation fails or collapses (too small), the app falls back to a pyramid approximation: V ≈ (1/3) * A_o * D_avg, where D_avg is average depth along flow.

1.2 TIN method (mesh-based)

Inputs: same as geometric method plus optional channel line.

Procedure (conceptual):
- Create 3D point rings for outer (Z = 0) and inner (Z = -local depth) boundaries and construct a triangular mesh (TIN) connecting them. Compute signed volumes of triangular prisms / tetrahedra and sum inside-basin contributions.

Implementation note:
- The current implementation uses the geometric frustum calculation as the authoritative numeric value and uses the TIN pathway as a conceptual method and fallback for small basins; if inner area is very small relative to outer area the code uses the pyramid/frustum approximation for numerical stability.

1.3 DEM differencing method (raster comparison)

Inputs:
- Original DEM raster (Z_orig)
- Modified DEM raster after applying basin cut (Z_mod)
- Polygon (outer) in DEM projection or transformed into analysis CRS
- Raster transform (transform) and nodata value

Procedure:
1. Reproject/resample DEMs into a common analysis CRS and grid if necessary.
2. Compute difference: diff = Z_orig - Z_mod. Positive values indicate excavation (cut).
3. Sum positive differences for cells whose centers lie inside the polygon mask:

   volume = Σ_{cells inside polygon} max(diff_cell, 0) * cell_area

   where cell_area = |transform.a * transform.e| (meters² assuming transform.a is pixel width and transform.e is negative pixel height).

Handling nodata and NaNs:
- Cells with nodata in either DEM or NaN are skipped and not included in the sum.

Uncertainty analysis:
- The app can resample DEMs to multiple cell sizes (e.g., 0.5, 1, 2, 3, 4, 5 m) and compute volumes for each resolution. The resulting set of volumes is summarized with mean, std, min, max to provide an indication of resolution sensitivity.

2. Cross-section generation
---------------------------

2.1 Stationing and sampling

Profile extraction modes:
- Corner-vertex mode: the app creates design stations at each vertex of the user-drawn polyline (extract_profile_from_line).
- Equal-spacing sampling: optionally a denser sampling along the centreline is computed using `sample_line_at_spacing` to produce smooth visualization lines and terrain sampling.

Coordinate transforms
- Profile coordinates are normalized to [lon, lat] and transformed to the analysis CRS (projected meters) using pyproj. All distances and stationing are computed in the analysis CRS.

Normals and tangents
- Tangent vectors are computed at each station using forward/backward differences: interior points use centered difference, endpoints use forward/backward difference. Normals are 90° rotated tangents and used to project perpendicular offsets into plan coordinates.

Cross-section construction
1. For a given station, construct a set of offsets perpendicular to the centreline, typically N=201 samples across the full influence width: offsets = linspace(-W, +W, 201) where W = influence_width (m).
2. For each offset, compute the plan coordinate (x = xc + offset * nx, y = yc + offset * ny).
3. Use raster row/col mapping (rasterio.transform.rowcol) to sample the DEM elevation at the pixel containing the plan coordinate. If outside DEM bounds or nodata, elevation is NaN.
4. Template geometry (berm/ditch/swale) is evaluated at each offset to produce a template elevation z_tpl. Final elevation is chosen by operation mode:
   - fill: z_final = max(z_old, z_tpl)
   - cut: z_final = min(z_old, z_tpl)
   - both: z_final = z_tpl

Area integration across cross-section
- The cross-section area (cut or fill) is computed by integrating vertical differences between existing and final elevations across offsets. The code integrates between consecutive offset points using a trapezoidal-like approach (average elevation difference * width segment).

3. Plan and basin areas
-----------------------

Plan areas are computed with shapely in the analysis CRS. The polygon area returned by shapely is in square meters when coordinates are in a projected CRS with meter units.

Inner polygon (basin bottom) generation
- Inner polygon is created by buffering the outer polygon inward by offset_distance = depth / side_slope using shapely.buffer(-offset_distance). Join styles (mitre/bevel/round) are attempted if the first buffer fails. If a multipolygon is produced the largest piece is selected.

Grid / mesh assumptions
- DEM differencing uses raster cell centers to decide polygon membership and cell_area from transform (assumes square or rectangular pixels). If DEM is reprojected, resampling uses bilinear or configured resampling.

4. Coordinate system, vertical datum, and nodata
------------------------------------------------

- Coordinate systems: Input vector geometries are expected in geographic coordinates (lon/lat) or in a projected CRS. The app transforms between map CRS (EPSG:4326) and an analysis projected CRS (UTM-like) selected based on the DEM centroid. All area and distance calculations use the analysis CRS in meters.
- Vertical datum: Heights are taken as provided in the DEM. No vertical datum conversion is performed — if DEM uses a local vertical datum, volumes will be relative to that datum.
- Nodata handling: Pixels with nodata or NaN in either original or modified DEM are excluded from DEM differencing sums. Cross-section sampling returns NaN where DEM has nodata.

5. Rounding and numerical stability
----------------------------------
- Calculations use double precision floats (numpy float64/float32). Final UI metrics are typically shown rounded to 2 decimal places. Internal volume sums preserve full precision until presentation.
- When inner polygon area is tiny relative to outer area (<1% by default) the app falls back to pyramid/frustum approximations to avoid unstable geometry operations.

6. Typical sources of error and caveats
-------------------------------------
- DEM resolution and projection: coarse DEMs can under/over-estimate volumes when using DEM differencing. Resampling and reprojecting can introduce interpolation error.
- Inner polygon buffer failures: very deep offsets relative to polygon size can cause the offset operation to produce empty or degenerate geometries. The app enforces a heuristic maximum offset fraction and returns a clear message when offset is too large.
- Channel alignment: longitudinal slope calculations assume the channel line correctly represents upstream→downstream flow; reversed channel direction will invert slopes.
- Nodata handling: unfilled or masked DEM areas inside the polygon will reduce counted volume; check DEM completeness before trusting DEM-based volumes.

7. Worked examples
------------------

Example A — Frustum (no longitudinal slope)

Given:
- Outer polygon area A_o = 1200 m²
- Inner polygon area A_i = 400 m²
- Depth D = 3.0 m

Compute:

frustum(D) = (D/3) * (A_o + A_i + sqrt(A_o * A_i))

sqrt(A_o*A_i) = sqrt(1200 * 400) = sqrt(480000) ≈ 692.82

frustum = (3/3) * (1200 + 400 + 692.82) = 1 * 2292.82 = 2292.82 m³

Example B — Frustum with longitudinal slope

Given same A_o and A_i and upstream depth D_up = 3.0 m, longitudinal_slope = 20% over flow_length = 50 m.

D_down = 3.0 + 0.20 * 50 = 3.0 + 10.0 = 13.0 m (clamped as needed)

D_mid = (3.0 + 13.0)/2 = 8.0 m

Compute V_up, V_mid, V_down using frustum formula and then Simpson's rule:

V_total ≈ (V_up + 4*V_mid + V_down)/6

(Numeric example omitted here for brevity — same steps as Example A but with D values substituted.)

Example C — DEM differencing

Given a DEM with 1 m × 1 m cells, a polygon covering 10 cells where positive differences (orig - mod) are [0.5, 0.2, 1.0, 0, 0.6, 0.0, 0.8, 0.0, 0.3, 0.4] m

Volume = Σ positive diffs * cell_area = (0.5+0.2+1.0+0.6+0.8+0.3+0.4) * 1 m² = 3.8 m³

Example D — Cross-section area integration

Offsets: [-2, -1, 0, 1, 2] m (uniform spacing 1 m)
Existing elevations: [100, 101, 102, 101, 100]
Final elevations after template: [100, 100.5, 102.5, 100.5, 100]

At each segment between offsets compute average difference final - existing and multiply by width.
Segment 1 (between -2 and -1): avg diff = (0 -1?) (compute per values) — follow trapezoidal sums to obtain cut/fill areas in m².

8. References
- Raster math: rasterio transform conventions (rowcol, xy).
- Geometry operations: shapely buffer semantics and join styles.

If you need a worked numeric walk-through for your specific DEM and polygon, paste the polygon coordinates and a small DEM excerpt and the app or a developer can compute a step-by-step result.
