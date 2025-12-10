# Terrain Editor Pro v8.0 - Visual Guide

## 📊 BEFORE vs AFTER

### Station Direction

**BEFORE (v7.0):**
```
User draws: A ━━━━━━━━━━━━━━━━━━━━━━→ B
             (high)              (low)

App reverses: B ←━━━━━━━━━━━━━━━━━━━━━ A
             Station 0           Station N
```

**AFTER (v8.0):**
```
User draws: A ━━━━━━━━━━━━━━━━━━━━━━→ B
             (high)              (low)

App keeps:  A ━━━━━━━━━━━━━━━━━━━━━━→ B
           Station 0           Station N
```

---

### Profile Plot Y-Axis

**BEFORE (v7.0):**
```
Elevation (m)
    300 ┤
    250 ┤
    200 ┤     Profile line here
    150 ┤
    100 ┤
     50 ┤
      0 ┼───────────────────
        0   25   50   75  100
             Distance (m)
    
    ↑ Lots of wasted space!
```

**AFTER (v8.0):**
```
Elevation (m)
    252 ┤
    250 ┤─╲
    248 ┤  ╲  Profile line
    246 ┤   ╲
    244 ┤    ╲____
    242 ┼────────────────────
        0   25   50   75  100
             Distance (m)
    
    ↑ Zoomed to data!
```

---

### Berm+Ditch Configuration

**BEFORE (v7.0):**
```
Generic berm:
┌────┐
│    │ Berm
│    │
└────┘ Single parameter
```

**AFTER (v8.0):**
```
Professional design (matches screenshot):

        ╱╲ ← Berm Outer Slope (3:1)
       ╱  ╲
      ╱____╲ ← Berm Crest (3m wide)
     ╱      ╲
    ╱        ╲ ← Berm Inner Slope (2:1)
   ╱          ╲
  ╱            ╲
 ╱    Ditch     ╲ ← Ditch Side Slope (3:1)
╱______________╲ ← Ditch Bottom (2.5m wide)

Parameters:
1. Ditch Bottom Width: 2.5m
2. Ditch Side Slope: 3:1
3. Berm Height: 2.5m (above ditch)
4. Berm Inner Slope: 2:1
5. Berm Outer Slope: 3:1
6. Berm Top Width: 3.0m
```

---

### Next Button Behavior

**BEFORE (v7.0):**
```
User at Station 12
Click Next →
Goes to Station 0 ❌
```

**AFTER (v8.0):**
```
User at Station 12
Click Next →
Goes to Station 13 ✅
```

---

## 🆕 NEW FEATURES

### Polygon Basin Design Mode

**Design Mode Selection:**
```
┌─────────────────────────────────────┐
│ Design Mode ❓                       │
├─────────────────────────────────────┤
│ ⚪ Profile Line (Berm/Ditch)        │
│ ⚫ Polygon Basin                     │
└─────────────────────────────────────┘
```

**Map View (Basin Mode):**
```
     ╔════════════════╗
     ║  Basin Area    ║ ← Blue polygon (outer boundary)
     ║  (sediment     ║
     ║   retention)   ║
     ║                ║
     ║  ────────────  ║ ← Green line (channel, optional)
     ╚════════════════╝
         ↓
    Parameters:
    • Depth: 3.0m (at upstream)
    • Side Slope: 1.5 H:1V
    • Longitudinal Slope: 2.0%
         ↓
    [Compute Basin Cut]
         ↓
    Results:
    • Excavation Volume: 4,934 m³
    • Outer Area (Top): 1,853 m²
    • Inner Area (Bottom): 328 m²
```

**Basin Cross-Section (with longitudinal slope):**
```
Upstream (shallow):        Downstream (deeper):
    ╱╲                          ╱╲
   ╱  ╲                        ╱  ╲
  ╱____╲                      ╱    ╲
 Ground                      ╱      ╲
                            ╱   ╱────╲  ← Deeper basin bottom
                           ╱   ╱      ╲
                          ╱───╱        ╲───
     Depth: 3.0m              Depth: 3.4m (3.0 + 2% slope)
```

