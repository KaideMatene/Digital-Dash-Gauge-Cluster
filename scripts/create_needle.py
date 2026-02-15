#!/usr/bin/env python3
"""Create a simple needle image for testing"""

from PIL import Image, ImageDraw
import os

# Create a simple needle: thin red line pointing up
width, height = 20, 200
needle = Image.new("RGBA", (width, height), (0, 0, 0, 0))
draw = ImageDraw.Draw(needle)

# Draw a red needle pointing upward
draw.rectangle([(8, 50), (12, 200)], fill=(255, 0, 0, 255))  # shaft
draw.polygon([(6, 50), (14, 50), (10, 30)], fill=(255, 0, 0, 255))  # tip

needle.save("gauges/needle.png")
print("✅ Created: gauges/needle.png")
