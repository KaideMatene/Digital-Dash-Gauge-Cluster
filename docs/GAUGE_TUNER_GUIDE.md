# Gauge Tuner - Real-Time Configurator Guide

## Quick Start

```bash
python gauge_tuner_launcher.py
```

This launches the real-time gauge configurator with:
- **Left panel**: Configuration controls for each gauge
- **Right panel**: Live preview of all 3 gauges with simulated data

## Features

### 1. Real-Time Control Panels

Each gauge (Tachometer, Speedometer, Fuel) has its own tab with controls:

#### Position & Sweep
- **Start Angle**: Set where the needle starts (0° = 3 o'clock, 90° = 12 o'clock, 180° = 9 o'clock, 270° = 6 o'clock)
- **Sweep Angle**: How far the needle sweeps (90° = quarter circle, 270° = three-quarters)

#### Value Range
- **Min Value**: Bottom of gauge range (e.g., 0 RPM)
- **Max Value**: Top of gauge range (e.g., 8000 RPM)

#### Main Needle Settings
- **Length Offset**: Distance from edge (lower = longer needle)
- **Thickness**: Needle width in pixels (1-10 px)
- **Center Cap**: Size of the center disc in mm (red pointer style = 15mm)
- **Color**: Pick needle color with color picker button

### 2. Live Gauge Display

Right side shows 3 gauges with simulated data:
- **Tachometer**: RPM oscillating between 1000-5000
- **Speedometer**: Speed ramping up and down 50-150 km/h
- **Fuel**: Steady ~80% with slow drain simulation
- **Water Temp**: Secondary needle on fuel gauge (blue)

Changes to controls update gauges **instantly** with no delay.

### 3. Configuration Files

Each gauge is saved independently:

```
config/
  tachometer.json      # RPM gauge settings
  speedometer.json     # Speed gauge settings
  fuel.json           # Fuel + Water temp settings
```

**Auto-save**: Changes save every 5 seconds automatically
**Manual save**: Click "Save Configuration" button in the active tab

### 4. Configuration Format

Each gauge config includes:

```json
{
  "name": "Tachometer",
  "gauge_type": "tachometer",
  "start_angle": 270,
  "sweep_angle": 279,
  "min_value": 0,
  "max_value": 8000,
  "number_interval": 1000,
  "needles": {
    "main": {
      "name": "RPM Needle",
      "color_r": 255,
      "color_g": 0,
      "color_b": 0,
      "thickness": 3.0,
      "length_offset": 40,
      "center_cap_size": 15,
      "style": "3d_pointer"
    }
  },
  "background_color_r": 245,
  "background_color_g": 235,
  "background_color_b": 215
}
```

## Common Adjustments

### Red Pointer Needles (3D Style)

The default is already set up:
- **Style**: `3d_pointer` (tapered triangular shape)
- **Color**: Red (255, 0, 0)
- **Center Cap**: 15mm red disc
- **Thickness**: 3px at base

To adjust size:
- Increase **Thickness** to 4-6px for bolder needles
- Decrease **Length Offset** to 20-25 for longer needles
- Increase **Center Cap** to 18-20mm for larger center disc

### Gauge Positions

**Current Setup:**
- **Tachometer**: 6 o'clock (270°) → 10% past 3 o'clock (351°) = 279° sweep
- **Speedometer**: 8 o'clock (240°) → sweeps 300° clockwise
- **Fuel**: 9 o'clock (180°) → 12 o'clock (90°) = 90° sweep

To change:
1. Adjust **Start Angle** slider (0-360°)
2. Adjust **Sweep Angle** slider to set end position

### Multiple Needles (Fuel Gauge)

Fuel gauge has **two independent needles**:
- **Fuel**: Main red needle for fuel level (E-F)
- **Water**: Blue secondary needle for water temperature

Both are independently configurable. Edit the fuel.json directly to customize the water needle.

### Color Selection

Click "Pick Color" button to open color picker:
- Current needle color shown as button background
- Pick any RGB color
- Applies instantly to live display

## Advanced: Editing JSON Directly

For fine-tuning beyond slider ranges, edit the JSON files directly:

```bash
# Open in your editor
notepad config/tachometer.json
```

After editing, the gauge tuner will reload on restart.

### Needle Styles

Available needle shapes in JSON (replace `"3d_pointer"`):
- **`"3d_pointer"`**: Tapered triangular (default, TRD-style)
- **`"line"`**: Simple straight line
- **`"arrow"`**: Arrow with pointed head

Change in config:
```json
"needles": {
  "main": {
    "style": "3d_pointer"  // Change to "line" or "arrow"
  }
}
```

## Split Screen Configuration

Each gauge saves independently in its own JSON file:

```
config/
  tachometer.json   → Left screen
  speedometer.json  → Center screen  
  fuel.json        → Right screen
```

This allows each display to have its own:
- Position (start angle, sweep)
- Value range (min/max)
- Needle style and appearance
- Background image (future)

No conflicts - each gauge is completely independent.

## Troubleshooting

### Gauges not updating
- Check that "Tachometer", "Speedometer", "Fuel" tabs are active
- Restart gauge_tuner_launcher.py
- Verify config/*.json files exist and are readable

### Changes not saving
- Check that config/ folder is writable
- Look for error messages in console
- Try clicking "Save Configuration" manually

### Images not loading
- Ensure background images are in `gauges/` folder
- Use PNG or JPG format
- Set correct path in config JSON

### Needle color not changing
- After color pick, click elsewhere to confirm change
- Check console for error messages

## Integration with Main Emulator

The gauge tuner uses separate configs from the main emulator. To use tuner configs in emulator:

1. Configure gauges in gauge_tuner_launcher.py
2. Gauges are auto-saved to config/*.json
3. Run main emulator - it will load your saved configs

```bash
# Main emulator (uses saved gauge configs + CAN data)
python emulator.py

# Or gauge tuner (uses saved configs + simulated data)
python gauge_tuner_launcher.py
```

## Next Steps

1. **Launch tuner**: `python gauge_tuner_launcher.py`
2. **Adjust tachometer**: Use Tachometer tab sliders
3. **Adjust speedometer**: Use Speedometer tab
4. **Adjust fuel**: Use Fuel tab (includes water temp needle)
5. **Save**: Click "Save Configuration" or auto-saves every 5 seconds
6. **Test in emulator**: Run `python emulator.py` to see configs in action

## File Locations

```
Supra Digital Cluster/
  gauge_tuner_launcher.py     ← Run this to launch tuner
  src/
    gauge_tuner.py            ← Tuner UI code
    gauge_config.py           ← Config management
    configurable_gauges.py    ← Gauge rendering
    emulator.py               ← Main emulator (uses saved configs)
    gauge_renderer.py         ← Original gauge code (legacy)
  config/
    tachometer.json           ← Auto-saved tach config
    speedometer.json          ← Auto-saved speed config
    fuel.json                 ← Auto-saved fuel config
```

## Performance

- Updates at ~20 Hz (50ms intervals)
- All changes apply instantly 
- Auto-save every 5 seconds (non-blocking)
- Suitable for real-time tweaking while developing cluster
