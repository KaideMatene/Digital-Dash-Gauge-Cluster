#!/usr/bin/env python3
"""
Rotate gauge images 90 degrees to the left
"""

from PIL import Image
from pathlib import Path

gauges_dir = Path("gauges")

images_to_rotate = [
    "tachometer_bg.png",
    "speedometer_bg.png",
    "fuel_bg.png",
]

for img_file in images_to_rotate:
    img_path = gauges_dir / img_file
    
    if not img_path.exists():
        print(f"Not found: {img_file}")
        continue
    
    # Open and rotate 90 degrees counter-clockwise (to the left)
    img = Image.open(img_path)
    rotated = img.rotate(90, expand=True)
    
    # Save back
    rotated.save(img_path)
    print(f"Rotated {img_file}: {img.size} -> {rotated.size}")

print("\nAll gauges rotated 90 degrees to the left!")
