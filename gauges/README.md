"""
Quick start guide for using custom gauge images

This file explains how to set up custom gauge backgrounds.
"""

# Option 1: Generate Images Automatically (requires Pillow)
# =========================================================
# Install Pillow first:
#     pip install Pillow
# 
# Then run:
#     python create_gauge_images.py
#
# This will generate placeholder images you can customize.

# Option 2: Create Images in Image Editor (Recommended)
# =====================================================
# Create three 1080x1080 PNG files:
# 1. gauges/tachometer_bg.png  - Tachometer gauge background
# 2. gauges/speedometer_bg.png - Speedometer gauge background
# 3. gauges/fuel_bg.png        - Fuel gauge background
#
# Design tips:
# - Use cream/light background (similar to car dashboards)
# - Add concentric circles for gauge face
# - Draw tick marks around the circle (0° at top, going clockwise)
# - Add numbers/labels (0-8000 for RPM, 0-260 for Speed, E-F for Fuel)
# - Leave center circle clear for needle overlay
#
# Tools you can use:
# - Figma (free, online)
# - GIMP (free, offline)
# - Photoshop
# - Inkscape (vector-based)
# - Affinity Designer

# Option 3: Use Vector Gauges (Default)
# ====================================
# The code includes built-in vector gauges that work without images.
# They look clean and work perfectly at any resolution.
# 
# To stick with vector gauges, just run normally:
#     python emulator.py
#
# The system automatically detects this and uses vector rendering.

# How to Switch Gauges
# ====================
# 1. Place your PNG images in the gauges/ folder
# 2. Run the emulator:
#     python emulator.py
# 3. Automatically switches to image-based gauges if images exist
# 4. Falls back to vector gauges if images can't be found

# Gauge Image Specifications
# ==========================
# Filename: gauges/tachometer_bg.png
#   - Resolution: 1080x1080 pixels (matches display)
#   - Format: PNG with transparency (optional)
#   - Content: Tachometer gauge face with ticks and numbers
#   - 0 RPM at top, 8000 RPM continues around (270° sweep)
#
# Filename: gauges/speedometer_bg.png
#   - Resolution: 1080x1080 pixels
#   - Format: PNG
#   - Content: Speedometer gauge face with ticks and numbers
#   - 0 km/h at top, 260 km/h continues around (270° sweep)
#
# Filename: gauges/fuel_bg.png
#   - Resolution: 1080x1080 pixels
#   - Format: PNG
#   - Content: Fuel gauge with E-F labels
#   - E (empty) at left (180°), F (full) at top-right (90°)

# Example: Creating Gauges in Figma
# =================================
# 1. Create 1080x1080 artboard
# 2. Add circle in center (radius ~500px)
# 3. Add tick marks around edge every 40px
# 4. Add numbers/text for scale labels
# 5. Export as PNG
# 6. Save to gauges/tachometer_bg.png
# 7. Repeat for speedometer and fuel gauge

# Code Structure
# ==============
# src/gauge_renderer.py    - Vector gauge implementations
# src/image_gauge.py       - Image-based gauge with needle overlay
# src/display_manager.py   - Layout manager (auto-switches gauge types)
# gauges/                  - Folder for PNG background images
# create_gauge_images.py   - Script to generate test images (requires Pillow)

print(__doc__)
print("\n" + "="*70)
print("QUICK START")
print("="*70)
print("""
1. Vector Gauges (Built-in, no setup needed):
   python emulator.py

2. Generate Simple Test Images (if PIL installed):
   pip install Pillow
   python create_gauge_images.py
   python emulator.py

3. Create Custom Gauge Images:
   - Design in Figma, GIMP, Photoshop, etc.
   - Export as PNG (1080x1080)
   - Save to gauges/ folder
   - python emulator.py (auto-detects and uses them)

See GAUGE_CUSTOMIZATION.md for detailed guide.
""")
