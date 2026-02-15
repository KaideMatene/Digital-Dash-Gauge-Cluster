# Gauge Calibration System

## Overview

The **Gauge Calibration System** is an interactive, point-and-click interface for configuring how gauge needles rotate and scale across their ranges. This eliminates guesswork and ensures accurate needle positioning.

### What It Does

✅ **Visual Setup** - Click directly on needle images to set rotation centers
✅ **Value Mapping** - Add calibration points to map gauge values to needle angles
✅ **Multiple Gauges** - Configure tachometer, speedometer, fuel, and water simultaneously
✅ **Save & Load** - Persist configurations to JSON files for reproducibility
✅ **Interactive Testing** - Works alongside the emulator for real-time validation

---

## File Structure

```
gauge_calibrator_app.py          ← Launch script for the calibrator GUI
src/
  gauge_calibrator.py            ← Main calibration interface (PyQt5)
  calibration_utils.py           ← Angle calculation utility
  gauge_config.py                ← Configuration data structures (updated)

config/
  tachometer_calibration.json    ← Saved tachometer calibration
  speedometer_calibration.json   ← Saved speedometer calibration  
  fuel_calibration.json          ← Saved fuel gauge calibration
  water_calibration.json         ← Saved water temperature calibration
  
  example_tachometer_calibration.json    ← Reference examples
  example_speedometer_calibration.json
  example_fuel_calibration.json
  example_water_calibration.json

Documentation:
  CALIBRATOR_QUICK_START.md      ← 5-minute setup guide
  CALIBRATOR_GUIDE.md            ← Detailed usage guide
  CALIBRATION_README.md          ← This file
```

---

## Core Concept: Value → Angle Mapping

Each gauge calibration converts **gauge values** to **needle angles**:

```
Input:  0 RPM        → Output:  270°  (12 o'clock)
Input:  5000 RPM     → Output:  135°  (4:30)
Input:  10000 RPM    → Output:  0°    (3 o'clock)
```

The system uses **linear interpolation** between calibration points for smooth scaling.

### Angle Coordinate System

```
        0° / 360°
       (3 o'clock)
           ↑
           |
270° ←-----●-----→ 90°
(12 o'click)   (6 o'clock)
           |
           ↓
        180°
      (9 o'clock)
```

