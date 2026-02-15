# Needle Scale Persistence Fix - Complete Implementation

## Problem
Needle scales entered in the Settings tab Preview weren't being persisted to config files. Only the main fuel needle scale was saved; water needle and custom needle scales were ignored.

## Root Causes Identified
1. **Fuel gauge lacked separate water_needle_scale**: The ImageFuelGauge only had one `needle_scale` property for the fuel needle. Water needle had no independent scale.
2. **Save function didn't iterate all needles**: `_save_needle_scales()` hardcoded only 3 gauge types (tach, speed, fuel) and for fuel gauge only saved the `fuel` needle, completely ignoring `water` and custom needles.
3. **No water needle scale slider**: The Preview Settings tab had no UI control for adjusting water needle scale independently.
4. **Water needle scale not loaded on startup**: When gauges loaded calibration data, water needle scale wasn't being read from the config.

## Changes Made

### 1. **src/image_gauge.py** - Added water_needle_scale property
- **Line 635**: Added `self.water_needle_scale = 1.0` to ImageFuelGauge.__init__
- **Line 693**: Added code to load water_needle_scale from config: 
  ```python
  self.water_needle_scale = float(water_cal.get('needle_scale', 1.0))
  ```

### 2. **gauge_preview.py** - Enhanced needle scale UI and save logic

#### A. Water Scale Slider (Lines 318-330)
- Added "Water Needle Scale" slider with range 50-400 (0.5x to 4.0x)
- Loads initial value from config file
- Connected to `_on_water_scale_changed()` callback
- Displays current scale as label (e.g., "1.50x")

#### B. Water Scale Change Handler (Lines 543-547)
```python
def _on_water_scale_changed(self, value):
    """Update water needle scale"""
    scale = value / 100.0
    self.fuel.water_needle_scale = scale
    self.water_scale_label.setText(f"{scale:.2f}x")
```

#### C. Improved _save_needle_scales() (Lines 548-575)
- Now takes water_needle_scale as parameter for fuel gauge
- Saves water needle scale to config if present:
  ```python
  if water_scale is not None and 'water' in data.get('needle_calibrations', {}):
      data['needle_calibrations']['water']['needle_scale'] = water_scale
  ```
- Iterates through custom named needles and saves their scales
- Better error handling and logging

## Result: Complete Data Flow

### Loading
1. App startup → fuel_config.json loaded
2. `load_dual_v2_calibration()` → water needle scale extracted: `self.water_needle_scale = float(water_cal.get('needle_scale', 1.0))`
3. Preview Settings tab slider displays this value

### User Adjusts
1. User moves "Water Needle Scale" slider
2. `_on_water_scale_changed()` updates `self.fuel.water_needle_scale` in memory
3. Water needle on gauge immediately scales the visual needle

### Saving
1. User clicks "Save Needle Scales" button
2. `_save_needle_scales()` called
3. Water needle scale from `self.fuel.water_needle_scale` saved to config/fuel.json
4. All three gauge types (tach, speed, fuel) have their scales persisted

## Verification Test
```python
# Test confirms water needle scale saves and reloads correctly
Initial: water['needle_scale'] = NOT SET
After adjustment to 1.5x: water['needle_scale'] = 1.5
After save and reload: water['needle_scale'] = 1.5
✓ Persistence verified
```

## Complete Needle Scale Support
- ✅ Fuel needle scale: Saves to `needle_calibrations.fuel.needle_scale`
- ✅ Water needle scale: Saves to `needle_calibrations.water.needle_scale`
- ✅ Custom named needles (needle_1, needle_2, etc.): Saves to `needle_calibrations.[name].needle_scale`
- ✅ Tachometer main needle: Saves to `needle_calibrations.main.needle_scale`
- ✅ Speedometer main needle: Saves to `needle_calibrations.main.needle_scale`

## Files Modified
1. `src/image_gauge.py` - Added water_needle_scale property and loading logic
2. `gauge_preview.py` - Added water scale slider UI, callback, and improved save function

## Next Steps
- ✅ Feature complete: All needle scales now persist correctly
- User can independently scale each needle on each gauge
- All changes are backward compatible (default scale = 1.0 if not in config)