**Basin Plan View:**
```
     ╔════════════════╗ ← Red: Outer polygon (top edge)
     ║                ║
     ║  ╔═══════╗    ║ ← Blue: Inner polygon (bottom)
     ║  ║       ║    ║
     ║  ║  ───  ║    ║ ← Green: Channel line
     ║  ║       ║    ║
     ║  ╚═══════╝    ║
     ╚════════════════╝
```

---

### Measurement Tools

**Displayed Metrics:**
```
┌──────────────────────────────────────┐
│ 📏 Cross-Section Metrics:            │
├──────────────────────────────────────┤
│ Cut Area/m:    2.5 m²/m              │
│ Fill Area/m:   1.2 m²/m              │
│ Total Width:   35.0 m                │
├──────────────────────────────────────┤
│ Template Parameters:                 │
│ • Ditch Width:     2.5 m             │
│ • Berm Height:     2.5 m             │
│ • Berm Top Width:  3.0 m             │
└──────────────────────────────────────┘
```

---

### Sampling Interval Control

**Map Tab:**
```
┌──────────────────────────────┐
│ Profile Sampling Interval    │
│ [═══════╬════] 5.0 m         │
│                              │
│ Range: 1m to 50m             │
│ Default: 5m                  │
└──────────────────────────────┘

Effect:
• 5m → 21 stations in 100m profile
• 10m → 11 stations in 100m profile
• 1m → 101 stations in 100m profile
```

---

## 🎨 USER INTERFACE LAYOUT

### Input Data Tab
```
┌─────────────────────────────────────────────┐
│ 🗺️ Input Data                               │
├───────────────────────────┬─────────────────┤
│                           │ Design Mode     │
│  [Google Satellite Map]   │ ⚪ Profile Line │
│                           │   (Berm/Ditch)  │
│  Profile: ────────────    │ ⚫ Polygon Basin│
│  Basin: ▨▨▨▨▨▨▨▨         │                 │
│  Channel: ────────────    │ Map Controls    │
│                           │ Satellite: ▓▓▓  │
│  [Drawing Tools]          │ Hillshade: ▓░░  │
│  📏 Line  ⬟ Polygon      │                 │
│                           │ Sampling:       │
│                           │ [5.0] m         │
│                           │                 │
│                           │ Instructions    │
│                           │ Profile Mode:   │
│                           │ • Draw line     │
│                           │ Basin Mode:     │
│                           │ • Draw polygon  │
│                           │ • Draw channel  │
└───────────────────────────┴─────────────────┘
```

### Cross-Section Tab (Profile Mode Only)
```
┌─────────────────────────────────────────────────────────┐
│ 🔍 Cross-Section Setup & Browser                        │
├─────────────────────────────────────────────────────────┤
│ Template: [Berm+Ditch ▼]  Mode: [Cut+Fill ▼]  Width: 20m│
├──────────────────┬──────────────────┬──────────────────┤
│ Ditch Config:    │ Berm Config:     │ Berm Slopes:     │
│ Width: 2.5m      │ Height: 2.5m     │ Inner: 2:1       │
│ Slope: 3:1       │ Top: 3.0m        │ Outer: 3:1       │
│ Side: [Left ▼]   │                  │                  │
├──────────────────┴──────────────────┴──────────────────┤
│ Controls │ Cross-Section Plot           │ Map           │
├──────────┼──────────────────────────────┼───────────────┤
│ ◄ | ►    │                              │               │
│ Station  │   ╱═══════╲                  │   🟡          │
│ [═══╬═] │  ╱         ╲                 │               │
│ 12/50    │ ══           ══              │  ━━━━━━━━    │
│          │                              │               │
│ Elev:    │ 📏 Metrics:                  │               │
│ [═══╬═] │ Cut: 2.5 m²/m                │               │
│ 245.3m   │ Fill: 1.2 m²/m               │               │
│          │ Width: 35.0 m                │               │
└──────────┴──────────────────────────────┴───────────────┘
```