- **0°** = Right (3 o'clock)
- **90°** = Down (6 o'clock)
- **180°** = Left (9 o'clock)
- **270°** = Up (12 o'clock)

Angles can be negative or > 360° (automatically normalized).

---

## How to Use

### Launch the Calibrator

```bash
cd "c:\Projects\Supra Digital Cluster"
python gauge_calibrator_app.py
```

A GUI window opens with:
- **Left**: Needle image display (click to set rotation center)
- **Right**: Configuration controls

### 4-Step Process for Each Gauge

#### Step 1: Select Gauge
```python
Dropdown: [Tachometer ▼]
```
Choose from: Tachometer, Speedometer, Fuel, Water

#### Step 2: Load Needle Image
```
[Load Needle Image] → Select needle.png
```
Image appears on left side ready for clicking.

#### Step 3: Set Rotation Center
```
Click directly on needle image at the center point
↓
Red crosshair appears
↓
Coordinates update: X: 256 | Y: 245
```

**Why this matters:** The needle must rotate around a precise point. Setting this correctly prevents:
- Needle appearing off-center
- Rotation "wobble"
- Visual artifacts

#### Step 4: Add Calibration Points
```
Value: [0_____]  Angle: [270____]  [Add Point]
Value: [5000__]  Angle: [135____]  [Add Point]
Value: [10000_]  Angle: [0______]  [Add Point]

Result:
┌──────────────────┬───────────┬────────┐
│ Value            │ Angle (°) │ Delete │
├──────────────────┼───────────┼────────┤
│ 0                │ 270.0     │   X    │
│ 5000             │ 135.0     │   X    │
│ 10000            │ 0.0       │   X    │
└──────────────────┴───────────┴────────┘
```

Save when ready: `[Save Configuration]`

---

## Calibration Point Strategy

### Minimum (Quick Setup)
Use 2-3 points:
- Start position (value=0 or minimum)
- End position (value=max)
- Optional: One midpoint for verification

### Recommended (Accurate Setup)
Use 3-5 points for better interpolation:
```
Tachometer:
  0 RPM    → 270°
  2500     → 202°
  5000     → 135°  ← Midpoint
  7500     → 67°
  10000    → 0°
```

### Advanced (Highly Accurate)
Use more points if gauge response is non-linear:
```
Speedometer:
  0 km/h   → 240°
  40       → 210°
  80       → 165°
  120      → 127°
  160      → 90°   ← Midpoint
  200      → 53°
  240      → 15°
  280      → -22°
  320      → -60°
```

---

## Configuration File Format

After saving, files are stored as JSON:

```json
{
  "gauge_name": "Tachometer",
  "needle_image_path": "gauges/tachometer_needle.png",
  "rotation_center_x": 256,
  "rotation_center_y": 245,
  "start_value": 0,
  "start_angle": 270,
  "end_value": 10000,
  "end_angle": 0,
  "calibration_points": [
    {"value": 0, "angle": 270},
    {"value": 5000, "angle": 135},
    {"value": 10000, "angle": 0}
  ]
}
```

**Fields:**
- `gauge_name` - Identifier (Tachometer, Speedometer, Fuel, Water)
- `needle_image_path` - Path to needle PNG
- `rotation_center_x/y` - Pixel coordinates for rotation axis
- `calibration_points` - Array of value→angle mappings

---

## Using Calibrations in Code

The `calibration_utils.py` module provides the `NeedleAngleCalculator` class:

```python
from src.calibration_utils import NeedleAngleCalculator, CalibrationPoint

# Create calculator
calc = NeedleAngleCalculator()

# Add points
calc.add_point(0, 270)
calc.add_point(5000, 135)
calc.add_point(10000, 0)

# Convert value to angle
angle = calc.value_to_angle(3500)  # Returns interpolated angle
# → 183.5° (between 5000's 135° and next point)

# Or use preset
from src.calibration_utils import tachometer_calibration
calc = tachometer_calibration()
angle = calc.value_to_angle(7500)
```

---

## Workflow Example

### Scenario: Calibrate Tachometer

**Step 1: Preparation**
- Gather tachometer needle PNG image
- Start calibrator: `python gauge_calibrator_app.py`

**Step 2: Load**
- Select: "Tachometer"
- Click: "Load Needle Image"
- Navigate to: `gauges/tachometer_needle.png`

**Step 3: Find Rotation Center**
- Look at needle image
- Identify the center hub/mount point
- Click precisely on that spot in the image
- Verify coordinates look correct

**Step 4: Add Calibration Points**
- RPM 0 @ 270° (points up at 12 o'clock)
- RPM 5000 @ 135° (points down-right at 4:30)
- RPM 10000 @ 0° (points right at 3 o'clock)

**Step 5: Save**
- Click: "Save Configuration"
- → Saves to `config/tachometer_calibration.json`

**Step 6: Test**
- Run emulator: `python emulator.py`
- Manually change RPM values
- Watch needle movement
- Compare against actual gauges if available

**Step 7: Refine (if needed)**
- If movement looks wrong:
  - Return to calibrator
  - Load configuration
  - Adjust calibration points
  - Save and test again

---

## Preset Calibrations

Quick-add buttons for standard gauges:

| Preset | Gauge | Points |
|--------|-------|--------|
| **Tach** | Tachometer | 0, 5000, 10000 RPM |
| **Speed** | Speedometer | 0, 160, 320 km/h |

```python
# From calibration_utils.py
tachometer_calibration()     # Returns configured NeedleAngleCalculator
speedometer_calibration()    # 0-320 km/h
fuel_gauge_calibration()     # 0-100%
water_temp_calibration()     # 50-130°C
```

---

## Troubleshooting

### Issue: Needle rotates around wrong point
**Cause:** Rotation center not set correctly
**Solution:** 
1. Load image again
2. Click more carefully on the center
3. Try zooming in on the image if possible

### Issue: Needle doesn't span full range
**Cause:** Incorrect start/end angles
**Solution:**
1. Enable emulator with test values
2. Set value to 0, note where needle points
3. Set value to max, note where needle points
4. Update calibration angles to match

### Issue: Needle movement looks non-linear
**Cause:** Only 2 calibration points (linear interpolation)
**Solution:** Add more midpoint calibrations

### Issue: Can't find saved configuration
**Cause:** File naming
**Solution:** Look in `config/` folder for `{gauge_name}_calibration.json`

### Issue: Image won't load
**Cause:** File path issue
**Solution:**
- Use absolute path starting with `C:\`
- Ensure file is PNG with alpha channel
- Check file permissions

---

## Integration Points

### With `gauge_config.py`
```python
from src.gauge_config import GaugeConfig, CalibrationPoint

config = GaugeConfig.from_dict(json_data)
# Includes calibration_points and rotation_center fields
```

### With Needle Rendering
```python
# In needle_gauge.py or custom renderer
from src.calibration_utils import NeedleAngleCalculator

angle = calculator.value_to_angle(current_rpm)
# Use angle to rotate needle image
```

---

## Tips & Best Practices

✅ **DO:**
- Test each gauge immediately after calibration
- Add minimum 3 calibration points
- Take screenshots of working configurations
- Document any unusual gauge behavior
- Use consistent angle directions (all positive or handle negative correctly)

❌ **DON'T:**
- Set rotation center outside image bounds
- Mix calibration point units (e.g., RPM vs percentage)
- Forget to save before closing calibrator
- Manually edit JSON unless you understand the format
- Use rotation center values from different gauge types

---

## File Examples

See `config/example_*_calibration.json` files for reference implementations of all four gauge types.

---

## Next Steps

1. **Launch calibrator**: `python gauge_calibrator_app.py`
2. **Calibrate all 4 gauges** - Save configurations
3. **Test with emulator**: `python emulator.py`
4. **Fine-tune as needed** - Adjusting calibration points
5. **Document results** - Note working configurations
6. **Deploy** - System ready for real CAN data

---

## Support

- **Quick Start**: See [CALIBRATOR_QUICK_START.md](CALIBRATOR_QUICK_START.md)
- **Detailed Guide**: See [CALIBRATOR_GUIDE.md](CALIBRATOR_GUIDE.md)
- **Code Reference**: See docstrings in `src/gauge_calibrator.py` and `src/calibration_utils.py`

Happy calibrating! 🎯
