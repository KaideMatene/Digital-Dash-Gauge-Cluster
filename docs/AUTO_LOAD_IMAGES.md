# 🖼️ Auto-Load Images Feature

## What Changed

The gauge calibrator now **automatically loads needle images** from the `gauges/` folder instead of requiring manual file selection.

### Before ❌
1. Select gauge
2. Select needle  
3. Click "Load Needle Image"
4. Browse file system
5. Select PNG file
6. Wait for dialog to close

### After ✅
1. Select gauge
2. Select needle
3. **Image auto-loads instantly!** (From `gauges/` folder)
4. Image path and status shown
5. Ready to calibrate immediately

---

## How It Works

### Image Path Convention

Images follow a simple naming pattern in the `gauges/` folder:

```
gauges/
  ├── tachometer_needle.png    ← For Tachometer
  ├── speedometer_needle.png   ← For Speedometer
  ├── fuel_needle.png          ← For Fuel gauge (main needle)
  └── water_needle.png         ← For Fuel gauge (water temperature)
```

The calibrator automatically looks for:
- Gauge type in lowercase + `_needle.png` for single-needle gauges
- Needle ID + `_needle.png` for multi-needle gauges

### Auto-Load Status

The calibrator shows the status of image loading:

```
✓ Auto-loaded: tachometer_needle.png
✓ Auto-loaded: fuel_needle.png
⚠ Not found: gauges/custom_needle.png
```

### Fallback: Browse Button

If you want to use a custom image from elsewhere:
- Click **"Browse for Different Image"** button
- Select the custom PNG file
- It will be used and the path saved

---

## What Gets Saved

When you save a calibration:

### Needle Image Path
The actual file path is saved to the config file, so it can be:
- `gauges/fuel_needle.png` (auto-loaded)
- `other/location/custom.png` (manually selected)
- Any valid path to a PNG file

### Rotation Center & Points
- Saved to: `config/{gauge_type}.json`
- Structure: `needle_calibrations[{needle_id}]`

Example:
```json
{
  "name": "Fuel",
  "needle_calibrations": {
    "fuel": {
      "needle_id": "fuel",
      "needle_image_path": "gauges/fuel_needle.png",
      "rotation_center_x": 128,
      "rotation_center_y": 145,
      "calibration_points": [
        {"value": 0, "angle": 180},
        {"value": 100, "angle": 90}
      ]
    },
    "water": {
      "needle_id": "water",
      "needle_image_path": "gauges/water_needle.png",
      "rotation_center_x": 110,
      "rotation_center_y": 150,
      "calibration_points": [...]
    }
  }
}
```

---

## File Structure

Required files:
```
Supra Digital Cluster/
  ├── gauges/                    ← All images here
  │   ├── tachometer_needle.png
  │   ├── speedometer_needle.png
  │   ├── fuel_needle.png
  │   └── water_needle.png
  ├── config/                    ← Calibration saved here
  │   ├── tachometer.json
  │   ├── speedometer.json
  │   ├── fuel.json
  │   └── water.json
  └── gauge_calibrator_app.py    ← Launch this
```

---

## Quick Visual

```
┌─────────────────────────────────────────┐
│ Select Gauge: [Tachometer ▼]            │
│ Select Needle: [main ▼]                 │
│                                         │
│ ✓ Auto-loaded: tachometer_needle.png   │
│              [Browse for Different...]  │
│                                         │
│ [Image displays here - ready to use]    │
│                                         │
│ Click on image to set rotation center   │
└─────────────────────────────────────────┘
```

---

## Workflow

### Standard Workflow (Using Auto-Load)
```
Launch calibrator
  ↓
Select gauge (e.g., "Fuel")
  ↓
Select needle (e.g., "fuel")
  ↓
✓ Image auto-loads from gauges/fuel_needle.png
  ↓
Click image to set rotation center
  ↓
Add calibration points
  ↓
Save configuration
  ↓
✓ All data saved to config/fuel.json
```

### Using Custom Image
```
Select gauge & needle
  ↓
⚠ Image not found in gauges/
  ↓
Click "Browse for Different Image"
  ↓
Select custom image from your location
  ↓
Rest of workflow continues normally
  ↓
✓ Custom path saved to config
```

---

## Benefits

✅ **Faster**: No file dialog, images load instantly
✅ **Predictable**: Standard naming makes it obvious where images should be
✅ **Flexible**: Still supports custom paths if needed
✅ **Smart**: Pre-loads saved rotation center if available
✅ **Clear**: Status shows what was loaded and why

---

## Adding New Gauges

To add a new gauge type:

1. Create needle image: `gauges/{gauge_type}_needle.png`
2. Add gauge to calibrator dropdown
3. Image will auto-load when selected!
4. No other setup needed

---

## FAQ

**Q: Do I need to move my images?**
A: Yes, if they're not in `gauges/` folder with the right names. Just move them there.

**Q: What if I want images in a different location?**
A: Use the "Browse for Different Image" button. The custom path will be saved.

**Q: Can I rename the gauges/ folder?**
A: Yes, but then images won't auto-load. You'd need to browse manually each time.

**Q: What if the image doesn't exist?**
A: You'll see a warning and the "Browse" button to select one manually.

**Q: Does this work with the emulator?**
A: Yes! The emulator reads image paths from the saved config files.

---

## Status Indicators

| Symbol | Meaning | Action Needed |
|--------|---------|---------------|
| ✓ | Image auto-loaded successfully | None - ready to calibrate |
| ⚠ | Image not found in standard location | Click "Browse" to select manually |
| ❌ | Error loading image | Check file format (must be PNG) |

---

## Version History

**v2.0** (Current)
- Added auto-load from gauges/ folder
- Smart status display
- Fallback browse button
- Pre-loads saved settings when available

**v1.0** (Previous)
- Manual file selection via dialog

---

That's it! Your calibrator now works automatically. Just select gauge + needle, and you're ready to calibrate. 🎯
