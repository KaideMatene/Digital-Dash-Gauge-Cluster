"""
Interactive Gauge Calibrator

Point-and-click interface to:
- Set needle rotation center on needle.png
- Configure start/end positions
- Add multiple calibration points for accurate scaling
- Save calibration data to gauge configs
"""

import json
import logging
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Tuple
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QSpinBox, QDoubleSpinBox, QPushButton, QTableWidget, 
    QTableWidgetItem, QFileDialog, QMessageBox, QTabWidget, QGroupBox,
    QFrame, QComboBox
)
from PyQt5.QtGui import QPixmap, QImage, QColor, QPainter, QFont, QPen
from PyQt5.QtCore import Qt, QPoint, QRect
from PIL import Image

logger = logging.getLogger(__name__)


@dataclass
class CalibrationPoint:
    """Stores a calibration point (value -> angle mapping)"""
    value: float  # RPM, km/h, %, °C, etc.
    angle: float  # Rotation angle in degrees
    
    def to_dict(self):
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


@dataclass
class GaugeCalibration:
    """Calibration data for a single needle"""
    needle_id: str
    gauge_name: str
    needle_image_path: str
    rotation_center_x: float = 0  # Pixel coordinates on needle image
    rotation_center_y: float = 0
    start_value: float = 0  # Starting value (0 for RPM/speed, 50 for water, "E" for fuel)
    start_angle: float = 270  # Starting angle
    end_value: float = 10000  # Ending value
    end_angle: float = 0  # Ending angle
    calibration_points: List[CalibrationPoint] = field(default_factory=list)
    
    def to_dict(self):
        data = asdict(self)
        data['calibration_points'] = [p.to_dict() for p in self.calibration_points]
        return data
    
    @classmethod
    def from_dict(cls, data: dict):
        points = data.pop('calibration_points', [])
        calib = cls(**data)
        calib.calibration_points = [CalibrationPoint.from_dict(p) for p in points]
        return calib


