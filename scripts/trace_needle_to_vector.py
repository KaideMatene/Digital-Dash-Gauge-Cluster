#!/usr/bin/env python3
"""
Trace needle PNG to vector QPainterPath code

Analyzes needle image and generates Python code for vector needle.
"""

import sys
from PIL import Image
from pathlib import Path

def analyze_needle(image_path):
    """Analyze needle image and generate vector path"""
    img = Image.open(image_path).convert('RGBA')
    width, height = img.size
    
    # Find center (pivot point) - assume center of image
    center_x = width // 2
    center_y = height // 2
    
    # Scan for non-transparent pixels to find needle bounds
    tip_y = None
    base_y = None
    
    for y in range(height):
        row_has_content = False
        for x in range(width):
            r, g, b, a = img.getpixel((x, y))
            if a > 128:
                row_has_content = True
                break
        
        if row_has_content:
            if tip_y is None:
                tip_y = y
            base_y = y
    
    if tip_y is None:
        print("❌ No non-transparent pixels found!")
        return
    
    # Measure width at different points
    def measure_width(y):
        left = None
        right = None
        for x in range(width):
            r, g, b, a = img.getpixel((x, y))
            if a > 128:
                if left is None:
                    left = x
                right = x
        return (right - left + 1) if left is not None else 0
    
    base_width = measure_width(base_y)
    tip_width = measure_width(tip_y)
    
    # Calculate dimensions
    length = base_y - tip_y
    
    # Sample width at quarter points
    quarter_y = int(tip_y + length * 0.25)
    mid_y = int(tip_y + length * 0.5)
    three_quarter_y = int(tip_y + length * 0.75)
    
    quarter_width = measure_width(quarter_y)
    mid_width = measure_width(mid_y)
    three_quarter_width = measure_width(three_quarter_y)
    
    print(f"📐 Needle Analysis: {image_path}")
    print(f"   Image size: {width}x{height}")
    print(f"   Center (pivot): ({center_x}, {center_y})")
    print(f"   Needle length: {length}px")
    print(f"   Base width: {base_width}px")
    print(f"   Mid width: {mid_width}px")
    print(f"   Tip width: {tip_width}px")
    print()
    
    # Generate QPainterPath code
    print("=" * 70)
    print("GENERATED VECTOR NEEDLE CODE:")
    print("=" * 70)
    print()
    print("from PyQt5.QtGui import QPainterPath, QLinearGradient, QColor")
    print("from PyQt5.QtCore import QPointF")
    print()
    print("def create_needle_path():")
    print("    \"\"\"Vector needle traced from PNG\"\"\"")
    print("    path = QPainterPath()")
    print("    ")
    print("    # Needle shape (pivot at 0,0, pointing up)")
    
    # Create a tapered needle path
    half_base = base_width / 2
    half_tip = tip_width / 2
    half_quarter = quarter_width / 2
    half_mid = mid_width / 2
    half_three_quarter = three_quarter_width / 2
    
    # Calculate relative y positions
    rel_quarter = -(length * 0.75)
    rel_mid = -(length * 0.5)
    rel_three_quarter = -(length * 0.25)
    
    print(f"    path.moveTo(0, 0)  # Base center (pivot)")
    print(f"    path.lineTo(-{half_base:.1f}, 0)  # Left base edge")
    print(f"    path.lineTo(-{half_three_quarter:.1f}, {rel_three_quarter:.1f})  # Left side")
    print(f"    path.lineTo(-{half_mid:.1f}, {rel_mid:.1f})  # Left mid")
    print(f"    path.lineTo(-{half_quarter:.1f}, {rel_quarter:.1f})  # Near tip")
    print(f"    path.lineTo(-{half_tip:.1f}, -{length})  # Tip left")
    print(f"    path.lineTo({half_tip:.1f}, -{length})  # Tip right")
    print(f"    path.lineTo({half_quarter:.1f}, {rel_quarter:.1f})  # Near tip")
    print(f"    path.lineTo({half_mid:.1f}, {rel_mid:.1f})  # Right mid")
    print(f"    path.lineTo({half_three_quarter:.1f}, {rel_three_quarter:.1f})  # Right side")
    print(f"    path.lineTo({half_base:.1f}, 0)  # Right base edge")
    print("    path.closeSubpath()")
    print("    ")
    print("    return path")
    print()
    print()
    print("def create_needle_gradient(length):")
    print("    \"\"\"Metallic gradient for realistic look\"\"\"")
    print(f"    gradient = QLinearGradient(0, 0, 0, -{length})")
    print("    gradient.setColorAt(0.0, QColor(80, 80, 80))      # Dark base")
    print("    gradient.setColorAt(0.2, QColor(200, 200, 200))   # Bright edge")
    print("    gradient.setColorAt(0.5, QColor(140, 140, 140))   # Mid tone")
    print("    gradient.setColorAt(0.8, QColor(180, 180, 180))   # Light")
    print("    gradient.setColorAt(1.0, QColor(220, 220, 220))   # Bright tip")
    print("    return gradient")
    print()
    print("# Usage in paintEvent:")
    print("# painter.save()")
    print("# painter.translate(center_x, center_y)  # Move to pivot")
    print("# painter.rotate(angle)  # Rotate to desired angle")
    print("# gradient = create_needle_gradient(length)")
    print("# painter.fillPath(create_needle_path(), gradient)")
    print("# painter.restore()")
    print()
    print("=" * 70)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        needle_path = sys.argv[1]
    else:
        # Default to tachometer needle
        needle_path = "gauges/tachometer_needle.png"
    
    if not Path(needle_path).exists():
        print(f"❌ File not found: {needle_path}")
        print()
        print("Usage: python trace_needle_to_vector.py <needle_image.png>")
        print()
        print("Available needles:")
        gauges_dir = Path("gauges")
        if gauges_dir.exists():
            for needle in gauges_dir.glob("*_needle.png"):
                print(f"  - {needle}")
        sys.exit(1)
    
    analyze_needle(needle_path)
