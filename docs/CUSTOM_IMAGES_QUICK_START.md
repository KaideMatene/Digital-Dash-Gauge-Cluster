# Custom Gauge Images - Quick Start

## ✅ What I Set Up

I've created a complete image-based gauge system that lets you use custom PNG backgrounds with automatic needle overlays.

**Files Created:**
- `src/image_gauge.py` - Image gauge implementation (auto-loads PNGs, draws needles on top)
- `create_gauge_images.py` - Script to generate test images
- `gauges/` folder - Where your gauge background images go

**Updated:**
- `src/display_manager.py` - Auto-detects and uses images if available, falls back to vector gauges otherwise

---

## 🎨 Three Ways to Use Custom Gauges

### Option 1: Generate Test Images (if Pillow installed)

```powershell
pip install Pillow
python create_gauge_images.py
python emulator.py
```

This creates simple placeholder images in the `gauges/` folder that you can customize.

---

### Option 2: Design Your Own in Figma/GIMP (Recommended)

**1. Create 1080×1080 PNG images**
- Use Figma (free online), GIMP (free offline), or Photoshop
- One for each gauge: tachometer, speedometer, fuel

**2. Design guidelines for each gauge:**

**Tachometer (0-8000 RPM)**
- Circular gauge face
- Tick marks around edge
- Numbers 0, 1, 2, 3, ... 8 around the circle
- Optional: Red zone from 7-8 (top right area)
- Angle sweep: 135° (top) → -135° (bottom) = 270° sweep

**Speedometer (0-260 km/h)**
- Circular gauge face
- Tick marks every 20 km/h
- Numbers 0, 40, 80, 120, 160, 200, 240 around circle
- Same 270° sweep as tachometer

**Fuel Gauge (E-F)**
- Circular gauge face
- "E" label at left (180°)
- "F" label at top-right (90°)
- Tick marks at E and F positions
- 90° sweep from E to F

**3. Export and save:**
```
gauges/
├── tachometer_bg.png
├── speedometer_bg.png
└── fuel_bg.png
```

**4. Run emulator:**
```powershell
python emulator.py
```

It auto-detects your images and uses them!

---

### Option 3: Stick with Vector Gauges (Today's Default)

No images needed. The built-in vector gauges work perfectly:

```powershell
python emulator.py
```

Automatically uses vector rendering. Swap to images anytime by adding PNGs to the `gauges/` folder.

---

## 📐 Image Specifications

| Spec | Value |
|------|-------|
| Resolution | 1080×1080 pixels |
| Format | PNG (JPG works too) |
| Background | Cream/light color recommended |
| Layout | Circular gauge face |
| Transparency | Optional (PNG supports alpha) |

---

## 🔧 How It Works

1. **Emulator starts** → DisplayManager initializes
2. **Checks gauges/ folder** for image files
3. **If images found** → Loads image-based gauges, draws needles on top
4. **If images missing** → Falls back to vector gauges (what you have now)
5. **Needle renders** in real-time at 50 FPS smoothly over your image

No code changes needed. Just add images and it auto-switches!

---

## 📝 Example: Create Tachometer Gauge

**In Figma:**
1. Create 1080×1080 canvas
2. Draw circle (radius ~500px, center at 540,540)
3. Add tick marks:
   - Every 1000 RPM around the edge
   - Longer ticks at 1000, 2000, 3000, etc.
   - Shorter ticks in between
4. Add numbers: 0, 1, 2, 3, 4, 5, 6, 7, 8 (for 8000 RPM)
5. Optional: Red arc from 7 to 8 for redline
6. Export as PNG → `gauges/tachometer_bg.png`

**In GIMP:**
1. Image → New (1080×1080, white background)
2. Filters → Render → Gfig → Draw circle
3. Edit → Stroke Selection → Create outline
4. Use text tool to add numbers
5. File → Export As → `gauges/tachometer_bg.png`

---

## 🧪 Testing

**With vector gauges (default now):**
```powershell
python emulator.py
```

**After creating custom images:**
1. Check images are in `gauges/` folder
2. Run: `python emulator.py`
3. Should see your custom gauge backgrounds
4. Needles overlay automatically

**If images don't load:**
- Check file paths (must be exactly `gauges/tachometer_bg.png`)
- Check image exists in folder
- Emulator logs will show which mode is being used

---

## 💡 Design Tips

- **Visible area:** Leave center ~200px clear for needle
- **Contrast:** Use dark colors on light background or vice versa
- **Font:** Use bold, readable fonts for numbers
- **Grid:** Start with simple sketch or gridlines before detailing
- **Test:** Save, run emulator, iterate on design

---

## Files & Code

**To use image gauges in your own code:**

```python
from image_gauge import ImageTachometer, ImageSpeedometer, ImageFuelGauge

# Load backgrounds and create gauges
tachometer = ImageTachometer("gauges/tachometer_bg.png")
tachometer.set_rpm(3000)  # Draw needle
```

All automatic in emulator. Just add images!

---

## Next Steps

1. **Option A (quickest):** Install Pillow, run `create_gauge_images.py`
2. **Option B (best quality):** Design custom images in Figma/GIMP
3. **Option C (keep it simple):** Stay with vector gauges (no images needed)

**Any option works. Emulator auto-detects and uses whatever's available!**
