# Multi-Needle Gauge Calibration - Fuel + Water

## Overview

The fuel gauge now supports **two independent needle images**:
- **Fuel Needle** (red) - Shows fuel level (0-100%)
- **Water Needle** (blue) - Shows water temperature (50-130°C)

Both needles rotate on the same gauge background, allowing you to display two separate measurements on a single gauge dashboard.

---

## Using the Multi-Needle Calibrator

### Step 1: Launch the Calibrator
```powershell
python gauge_calibrator_app.py
```

### Step 2: Select the Fuel Gauge
```
Dropdown: [Fuel ▼]
```

You'll notice a new **"Select Needle:"** dropdown appears below the gauge selector.

### Step 3: Choose Which Needle to Calibrate

```
Select Needle: [fuel ▼]  (or [water])
```

The dropdown shows:
- **fuel** - Calibrate the fuel level needle
- **water** - Calibrate the water temperature needle

### Step 4: Calibrate Each Needle Separately

**For Fuel Needle:**
1. Select: "fuel" from needle dropdown
2. Click: "Load Needle Image" → select `gauges/fuel_needle.png`
3. Click: Center of needle image (sets rotation center)
4. Add calibration points:
   - 0% @ 232°
   - 50% @ 187°
   - 100% @ 142°
5. Click: "Save Configuration"

**For Water Needle:**
1. Select: "water" from needle dropdown
2. Click: "Load Needle Image" → select `gauges/water_needle.png`
3. Click: Center of needle image
4. Add calibration points:
   - 50°C @ 232°
   - 90°C @ 187°
   - 130°C @ 142°
5. Click: "Save Configuration"

---

## Configuration Structure

The fuel gauge now saves with this structure:

```json
{
  "name": "Fuel",
  "gauge_type": "fuel",
  "needles": {
    "fuel": {...needle config...},
    "water": {...needle config...}
  },
  "needle_calibrations": {
    "fuel": {
      "needle_id": "fuel",
      "needle_image_path": "gauges/fuel_needle.png",
      "rotation_center_x": 256,
      "rotation_center_y": 245,
      "calibration_points": [
        {"value": 0, "angle": 232},
        {"value": 50, "angle": 187},
        {"value": 100, "angle": 142}
      ]
    },
    "water": {
      "needle_id": "water",
      "needle_image_path": "gauges/water_needle.png",
      "rotation_center_x": 256,
      "rotation_center_y": 245,
      "calibration_points": [
        {"value": 50, "angle": 232},
        {"value": 90, "angle": 187},
        {"value": 130, "angle": 142}
      ]
    }
  }
}
```

Each needle has its own:
- `needle_image_path` - Path to the PNG file
- `rotation_center_x/y` - The point it rotates around
- `calibration_points` - Its value-to-angle mapping

---

## Why Two Needles?

On real car dashboards, single gauges often show two measurements:
- Fuel + Reserve indicator
- Temperature + Oil pressure
- Speed + GPS speed

This setup allows you to:
✅ Display fuel level and water temperature together
✅ Use different needle images for visual distinction
✅ Set independent rotation centers if needles don't overlap
✅ Configure different value ranges for each needle
✅ Save all calibrations in a single file

---

## Using Multiple Needles in Your Emulator

When your emulator loads the fuel gauge, both calibrations are available:

```python
from src.gauge_config import GaugeConfig

# Load fuel gauge config
config = GaugeConfig.load_gauge("fuel")

# Access both needle calibrations
fuel_calib = config.needle_calibrations["fuel"]
water_calib = config.needle_calibrations["water"]

# Each has rotation center and calibration points
fuel_angle = NeedleAngleCalculator(fuel_calib.calibration_points).value_to_angle(current_fuel)
water_angle = NeedleAngleCalculator(water_calib.calibration_points).value_to_angle(current_temp)

# Render both needles from their respective PNG files
# fuel_calib.needle_image_path → "gauges/fuel_needle.png"
# water_calib.needle_image_path → "gauges/water_needle.png"
```

---

## Typical Values

### Fuel Needle (0-100%)
```
0%   → 232° (left)
50%  → 187° (diagonal)
100% → 142° (down-left)
```

### Water Needle (50-130°C)
```
50°C  → 232° (left/cold)
90°C  → 187° (diagonal/normal)
130°C → 142° (down-left/hot)
```

Both needles traverse the same angular range but represent different value ranges.

---

## Troubleshooting Multi-Needle Setup

### Issue: Can't see both needles in dropdown
**Solution:** Must select "Fuel" gauge first. Other gauges only show a single "main" needle.

### Issue: Saved one needle but can't load the other
**Solution:** Make sure you select the correct needle from dropdown before clicking "Load Configuration".

### Issue: Both needles overlap oddly
**Solution:** Set different rotation centers for each needle or adjust calibration angles.

### Issue: Water needle saves but then disappears
**Solution:** Check that `gauges/water_needle.png` exists and has proper transparency.

---

## Advanced: Extending to Other Gauges

The multi-needle system is built into the calibrator, so you can add multiple needles to other gauges if needed. Just modify `GaugeCalibratorWindow.on_gauge_changed()` to include more needles for other gauge types.

For example, to add a second needle to Tachometer:
```python
if gauge_name == "Fuel":
    needles = ["fuel", "water"]
elif gauge_name == "Tachometer":
    needles = ["main", "peak"]  # Add this
else:
    needles = ["main"]
```

---

## Summary

✅ Fuel gauge now supports fuel + water temperature needles
✅ Calibrator automatically offers needle selection for multi-needle gauges
✅ Each needle has independent calibration, image path, and rotation center
✅ All data saved to single gauge config file
✅ Backward compatible with single-needle gauges
✅ No code changes needed to use - it just works!

---

**Ready to calibrate both needles?**

```powershell
python gauge_calibrator_app.py
```

Select "Fuel" → Choose needle → Load image → Calibrate → Save!