### Basin Design Tab (Basin Mode Only)
```
┌─────────────────────────────────────────────────────────┐
│ 🏗️ Basin Design                                          │
├─────────────────────────────────────────────────────────┤
│ Basin Parameters:                                        │
│ Depth: [3.0] m  Side Slope: [1.5] H:1V                   │
│ Longitudinal Slope: [2.0] %                             │
├──────────────────────────────────────────────────────────┤
│ Channel Definition (Optional):                           │
│ 💡 Draw channel line on Input Data map                  │
│ ✅ Channel defined with 8 points                        │
│ [🗑️ Clear Channel]                                     │
├──────────────────────────────────────────────────────────┤
│ Basin Metrics:                                           │
│ Excavation Volume: 4,934 m³                             │
│ Outer Area (Top): 1,853 m²                              │
│ Inner Area (Bottom): 328 m²                             │
├──────────────────────────────────────────────────────────┤
│ Basin Longitudinal Profile:                              │
│ Elevation (m)                                            │
│ 390 ┤                                                    │
│ 385 ┤  ╱╲  Existing Ground                               │
│ 380 ┤ ╱  ╲                                               │
│ 375 ┤╱────╲ Basin Bottom                                │
│     ┼────────────────────                                │
│     0    15    30    45                                  │
│     Distance (m)                                         │
│     ▲ Upstream    ▼ Downstream                           │
├──────────────────────────────────────────────────────────┤
│ Basin Plan View:                                         │
│ [Map showing outer/inner polygons and channel]          │
│ 🔴 Red: Outer boundary  🔵 Blue: Inner boundary         │
│ 🟢 Green: Channel line                                  │
├──────────────────────────────────────────────────────────┤
│ [🔄 Compute Basin Cut]  [💾 Download Modified DEM]     │
└──────────────────────────────────────────────────────────┘
```

### Profile Tab (Profile Mode Only)
```
┌─────────────────────────────────────────────────────────┐
│ 📈 Profile Editor                                       │
├──────────────────────────────────────────────────────────┤
│ Controls │ Profile Plot                 │ Map           │
├──────────┼──────────────────────────────┼───────────────┤
│ ◄ | ►    │ Elevation (m)                │               │
│ Station  │ 252 ┤                        │               │
│ [═══╬═] │ 250 ┤─╲                      │  🟡━━━━━━━━  │
│ 1/50     │ 248 ┤  ╲  🟡                 │               │
│          │ 246 ┤   ╲                    │               │
│          │ 244 ┤    ╲____               │               │
│ Design   │ 242 ┼────────────────────    │               │
│ Gradient │     0   25   50   75  100   │               │
│ Slope:   │     Distance (m)             │               │
│ [-3.00]% │                              │               │
│          │ 💡 Edit elevations:          │               │
│ Station  │ • Use slider                │               │
│ Elev:    │ • Or edit table (selected    │               │
│ [═══╬═] │   station only)              │               │
│ 245.3m   │                              │               │
│          │ Station | Dist | Elev       │               │
│          │    0    |  0.0 | 388.34     │               │
│          │  [1]    | 20.3 | 388.34  ←  │               │
│          │    2    | 35.2 | 387.68     │               │
│          │  (Only selected editable)    │               │
└──────────┴──────────────────────────────┴───────────────┘
```

---

## 🔧 PARAMETER GUIDE

### Berm + Ditch Design

**Typical Values for Debris Flow Mitigation:**

