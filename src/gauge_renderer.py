"""
Gauge Renderer - TRD/JDM Style Analog Gauges

Creates authentic TRD manual gauge appearance with thin needles.
Includes smooth interpolation for fluid needle movement and display
of temperature/boost on fuel gauge.
"""

import math
import logging
from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QPainter, QColor, QPen, QFont, QBrush, QPainterPath, QGraphicsDropShadowEffect
from PyQt5.QtCore import Qt, QPointF, QRectF, QSize

logger = logging.getLogger(__name__)


class BaseGauge(QWidget):
    """Base class for circular analog gauges"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.value = 0
        self.target_value = 0  # Target value to smoothly interpolate toward
        self.smoothing_factor = 0.2  # 0-1, higher = faster smoothing (0.2 = smooth but responsive)
        self.night_mode = False
        self.setMinimumSize(400, 400)
    
    def sizeHint(self):
        """Return preferred size for layout (1080x1080 matches actual displays)"""
        return QSize(1080, 1080)
    
    def _smooth_value(self):
        """Smoothly interpolate current value toward target value"""
        delta = self.target_value - self.value
        self.value += delta * self.smoothing_factor
    
    def _get_colors(self):
        """Get color scheme based on night mode"""
        if self.night_mode:
            return {
                'background': QColor(20, 20, 20),
                'face': QColor(30, 30, 30),
                'text': QColor(255, 255, 255),
                'needle': QColor(255, 255, 255),
                'tick_major': QColor(200, 200, 200),
                'tick_minor': QColor(100, 100, 100),
                'center': QColor(150, 150, 150)
            }
        else:
            return {
                'background': QColor(245, 235, 215),  # Cream/beige
                'face': QColor(245, 235, 215),
                'text': QColor(0, 0, 0),
                'needle': QColor(0, 0, 0),
                'tick_major': QColor(0, 0, 0),
                'tick_minor': QColor(80, 80, 80),
                'center': QColor(100, 100, 100)
            }
    
    def _draw_gauge_face(self, painter: QPainter, center: QPointF, radius: float):
        """Draw base gauge face with ticks"""
        colors = self._get_colors()
        
        # Draw gauge background
        painter.setBrush(QBrush(colors['face']))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(center, radius, radius)


class TachometerWidget(BaseGauge):
    """Tachometer gauge (0-8000 RPM)"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.max_rpm = 8000
        self.redline = 7000
    
    def set_rpm(self, rpm: float):
        """Update RPM value"""
        self.target_value = max(0, min(rpm, self.max_rpm))
        self.update()
    
    def paintEvent(self, event):
        """Render tachometer"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Smooth the value toward target
        self._smooth_value()
        
        colors = self._get_colors()
        center = QPointF(self.width() / 2, self.height() / 2)
        radius = min(self.width(), self.height()) / 2 - 20
        
        # Draw gauge face
        self._draw_gauge_face(painter, center, radius)
        
        # Draw tick marks and numbers
        self._draw_ticks(painter, center, radius, colors)
        
        # Draw redline zone
        self._draw_redline(painter, center, radius, colors)
        
        # Draw needle
        self._draw_needle(painter, center, radius, colors)
        
        # Draw center cap
        painter.setBrush(QBrush(colors['center']))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(center, 10, 10)
    
    def _draw_ticks(self, painter: QPainter, center: QPointF, radius: float, colors: dict):
        """Draw tick marks and RPM numbers"""
        # Clockwise sweep: 0 RPM at 6 o'clock (270°), max RPM 10% past 3 o'clock
        start_angle = 270  # 6 o'clock position
        sweep_angle = 279  # 279° clockwise sweep (ends 10% past 3 o'clock)
        
        for rpm in range(0, self.max_rpm + 1, 1000):
            angle_fraction = rpm / self.max_rpm
            angle = start_angle - sweep_angle * angle_fraction  # Subtract for clockwise
            rad = math.radians(angle)
            
            tick_start = QPointF(
                center.x() + (radius - 20) * math.cos(rad),
                center.y() + (radius - 20) * math.sin(rad)
            )
            tick_end = QPointF(
                center.x() + radius * math.cos(rad),
                center.y() + radius * math.sin(rad)
            )
            
            pen = QPen(colors['tick_major'], 2)
            painter.setPen(pen)
            painter.drawLine(tick_start, tick_end)
            
            # Draw number
            painter.setFont(QFont('Arial', 10))
            number_distance = radius - 50
            number_x = center.x() + number_distance * math.cos(rad)
            number_y = center.y() + number_distance * math.sin(rad)
            painter.drawText(int(number_x - 10), int(number_y + 5), 20, 15, Qt.AlignCenter, str(rpm // 1000))
    
    def _draw_redline(self, painter: QPainter, center: QPointF, radius: float, colors: dict):
        """Draw redline zone"""
        start_angle = 270  # 6 o'clock
        sweep_angle = 279  # 279° clockwise sweep (ends 10% past 3 o'clock)
        
        redline_start_fraction = self.redline / self.max_rpm
        redline_start_angle = start_angle - sweep_angle * redline_start_fraction
        end_angle = start_angle - sweep_angle  # Full sweep end
        
        # Draw red arc from redline to max (clockwise)
        redline_pen = QPen(QColor(255, 0, 0), 8)
        painter.setPen(redline_pen)
        
        rect = QRectF(center.x() - radius, center.y() - radius, radius * 2, radius * 2)
        # Arc angles: startAngle and spanAngle (negative span = clockwise)
        span_angle = end_angle - redline_start_angle
        painter.drawArc(rect, int(redline_start_angle * 16), int(span_angle * 16))
    
    def _draw_needle(self, painter: QPainter, center: QPointF, radius: float, colors: dict):
        """Draw RPM needle with optional glow in night mode"""
        # Clockwise sweep from 6 o'clock (270°) to 10% past 3 o'clock (351°)
        start_angle = 270
        sweep_angle = 279
        
        angle_fraction = self.value / self.max_rpm
        angle = start_angle - sweep_angle * angle_fraction
        rad = math.radians(angle)
        
        # NEEDLE SIZE: Change needle_length for length, pen width (below) for thickness
        needle_length = radius - 40  # Distance from center to needle tip
        needle_end = QPointF(
            center.x() + needle_length * math.cos(rad),
            center.y() + needle_length * math.sin(rad)
        )
        
        # Draw glow effect in night mode
        if self.night_mode:
            for glow_width in [8, 6, 4]:
                glow_alpha = 80 - (8 - glow_width) * 15  # Fade out the glow layers
                glow_color = QColor(colors['needle'].red(), colors['needle'].green(), colors['needle'].blue(), glow_alpha)
                glow_pen = QPen(glow_color, glow_width)
                painter.setPen(glow_pen)
                painter.drawLine(center, needle_end)
        
        # NEEDLE THICKNESS: Change the '2' to make needle thicker/thinner
        pen = QPen(colors['needle'], 2)
        painter.setPen(pen)
        painter.drawLine(center, needle_end)


class SpeedometerWidget(BaseGauge):
    """Speedometer gauge (0-260 km/h)"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.max_speed = 260
    
    def set_speed(self, speed: float):
        """Update speed value"""
        self.target_value = max(0, min(speed, self.max_speed))
        self.update()
    
    def paintEvent(self, event):
        """Render speedometer"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Smooth the value toward target
        self._smooth_value()
        
        colors = self._get_colors()
        center = QPointF(self.width() / 2, self.height() / 2)
        radius = min(self.width(), self.height()) / 2 - 20
        
        # Draw gauge face
        self._draw_gauge_face(painter, center, radius)
        
        # Draw tick marks and numbers
        self._draw_ticks_speed(painter, center, radius, colors)
        
        # Draw needle
        self._draw_needle_speed(painter, center, radius, colors)
        
        # Draw center cap
        painter.setBrush(QBrush(colors['center']))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(center, 10, 10)
    
    def _draw_ticks_speed(self, painter: QPainter, center: QPointF, radius: float, colors: dict):
        """Draw tick marks and speed numbers (0-260 km/h)"""
        # Clockwise sweep: 0 km/h at 8 o'clock (240°), sweeping clockwise
        start_angle = 240  # 8 o'clock position
        sweep_angle = 300  # 300° clockwise sweep (ends ~7 o'clock after going around)
        
        for speed in range(0, int(self.max_speed) + 1, 20):
            angle_fraction = speed / self.max_speed
            angle = start_angle - sweep_angle * angle_fraction  # Subtract for clockwise
            rad = math.radians(angle)
            
            # Major tick every 40 km/h
            is_major = (speed % 40) == 0
            tick_length = 30 if is_major else 15
            tick_width = 3 if is_major else 1
            
            tick_start = QPointF(
                center.x() + (radius - tick_length) * math.cos(rad),
                center.y() + (radius - tick_length) * math.sin(rad)
            )
            tick_end = QPointF(
                center.x() + radius * math.cos(rad),
                center.y() + radius * math.sin(rad)
            )
            
            painter.setPen(QPen(colors['tick_major'] if is_major else colors['tick_minor'], tick_width))
            painter.drawLine(tick_start, tick_end)
            
            # Draw number for major ticks
            if is_major:
                painter.setFont(QFont('Arial', 9))
                number_distance = radius - 50
                number_x = center.x() + number_distance * math.cos(rad)
                number_y = center.y() + number_distance * math.sin(rad)
                painter.drawText(int(number_x - 15), int(number_y + 5), 30, 15, Qt.AlignCenter, str(speed))
    
    def _draw_needle_speed(self, painter: QPainter, center: QPointF, radius: float, colors: dict):
        """Draw speed needle with optional glow in night mode"""
        # Clockwise sweep from 8 o'clock (240°)
        start_angle = 240
        sweep_angle = 300  # 300° clockwise sweep
        
        angle_fraction = self.value / self.max_speed
        angle = start_angle - sweep_angle * angle_fraction
        rad = math.radians(angle)
        
        # NEEDLE SIZE: Change needle_length for length, pen width (below) for thickness
        needle_length = radius - 40  # Distance from center to needle tip
        needle_end = QPointF(
            center.x() + needle_length * math.cos(rad),
            center.y() + needle_length * math.sin(rad)
        )
        
        # Draw glow effect in night mode
        if self.night_mode:
            for glow_width in [8, 6, 4]:
                glow_alpha = 80 - (8 - glow_width) * 15  # Fade out the glow layers
                glow_color = QColor(colors['needle'].red(), colors['needle'].green(), colors['needle'].blue(), glow_alpha)
                glow_pen = QPen(glow_color, glow_width)
                painter.setPen(glow_pen)
                painter.drawLine(center, needle_end)
        
        # NEEDLE THICKNESS: Change the '2' to make needle thicker/thinner
        pen = QPen(colors['needle'], 2)
        painter.setPen(pen)
        painter.drawLine(center, needle_end)


class FuelGaugeWidget(BaseGauge):
    """Fuel level gauge (E-F, 0-100%) with temperature and boost display"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # Value is percentage (0-100)
        self.temperature = 80
        self.boost = 0.0
    
    def set_fuel(self, percentage: float):
        """Update fuel level"""
        self.target_value = max(0, min(percentage, 100))
        self.update()
    
    def set_temperature(self, temp: float):
        """Update coolant temperature"""
        self.temperature = max(0, min(temp, 120))
    
    def set_boost(self, boost: float):
        """Update boost pressure"""
        self.boost = max(0, min(boost, 2.5))
    
    def paintEvent(self, event):
        """Render fuel gauge"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Smooth the value toward target
        self._smooth_value()
        
        colors = self._get_colors()
        center = QPointF(self.width() / 2, self.height() / 2)
        radius = min(self.width(), self.height()) / 2 - 20
        
        # Draw gauge face
        self._draw_gauge_face(painter, center, radius)
        
        # Draw E and F marks
        self._draw_fuel_labels(painter, center, radius, colors)
        
        # Draw needle
        self._draw_needle_fuel(painter, center, radius, colors)
        
        # Draw temperature and boost text
        self._draw_info_text(painter, center, colors)
        
        # Draw center cap
        painter.setBrush(QBrush(colors['center']))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(center, 8, 8)
    
    def _draw_fuel_labels(self, painter: QPainter, center: QPointF, radius: float, colors: dict):
        """Draw E (empty) and F (full) labels"""
        # Fuel gauge typically uses 90 degree sweep (left to right)
        left_angle = 180  # E (empty) on left
        right_angle = 90  # F (full) on right
        
        # Draw E (empty) label
        e_rad = math.radians(left_angle)
        e_pos = QPointF(
            center.x() + (radius - 60) * math.cos(e_rad),
            center.y() + (radius - 60) * math.sin(e_rad)
        )
        painter.setPen(colors['text'])
        painter.setFont(QFont('Arial', 16, QFont.Bold))
        painter.drawText(int(e_pos.x() - 10), int(e_pos.y() + 5), "E")
        
        # Draw F (full) label
        f_rad = math.radians(right_angle)
        f_pos = QPointF(
            center.x() + (radius - 60) * math.cos(f_rad),
            center.y() + (radius - 60) * math.sin(f_rad)
        )
        painter.drawText(int(f_pos.x() - 10), int(f_pos.y() + 5), "F")
        
        # Draw tick marks at E and F
        for angle in [left_angle, right_angle]:
            rad = math.radians(angle)
            tick_start = QPointF(
                center.x() + (radius - 30) * math.cos(rad),
                center.y() + (radius - 30) * math.sin(rad)
            )
            tick_end = QPointF(
                center.x() + radius * math.cos(rad),
                center.y() + radius * math.sin(rad)
            )
            pen = QPen(colors['tick_major'], 3)
            painter.setPen(pen)
            painter.drawLine(tick_start, tick_end)
    
    def _draw_needle_fuel(self, painter: QPainter, center: QPointF, radius: float, colors: dict):
        """Draw fuel gauge needle with optional glow in night mode"""
        # 90 degree sweep from E (180°) to F (90°)
        left_angle = 180
        right_angle = 90
        
        angle_fraction = self.value / 100  # percentage to fraction
        angle = left_angle + (right_angle - left_angle) * angle_fraction
        rad = math.radians(angle)
        
        needle_length = radius - 30
        needle_end = QPointF(
            center.x() + needle_length * math.cos(rad),
            center.y() + needle_length * math.sin(rad)
        )
        
        # Draw glow effect in night mode
        if self.night_mode:
            for glow_width in [8, 6, 4]:
                glow_alpha = 80 - (8 - glow_width) * 15  # Fade out the glow layers
                glow_color = QColor(colors['needle'].red(), colors['needle'].green(), colors['needle'].blue(), glow_alpha)
                glow_pen = QPen(glow_color, glow_width)
                painter.setPen(glow_pen)
                painter.drawLine(center, needle_end)
        
        pen = QPen(colors['needle'], 3)
        painter.setPen(pen)
        painter.drawLine(center, needle_end)
    
    def _draw_info_text(self, painter: QPainter, center: QPointF, colors: dict):
        """Draw temperature and boost information"""
        painter.setPen(QPen(colors['text']))
        painter.setFont(QFont('Arial', 10))
        
        # Temperature display (top)
        temp_text = f"T:{int(self.temperature)}°C"
        painter.drawText(int(center.x() - 40), int(center.y() - 50), 80, 25, Qt.AlignCenter, temp_text)
        
        # Boost display (slightly below temperature)
        boost_text = f"B:{self.boost:.1f}bar"
        painter.drawText(int(center.x() - 40), int(center.y() - 20), 80, 25, Qt.AlignCenter, boost_text)
