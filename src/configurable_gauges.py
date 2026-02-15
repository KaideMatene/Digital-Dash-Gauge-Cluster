"""
Configurable Gauge Rendering

Renders gauges based on configuration objects instead of hardcoded values.
Supports multiple needles per gauge and 3D needle styles.
Displays background images for visual alignment.
"""

import math
import logging
from pathlib import Path
from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QPainter, QColor, QPen, QFont, QBrush, QPainterPath, QPolygonF, QPixmap
from PyQt5.QtCore import Qt, QPointF, QRectF, QSize, QTimer

from src.gauge_config import GaugeConfig, NeedleConfig

logger = logging.getLogger(__name__)


class ConfigurableGauge(QWidget):
    """Gauge rendered from configuration"""
    
    def __init__(self, config: GaugeConfig, parent=None, gauge_image_name: str = None):
        super().__init__(parent)
        self.config = config
        self.value = config.min_value
        self.night_mode = False
        self.setMinimumSize(400, 400)
        
        # Try to load background image
        self.bg_pixmap = None
        if gauge_image_name:
            self._load_background_image(gauge_image_name)
    
    def sizeHint(self):
        return QSize(1080, 1080)
    
    def _load_background_image(self, image_name: str):
        """Load background image from gauges/ folder"""
        try:
            # Look for image in gauges/ folder
            gauge_dir = Path(__file__).parent.parent / "gauges"
            image_path = gauge_dir / image_name
            
            if image_path.exists():
                self.bg_pixmap = QPixmap(str(image_path))
                if not self.bg_pixmap.isNull():
                    logger.info(f"✅ Loaded background image for tuner: {image_name}")
                else:
                    logger.warning(f"⚠️ Failed to load image: {image_path}")
                    self.bg_pixmap = None
            else:
                logger.debug(f"📁 Image not found: {image_path}")
        except Exception as e:
            logger.warning(f"Error loading background image: {e}")
            self.bg_pixmap = None
    
    def set_value(self, value: float):
        """Update the gauge value"""
        self.value = max(self.config.min_value, min(value, self.config.max_value))
        self.update()
    
    def set_needle_value(self, needle_name: str, value: float):
        """Update a specific needle's value"""
        # Store needle-specific values
        if not hasattr(self, 'needle_values'):
            self.needle_values = {}
        
        value = max(self.config.min_value, min(value, self.config.max_value))
        self.needle_values[needle_name] = value
        self.update()
    
    def _get_needle_value(self, needle_name: str) -> float:
        """Get a needle's current value"""
        if not hasattr(self, 'needle_values'):
            self.needle_values = {}
        
        if needle_name == "main":
            return self.value
        
        return self.needle_values.get(needle_name, self.config.min_value)
    
    def paintEvent(self, event):
        """Render the gauge"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        color_scheme = self._get_colors()
        center = QPointF(self.width() / 2, self.height() / 2)
        radius = min(self.width(), self.height()) / 2 - 20
        
        # Draw background (image or solid color)
        if self.bg_pixmap and not self.bg_pixmap.isNull():
            # Draw background image (stretched to fill)
            painter.drawPixmap(self.rect(), self.bg_pixmap)
        else:
            # Draw solid color background
            painter.setBrush(QBrush(color_scheme['background']))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(center, radius, radius)
        
        # Draw ticks and numbers (only if no image)
        if not self.bg_pixmap or self.bg_pixmap.isNull():
            self._draw_ticks(painter, center, radius, color_scheme)
        
        # Draw each needle
        for needle_name, needle_config in self.config.needles.items():
            if needle_config.enabled:
                value = self._get_needle_value(needle_name)
                self._draw_needle(painter, center, radius, needle_config, value, color_scheme)
    
    def _get_colors(self):
        """Get color scheme"""
        if self.night_mode:
            return {
                'background': QColor(self.config.night_mode_bg_r, self.config.night_mode_bg_g, self.config.night_mode_bg_b),
                'text': QColor(self.config.night_mode_text_r, self.config.night_mode_text_g, self.config.night_mode_text_b),
                'tick': QColor(200, 200, 200),
            }
        else:
            return {
                'background': QColor(self.config.background_color_r, self.config.background_color_g, self.config.background_color_b),
                'text': QColor(0, 0, 0),
                'tick': QColor(0, 0, 0),
            }
    
    def _draw_ticks(self, painter: QPainter, center: QPointF, radius: float, colors: dict):
        """Draw tick marks"""
        if not self.config.show_numbers:
            return
        
        step = (self.config.max_value - self.config.min_value) / 10  # 10 divisions
        for i in range(11):
            value = self.config.min_value + i * step
            fraction = (value - self.config.min_value) / (self.config.max_value - self.config.min_value)
            angle = self.config.start_angle - self.config.sweep_angle * fraction
            rad = math.radians(angle)
            
            # Draw tick
            tick_start = QPointF(
                center.x() + (radius - 20) * math.cos(rad),
                center.y() + (radius - 20) * math.sin(rad)
            )
            tick_end = QPointF(
                center.x() + radius * math.cos(rad),
                center.y() + radius * math.sin(rad)
            )
            
            painter.setPen(QPen(colors['tick'], 2))
            painter.drawLine(tick_start, tick_end)
            
            # Draw number
            if self.config.number_interval > 0 and int(value) % self.config.number_interval == 0:
                painter.setFont(QFont('Arial', self.config.text_size))
                painter.setPen(colors['text'])
                number_distance = radius - 50
                number_x = center.x() + number_distance * math.cos(rad)
                number_y = center.y() + number_distance * math.sin(rad)
                painter.drawText(int(number_x - 15), int(number_y + 5), 30, 15, Qt.AlignCenter, str(int(value)))
    
    def _draw_needle(self, painter: QPainter, center: QPointF, radius: float, 
                     needle_config: NeedleConfig, value: float, colors: dict):
        """Draw a single needle based on configuration"""
        
        # Calculate angle for this value
        fraction = (value - self.config.min_value) / (self.config.max_value - self.config.min_value)
        angle = self.config.start_angle - self.config.sweep_angle * fraction
        rad = math.radians(angle)
        
        # Needle color
        needle_color = QColor(needle_config.color_r, needle_config.color_g, needle_config.color_b)
        
        if needle_config.style == "3d_pointer":
            self._draw_3d_pointer_needle(painter, center, radius, rad, needle_config, needle_color)
        elif needle_config.style == "arrow":
            self._draw_arrow_needle(painter, center, radius, rad, needle_config, needle_color)
        else:  # "line"
            self._draw_line_needle(painter, center, radius, rad, needle_config, needle_color)
    
    def _draw_line_needle(self, painter: QPainter, center: QPointF, radius: float,
                          rad: float, config: NeedleConfig, color: QColor):
        """Draw simple line needle"""
        needle_length = radius - config.length_offset
        needle_end = QPointF(
            center.x() + needle_length * math.cos(rad),
            center.y() + needle_length * math.sin(rad)
        )
        
        pen = QPen(color, config.thickness)
        painter.setPen(pen)
        painter.drawLine(center, needle_end)
    
    def _draw_3d_pointer_needle(self, painter: QPainter, center: QPointF, radius: float,
                                rad: float, config: NeedleConfig, color: QColor):
        """Draw 3D-style tapered pointer needle"""
        needle_length = radius - config.length_offset
        needle_width = 8  # Width at base
        
        # Tip position
        tip_x = center.x() + needle_length * math.cos(rad)
        tip_y = center.y() + needle_length * math.sin(rad)
        
        # Perpendicular angle for needle base width
        perp_rad = rad + math.radians(90)
        base_half_width = needle_width / 2
        
        # Create triangle
        poly = QPolygonF([
            QPointF(tip_x, tip_y),  # Tip
            QPointF(center.x() + base_half_width * math.cos(perp_rad),
                   center.y() + base_half_width * math.sin(perp_rad)),  # Base corner 1
            QPointF(center.x() - base_half_width * math.cos(perp_rad),
                   center.y() - base_half_width * math.sin(perp_rad))   # Base corner 2
        ])
        
        # Draw with gradient effect (darken edges)
        painter.setBrush(QBrush(color))
        painter.setPen(QPen(color.darker(120), 0.5))
        painter.drawPolygon(poly)
    
    def _draw_arrow_needle(self, painter: QPainter, center: QPointF, radius: float,
                          rad: float, config: NeedleConfig, color: QColor):
        """Draw arrow-style needle"""
        needle_length = radius - config.length_offset
        
        # Main needle line
        needle_end = QPointF(
            center.x() + needle_length * math.cos(rad),
            center.y() + needle_length * math.sin(rad)
        )
        
        # Arrow head
        arrow_size = 15
        perp_rad = rad + math.radians(90)
        
        left_point = QPointF(
            needle_end.x() - arrow_size * math.cos(rad) - arrow_size/2 * math.cos(perp_rad),
            needle_end.y() - arrow_size * math.sin(rad) - arrow_size/2 * math.sin(perp_rad)
        )
        right_point = QPointF(
            needle_end.x() - arrow_size * math.cos(rad) + arrow_size/2 * math.cos(perp_rad),
            needle_end.y() - arrow_size * math.sin(rad) + arrow_size/2 * math.sin(perp_rad)
        )
        
        # Draw arrow polygon
        arrow = QPolygonF([needle_end, left_point, right_point])
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.NoPen)
        painter.drawPolygon(arrow)


class ConfigurableGaugeWidget(QWidget):
    """Widget displaying all 3 gauges with live config updates"""
    
    def __init__(self, tach_config: GaugeConfig, speed_config: GaugeConfig, fuel_config: GaugeConfig, parent=None):
        super().__init__(parent)
        
        # Create gauges with background images for visual alignment
        self.tach_gauge = ConfigurableGauge(tach_config, gauge_image_name="tachometer_bg.png")
        self.speed_gauge = ConfigurableGauge(speed_config, gauge_image_name="speedometer_bg.png")
        self.fuel_gauge = ConfigurableGauge(fuel_config, gauge_image_name="fuel_bg.png")
        
        # Setup layout (3 gauges side by side)
        from PyQt5.QtWidgets import QHBoxLayout
        layout = QHBoxLayout()
        layout.addWidget(self.tach_gauge)
        layout.addWidget(self.speed_gauge)
        layout.addWidget(self.fuel_gauge)
        self.setLayout(layout)
        
        # Simulation timer (update gauges with test data)
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_simulation)
        self.timer.start(50)  # 20 Hz update
        
        self.frame = 0
    
    def update_configs(self, tach_config: GaugeConfig, speed_config: GaugeConfig, fuel_config: GaugeConfig):
        """Update gauge configurations"""
        self.tach_gauge.config = tach_config
        self.speed_gauge.config = speed_config
        self.fuel_gauge.config = fuel_config
        
        self.tach_gauge.update()
        self.speed_gauge.update()
        self.fuel_gauge.update()
    
    def _update_simulation(self):
        """Simulate changing values"""
        self.frame += 1
        
        # Tachometer: oscillating RPM
        rpm = 3000 + 2000 * math.sin(self.frame * 0.02)
        self.tach_gauge.set_value(rpm)
        
        # Speedometer: gradually increasing
        speed = 50 + 80 * (math.sin(self.frame * 0.015) + 1) / 2
        self.speed_gauge.set_value(speed)
        
        # Fuel: steady with slow drain
        fuel = 80 - (self.frame % 3000) / 30
        self.fuel_gauge.set_value(fuel)
        
        # Water temp on fuel gauge (second needle)
        water_temp = 70 + 30 * (math.sin(self.frame * 0.01) + 1) / 2
        self.fuel_gauge.set_needle_value("water", water_temp)