class NeedleImageWidget(QFrame):
    """Widget to display background and needle images with rotation center clicks"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.background_image = None
        self.original_pixmap = None
        self.scaled_pixmap = None
        self.rotation_center = None
        self.calibration_points_display = []
        self.setMinimumSize(400, 400)
        self.setStyleSheet("border: 2px solid #333;")
        self.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        
    def load_image(self, image_path: str):
        """Load needle image"""
        try:
            if not Path(image_path).exists():
                self.original_pixmap = None
                self.update()
                return False
            
            pil_image = Image.open(image_path).convert("RGBA")
            self.original_pixmap = pil_image
            self._scale_and_display()
            return True
        except Exception as e:
            logger.error(f"Error loading image: {e}")
            return False
    
    def load_background(self, image_path: str):
        """Load background image (optional)"""
        try:
            if not Path(image_path).exists():
                self.background_image = None
                self._scale_and_display()
                return False
            
            pil_image = Image.open(image_path).convert("RGBA")
            self.background_image = pil_image
            self._scale_and_display()
            return True
        except Exception as e:
            logger.debug(f"No background image found: {e}")
            self.background_image = None
            return False
    
    def _composite_images(self):
        """Composite background and needle images"""
        if self.background_image and self.original_pixmap:
            # Use background as base, needle on top
            composite = self.background_image.copy()
            composite.paste(self.original_pixmap, (0, 0), self.original_pixmap)
            return composite
        elif self.original_pixmap:
            return self.original_pixmap
        elif self.background_image:
            return self.background_image
        return None
    
    def _scale_and_display(self):
        """Scale images to fit widget"""
        image_to_display = self._composite_images()
        if not image_to_display:
            return
        
        # Scale image to widget size
        display_size = min(self.width() - 4, self.height() - 4)
        pil_scaled = image_to_display.resize(
            (display_size, display_size), 
            Image.Resampling.LANCZOS
        )
        
        # Convert to QPixmap
        qimg = QImage(pil_scaled.tobytes(), pil_scaled.width, pil_scaled.height, 
                      QImage.Format_RGBA8888)
        self.scaled_pixmap = QPixmap.fromImage(qimg)
        
        # Scale rotation center if it exists (use original needle for reference)
        needle = self.original_pixmap if self.original_pixmap else self.background_image
        if self.rotation_center and needle:
            scale_factor = display_size / max(needle.size)
            self._scaled_center = (
                int(self.rotation_center[0] * scale_factor) + 2,
                int(self.rotation_center[1] * scale_factor) + 2
            )
        
        self.update()
    
    def resizeEvent(self, event):
        """Handle resize"""
        super().resizeEvent(event)
        self._scale_and_display()
    
    def mousePressEvent(self, event):
        """Handle mouse click to set rotation center"""
        if not self.original_pixmap:
            return
        
        # Get click position in scaled image coordinates
        click_x = event.x() - 2  # Account for border
        click_y = event.y() - 2
        
        # Calculate scale factor
        display_size = min(self.width() - 4, self.height() - 4)
        scale_factor = max(self.original_pixmap.size) / display_size
        
        # Convert to original image coordinates
        orig_x = int(click_x * scale_factor)
        orig_y = int(click_y * scale_factor)
        
        # Clamp to image bounds
        orig_x = max(0, min(orig_x, self.original_pixmap.width - 1))
        orig_y = max(0, min(orig_y, self.original_pixmap.height - 1))
        
        self.rotation_center = (orig_x, orig_y)
        self._scale_and_display()
        
        # Notify parent
        if hasattr(self.parent(), 'on_rotation_center_set'):
            self.parent().on_rotation_center_set(orig_x, orig_y)
    
    def set_rotation_center(self, x: float, y: float):
        """Set rotation center programmatically"""
        self.rotation_center = (x, y)
        self._scale_and_display()
    
    def paintEvent(self, event):
        """Paint the image and overlay markers"""
        super().paintEvent(event)
        
        if not self.scaled_pixmap:
            return
        
        painter = QPainter(self)
        
        # Draw scaled image
        painter.drawPixmap(2, 2, self.scaled_pixmap)
        
        # Draw rotation center marker
        if hasattr(self, '_scaled_center'):
            painter.setPen(QPen(QColor(255, 0, 0), 3))
            cx, cy = self._scaled_center
            size = 15
            painter.drawLine(cx - size, cy, cx + size, cy)
            painter.drawLine(cx, cy - size, cx, cy + size)
            painter.drawEllipse(cx - size, cy - size, size * 2, size * 2)
            
            # Label
            painter.setFont(QFont("Arial", 9, QFont.Bold))
            painter.setPen(QColor(255, 0, 0))
            painter.drawText(cx + 10, cy - 10, "ROTATION CENTER")


class GaugeCalibratorWindow(QMainWindow):
    """Main calibration window"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gauge Calibrator - Point & Click Setup")
        self.setGeometry(100, 100, 1200, 800)
        
        self.current_calibration = None
        self.config_dir = Path("config")
        self.config_dir.mkdir(exist_ok=True)
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize UI"""
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        layout = QHBoxLayout()
        
        # Left side: Image display
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("Click on needle image to set rotation center:"))
        self.image_widget = NeedleImageWidget()
        left_layout.addWidget(self.image_widget)
        
        # Right side: Configuration
        right_layout = QVBoxLayout()
        
        # Gauge selector
        gauge_group = QGroupBox("Gauge Selection")
        gauge_layout = QVBoxLayout()
        self.gauge_combo = QComboBox()
        self.gauge_combo.addItems(["Tachometer", "Speedometer", "Fuel", "Water"])
        self.gauge_combo.currentTextChanged.connect(self.on_gauge_changed)
        gauge_layout.addWidget(QLabel("Select Gauge:"))
        gauge_layout.addWidget(self.gauge_combo)
        
        # Needle selector (for gauges with multiple needles)
        needle_layout = QHBoxLayout()
        needle_layout.addWidget(QLabel("Select Needle:"))
        self.needle_combo = QComboBox()
        self.needle_combo.currentTextChanged.connect(self.on_needle_changed)
        needle_layout.addWidget(self.needle_combo)
        gauge_layout.addLayout(needle_layout)
        
        # Image status and load button
        image_layout = QHBoxLayout()
        self.image_status_label = QLabel("Loading image...")
        self.image_status_label.setStyleSheet("color: #888; font-size: 10px;")
        image_layout.addWidget(self.image_status_label)
        image_layout.addStretch()
        
        load_btn = QPushButton("Browse for Different Image")
        load_btn.clicked.connect(self.load_needle_image)
        image_layout.addWidget(load_btn)
        gauge_layout.addLayout(image_layout)
        gauge_group.setLayout(gauge_layout)
        right_layout.addWidget(gauge_group)
        
        # Rotation center display
        center_group = QGroupBox("Rotation Center (click on image to set)")
        center_layout = QHBoxLayout()
        center_layout.addWidget(QLabel("X:"))
        self.center_x_spin = QSpinBox()
        self.center_x_spin.setRange(0, 2000)
        center_layout.addWidget(self.center_x_spin)
        center_layout.addWidget(QLabel("Y:"))
        self.center_y_spin = QSpinBox()
        self.center_y_spin.setRange(0, 2000)
        center_layout.addWidget(self.center_y_spin)
        center_group.setLayout(center_layout)
        right_layout.addWidget(center_group)
        
        # Calibration points
        calib_group = QGroupBox("Calibration Points")
        calib_layout = QVBoxLayout()
        
        calib_input_layout = QHBoxLayout()
        calib_input_layout.addWidget(QLabel("Value:"))
        self.calib_value_spin = QDoubleSpinBox()
        self.calib_value_spin.setRange(-1000, 20000)
        self.calib_value_spin.setValue(0)
        calib_input_layout.addWidget(self.calib_value_spin)
        
        calib_input_layout.addWidget(QLabel("Angle (°):"))
        self.calib_angle_spin = QDoubleSpinBox()
        self.calib_angle_spin.setRange(-360, 360)
        self.calib_angle_spin.setValue(270)
        calib_input_layout.addWidget(self.calib_angle_spin)
        
        add_calib_btn = QPushButton("Add Point")
        add_calib_btn.clicked.connect(self.add_calibration_point)
        calib_input_layout.addWidget(add_calib_btn)
        calib_layout.addLayout(calib_input_layout)
        
        # Calibration table
        self.calib_table = QTableWidget()
        self.calib_table.setColumnCount(3)
        self.calib_table.setHorizontalHeaderLabels(["Value", "Angle (°)", "Delete"])
        self.calib_table.setMaximumHeight(200)
        calib_layout.addWidget(self.calib_table)
        
        # Quick presets
        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("Quick Add:"))
        
        for preset_name, presets in [
            ("Tach", [(0, 270), (5000, 135), (10000, 0)]),
            ("Speed", [(0, 240), (160, 90), (320, -60)]),
        ]:
            btn = QPushButton(preset_name)
            btn.clicked.connect(lambda checked, p=presets: self.add_preset(p))
            preset_layout.addWidget(btn)
        
        calib_layout.addLayout(preset_layout)
        calib_group.setLayout(calib_layout)
        right_layout.addWidget(calib_group)
        
        # Save buttons
        save_layout = QHBoxLayout()
        save_btn = QPushButton("Save Configuration")
        save_btn.clicked.connect(self.save_configuration)
        save_layout.addWidget(save_btn)
        
        load_config_btn = QPushButton("Load Configuration")
        load_config_btn.clicked.connect(self.load_configuration)
        save_layout.addWidget(load_config_btn)
        
        right_layout.addLayout(save_layout)
        right_layout.addStretch()
        
        # Combine layouts
        layout.addLayout(left_layout, 2)
        layout.addLayout(right_layout, 1)
        main_widget.setLayout(layout)
    
    def on_gauge_changed(self, gauge_name: str):
        """Handle gauge selection"""
        # Determine which needles this gauge has
        needles = ["main"]  # Default
        if gauge_name == "Fuel":
            needles = ["fuel", "water"]
        
        # Update needle selector
        self.needle_combo.blockSignals(True)
        self.needle_combo.clear()
        self.needle_combo.addItems(needles)
        self.needle_combo.blockSignals(False)
        
        # Create calibration for first needle
        self.on_needle_changed(needles[0])
    
    def on_needle_changed(self, needle_name: str):
        """Handle needle selection"""
        gauge_name = self.gauge_combo.currentText()
        
        self.current_calibration = GaugeCalibration(
            needle_id=needle_name,
            gauge_name=gauge_name,
            needle_image_path="",
            start_value=0 if needle_name == "fuel" or gauge_name != "Water" else 50,
            end_value=10000 if gauge_name == "Tachometer" else 
                     320 if gauge_name == "Speedometer" else
                     100 if needle_name == "fuel" else 130
        )
        self.calib_table.setRowCount(0)
        
        # Auto-load image from gauges folder
        self._try_auto_load_image()
    
    def _get_expected_image_path(self) -> Path:
        """Generate expected image path based on gauge and needle"""
        if not self.current_calibration:
            return None
        
        # Use needle_id for multi-needle gauges (fuel, water)
        # Use gauge_name (lowercase) for single-needle gauges (tachometer_needle.png, etc)
        if self.current_calibration.needle_id == "main":
            needle_name = self.current_calibration.gauge_name.lower()
        else:
            needle_name = self.current_calibration.needle_id
        
        return Path("gauges") / f"{needle_name}_needle.png"
    
    def _get_expected_background_path(self) -> Path:
        """Generate expected background image path"""
        if not self.current_calibration:
            return None
        
        # Use gauge name for background (not needle ID)
        gauge_name = self.current_calibration.gauge_name.lower()
        return Path("gauges") / f"{gauge_name}_bg.png"
    
    def _try_auto_load_image(self):
        """Try to auto-load image from gauges folder"""
        if not self.current_calibration:
            self.image_status_label.setText("No gauge selected")
            return
        
        expected_path = self._get_expected_image_path()
        if expected_path and expected_path.exists():
            if self.image_widget.load_image(str(expected_path)):
                self.current_calibration.needle_image_path = str(expected_path)
                
                # Also try to load background image
                bg_path = self._get_expected_background_path()
                if bg_path and bg_path.exists():
                    self.image_widget.load_background(str(bg_path))
                    self.image_status_label.setText(f"✓ Loaded: {expected_path.name} + {bg_path.name}")
                else:
                    self.image_status_label.setText(f"✓ Auto-loaded: {expected_path.name}")
                
                self.image_status_label.setStyleSheet("color: #008000; font-size: 10px;")
                
                # Try to load existing calibration center if available
                config_file = self.config_dir / f"{self.current_calibration.gauge_name.lower()}.json"
                if config_file.exists():
                    try:
                        from src.gauge_config import GaugeConfig
                        with open(config_file, 'r') as f:
                            gauge_config = GaugeConfig.from_dict(json.load(f))
                        
                        if self.current_calibration.needle_id in gauge_config.needle_calibrations:
                            saved_calib = gauge_config.needle_calibrations[self.current_calibration.needle_id]
                            if saved_calib.rotation_center_x and saved_calib.rotation_center_y:
                                self.image_widget.set_rotation_center(
                                    saved_calib.rotation_center_x,
                                    saved_calib.rotation_center_y
                                )
                                self.center_x_spin.setValue(int(saved_calib.rotation_center_x))
                                self.center_y_spin.setValue(int(saved_calib.rotation_center_y))
                    except Exception:
                        pass  # Auto-load is best-effort, don't fail if config unavailable
        else:
            self.image_status_label.setText(f"⚠ Not found: gauges/{self._get_expected_image_path().name}")
            self.image_status_label.setStyleSheet("color: #CC6600; font-size: 10px;")
    
    def load_needle_image(self):
        """Load needle image file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Needle Image", "", "PNG Files (*.png);;All Files (*)"
        )
        if file_path:
            if self.image_widget.load_image(file_path):
                self.current_calibration.needle_image_path = file_path
                self.image_status_label.setText(f"✓ Loaded: {Path(file_path).name}")
                self.image_status_label.setStyleSheet("color: #008000; font-size: 10px;")
                QMessageBox.information(self, "Success", "Image loaded. Click to set rotation center.")
            else:
                QMessageBox.warning(self, "Error", "Could not load image")
    
    def on_rotation_center_set(self, x: float, y: float):
        """Update rotation center display"""
        self.center_x_spin.setValue(int(x))
        self.center_y_spin.setValue(int(y))
        if self.current_calibration:
            self.current_calibration.rotation_center_x = x
            self.current_calibration.rotation_center_y = y
    
    def add_calibration_point(self):
        """Add calibration point from input"""
        value = self.calib_value_spin.value()
        angle = self.calib_angle_spin.value()
        
        if not self.current_calibration:
            QMessageBox.warning(self, "Error", "Please select a gauge first")
            return
        
        point = CalibrationPoint(value=value, angle=angle)
        self.current_calibration.calibration_points.append(point)
        self._refresh_calibration_table()
    
    def add_preset(self, presets: List[Tuple[float, float]]):
        """Add preset calibration points"""
        if not self.current_calibration:
            QMessageBox.warning(self, "Error", "Please select a gauge first")
            return
        
        self.current_calibration.calibration_points.clear()
        for value, angle in presets:
            self.current_calibration.calibration_points.append(
                CalibrationPoint(value=value, angle=angle)
            )
        self._refresh_calibration_table()
    
    def _refresh_calibration_table(self):
        """Refresh calibration table display"""
        if not self.current_calibration:
            return
        
        self.calib_table.setRowCount(len(self.current_calibration.calibration_points))
        
        for i, point in enumerate(self.current_calibration.calibration_points):
            value_item = QTableWidgetItem(f"{point.value:.1f}")
            angle_item = QTableWidgetItem(f"{point.angle:.1f}")
            self.calib_table.setItem(i, 0, value_item)
            self.calib_table.setItem(i, 1, angle_item)
            
            del_btn = QPushButton("X")
            del_btn.clicked.connect(lambda checked, row=i: self.delete_calibration_point(row))
            self.calib_table.setCellWidget(i, 2, del_btn)
    
    def delete_calibration_point(self, row: int):
        """Delete calibration point"""
        if self.current_calibration and 0 <= row < len(self.current_calibration.calibration_points):
            del self.current_calibration.calibration_points[row]
            self._refresh_calibration_table()
    
    def save_configuration(self):
        """Save calibration to gauge config file"""
        if not self.current_calibration:
            QMessageBox.warning(self, "Error", "No gauge selected")
            return
        
        if not self.current_calibration.needle_image_path:
            QMessageBox.warning(self, "Error", "Please load needle image first")
            return
        
        # Update from UI
        self.current_calibration.rotation_center_x = self.center_x_spin.value()
        self.current_calibration.rotation_center_y = self.center_y_spin.value()
        
        # Load existing gauge config
        from src.gauge_config import GaugeConfig, NeedleCalibration
        config_file = self.config_dir / f"{self.current_calibration.gauge_name.lower()}.json"
        
        try:
            # Load existing config or create new one
            if config_file.exists():
                with open(config_file, 'r') as f:
                    gauge_config = GaugeConfig.from_dict(json.load(f))
            else:
                # Create minimal gauge config
                gauge_config = GaugeConfig(name=self.current_calibration.gauge_name)
            
            # Update needle calibration
            needle_calib = NeedleCalibration(
                needle_id=self.current_calibration.needle_id,
                needle_image_path=self.current_calibration.needle_image_path,
                rotation_center_x=self.current_calibration.rotation_center_x,
                rotation_center_y=self.current_calibration.rotation_center_y,
                calibration_points=self.current_calibration.calibration_points
            )
            gauge_config.needle_calibrations[self.current_calibration.needle_id] = needle_calib
            
            # Save updated config
            with open(config_file, 'w') as f:
                json.dump(gauge_config.to_dict(), f, indent=2)
            
            QMessageBox.information(
                self, "Success", 
                f"Saved {self.current_calibration.needle_id} needle calibration to {config_file}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save: {e}")
    
    def load_configuration(self):
        """Load calibration from gauge config file"""
        if not self.current_calibration:
            QMessageBox.warning(self, "Error", "Please select a gauge and needle first")
            return
        
        config_file = self.config_dir / f"{self.current_calibration.gauge_name.lower()}.json"
        
        if not config_file.exists():
            QMessageBox.warning(self, "Not Found", f"No configuration found for {self.current_calibration.gauge_name}")
            return
        
        try:
            from src.gauge_config import GaugeConfig
            
            with open(config_file, 'r') as f:
                gauge_config = GaugeConfig.from_dict(json.load(f))
            
            # Load calibration for selected needle
            needle_id = self.current_calibration.needle_id
            if needle_id not in gauge_config.needle_calibrations:
                QMessageBox.warning(
                    self, "Not Found", 
                    f"No calibration found for {needle_id} needle"
                )
                return
            
            needle_calib = gauge_config.needle_calibrations[needle_id]
            
            # Update current calibration
            self.current_calibration.needle_image_path = needle_calib.needle_image_path
            self.current_calibration.rotation_center_x = needle_calib.rotation_center_x
            self.current_calibration.rotation_center_y = needle_calib.rotation_center_y
            self.current_calibration.calibration_points = needle_calib.calibration_points
            
            # Update UI
            if self.image_widget.load_image(self.current_calibration.needle_image_path):
                self.image_widget.set_rotation_center(
                    self.current_calibration.rotation_center_x,
                    self.current_calibration.rotation_center_y
                )
                self.center_x_spin.setValue(int(self.current_calibration.rotation_center_x))
                self.center_y_spin.setValue(int(self.current_calibration.rotation_center_y))
                self._refresh_calibration_table()
                QMessageBox.information(
                    self, "Success", 
                    f"Loaded {needle_id} needle calibration"
                )
            else:
                QMessageBox.warning(self, "Warning", "Loaded config but couldn't find image")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load: {e}")


def main():
    import sys
    app = QApplication(sys.argv)
    window = GaugeCalibratorWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
