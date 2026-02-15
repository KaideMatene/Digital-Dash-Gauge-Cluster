"""
Display Manager - Multi-Screen Layout

Manages 3x round displays with gauge positioning.
Supports both vector-based and image-based gauges.
"""

import logging
import os
from pathlib import Path
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt, QRect
from PyQt5.QtGui import QScreen

# Vector gauges (always available)
try:
    from gauge_renderer import TachometerWidget, SpeedometerWidget, FuelGaugeWidget
except ImportError:
    from .gauge_renderer import TachometerWidget, SpeedometerWidget, FuelGaugeWidget

# Image-based gauges (optional)
try:
    from image_gauge import ImageTachometer, ImageSpeedometer, ImageFuelGauge
    IMAGE_GAUGES_AVAILABLE = True
except ImportError:
    try:
        from .image_gauge import ImageTachometer, ImageSpeedometer, ImageFuelGauge
        IMAGE_GAUGES_AVAILABLE = True
    except ImportError:
        IMAGE_GAUGES_AVAILABLE = False

logger = logging.getLogger(__name__)


class DisplayManager(QWidget):
    """Manages layout across 3 displays"""
    
    def __init__(self, use_images: bool = True, scale: float = 0.3):
        super().__init__()
        self.use_images = use_images
        self.scale = scale  # Scale factor (0.3 = 30%, 1.0 = 100%)
        self.brightness = 100  # Screen brightness 0-100
        self.setWindowTitle("Supra Digital Cluster")
        
        # Get project root path
        self.project_root = Path(__file__).parent.parent
        self.gauges_dir = self.project_root / "gauges"
        
        # Check if images exist and use them if available
        if self.use_images and IMAGE_GAUGES_AVAILABLE and self.gauges_dir.exists():
            self._init_image_gauges()
        else:
            self._init_vector_gauges()
        
        # Create indicator labels
        self.high_beam_indicator = QLabel("💡")  # High beam icon
        self.warning_indicator = QLabel("⚠")     # Warning icon
        
        self._setup_layout()
        self._setup_displays()
        
        logger.info("Display manager initialized")
    
    def _init_vector_gauges(self):
        """Initialize vector-based gauges (default)"""
        self.tachometer = TachometerWidget()
        self.speedometer = SpeedometerWidget()
        self.fuel_gauge = FuelGaugeWidget()
        logger.info("📊 Using vector-based gauges")
    
    def _init_image_gauges(self):
        """Initialize image-based gauges if images exist"""
        tach_path = self.gauges_dir / "tachometer_bg.png"
        speed_path = self.gauges_dir / "speedometer_bg.png"
        fuel_path = self.gauges_dir / "fuel_bg.png"
        
        logger.info(f"🔍 Looking for gauge images in: {self.gauges_dir}")
        logger.info(f"   Tachometer: {tach_path} - {'✓ Found' if tach_path.exists() else '✗ Missing'}")
        logger.info(f"   Speedometer: {speed_path} - {'✓ Found' if speed_path.exists() else '✗ Missing'}")
        logger.info(f"   Fuel: {fuel_path} - {'✓ Found' if fuel_path.exists() else '✗ Missing'}")
        
        # Check if all images exist
        if tach_path.exists() and speed_path.exists() and fuel_path.exists():
            try:
                if not IMAGE_GAUGES_AVAILABLE:
                    logger.warning("Image gauge module not available, falling back to vector")
                    self._init_vector_gauges()
                    return
                
                self.tachometer = ImageTachometer(str(tach_path))
                self.speedometer = ImageSpeedometer(str(speed_path))
                self.fuel_gauge = ImageFuelGauge(str(fuel_path))
                logger.info("🎨 Using image-based gauges")
            except Exception as e:
                logger.warning(f"Failed to load image gauges: {e}, falling back to vector")
                import traceback
                logger.warning(traceback.format_exc())
                self._init_vector_gauges()
        else:
            logger.info("📁 Gauge images not found in gauges/ folder")
            logger.info("   To create them, run: python create_gauge_images.py")
            self._init_vector_gauges()
    
    def _setup_layout(self):
        """Configure widget layout"""
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Set sizes to match actual 1080x1080 displays (scaled)
        gauge_size = int(1080 * self.scale)
        self.tachometer.setMinimumSize(gauge_size, gauge_size)
        self.tachometer.setMaximumSize(gauge_size, gauge_size)
        self.speedometer.setMinimumSize(gauge_size, gauge_size)
        self.speedometer.setMaximumSize(gauge_size, gauge_size)
        self.fuel_gauge.setMinimumSize(gauge_size, gauge_size)
        self.fuel_gauge.setMaximumSize(gauge_size, gauge_size)
        
        # Left display: Tachometer
        layout.addWidget(self.tachometer, 1)
        
        # Center display: Speedometer with warning light on top
        center_layout = QVBoxLayout()
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)
        self.warning_indicator.setStyleSheet("QLabel { font-size: 24px; text-align: center; color: yellow; }")
        center_layout.addWidget(self.warning_indicator, 0, Qt.AlignHCenter)
        center_layout.addWidget(self.speedometer, 1)
        layout.addLayout(center_layout, 1)
        
        # Right display: Fuel + high beam at top right
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        self.high_beam_indicator.setStyleSheet("QLabel { font-size: 20px; color: cyan; }")
        right_layout.addWidget(self.high_beam_indicator, 0, Qt.AlignRight)
        right_layout.addWidget(self.fuel_gauge, 1)
        layout.addLayout(right_layout, 1)
        
        self.setLayout(layout)
    
    def _setup_displays(self):
        """Configure window to span multiple displays"""
        # TODO: Implement proper multi-display spanning
        # This requires detecting 3 displays and positioning windows correctly
        
        # For development: single window fullscreen
        # self.showFullScreen()
        pass
    
    def update_scale(self, gauge_size: int):
        """Update gauge sizes dynamically (called when window is resized)"""
        self.tachometer.setMinimumSize(gauge_size, gauge_size)
        self.tachometer.setMaximumSize(gauge_size, gauge_size)
        self.speedometer.setMinimumSize(gauge_size, gauge_size)
        self.speedometer.setMaximumSize(gauge_size, gauge_size)
        self.fuel_gauge.setMinimumSize(gauge_size, gauge_size)
        self.fuel_gauge.setMaximumSize(gauge_size, gauge_size)
        self.update()
    
    def update_gauges(self, rpm: float, speed: float, coolant_temp: float,
                     boost: float, fuel: float, night_mode: bool,
                     high_beam: bool, warning: bool, brightness: int):
        """
        Update all gauges with latest data
        
        Args:
            rpm: Engine RPM (0-8000)
            speed: Vehicle speed km/h (0-260)
            coolant_temp: Coolant temperature °C (0-120)
            boost: Boost pressure PSI
            fuel: Fuel level percentage (0-100)
            night_mode: Night mode active
            high_beam: High beam indicator
            warning: Warning light active
            brightness: Screen brightness percentage (0-100)
        """
        # Update gauge values
        self.tachometer.set_rpm(rpm)
        self.speedometer.set_speed(speed)
        self.fuel_gauge.set_fuel(fuel)
        
        # Update fuel gauge with temperature and boost
        self.fuel_gauge.set_temperature(coolant_temp)
        self.fuel_gauge.set_boost(boost)
        
        # Update night mode
        self.tachometer.night_mode = night_mode
        self.speedometer.night_mode = night_mode
        self.fuel_gauge.night_mode = night_mode
        
        # Update indicators (only show when active)
        self.high_beam_indicator.setVisible(high_beam)
        self.warning_indicator.setVisible(warning)
        
        # Update brightness
        self.brightness = brightness
        self._apply_brightness()
        
        # Force repaint
        self.update()
    
    def _apply_brightness(self):
        """Apply brightness dimming to display"""
        # Calculate opacity based on brightness percentage
        # At 100% brightness = full opacity
        # At 20% brightness = 0.2 opacity with dark overlay
        if self.brightness < 100:
            opacity = self.brightness / 100.0
            self.setWindowOpacity(opacity)
        else:
            self.setWindowOpacity(1.0)
    
    def show(self):
        """Show the display manager"""
        super().show()
        logger.info("Display manager shown")
