# Needle Customization Guide

Complete guide for customizing gauge needle appearance.

## Quick Reference

**File:** `src/gauge_renderer.py`

### Needle Length
Change `needle_length` in the `_draw_needle*` methods:
```python
needle_length = radius - 40  # Smaller number = longer needle
```
- Current: `radius - 40`
- Longer needle: `radius - 20` (20 pixels from edge)
- Shorter needle: `radius - 80` (80 pixels from edge)

### Needle Thickness
Change the pen width in QPen():
```python
pen = QPen(colors['needle'], 2)  # Last number is thickness in pixels
```
- Current: `2` pixels (thin)
- Thicker: `4` or `6` pixels
- Very thin: `1` pixel

### Needle Color
Colors are defined in `_get_colors()` method. Currently:
- Day mode: Black `QColor(0, 0, 0)`
- Night mode: White `QColor(255, 255, 255)`

## Detailed Customization

### 1. Simple Line Needle (Current)

**Location:** All three `_draw_needle*()` methods

```python
def _draw_needle(self, painter: QPainter, center: QPointF, radius: float, colors: dict):
    # ... angle calculations ...
    
    needle_length = radius - 40  # LENGTH: distance from center
    needle_end = QPointF(
        center.x() + needle_length * math.cos(rad),
        center.y() + needle_length * math.sin(rad)
    )
    
    pen = QPen(colors['needle'], 2)  # THICKNESS: 2 pixels wide
    painter.setPen(pen)
    painter.drawLine(center, needle_end)
```

**To modify:**
- Line 171 (Tachometer): `needle_length = radius - 40`
- Line 179 (Tachometer): `pen = QPen(colors['needle'], 2)`
- Line 262 (Speedometer): `needle_length = radius - 40`
- Line 270 (Speedometer): `pen = QPen(colors['needle'], 2)`
- Line 378 (Fuel): `needle_length = radius - 30`
- Line 384 (Fuel): `pen = QPen(colors['needle'], 3)`

### 2. Tapered/Triangular Needle

Replace the simple line with a polygon:

```python
def _draw_needle(self, painter: QPainter, center: QPointF, radius: float, colors: dict):
    # ... angle calculations ...
    
    needle_length = radius - 40
    needle_width = 8  # Width at base of needle
    
    # Calculate needle tip
    tip_x = center.x() + needle_length * math.cos(rad)
    tip_y = center.y() + needle_length * math.sin(rad)
    
    # Calculate perpendicular angle for needle base width
    perp_rad = rad + math.radians(90)
    base_half_width = needle_width / 2
    
    # Create triangle points: tip + two base corners
    from PyQt5.QtGui import QPolygonF
    needle_poly = QPolygonF([
        QPointF(tip_x, tip_y),  # Tip
        QPointF(center.x() + base_half_width * math.cos(perp_rad),
                center.y() + base_half_width * math.sin(perp_rad)),  # Base corner 1
        QPointF(center.x() - base_half_width * math.cos(perp_rad),
                center.y() - base_half_width * math.sin(perp_rad))   # Base corner 2
    ])
    
    painter.setBrush(QBrush(colors['needle']))
    painter.setPen(Qt.NoPen)
    painter.drawPolygon(needle_poly)
```

**Adjust:**
- `needle_width`: Base width (4-12 pixels typical)
- `needle_length`: Overall length

### 3. Outlined Needle

Add an outline around the needle for better visibility:

```python
def _draw_needle(self, painter: QPainter, center: QPointF, radius: float, colors: dict):
    # ... angle calculations ...
    
    needle_length = radius - 40
    needle_end = QPointF(
        center.x() + needle_length * math.cos(rad),
        center.y() + needle_length * math.sin(rad)
    )
    
    # Draw outline (thicker, different color)
    outline_pen = QPen(QColor(100, 100, 100), 4)  # Gray, 4px wide
    painter.setPen(outline_pen)
    painter.drawLine(center, needle_end)
    
    # Draw main needle on top (thinner)
    needle_pen = QPen(colors['needle'], 2)
    painter.setPen(needle_pen)
    painter.drawLine(center, needle_end)
```

### 4. Two-Tone Needle (Tip in different color)

```python
def _draw_needle(self, painter: QPainter, center: QPointF, radius: float, colors: dict):
    # ... angle calculations ...
    
    needle_length = radius - 40
    
    # Main needle (80% length)
    main_length = needle_length * 0.8
    main_end = QPointF(
        center.x() + main_length * math.cos(rad),
        center.y() + main_length * math.sin(rad)
    )
    pen = QPen(colors['needle'], 2)
    painter.setPen(pen)
    painter.drawLine(center, main_end)
    
    # Tip (last 20%, red)
    tip_end = QPointF(
        center.x() + needle_length * math.cos(rad),
        center.y() + needle_length * math.sin(rad)
    )
    tip_pen = QPen(QColor(255, 0, 0), 3)  # Red, slightly thicker
    painter.setPen(tip_pen)
    painter.drawLine(main_end, tip_end)
```

### 5. Glowing Needle Effect

Add transparency and blur (requires additional imports):

