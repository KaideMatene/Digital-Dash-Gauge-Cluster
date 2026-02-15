"""
Needle-Based Gauge Renderer

Uses PNG background + PNG needle images that rotate based on gauge values.
Simple, flexible, and visually accurate.
"""

import math
import logging
from pathlib import Path
from PIL import Image
from PIL.ImageQt import ImageQt
from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QPixmap, QPainter, QImage
from PyQt5.QtCore import Qt, QSize

logger = logging.getLogger(__name__)


class NeedleGauge(QWidget):
    """Gauge using PNG background and rotating PNG needle"""
    
    def __init__(self, bg_image_path: str, needle_image_path: str, parent=None):
        super().__init__(parent)
        self.value = 0
        self.target_value = 0
        self.smoothing_factor = 0.2
        self.night_mode = False
        
        # Load images
        self.bg_image = None
        self.needle_image = None
        self.bg_pixmap = None
        self.current_pixmap = None
        
        self._load_images(bg_image_path, needle_image_path)
        self.setMinimumSize(400, 400)
    
    def _load_images(self, bg_path: str, needle_path: str):
        """Load background and needle images"""
        try:
            # Load background
            if Path(bg_path).exists():
                self.bg_image = Image.open(bg_path).convert("RGBA")
                logger.info(f"✅ Loaded background: {Path(bg_path).name}")
            else:
                logger.warning(f"❌ Background not found: {bg_path}")
                return
            
            # Load needle
            if Path(needle_path).exists():
                self.needle_image = Image.open(needle_path).convert("RGBA")
                logger.info(f"✅ Loaded needle: {Path(needle_path).name}")
            else:
                logger.warning(f"❌ Needle not found: {needle_path}")
                return
            
            # Convert background to QPixmap for display
            self.bg_pixmap = self._pil_to_qpixmap(self.bg_image)
            
        except Exception as e:
            logger.error(f"Error loading images: {e}")
    
    def sizeHint(self):
        return QSize(1080, 1080)
    
    def set_value(self, value: float):
        """Update gauge value"""
        self.target_value = value
        self.update()
    
    def _smooth_value(self):
        """Smooth interpolation toward target value"""
        delta = self.target_value - self.value
        self.value += delta * self.smoothing_factor
    
    def paintEvent(self, event):
        """Render gauge with rotated needle"""
        if not self.bg_image or not self.needle_image:
            # Fallback if images didn't load
            painter = QPainter(self)
            painter.fillRect(self.rect(), Qt.gray)
            painter.drawText(10, 20, "Images not loaded")
            return
        
        self._smooth_value()
        
        # Create composite image (background + rotated needle)
        composite = self._create_composite_image()
        
        # Convert to QPixmap and display
        if composite:
            qpixmap = self._pil_to_qpixmap(composite)
            painter = QPainter(self)
            painter.drawPixmap(self.rect(), qpixmap)
    
    def _create_composite_image(self) -> Image:
        """Create composite image with rotated needle on background"""
        # Work at original resolution
        width, height = self.bg_image.size
        
        # Start with background
        composite = self.bg_image.copy()
        
        # Calculate rotation angle
        angle = self._get_needle_angle()
        
        # Rotate needle
        rotated_needle = self.needle_image.rotate(
            angle,
            expand=False,
            resample=Image.BILINEAR,
            center=None  # Rotates around center
        )
        
        # Center needle on composite
        needle_x = (width - rotated_needle.width) // 2
        needle_y = (height - rotated_needle.height) // 2
        
        # Composite needle onto background
        composite.paste(rotated_needle, (needle_x, needle_y), rotated_needle)
        
        return composite
    
    def _get_needle_angle(self) -> float:
        """
        Calculate needle rotation angle.
        Override in subclass for specific gauge behavior.
        """
        return 0  # Default: no rotation
    
    def _pil_to_qpixmap(self, pil_image: Image) -> QPixmap:
        """Convert PIL Image to QPixmap"""
        try:
            # Use ImageQt to avoid encoder issues on some Pillow builds
            pil_rgba = pil_image.convert("RGBA")
            qimage = ImageQt(pil_rgba)
            return QPixmap.fromImage(qimage)
        except Exception as e:
            logger.error(f"Error converting image: {e}")
            return QPixmap()


class TachometerNeedle(NeedleGauge):
    """Tachometer with png needle (0-8000 RPM)"""
    
    def __init__(self, bg_path: str, needle_path: str, parent=None):
        self.max_rpm = 8000
        self.start_angle = 270  # 6 o'clock
        self.sweep_angle = 279  # Clockwise sweep to ~10% past 3 o'clock
        super().__init__(bg_path, needle_path, parent)
    
    def set_rpm(self, rpm: float):
        """Update RPM"""
        self.target_value = max(0, min(rpm, self.max_rpm))
        self.update()
    
    def _get_needle_angle(self) -> float:
        """Calculate angle: 0 RPM at 6 o'clock, max at ~3:54"""
        fraction = self.value / self.max_rpm
        angle = self.start_angle - self.sweep_angle * fraction
        # Convert to standard rotation (counterclockwise positive)
        # PIL rotation: 0° = right, 90° = up, 180° = left, 270° = down
        return angle


class SpeedometerNeedle(NeedleGauge):
    """Speedometer with png needle (0-260 km/h)"""
    
    def __init__(self, bg_path: str, needle_path: str, parent=None):
        self.max_speed = 260
        self.start_angle = 240  # 8 o'clock
        self.sweep_angle = 300  # Clockwise sweep
        super().__init__(bg_path, needle_path, parent)
    
    def set_speed(self, speed: float):
        """Update speed"""
        self.target_value = max(0, min(speed, self.max_speed))
        self.update()
    
    def _get_needle_angle(self) -> float:
        """Calculate angle: 0 km/h at 8 o'clock"""
        fraction = self.value / self.max_speed
        angle = self.start_angle - self.sweep_angle * fraction
        return angle


class FuelNeedle(NeedleGauge):
    """Fuel gauge with png needle (E-F, 0-100%)"""
    
    def __init__(self, bg_path: str, needle_path: str, parent=None):
        self.start_angle = 180  # Empty at 9 o'clock (left)
        self.sweep_angle = 90   # Full at 12 o'clock (top)
        super().__init__(bg_path, needle_path, parent)
    
    def set_fuel(self, percentage: float):
        """Update fuel level (0-100)"""
        self.target_value = max(0, min(percentage, 100))
        self.update()
    
    def _get_needle_angle(self) -> float:
        """Calculate angle: E (empty) at 9 o'clock, F (full) at 12 o'clock"""
        fraction = self.target_value / 100
        angle = self.start_angle - self.sweep_angle * fraction
        return angle


class WaterTempNeedle(NeedleGauge):
    """Water temperature needle for fuel gauge (0-120°C)"""
    
    def __init__(self, bg_path: str, needle_path: str, parent=None):
        self.max_temp = 120
        self.start_angle = 180  # Start at 9 o'clock (left)
        self.sweep_angle = 90   # Sweep to 12 o'clock (top)
        super().__init__(bg_path, needle_path, parent)
    
    def set_temperature(self, temp: float):
        """Update temperature (0-120°C)"""
        self.target_value = max(0, min(temp, self.max_temp))
        self.update()
    
    def _get_needle_angle(self) -> float:
        """Calculate angle for temperature"""
        fraction = self.target_value / self.max_temp
        angle = self.start_angle - self.sweep_angle * fraction
        return angle
