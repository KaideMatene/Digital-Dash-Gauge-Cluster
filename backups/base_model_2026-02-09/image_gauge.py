"""
Image-Based Gauge Renderer

Uses PNG/JPG background images with needle overlays.
Allows for custom gauge styling without code changes.
Supports v2 calibrations with automatic angle calculation.
"""

import math
import logging
import json
from pathlib import Path
from typing import Optional, Dict, Any

from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QPainter, QPixmap, QColor, QPen, QFont, QTransform, QImage
from PyQt5.QtCore import Qt, QPointF, QSize, QRectF
from PyQt5.QtSvg import QSvgRenderer

try:
    from angle_calculator import AngleCalculator
except ImportError:
    AngleCalculator = None

logger = logging.getLogger(__name__)


class ImageBasedGauge(QWidget):
    """Base class for image-based gauges with needle overlay"""
    
    def __init__(self, bg_image_path: str, needle_image_path: str = None, parent=None):
        super().__init__(parent)
        self.bg_pixmap = QPixmap(bg_image_path)
        
        # Load needle image if provided (supports PNG and SVG)
        self.needle_pixmap = None
        self.needle_svg = None
        self.is_svg_needle = False
        
        if needle_image_path:
            # Check if it's an SVG file
            if needle_image_path.lower().endswith('.svg'):
                self.needle_svg = QSvgRenderer(needle_image_path)
                if self.needle_svg.isValid():
                    self.is_svg_needle = True
                    logger.info(f"✅ Loaded SVG needle: {needle_image_path}")
                else:
                    logger.warning(f"⚠️ Failed to load SVG needle: {needle_image_path}")
                    self.needle_svg = None
            else:
                # Load as PNG/JPG
                self.needle_pixmap = QPixmap(needle_image_path)
                if self.needle_pixmap.isNull():
                    logger.warning(f"⚠️ Failed to load needle image: {needle_image_path}")
                else:
                    logger.info(f"✅ Loaded needle image: {needle_image_path}")
        
        self.value = 0
        self.target_value = 0
        self.smoothing_factor = 0.2
        self.night_mode = False
        
        # Needle rotation center offset (x, y) as fraction of gauge size (0.5, 0.5 = center)
        # Adjust these if the needle doesn't rotate from the right point
        self.needle_center_offset = (0.5, 0.5)
        
        # Needle pivot point in the PNG image (x, y) as fraction of needle image size
        # Default (0.5, 1.0) = bottom center of needle image
        # This is where the needle actually rotates from
        self.needle_pivot = (0.5, 1.0)
        
        # V2 Calibration support
        self.angle_calculator = None
        self.gauge_bg_width = None  # Track gauge background dimensions
        self.gauge_bg_height = None
        self.gauge_display_scale = 1.0
        self.gauge_pivot_px = None
        self.calibration_points_px = []
        self.needle_length_px = None
        self.desired_tip_radius_px = None
        self.needle_base_angle = 0.0
        self.needle_scale = 1.0  # Scale multiplier for needle length (0.5-2.0)
        
        # Multi-needle support: dictionary of named needles loaded from config
        self.named_needles = {}  # {'needle_name': {'value': 0, 'angle': 0, 'scale': 1.0, 'angle_calc': ...}}
        
        self.setMinimumSize(400, 400)
        
        if self.bg_pixmap.isNull():
            logger.warning(f"⚠️ Failed to load image: {bg_image_path}")
        else:
            logger.info(f"✅ Loaded gauge image: {bg_image_path}")
            # Store background dimensions for coordinate conversion
            self.gauge_bg_width = self.bg_pixmap.width()
            self.gauge_bg_height = self.bg_pixmap.height()
    
    def set_needle_center(self, x_fraction: float, y_fraction: float):
        """
        Set needle rotation center as fraction of gauge size (0.0 to 1.0)
        Default is (0.5, 0.5) for center
        Example: set_needle_center(0.48, 0.52) for slightly offset center
        """
        self.needle_center_offset = (max(0, min(x_fraction, 1.0)), max(0, min(y_fraction, 1.0)))
        self.update()
    
    def set_needle_pivot(self, x_fraction: float, y_fraction: float):
        """
        Set needle pivot point in the PNG image as fraction of needle size (0.0 to 1.0)
        Default is (0.5, 1.0) = bottom center of needle image
        Adjust if the needle rotates from the wrong point in the PNG
        Example: set_needle_pivot(0.5, 0.8) if pivot is higher up
        """
        self.needle_pivot = (max(0, min(x_fraction, 1.0)), max(0, min(y_fraction, 1.0)))
        self.update()
    
    def load_v2_calibration(self, calibration_data: Dict[str, Any], needle_id: str):
        """
        Load v2 calibration from dictionary (from JSON config).
        
        Args:
            calibration_data: Dict with needle_calibrations structure
            needle_id: Which needle to load (e.g., 'fuel', 'water', 'main')
        """
        if not calibration_data or needle_id not in calibration_data:
            logger.warning(f"⚠️ No calibration found for needle: {needle_id}")
            return False
        
        try:
            needle_cal = calibration_data[needle_id]
            
            # Create angle calculator with gauge pivot
            gauge_pivot_x = needle_cal.get('gauge_pivot_x', 0)
            gauge_pivot_y = needle_cal.get('gauge_pivot_y', 0)
            
            if AngleCalculator:
                self.angle_calculator = AngleCalculator(gauge_pivot_x, gauge_pivot_y)
                
                # Load calibration points
                points = needle_cal.get('calibration_points', [])
                self.angle_calculator.points_from_list(points)
                self.calibration_points_px = points
                self.gauge_pivot_px = (gauge_pivot_x, gauge_pivot_y)
                
                logger.info(f"✅ Loaded v2 calibration for {needle_id} with {len(points)} points")
                
                # Set needle pivot from calibration (convert pixel to fraction)
                needle_piv_x = needle_cal.get('needle_pivot_x', 0)
                needle_piv_y = needle_cal.get('needle_pivot_y', 0)
                needle_end_x = needle_cal.get('needle_end_x', 0)
                needle_end_y = needle_cal.get('needle_end_y', 0)
                
                # Get needle dimensions (from SVG or PNG)
                needle_w = 1
                needle_h = 1
                
                if self.is_svg_needle and self.needle_svg:
                    # Get dimensions from SVG
                    svg_size = self.needle_svg.defaultSize()
                    needle_w = svg_size.width() if svg_size.width() > 0 else 1
                    needle_h = svg_size.height() if svg_size.height() > 0 else 1
                    if needle_w > 0 and needle_h > 0:
                        self.needle_pivot = (needle_piv_x / needle_w, needle_piv_y / needle_h)
                        logger.info(f"  ✅ Set SVG needle pivot to {self.needle_pivot} (from pixels {needle_piv_x}, {needle_piv_y} on {needle_w}x{needle_h} SVG)")
                        if needle_end_x or needle_end_y:
                            dx = needle_end_x - needle_piv_x
                            dy = needle_end_y - needle_piv_y
                            self.needle_length_px = (dx * dx + dy * dy) ** 0.5
                            self.needle_base_angle = (math.degrees(math.atan2(dy, dx)) + 360) % 360
                        else:
                            self.needle_length_px = None
                elif self.needle_pixmap and not self.needle_pixmap.isNull():
                    # Get dimensions from PNG
                    needle_w = self.needle_pixmap.width()
                    needle_h = self.needle_pixmap.height()
                    if needle_w > 0 and needle_h > 0:
                        self.needle_pivot = (needle_piv_x / needle_w, needle_piv_y / needle_h)
                        logger.info(f"  ✅ Set needle pivot to {self.needle_pivot} (from pixels {needle_piv_x}, {needle_piv_y} on {needle_w}x{needle_h} image)")
                        if needle_end_x or needle_end_y:
                            dx = needle_end_x - needle_piv_x
                            dy = needle_end_y - needle_piv_y
                            self.needle_length_px = (dx * dx + dy * dy) ** 0.5
                            self.needle_base_angle = (math.degrees(math.atan2(dy, dx)) + 360) % 360
                        else:
                            self.needle_length_px = None
                    else:
                        logger.warning(f"  ⚠️ Needle image has invalid dimensions: {needle_w}x{needle_h}")
                else:
                    logger.warning(f"  ⚠️ No needle loaded (neither SVG nor pixmap)")
                
                # Debug: Show calibration details
                logger.info(f"  📏 Gauge BG dims: {self.gauge_bg_width} x {self.gauge_bg_height}")
                logger.info(f"  📌 Gauge pivot (px): ({gauge_pivot_x}, {gauge_pivot_y})")
                logger.info(f"  📏 Needle dims: {needle_w} x {needle_h}")
                logger.info(f"  📍 Needle pivot (px): ({needle_piv_x}, {needle_piv_y}) → fraction: {self.needle_pivot}")
                
                # Calculate needle center from gauge pivot (convert to fraction)
                if self.gauge_bg_width and self.gauge_bg_height:
                    center_x = gauge_pivot_x / self.gauge_bg_width
                    center_y = gauge_pivot_y / self.gauge_bg_height
                    self.needle_center_offset = (center_x, center_y)
                    logger.info(f"  🎯 Needle center offset (fraction): {self.needle_center_offset}")

                # Calculate desired tip radius from calibration points
                if self.gauge_pivot_px and points:
                    distances = []
                    for point in points:
                        px = point.get('x', 0)
                        py = point.get('y', 0)
                        dx = px - gauge_pivot_x
                        dy = py - gauge_pivot_y
                        distances.append((dx * dx + dy * dy) ** 0.5)
                    if distances:
                        self.desired_tip_radius_px = sum(distances) / len(distances)
                
                # Load needle scale if present
                if 'needle_scale' in needle_cal:
                    self.needle_scale = float(needle_cal['needle_scale'])
                    logger.info(f"  ⚖️ Needle scale: {self.needle_scale:.2f}x")
                
                # Show first few calibration points
                if points:
                    logger.info(f"  📊 Calibration points (first 3):")
                    for p in points[:3]:
                        logger.info(f"     Value {p.get('value', 'N/A'):6.1f} → px ({p.get('x', 0):4.0f}, {p.get('y', 0):4.0f})")
                
                return True
            else:
                logger.warning("⚠️ AngleCalculator not available")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to load v2 calibration: {e}")
            return False
    
    def load_v2_from_file(self, config_path: str, needle_id: str):
        """
        Load v2 calibration directly from a config JSON file.
        
        Args:
            config_path: Path to config JSON file
            needle_id: Which needle to load
        """
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            needle_calibrations = config.get('needle_calibrations', {})
            return self.load_v2_calibration(needle_calibrations, needle_id)
        except Exception as e:
            logger.error(f"❌ Failed to load config from {config_path}: {e}")
            return False
    
    def load_all_needles_from_file(self, config_path: str, main_needle_id: str = "main"):
        """
        Load ALL needle calibrations from a config file.
        
        Args:
            config_path: Path to config JSON file
            main_needle_id: The primary needle ID to use for the main gauge needle
        """
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            needle_calibrations = config.get('needle_calibrations', {})
            
            # Load main needle first
            if main_needle_id in needle_calibrations:
                self.load_v2_calibration(needle_calibrations, main_needle_id)
                logger.info(f"✅ Loaded main needle: {main_needle_id}")
            
            # Load all other needles as named needles
            for needle_id in needle_calibrations:
                if needle_id != main_needle_id:
                    # Create AngleCalculator for this needle
                    needle_cal = needle_calibrations[needle_id]
                    points = needle_cal.get('calibration_points', [])
                    
                    if points and len(points) >= 2:
                        from angle_calculator import AngleCalculator
                        angle_calc = AngleCalculator()
                        angle_calc.load_calibration_points(points)
                        
                        scale = needle_cal.get('scale', 1.0)
                        
                        self.named_needles[needle_id] = {
                            'value': 0,
                            'scale': scale,
                            'angle_calc': angle_calc
                        }
                        logger.info(f"✅ Loaded named needle: {needle_id} (scale: {scale:.2f})")
                    else:
                        logger.debug(f"⚠️ Skipping {needle_id} - not enough calibration points")
            
            return True
        except Exception as e:
            logger.error(f"❌ Failed to load all needles from {config_path}: {e}")
            return False

    def get_needle_names(self) -> list:
        """Get list of all custom named needles (not including main/fuel/water)"""
        return list(self.named_needles.keys())
    
    def set_named_needle_value(self, needle_name: str, value: float):
        """Set value for a named needle"""
        if needle_name not in self.named_needles:
            # Create if doesn't exist
            self.named_needles[needle_name] = {'value': value, 'scale': 1.0}
            logger.debug(f"Created needle '{needle_name}'")
        else:
            self.named_needles[needle_name]['value'] = value
        self.update()
    
    def set_named_needle_scale(self, needle_name: str, scale: float):
        """Set scale multiplier for a named needle (0.5 to 2.0)"""
        if needle_name not in self.named_needles:
            self.named_needles[needle_name] = {'value': 0, 'scale': scale}
        else:
            self.named_needles[needle_name]['scale'] = max(0.5, min(2.0, scale))
        self.update()
    
    def get_named_needle_scale(self, needle_name: str) -> float:
        """Get scale multiplier for a named needle"""
        if needle_name in self.named_needles:
            return self.named_needles[needle_name]['scale']
        elif needle_name == 'main':
            return self.needle_scale
        return 1.0
    
    def delete_named_needle(self, needle_name: str):
        """Remove a named needle"""
        if needle_name in self.named_needles:
            del self.named_needles[needle_name]
            logger.info(f"Deleted needle '{needle_name}'")
            self.update()
    
    def save_needle_config_to_file(self, config_path: str):
        """Save all needle configurations to a JSON file"""
        try:
            # Load existing config
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Update needle calibrations with any modifications
            # (This preserves existing calibrations while allowing scale changes)
            if 'needle_calibrations' not in config:
                config['needle_calibrations'] = {}
            
            # Update scale for main needle
            if 'main' in config['needle_calibrations']:
                config['needle_calibrations']['main']['needle_scale'] = self.needle_scale
            
            # Add or update all named needles
            for needle_name, needle_data in self.named_needles.items():
                if needle_name not in config['needle_calibrations']:
                    # New needle - create basic entry
                    config['needle_calibrations'][needle_name] = {
                        'needle_id': needle_name,
                        'needle_scale': needle_data.get('scale', 1.0),
                        'calibration_points': []
                    }
                else:
                    # Update existing needle's scale
                    config['needle_calibrations'][needle_name]['needle_scale'] = needle_data.get('scale', 1.0)
            
            # Write back
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            logger.info(f"✅ Saved needle config to {config_path}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to save needle config: {e}")
            return False

    
    def sizeHint(self):
        """Return preferred size for layout (1080x1080 matches actual displays)"""
        return QSize(1080, 1080)
    
    def _smooth_value(self):
        """Smoothly interpolate current value toward target value"""
        delta = self.target_value - self.value
        self.value += delta * self.smoothing_factor
    
    def _get_needle_color(self):
        """Get needle color based on mode"""
        if self.night_mode:
            return QColor(255, 255, 255)
        else:
            return QColor(0, 0, 0)
    
    def paintEvent(self, event):
        """Draw background image and overlay needle - maintaining aspect ratio"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Debug widget size (log only occasionally to avoid spam)
        if not hasattr(self, '_last_logged_size'):
            self._last_logged_size = None
        current_size = (self.width(), self.height())
        if self._last_logged_size != current_size:
            logger.debug(f"📐 Widget size: {self.width()}x{self.height()}px (sizeHint: 1080x1080)")
            self._last_logged_size = current_size
        
        self._smooth_value()
        
        # Calculate scaled pixmap that maintains aspect ratio
        # Scale to fit in widget without distortion
        if not self.bg_pixmap.isNull():
            scaled_pixmap = self.bg_pixmap.scaledToWidth(
                self.width(),
                Qt.SmoothTransformation
            )
            
            # If still taller than our widget, scale by height instead
            if scaled_pixmap.height() > self.height():
                scaled_pixmap = self.bg_pixmap.scaledToHeight(
                    self.height(),
                    Qt.SmoothTransformation
                )
            
            # Center the scaled image
            x = (self.width() - scaled_pixmap.width()) / 2
            y = (self.height() - scaled_pixmap.height()) / 2
            painter.drawPixmap(int(x), int(y), scaled_pixmap)
            
            # Calculate needle center based on offset and actual displayed size
            gauge_x = x
            gauge_y = y
            gauge_width = scaled_pixmap.width()
            gauge_height = scaled_pixmap.height()

            if self.gauge_bg_width:
                self.gauge_display_scale = gauge_width / self.gauge_bg_width
            
            center = QPointF(
                gauge_x + gauge_width * self.needle_center_offset[0],
                gauge_y + gauge_height * self.needle_center_offset[1]
            )
            radius = min(gauge_width, gauge_height) / 2
        else:
            center = QPointF(self.width() / 2, self.height() / 2)
            radius = min(self.width(), self.height()) / 2
        
        self._draw_needle(painter, center, radius)
    
    def _draw_needle(self, painter: QPainter, center: QPointF, radius: float):
        """Override in subclass"""
        pass
    
    def _draw_all_named_needles(self, painter: QPainter, center: QPointF, radius: float):
        """Draw all named custom needles"""
        for needle_name, needle_data in self.named_needles.items():
            # Use a simple linear angle mapping for custom needles
            # Assumes value range 0-100 maps to 270°-90° (like standard gauges)
            value = needle_data.get('value', 0)
            angle_fraction = (value - 0) / (100 - 0) if value > 0 else 0
            angle = 270 - 180 * angle_fraction  # 270° to 90° range
            
            # Apply scale multiplier
            old_scale = self.needle_scale
            self.needle_scale = needle_data.get('scale', 1.0)
            self._rotate_and_draw_needle(painter, center, angle, radius)
            self.needle_scale = old_scale
    
    def _rotate_and_draw_needle(self, painter: QPainter, center: QPointF, angle: float, radius: float):
        """Rotate needle image around its pivot point and draw it at the specified angle"""
        # Handle SVG needles
        if self.is_svg_needle and self.needle_svg:
            self._draw_svg_needle(painter, center, radius, angle)
            return
        
        # Handle PNG/JPG needles
        if not self.needle_pixmap or self.needle_pixmap.isNull():
            return

        # Scale needle to match calibration tip radius when possible
        desired_length = None
        if self.desired_tip_radius_px and self.gauge_display_scale:
            desired_length = self.desired_tip_radius_px * self.gauge_display_scale

        if self.needle_length_px and desired_length:
            desired_length *= self.needle_scale
            scale = desired_length / self.needle_length_px
            scaled_width = max(1, int(self.needle_pixmap.width() * scale))
            scaled_height = max(1, int(self.needle_pixmap.height() * scale))
            scaled_needle = self.needle_pixmap.scaled(
                scaled_width, scaled_height, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
        else:
            needle_height = int(radius * 1.5 * self.needle_scale)
            scaled_needle = self.needle_pixmap.scaledToHeight(needle_height, Qt.SmoothTransformation)

        # Calculate pivot point in the scaled needle image
        pivot_x = scaled_needle.width() * self.needle_pivot[0]
        pivot_y = scaled_needle.height() * self.needle_pivot[1]

        # Rotate around pivot without changing the pivot alignment
        painter.save()
        painter.translate(center)
        painter.rotate(angle - self.needle_base_angle)
        painter.translate(-pivot_x, -pivot_y)
        painter.drawPixmap(0, 0, scaled_needle)
        painter.restore()
    
    def _draw_svg_needle(self, painter: QPainter, center: QPointF, radius: float, angle: float):
        """Draw SVG needle with perfect quality at any rotation"""
        if not self.needle_svg:
            return
        
        # Calculate needle size
        desired_length = None
        if self.desired_tip_radius_px and self.gauge_display_scale and self.gauge_bg_width and self.gauge_bg_height and self.desired_tip_radius_px > 0:
            # Use calibration to determine needle as percentage of gauge radius
            # Use same radius calculation as paintEvent: min of width/height
            calibrated_gauge_radius = min(self.gauge_bg_width, self.gauge_bg_height) / 2
            needle_percentage_of_radius = self.desired_tip_radius_px / calibrated_gauge_radius
            # Apply that percentage to the actual displayed radius, then apply scale multiplier
            desired_length = radius * needle_percentage_of_radius * self.needle_scale
            logger.debug(f"🎯 Needle: {self.desired_tip_radius_px:.0f}px / {calibrated_gauge_radius:.0f}px = {needle_percentage_of_radius:.1%} * {self.needle_scale:.2f}x = {desired_length:.1f}px")
        else:
            # Fallback: make needle ~90% of gauge radius with scale applied
            desired_length = radius * 0.9 * self.needle_scale
            logger.debug(f"⚠️ Needle FALLBACK: using 90% of radius={radius:.1f} * {self.needle_scale:.2f}x = {desired_length:.1f}px")
        
        # Get SVG default size
        svg_size = self.needle_svg.defaultSize()
        svg_height = svg_size.height() if svg_size.height() > 0 else 370
        
        # Scale needle to desired length
        scale = desired_length / svg_height
        
        needle_width = int(svg_size.width() * scale)
        needle_height = int(svg_size.height() * scale)
        
        # Calculate pivot point
        pivot_x = needle_width * self.needle_pivot[0]
        pivot_y = needle_height * self.needle_pivot[1]
        
        # Render SVG to image at the target size (no pixelation!)
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        
        painter.translate(center)
        painter.rotate(angle - self.needle_base_angle)
        painter.translate(-pivot_x, -pivot_y)
        
        # Render SVG directly (crisp vector rendering)
        self.needle_svg.render(painter, QRectF(0, 0, needle_width, needle_height))
        
        painter.restore()


class ImageTachometer(ImageBasedGauge):
    """Image-based tachometer (0-8000 RPM)"""
    
    def __init__(self, bg_image_path: str, needle_image_path: str = "gauges/needle.png", parent=None):
        self.max_rpm = 8000
        super().__init__(bg_image_path, needle_image_path, parent)
    
    def set_rpm(self, rpm: float):
        """Update RPM value"""
        self.target_value = max(0, min(rpm, self.max_rpm))
        self.update()
    
    def _draw_needle(self, painter: QPainter, center: QPointF, radius: float):
        """Draw RPM needle"""
        if self.angle_calculator:
            # Use v2 calibration to calculate angle
            angle = self.angle_calculator.value_to_angle(self.value)
        else:
            # Fallback to hardcoded angle
            start_angle = 270
            sweep_angle = 279
            angle_fraction = self.value / self.max_rpm
            angle = start_angle - sweep_angle * angle_fraction
        
        self._rotate_and_draw_needle(painter, center, angle, radius)
        # Draw any custom named needles
        self._draw_all_named_needles(painter, center, radius)


class ImageSpeedometer(ImageBasedGauge):
    """Image-based speedometer (0-260 km/h)"""
    
    def __init__(self, bg_image_path: str, needle_image_path: str = "gauges/needle.png", parent=None):
        self.max_speed = 260
        super().__init__(bg_image_path, needle_image_path, parent)
    
    def set_speed(self, speed: float):
        """Update speed value"""
        self.target_value = max(0, min(speed, self.max_speed))
        self.update()
    
    def _draw_needle(self, painter: QPainter, center: QPointF, radius: float):
        """Draw speed needle"""
        if self.angle_calculator:
            # Use v2 calibration to calculate angle
            angle = self.angle_calculator.value_to_angle(self.value)
        else:
            # Fallback to hardcoded angle
            start_angle = 240
            sweep_angle = 300
            angle_fraction = self.value / self.max_speed
            angle = start_angle - sweep_angle * angle_fraction
        
        self._rotate_and_draw_needle(painter, center, angle, radius)
        # Draw any custom named needles
        self._draw_all_named_needles(painter, center, radius)


class ImageFuelGauge(ImageBasedGauge):
    """Image-based fuel gauge with dual needles (fuel + water temp)"""
    
    def __init__(self, bg_image_path: str, needle_image_path: str = "gauges/needle.png", parent=None):
        super().__init__(bg_image_path, needle_image_path, parent)
        self.temperature = 80
        self.boost = 0.0
        
        # Support for dual needles (fuel + water)
        self.fuel_angle_calculator = None
        self.water_angle_calculator = None
        self.water_needle_pixmap = None
        self.water_needle_svg = None
        self.is_water_svg_needle = False
        self.water_needle_pivot = (0.5, 1.0)
        self.water_needle_center_offset = (0.5, 0.5)
        self.water_needle_length_px = None
        self.water_tip_radius_px = None
        self.water_base_angle = 0.0
        self.water_value = 80  # Default water temp
        self.water_target_value = 80
        self.water_needle_scale = 1.0  # Separate scale for water needle
    
    def set_fuel(self, percentage: float):
        """Update fuel level"""
        self.target_value = max(0, min(percentage, 100))
        self.update()
    
    def set_temperature(self, temp: float):
        """Update coolant temperature"""
        self.temperature = max(0, min(temp, 120))
        self.water_target_value = temp
        self.update()
    
    def set_boost(self, boost: float):
        """Update boost pressure"""
        self.boost = max(0, min(boost, 2.5))
    
    def load_dual_v2_calibration(self, calibration_data: Dict[str, Any]):
        """
        Load both fuel and water temperature calibrations.
        
        Args:
            calibration_data: Dict with needle_calibrations structure
        """
        # Load fuel calibration
        if 'fuel' in calibration_data:
            self.load_v2_calibration(calibration_data, 'fuel')
            self.fuel_angle_calculator = self.angle_calculator
        
        # Load water temperature calibration
        if 'water' in calibration_data:
            water_cal = calibration_data['water']
            gauge_pivot_x = water_cal.get('gauge_pivot_x', 0)
            gauge_pivot_y = water_cal.get('gauge_pivot_y', 0)
            
            if AngleCalculator:
                self.water_angle_calculator = AngleCalculator(gauge_pivot_x, gauge_pivot_y)
                points = water_cal.get('calibration_points', [])
                self.water_angle_calculator.points_from_list(points)
                
                # Try to load water needle image (PNG or SVG)
                water_needle_path = water_cal.get('needle_image_path', '')
                if water_needle_path and Path(water_needle_path).exists():
                    if water_needle_path.lower().endswith('.svg'):
                        # Load as SVG
                        self.water_needle_svg = QSvgRenderer(water_needle_path)
                        if self.water_needle_svg.isValid():
                            self.is_water_svg_needle = True
                            logger.info(f"✅ Loaded SVG water needle from {water_needle_path}")
                        else:
                            self.water_needle_svg = None
                    else:
                        # Load as PNG
                        self.water_needle_pixmap = QPixmap(water_needle_path)
                        if not self.water_needle_pixmap.isNull():
                            logger.info(f"✅ Loaded water needle from {water_needle_path}")
                
                # Load water needle scale multiplier
                self.water_needle_scale = float(water_cal.get('needle_scale', 1.0))

                # Set water needle pivot from calibration (convert pixel to fraction)
                needle_piv_x = water_cal.get('needle_pivot_x', 0)
                needle_piv_y = water_cal.get('needle_pivot_y', 0)
                needle_end_x = water_cal.get('needle_end_x', 0)
                needle_end_y = water_cal.get('needle_end_y', 0)
                
                # Get needle dimensions (from SVG or pixmap)
                if self.is_water_svg_needle and self.water_needle_svg:
                    svg_size = self.water_needle_svg.defaultSize()
                    needle_w = svg_size.width() if svg_size.width() > 0 else 1
                    needle_h = svg_size.height() if svg_size.height() > 0 else 1
                else:
                    needle_w = self.water_needle_pixmap.width() if self.water_needle_pixmap else 1
                    needle_h = self.water_needle_pixmap.height() if self.water_needle_pixmap else 1
                
                self.water_needle_pivot = (needle_piv_x / needle_w, needle_piv_y / needle_h)
                if needle_end_x or needle_end_y:
                    dx = needle_end_x - needle_piv_x
                    dy = needle_end_y - needle_piv_y
                    self.water_needle_length_px = (dx * dx + dy * dy) ** 0.5
                    self.water_base_angle = (math.degrees(math.atan2(dy, dx)) + 360) % 360
                else:
                    self.water_needle_length_px = None

                # Calculate water needle center from gauge pivot (convert to fraction)
                if self.gauge_bg_width and self.gauge_bg_height:
                    center_x = gauge_pivot_x / self.gauge_bg_width
                    center_y = gauge_pivot_y / self.gauge_bg_height
                    self.water_needle_center_offset = (center_x, center_y)

                # Calculate desired tip radius from calibration points
                if points:
                    distances = []
                    for point in points:
                        px = point.get('x', 0)
                        py = point.get('y', 0)
                        dx = px - gauge_pivot_x
                        dy = py - gauge_pivot_y
                        distances.append((dx * dx + dy * dy) ** 0.5)
                    if distances:
                        self.water_tip_radius_px = sum(distances) / len(distances)
                
                logger.info(f"✅ Loaded water temperature calibration with {len(points)} points")
    
    def paintEvent(self, event):
        """Draw background, needles, and info text"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        self._smooth_value()
        self.water_value += (self.water_target_value - self.water_value) * self.smoothing_factor

        if not self.bg_pixmap.isNull():
            scaled_pixmap = self.bg_pixmap.scaledToWidth(
                self.width(),
                Qt.SmoothTransformation
            )
            if scaled_pixmap.height() > self.height():
                scaled_pixmap = self.bg_pixmap.scaledToHeight(
                    self.height(),
                    Qt.SmoothTransformation
                )

            x = (self.width() - scaled_pixmap.width()) / 2
            y = (self.height() - scaled_pixmap.height()) / 2
            painter.drawPixmap(int(x), int(y), scaled_pixmap)

            gauge_x = x
            gauge_y = y
            gauge_width = scaled_pixmap.width()
            gauge_height = scaled_pixmap.height()

            if self.gauge_bg_width:
                self.gauge_display_scale = gauge_width / self.gauge_bg_width
        else:
            gauge_x = 0
            gauge_y = 0
            gauge_width = self.width()
            gauge_height = self.height()

        radius = min(gauge_width, gauge_height) / 2

        fuel_center = QPointF(
            gauge_x + gauge_width * self.needle_center_offset[0],
            gauge_y + gauge_height * self.needle_center_offset[1]
        )
        water_center = QPointF(
            gauge_x + gauge_width * self.water_needle_center_offset[0],
            gauge_y + gauge_height * self.water_needle_center_offset[1]
        )

        # Draw fuel needle
        self._draw_fuel_needle(painter, fuel_center, radius)

        # Draw water needle
        if self.water_angle_calculator:
            self._draw_water_needle(painter, water_center, radius)
        
        # Draw any custom named needles
        self._draw_all_named_needles(painter, fuel_center, radius)
    
    def _draw_fuel_needle(self, painter: QPainter, center: QPointF, radius: float):
        """Draw fuel gauge needle"""
        if self.fuel_angle_calculator:
            # Use v2 calibration
            angle = self.fuel_angle_calculator.value_to_angle(self.value)
        else:
            # Fallback to hardcoded angle
            left_angle = 180
            right_angle = 90
            angle_fraction = self.value / 100
            angle = left_angle - (left_angle - right_angle) * angle_fraction
        
        self._rotate_and_draw_needle(painter, center, angle, radius)
    
    def _draw_water_needle(self, painter: QPainter, center: QPointF, radius: float):
        """Draw water temperature needle (PNG or SVG)"""
        if not self.water_angle_calculator:
            return
        
        angle = self.water_angle_calculator.value_to_angle(self.water_value)
        
        # Handle SVG water needle
        if self.is_water_svg_needle and self.water_needle_svg:
            self._draw_svg_water_needle(painter, center, radius, angle)
            return
        
        # Handle PNG water needle
        if not self.water_needle_pixmap:
            return

        # Scale needle to match calibration tip radius when possible
        desired_length = None
        if self.water_tip_radius_px and self.gauge_display_scale:
            desired_length = self.water_tip_radius_px * self.gauge_display_scale

        if self.water_needle_length_px and desired_length:
            desired_length *= self.water_needle_scale
            scale = desired_length / self.water_needle_length_px
            scaled_width = max(1, int(self.water_needle_pixmap.width() * scale))
            scaled_height = max(1, int(self.water_needle_pixmap.height() * scale))
            scaled_needle = self.water_needle_pixmap.scaled(
                scaled_width, scaled_height, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
        else:
            needle_height = int(radius * 1.5 * self.water_needle_scale)
            scaled_needle = self.water_needle_pixmap.scaledToHeight(needle_height, Qt.SmoothTransformation)

        # Calculate pivot point in the scaled needle image
        pivot_x = scaled_needle.width() * self.water_needle_pivot[0]
        pivot_y = scaled_needle.height() * self.water_needle_pivot[1]

        painter.save()
        painter.translate(center)
        painter.rotate(angle - self.water_base_angle)
        painter.translate(-pivot_x, -pivot_y)
        painter.drawPixmap(0, 0, scaled_needle)
        painter.restore()
    
    def _draw_svg_water_needle(self, painter: QPainter, center: QPointF, radius: float, angle: float):
        """Draw SVG water needle with perfect quality"""
        if not self.water_needle_svg:
            return
        
        # Calculate needle size
        desired_length = None
        if self.water_tip_radius_px and self.gauge_display_scale:
            desired_length = self.water_tip_radius_px * self.gauge_display_scale
        else:
            desired_length = radius * 1.5

        desired_length *= self.water_needle_scale
        
        # Get SVG default size and scale to desired length
        svg_size = self.water_needle_svg.defaultSize()
        if svg_size.height() > 0:
            scale = desired_length / svg_size.height()
        else:
            scale = 1.0
        
        needle_width = int(svg_size.width() * scale)
        needle_height = int(svg_size.height() * scale)
        
        # Calculate pivot point
        pivot_x = needle_width * self.water_needle_pivot[0]
        pivot_y = needle_height * self.water_needle_pivot[1]
        
        # Render SVG directly (crisp vector rendering)
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        
        painter.translate(center)
        painter.rotate(angle - self.water_base_angle)
        painter.translate(-pivot_x, -pivot_y)
        
        self.water_needle_svg.render(painter, QRectF(0, 0, needle_width, needle_height))
        
        painter.restore()
    
    def _draw_info_text(self, painter: QPainter, center: QPointF):
        """Draw temperature info"""
        text_color = QColor(255, 255, 255) if self.night_mode else QColor(0, 0, 0)
        painter.setPen(text_color)
        painter.setFont(QFont('Arial', 11, QFont.Bold))
        
        temp_text = f"T:{int(self.water_value)}°C"
        painter.drawText(int(center.x() - 50), int(center.y() - 60), 100, 25, Qt.AlignCenter, temp_text)