| Parameter | Typical Range | Example | Purpose |
|-----------|---------------|---------|---------|
| Ditch Width | 2-4m | 2.5m | Channel for debris |
| Ditch Slope | 2:1 to 4:1 | 3:1 | Stable excavation |
| Berm Height | 1.5-3.0m | 2.5m | Flow containment |
| Berm Inner | 1.5:1 to 3:1 | 2:1 | Erosion resistance |
| Berm Outer | 2:1 to 4:1 | 3:1 | Natural integration |
| Berm Top | 2-4m | 3.0m | Maintenance access |
| Influence | 15-30m | 20m | Corridor width |

**Design Rules:**
1. Berm Height > Expected Flow Depth + 0.5m
2. Ditch Width ≥ 2.0m for maintenance
3. Flatter slopes = more stable (higher H:V)
4. Berm Outer Slope ≥ Berm Inner Slope

---

### Swale Design

**Typical Values for Drainage:**

| Parameter | Typical Range | Example | Purpose |
|-----------|---------------|---------|---------|
| Bottom Width | 1-3m | 2.0m | Channel base |
| Depth | 0.5-1.5m | 1.0m | Capacity |
| Side Slope | 3:1 to 5:1 | 3:1 | Vegetated slopes |
| Influence | 10-20m | 15m | Corridor width |

---

### Polygon Basin Design

**Typical Values for Sediment Retention:**

| Parameter | Typical Range | Example | Purpose |
|-----------|---------------|---------|---------|
| Depth | 0.5-20m | 3.0m | Storage capacity at upstream |
| Side Slope | 0.5-10 H:1V | 1.5 H:1V | Stable excavation |
| Longitudinal Slope | -50% to +50% | 2.0% | Flow direction slope |
| Outer Area | 500-5000m² | 1,853m² | Basin top area |
| Inner Area | 100-2000m² | 328m² | Basin bottom area |

**Design Features:**
- **Channel Line (Optional)**: Draw green polyline to define exact flow path
- **Automatic Flow Path**: If no channel, uses first vertex → minimum elevation
- **Varying Depth**: Depth changes along flow path based on longitudinal slope
  - Upstream depth = Basin Depth
  - Downstream depth = Basin Depth + (Longitudinal Slope/100) × Flow Length
- **Volume Calculation**: Integrates varying depth along flow path
- **Inner Area**: Calculated using average depth (accounts for longitudinal slope)

**Capacity Estimation:**
- Volume automatically calculated considering longitudinal slope
- Inner area updates based on average depth
- Example: 3.0m depth, 2% slope, 45m flow length
  - Upstream: 3.0m depth
  - Downstream: 3.9m depth (3.0 + 2% × 45m)
  - Average: 3.45m depth
  - Volume accounts for this variation

---

## ⚡ PERFORMANCE TIPS

### Sampling Interval Selection

| Interval | Stations (100m) | Computation | Use Case |
|----------|----------------|-------------|----------|
| 1m | 101 | Slow | Final design |
| 2m | 51 | Medium | Detailed work |
| 5m | 21 | Fast | Standard |
| 10m | 11 | Very Fast | Preliminary |
| 20m | 6 | Instant | Rough layout |

**Recommendation**: Use 10m for initial design, 5m for refinement, 2m for final.

---

## 🎯 KEYBOARD SHORTCUTS

| Action | Shortcut |
|--------|----------|
| Next Station | Click Next ► |
| Previous Station | Click ◄ Prev |
| Slider Adjust | Click + Drag |
| Table Edit | Select station → Click Design_Elev cell → Enter |
| Apply Changes | Tab or Enter |
| Set Gradient | Select station → Enter slope % → Auto-applies downstream |

---

**VERSION**: 8.0 Production  
**STATUS**: ✅ Ready for Professional Use  
**INDUSTRY**: Geotechnical Engineering  
**APPLICATION**: Debris Flow Mitigation, Drainage Design & Sediment Retention  
**FEATURES**: 
- Profile Line Design (Berm/Ditch/Swale)
- Polygon Basin Design with Longitudinal Slope
- Channel Flow Path Definition
- Accurate Volume & Area Calculations