```python
from PyQt5.QtWidgets import QGraphicsBlurEffect, QGraphicsDropShadowEffect

def _draw_needle(self, painter: QPainter, center: QPointF, radius: float, colors: dict):
    # ... angle calculations ...
    
    needle_length = radius - 40
    needle_end = QPointF(
        center.x() + needle_length * math.cos(rad),
        center.y() + needle_length * math.sin(rad)
    )
    
    # Draw glow (wider, semi-transparent)
    glow_color = QColor(colors['needle'])
    glow_color.setAlpha(100)  # 40% opacity
    glow_pen = QPen(glow_color, 6)
    painter.setPen(glow_pen)
    painter.drawLine(center, needle_end)
    
    # Draw sharp needle on top
    pen = QPen(colors['needle'], 2)
    painter.setPen(pen)
    painter.drawLine(center, needle_end)
```

## Angle Adjustments

### Current Gauge Angles (Clockwise Rotation)

**Tachometer:**
```python
start_angle = 270  # 6 o'clock (0 RPM at bottom)
sweep_angle = 270  # 270° clockwise to 3 o'clock (max RPM at right)
```

**Speedometer:**
```python
start_angle = 240  # 8 o'clock (0 km/h)
sweep_angle = 300  # 300° clockwise sweep
```

**Fuel Gauge:**
```python
left_angle = 180   # E (empty) at 9 o'clock
right_angle = 90   # F (full) at 12 o'clock
```

### Angle Reference (Standard Qt)
```
        90° (12 o'clock)
             |
180° (9) ----+---- 0° (3)
             |
        270° (6 o'clock)
```

### Modify Start Position
Change `start_angle`:
```python
start_angle = 225  # 7:30 position
start_angle = 180  # 9 o'clock
start_angle = 135  # 10:30 position
```

### Modify Sweep Range
Change `sweep_angle`:
```python
sweep_angle = 180  # Half circle
sweep_angle = 240  # 2/3 circle
sweep_angle = 270  # 3/4 circle (most common)
```

### Clockwise vs Counter-Clockwise
```python
# Clockwise (current)
angle = start_angle - sweep_angle * fraction

# Counter-clockwise
angle = start_angle + sweep_angle * fraction
```

## Center Cap Customization

**Location:** End of each `paintEvent()` method

```python
# Current center cap (simple circle)
painter.setBrush(QBrush(colors['center']))
painter.setPen(Qt.NoPen)
painter.drawEllipse(center, 10, 10)  # Radius = 10 pixels
```

**Larger center cap:**
```python
painter.drawEllipse(center, 20, 20)  # Radius = 20 pixels
```

**Outlined center cap:**
```python
painter.setBrush(QBrush(colors['center']))
painter.setPen(QPen(QColor(0, 0, 0), 2))  # Black outline, 2px
painter.drawEllipse(center, 15, 15)
```

**Multi-ring center cap:**
```python
# Outer ring
painter.setBrush(QBrush(QColor(50, 50, 50)))
painter.setPen(Qt.NoPen)
painter.drawEllipse(center, 15, 15)

# Inner ring
painter.setBrush(QBrush(colors['center']))
painter.drawEllipse(center, 8, 8)
```

## Testing Your Changes

1. Save `gauge_renderer.py`
2. Run emulator: `python emulator.py`
3. Use keyboard to test different values:
   - `0-6`: Different driving modes
   - `?`: Show help/controls

## Common Examples

### Thick Racing Needle
```python
needle_length = radius - 30  # Longer
pen = QPen(colors['needle'], 5)  # Much thicker
```

### Short Stubby Needle
```python
needle_length = radius - 100  # Shorter
pen = QPen(colors['needle'], 6)  # Very thick
```

### Long Thin Precision Needle
```python
needle_length = radius - 15  # Very long
pen = QPen(colors['needle'], 1)  # Hair-thin
```

### Red Warning Needle (Always Red)
```python
pen = QPen(QColor(255, 0, 0), 3)  # Always red, ignore day/night mode
```

## Advanced: Custom Needle Shapes

For completely custom needle shapes (arrows, etc.), use QPainterPath:

```python
from PyQt5.QtGui import QPainterPath

def _draw_needle(self, painter: QPainter, center: QPointF, radius: float, colors: dict):
    # ... angle calculations ...
    
    needle_length = radius - 40
    
    # Create arrow shape
    path = QPainterPath()
    path.moveTo(0, 0)  # Start at center
    path.lineTo(needle_length - 10, -3)  # Upper edge
    path.lineTo(needle_length, 0)  # Arrow tip
    path.lineTo(needle_length - 10, 3)  # Lower edge
    path.closeSubpath()  # Back to center
    
    # Rotate and translate to proper position
    painter.save()
    painter.translate(center)
    painter.rotate(-math.degrees(rad))  # Rotate to angle
    
    painter.setBrush(QBrush(colors['needle']))
    painter.setPen(Qt.NoPen)
    painter.drawPath(path)
    
    painter.restore()
```

## Tips

1. **Always test incrementally**: Change one thing at a time
2. **Backup first**: Copy gauge_renderer.py before major changes
3. **Radius reference**: `radius` is the gauge's outer radius
4. **Coordinate system**: Center of gauge is (center.x(), center.y())
5. **Angles in radians**: Qt uses degrees, convert with `math.radians()`
6. **Colors**: Use `QColor(R, G, B)` where R, G, B are 0-255

## Quick Copy-Paste Examples

### Make all needles thicker (change to 4px):
Find all three lines with `pen = QPen(colors['needle'], 2)` and change `2` to `4`

### Make all needles longer:
Find all `needle_length = radius - XX` lines and reduce the number (e.g., `40` → `20`)

### Change needle color to red:
Replace `colors['needle']` with `QColor(255, 0, 0)` in the QPen() calls
