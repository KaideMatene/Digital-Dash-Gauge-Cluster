# Gauge Customization Guide

This guide explains how to customize the digital gauges in the Supra Digital Cluster emulator and production system.

## Overview

The gauges are implemented using PyQt5's vector drawing (QPainter) for maximum flexibility. There are three main gauge types:

1. **Tachometer** - 0-8000 RPM with redline zone (7000-8000 RPM in red)
2. **Speedometer** - 0-260 km/h 
3. **Fuel Gauge** - 0-100% (E-F) on 90° sweep

## Method 1: Customize Vector-Based Gauges (Recommended for Beginners)

### Edit Colors and Styling

All color schemes are defined in the `BaseGauge._get_colors()` method in `src/gauge_renderer.py`.

**Day Mode Colors:**
```python
'background': QColor(245, 235, 215),  # Cream/beige
'text': QColor(0, 0, 0),              # Black text
'needle': QColor(0, 0, 0),            # Black needle
'tick_major': QColor(0, 0, 0),        # Black ticks
```

**Night Mode Colors:**
```python
'background': QColor(20, 20, 20),     # Dark background
'text': QColor(255, 255, 255),        # White text
'needle': QColor(255, 255, 255),      # White needle
'tick_major': QColor(200, 200, 200),  # Light gray ticks
```

**To customize colors:**

1. Open `src/gauge_renderer.py`
2. Find the `_get_colors()` method in the `BaseGauge` class
3. Modify color values using PyQt5 `QColor(R, G, B)` format
4. Save and restart the emulator: `python emulator.py`

Example: Make tachometer needles red in day mode:
```python
'needle': QColor(255, 0, 0),  # Red needle in day mode
```

### Modify Gauge Ranges

Each gauge class has customizable parameters:

**Tachometer (`src/gauge_renderer.py`):**
```python
class TachometerWidget(BaseGauge):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.max_rpm = 8000      # Change max RPM
        self.redline = 7000      # Change redline threshold
```

**Speedometer:**
```python
class SpeedometerWidget(BaseGauge):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.max_speed = 260     # Change max speed (km/h)
```

**Fuel Gauge:**
- Currently 0-100% (E-F)
- Modify in `_draw_fuel_labels()` method if needed

### Change Tick Mark Density

Ticks are drawn in methods like `_draw_ticks()` and `_draw_ticks_speed()`.

Example - RPM tick marks every 500 (instead of 1000):
```python
# In TachometerWidget._draw_ticks()
for rpm in range(0, 8000 + 1, 500):  # Changed from 1000 to 500
    # ... draw tick code
```

### Modify Needle Style

Needles are drawn with `_draw_needle()` methods. Customize needle thickness and shape:

```python
# In _draw_needle() method
painter.setPen(QPen(colors['needle'], 3))  # Change 3 to thicker/thinner
```

## Method 2: Image-Based Gauge Backgrounds (Advanced)

### Concept

Instead of purely vector-drawn gauges, use a background image (PNG/JPG) and overlay the needle on top.

### Steps

1. **Prepare gauge background image:**
   - Create 1080x1080 PNG/JPG image (matches display size)
   - Design gauge face, ticks, and labels in image editor
   - Save as `gauges/tachometer_bg.png`, etc.

2. **Create image-based gauge class:**

Create a new file `src/image_gauge.py`:

```python
from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QPainter, QPixmap, QPen, QColor, QFont
from PyQt5.QtCore import Qt, QPointF, QRect
import math

class ImageBasedGauge(QWidget):
    """Gauge that uses image background with needle overlay"""
    
    def __init__(self, bg_image_path: str, parent=None):
        super().__init__(parent)
        self.bg_pixmap = QPixmap(bg_image_path)
        self.value = 0
        self.setMinimumSize(400, 400)
    
    def sizeHint(self):
        from PyQt5.QtCore import QSize
        return QSize(500, 500)
    
    def set_value(self, value: float):
        """Update gauge value"""
        self.value = max(0, min(value, self.max_value))
        self.update()
    
    def paintEvent(self, event):
        """Draw background image and needle"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Scale and draw background image
        center = QPointF(self.width() / 2, self.height() / 2)
        radius = min(self.width(), self.height()) / 2 - 20
        
        # Draw background image (stretch to fit)
        target_rect = QRect(0, 0, self.width(), self.height())
        painter.drawPixmap(target_rect, self.bg_pixmap)
        
        # Draw needle on top
        self._draw_needle(painter, center, radius)
    
    def _draw_needle(self, painter: QPainter, center: QPointF, radius: float):
        """Draw needle (override in subclass)"""
        pass


class ImageTachometer(ImageBasedGauge):
    """Image-based tachometer"""
    
    def __init__(self, bg_image_path: str, parent=None):
        self.max_value = 8000
        super().__init__(bg_image_path, parent)
    
    def set_rpm(self, rpm: float):
        self.set_value(rpm)
    
    def _draw_needle(self, painter: QPainter, center: QPointF, radius: float):
        # Needle sweeps 270 degrees (135° to -135°)
        angle_fraction = min(1.0, self.value / self.max_value)
        angle = 135 + (-270) * angle_fraction
        angle_rad = math.radians(angle)
        
        # Draw needle
        needle_length = radius * 0.85
        endpoint = QPointF(
            center.x() + needle_length * math.sin(angle_rad),
            center.y() - needle_length * math.cos(angle_rad)
        )
        
        painter.setPen(QPen(QColor(0, 0, 0), 3))
        painter.drawLine(center, endpoint)
        
        # Draw center cap
        painter.setBrush(QColor(100, 100, 100))
        painter.drawEllipse(center, 10, 10)
```

