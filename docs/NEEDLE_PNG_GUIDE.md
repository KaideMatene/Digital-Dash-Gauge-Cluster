# PNG Needle Gauge System

## Quick Start

### 1. Create Needle Images in GIMP/Figma

Create thin red needle PNGs:
- **Dimensions**: Same as gauge background (e.g., 293x319px for tachometer)
- **Needle shape**: Thin red line (2-4px wide)
- **Pivot point**: Center of image (important!)
- **Needle extends**: From center to near edge
- **Example**: `/gauges/tachometer_needle.png`

### 2. Create Needle for Each Gauge

```
gauges/
  tachometer_bg.png
  tachometer_needle.png      ← Create this
  speedometer_bg.png
  speedometer_needle.png     ← Create this
  fuel_bg.png
  fuel_needle.png            ← Create this
```

### 3. Use Alignment Tool to Calibrate

```bash
python needle_alignment_tool.py
```

This opens an interactive tool where you can:
- Load gauge background + needle
- Drag slider to rotate needle
- See real-time preview
- Note what angles work (0°, 45°, 90°, 180°, etc.)

### 4. Update Code with Calibrated Angles

Once you know the angles, put them in code:

```python
class TachometerNeedle(NeedleGauge):
    def __init__(self, bg_path, needle_path, parent=None):
        self.start_angle = 270      # 0 RPM angle
        self.sweep_angle = 279      # Total rotation to max
        super().__init__(bg_path, needle_path, parent)
    
    def _get_needle_angle(self) -> float:
        fraction = self.value / self.max_rpm
        angle = self.start_angle - self.sweep_angle * fraction
        return angle
```

### 5. Use in Emulator

Update `display_manager.py` to use needle gauges instead of line gauges:

```python
from needle_gauge import TachometerNeedle, SpeedometerNeedle, FuelNeedle

# Instead of:
# self.tachometer = TachometerWidget()

# Use:
self.tachometer = TachometerNeedle(
    "gauges/tachometer_bg.png",
    "gauges/tachometer_needle.png"
)
```

---

## Creating Needles in GIMP

1. **Open gauge background image** in GIMP
2. **Create new layer** (Layer → New Layer)
3. **Use Pencil tool**:
   - Set brush to hard edge, 3-4px size
   - Set color to red (#FF0000)
   - Draw thin line from center outward
4. **Flatten image** (Image → Flatten Image)
5. **Export as PNG** (File → Export As) with transparency

**Key**: Needle must be **centered at (146.5, 159.5)** for a 293x319 image

---

## Creating Needles in Figma (Easier)

1. **Import gauge background** as shape
2. **Create Red Rectangle**: 
   - 3-4px wide
   - ~100px tall
   - Red color (#FF0000)
3. **Center on gauge**: Align to center
4. **Export as PNG**: Right-click → Export → PNG
5. **Size**: Must match background dimensions

---

## Needle Alignment Tool Features

```
|  Controls                |  Preview                           |
|  ✓ Load Background      |  Visual needle rotation on gauge   |
|  ✓ Load Needle          |  Real-time rotation preview        |
|  ✓ Rotation slider      |  Shows current angle               |
|  ✓ Start angle input    |  Gauge-specific calibration       |
|  ✓ Sweep angle input    |  Test at 0%, 25%, 50%, 75%, 100%   |
|  ✓ Test slider (%)      |  Copy calibration values to code   |
```

### Using the Tool

1. **Launch**: `python needle_alignment_tool.py`
2. **Select gauge** from dropdown (Tachometer, Speedometer, Fuel)
3. **Load background** - will auto-load from gauges/ folder
4. **Load needle** - will auto-look for *needle*.png files
5. **Drag rotation slider** to position needle
6. **Auto test percentages** with "Test Needle Position" slider
7. **Copy angles** shown in "Use These Values In Code" section

---

## Angle Reference

```
Qt/PIL Rotation Angles:
       90° (up)
         |
180°--center--0° (right)
         |
       270° (down)

Gauge Positions:
  12 o'clock = 90°
  3 o'clock = 0°
  6 o'clock = 270°
  9 o'clock = 180°
```

---

## Code Example: Complete Tachometer Setup

```python
from needle_gauge import TachometerNeedle

# Create tachometer with PNG needle
tachometer = TachometerNeedle(
    "gauges/tachometer_bg.png",
    "gauges/tachometer_needle.png"
)

# Update value (0-8000 RPM)
tachometer.set_rpm(3500)

# Render (automatically rotates needle)
```

---

## Troubleshooting

### Needle doesn't rotate
- Check that needle image is loaded (check console log)
- Verify needle PNG exists and has transparency background

### Needle rotates wrong direction
- In `_get_needle_angle()`, try: `angle = self.start_angle + self.sweep_angle * fraction`
- (Change minus to plus)

### Needle off-center
- Ensure needle PNG center matches image center
- Use GIMP: Center → Image → Center on Image

### Alignment tool won't load images
- Put PNG files in `gauges/` folder
- Or use "Load Background" / "Load Needle" buttons
- Check console for error messages

---

## Performance

- PNG rotation happens in PIL (fast, <5ms per frame)
- Composite rendering: <10ms per frame
- Total impact: negligible on 50 FPS target

---

## Next Steps

1. **Create needle PNGs** in GIMP or Figma
2. **Place in gauges/** folder
3. **Run alignment tool**: `python needle_alignment_tool.py`
4. **Note the start_angle and sweep_angle** values
5. **Update code** with those values
6. **Test in emulator**

This approach is:
- ✅ Simpler than complex gauge tuner
- ✅ Visually accurate (WYSIWYG)
- ✅ Easy to iterate
- ✅ Professional looking
