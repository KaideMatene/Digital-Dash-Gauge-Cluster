"""
Vector Needle Renderer

High-quality vector needles using QPainterPath - no pixelation when rotating.
Traced from original PNG needle designs.
"""

from PyQt5.QtGui import QPainterPath, QLinearGradient, QColor, QPen, QPainter
from PyQt5.QtCore import QPointF


class VectorNeedle:
    """Vector-based needle renderer"""
    
    def __init__(self, length=70, width=65, tip_width=4, base_width=1):
        """
        Create vector needle shape.
        
        Args:
            length: Needle length in pixels (tip to pivot)
            width: Maximum width (in middle of needle)
            tip_width: Width at tip
            base_width: Width at base/pivot
        """
        self.length = length
        self.width = width
        self.tip_width = tip_width
        self.base_width = base_width
        self.path = self._create_path()
    
    def _create_path(self):
        """Create needle QPainterPath (diamond/kite shape)"""
        path = QPainterPath()
        
        # Calculate widths at key points
        half_base = self.base_width / 2
        half_tip = self.tip_width / 2
        
        # Diamond shape - wide in middle, narrow at ends
        quarter_y = -self.length * 0.25  # 25% from base
        mid_y = -self.length * 0.50      # 50% (widest)
        three_quarter_y = -self.length * 0.75  # 75%
        
        # Widths taper from narrow base -> wide middle -> narrow tip
        quarter_width = self.width * 0.32     # ~21px at 25%
        mid_width = self.width / 2            # ~32px at 50%
        three_quarter_width = self.width * 0.42  # ~27px at 75%
        
        # Build path from base (0,0) up to tip
        path.moveTo(0, 0)  # Base center (pivot point)
        path.lineTo(-half_base, 0)  # Left base edge
        path.lineTo(-quarter_width, quarter_y)  # Widen out
        path.lineTo(-mid_width, mid_y)  # Widest point
        path.lineTo(-three_quarter_width, three_quarter_y)  # Taper in
        path.lineTo(-half_tip, -self.length)  # Tip left
        path.lineTo(half_tip, -self.length)  # Tip right
        path.lineTo(three_quarter_width, three_quarter_y)  # Taper in
        path.lineTo(mid_width, mid_y)  # Widest point
        path.lineTo(quarter_width, quarter_y)  # Widen out
        path.lineTo(half_base, 0)  # Right base edge
        path.closeSubpath()
        
        return path
    
    def create_gradient(self, color=None):
        """
        Create metallic gradient for realistic needle.
        
        Args:
            color: Base color (defaults to silver/gray)
        """
        gradient = QLinearGradient(0, 0, 0, -self.length)
        
        if color:
            # Use provided color with lighter/darker shades
            r, g, b = color.red(), color.green(), color.blue()
            gradient.setColorAt(0.0, QColor(r//2, g//2, b//2))  # Dark base
            gradient.setColorAt(0.2, QColor(min(r+100, 255), min(g+100, 255), min(b+100, 255)))  # Highlight
            gradient.setColorAt(0.5, color)  # Mid tone
            gradient.setColorAt(0.8, QColor(min(r+50, 255), min(g+50, 255), min(b+50, 255)))  # Light
            gradient.setColorAt(1.0, QColor(min(r+80, 255), min(g+80, 255), min(b+80, 255)))  # Bright tip
        else:
            # Default metallic silver
            gradient.setColorAt(0.0, QColor(60, 60, 60))      # Dark base
            gradient.setColorAt(0.2, QColor(220, 220, 220))   # Bright highlight
            gradient.setColorAt(0.5, QColor(140, 140, 140))   # Mid tone
            gradient.setColorAt(0.8, QColor(190, 190, 190))   # Light
            gradient.setColorAt(1.0, QColor(230, 230, 230))   # Bright tip
        
        return gradient
    
    def draw(self, painter: QPainter, center_x, center_y, angle, color=None, 
             shadow=True, outline=True):
        """
        Draw the vector needle.
        
        Args:
            painter: QPainter instance
            center_x: X position of needle pivot
            center_y: Y position of needle pivot
            angle: Rotation angle in degrees
            color: Custom color (None = default silver)
            shadow: Draw shadow for depth
            outline: Draw dark outline for definition
        """
        painter.save()
        
        # Enable high quality rendering
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        
        # Move to pivot point
        painter.translate(center_x, center_y)
        
        # Draw shadow first (slightly offset)
        if shadow:
            painter.save()
            painter.translate(2, 2)  # Offset shadow
            painter.rotate(angle)
            shadow_brush = QColor(0, 0, 0, 80)  # Semi-transparent black
            painter.fillPath(self.path, shadow_brush)
            painter.restore()
        
        # Draw main needle
        painter.rotate(angle)
        gradient = self.create_gradient(color)
        painter.fillPath(self.path, gradient)
        
        # Draw outline for definition
        if outline:
            pen = QPen(QColor(40, 40, 40), 1.0)  # Dark outline
            painter.strokePath(self.path, pen)
        
        painter.restore()


# Pre-configured needles matching original PNG designs
class TachometerNeedle(VectorNeedle):
    """Tachometer needle (standard size)"""
    def __init__(self):
        super().__init__(length=70, width=65, tip_width=4, base_width=1)


class SpeedometerNeedle(VectorNeedle):
    """Speedometer needle (standard size)"""
    def __init__(self):
        super().__init__(length=70, width=65, tip_width=4, base_width=1)


class FuelNeedle(VectorNeedle):
    """Fuel gauge needle (standard size)"""
    def __init__(self):
        super().__init__(length=70, width=65, tip_width=4, base_width=1)


class WaterNeedle(VectorNeedle):
    """Water temperature needle (standard size)"""
    def __init__(self):
        super().__init__(length=70, width=65, tip_width=4, base_width=1)


# Example usage
if __name__ == '__main__':
    print("Vector Needle Module")
    print("=" * 50)
    print()
    print("Usage:")
    print("  from vector_needle import TachometerNeedle")
    print("  needle = TachometerNeedle()")
    print("  needle.draw(painter, center_x, center_y, angle)")
    print()
    print("Benefits:")
    print("  ✓ No pixelation at any rotation")
    print("  ✓ Lower memory usage (no PNG textures)")
    print("  ✓ Faster rendering")
    print("  ✓ Scalable to any size")
    print("  ✓ Customizable colors")