3. **Use image-based gauge in display manager:**

Update `src/display_manager.py`:

```python
from image_gauge import ImageTachometer, ImageSpeedometer, ImageFuelGauge

class DisplayManager(QWidget):
    def __init__(self):
        super().__init__()
        
        # Use image-based gauges
        self.tachometer = ImageTachometer("gauges/tachometer_bg.png")
        self.speedometer = ImageSpeedometer("gauges/speedometer_bg.png")
        self.fuel_gauge = ImageFuelGauge("gauges/fuel_bg.png")
        
        # ... rest of code
```

4. **Create gauge background images:**

Use any image editor (Photoshop, GIMP, Inkscape, Figma):
- 1080x1080 resolution
- Design gauge face, ticks, numbers, labels
- Leave circular area clear for needle overlay
- Save as PNG in `gauges/` folder

### Example Workflow

1. **Create base image:**
   - Open Figma or GIMP
   - Create 1080x1080 canvas
   - Draw gauge circle, grid lines, tick marks
   - Add RPM/KMH numbers around the edge
   - Add E/F labels for fuel gauge
   - Export as PNG

2. **Test in emulator:**
   ```bash
   python emulator.py
   ```

3. **Adjust if needed:**
   - Redesign image and re-export
   - Test again until satisfied

## Method 3: Hybrid Approach

Use image backgrounds for realistic styling, but keep vector-drawn elements for dynamic parts:

```python
class HybridGauge(QWidget):
    """Image background + vector drawn ticks/numbers"""
    
    def paintEvent(self, event):
        painter = QPainter(self)
        
        # 1. Draw background image
        painter.drawPixmap(self.rect(), self.bg_pixmap)
        
        # 2. Draw dynamic vector elements (optional)
        self._draw_dynamic_labels(painter)
        
        # 3. Draw needle on top
        self._draw_needle(painter)
```

## Preset Driving Modes for Testing

The emulator includes preset modes to test different scenarios:

**Press number keys in emulator:**
- `0` - IDLE (1000 RPM, stationary)
- `1` - SLOW REV (gentle acceleration to 3000 RPM)
- `2` - MEDIUM REV (moderate acceleration to 5000 RPM)
- `3` - FAST REV (aggressive acceleration to 7000 RPM)
- `4` - HIGHWAY (steady 130 km/h cruise)
- `5` - REDLINE (bouncing off 7000+ RPM)
- `6` - REALISTIC (full driving cycle)

Each mode simulates realistic vehicle behavior with proper temperature, boost, and fuel consumption curves.

## Testing Gauges Without Hardware

Run the emulator on Windows:
```bash
python emulator.py
```

For different FPS targets:
```bash
python emulator.py --fps 60
```

For fullscreen testing:
```bash
python emulator.py --fullscreen
```

## Common Customization Examples

### Make Tachometer Redline at 6000 RPM

```python
class TachometerWidget(BaseGauge):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.max_rpm = 8000
        self.redline = 6000  # Changed from 7000
```

### Change Speedometer Max to 300 km/h

```python
class SpeedometerWidget(BaseGauge):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.max_speed = 300  # Changed from 260
```

### Make Night Mode Red Needles

In `_get_colors()`:
```python
if self.night_mode:
    return {
        'needle': QColor(220, 0, 0),  # Red in night mode
        # ... rest of colors
    }
```

### Add Custom Font to Gauge Numbers

In gauge drawing method:
```python
font = QFont("Arial", 12, QFont.Bold)
painter.setFont(font)
painter.drawText(position, "3000")
```

## Performance Considerations

- **Vector-based gauges:** Lower CPU/GPU usage, smallest file size
- **Image-based gauges:** Higher quality appearance, minimal performance impact (just image blitting)
- **Hybrid approach:** Best of both worlds

All methods easily achieve **50+ FPS** on modern hardware and the Orange Pi 6 Plus.

## Files Reference

- **Gauge code:** `src/gauge_renderer.py`
- **Display layout:** `src/display_manager.py`
- **Emulator/testing:** `emulator.py`
- **Configuration:** `config/config.yaml`

## Support

For questions or issues:
1. Check `EMULATOR_GUIDE.md` for troubleshooting
2. Review code comments in `src/gauge_renderer.py`
3. Test with different driving modes (`0`-`6` keys) to verify gauge behavior
