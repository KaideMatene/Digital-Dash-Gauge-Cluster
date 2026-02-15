#!/usr/bin/env python3
"""
Needle Alignment Tool

Load gauge background + needle PNG, rotate needle visually to calibrate alignment.
Shows rotation angle in real-time.
"""

import sys
import logging
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QSlider, QSpinBox, QPushButton, QComboBox, QFileDialog
)
from PyQt5.QtCore import Qt, QTimer, QByteArray
from PyQt5.QtGui import QPixmap, QPainter, QImage
from PIL import Image
import io

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NeedleAlignmentTool(QMainWindow):
    """Interactive tool for aligning gauge needles"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Needle Alignment Tool - Visual Calibration")
        self.setGeometry(100, 100, 1200, 700)
        
        self.bg_image = None
        self.needle_image = None
        self.current_angle = 0
        
        self.init_ui()
        self.load_default_images()
    
    def init_ui(self):
        """Create UI"""
        central = QWidget()
        main_layout = QHBoxLayout()
        
        # Left: Controls
        control_widget = QWidget()
        control_layout = QVBoxLayout()
        
        # Gauge selector
        control_layout.addWidget(QLabel("Select Gauge:"))
        self.gauge_combo = QComboBox()
        self.gauge_combo.addItems(["Tachometer", "Speedometer", "Fuel"])
        self.gauge_combo.currentTextChanged.connect(self._on_gauge_changed)
        control_layout.addWidget(self.gauge_combo)
        
        # Load buttons
        load_bg_btn = QPushButton("Load Background Image")
        load_bg_btn.clicked.connect(self._load_background)
        control_layout.addWidget(load_bg_btn)
        
        load_needle_btn = QPushButton("Load Needle Image")
        load_needle_btn.clicked.connect(self._load_needle)
        control_layout.addWidget(load_needle_btn)
        
        # Rotation slider
        control_layout.addWidget(QLabel("\n🔄 Needle Rotation Angle:"))
        self.angle_slider = QSlider(Qt.Horizontal)
        self.angle_slider.setRange(-180, 180)
        self.angle_slider.setValue(0)
        self.angle_slider.sliderMoved.connect(self._on_angle_changed)
        control_layout.addWidget(self.angle_slider)
        
        # Angle display and spinner
        angle_layout = QHBoxLayout()
        angle_layout.addWidget(QLabel("Angle:"))
        self.angle_spinbox = QSpinBox()
        self.angle_spinbox.setRange(-180, 180)
        self.angle_spinbox.valueChanged.connect(self._on_spinbox_changed)
        angle_layout.addWidget(self.angle_spinbox)
        angle_layout.addWidget(QLabel("°"))
        control_layout.addLayout(angle_layout)
        
        # Gauge-specific angles
        control_layout.addWidget(QLabel("\n📐 Gauge-Specific Calibration:"))
        
        control_layout.addWidget(QLabel("Start Angle (0 value):"))
        self.start_angle_spin = QSpinBox()
        self.start_angle_spin.setRange(0, 360)
        self.start_angle_spin.setValue(270)
        self.start_angle_spin.setSuffix("°")
        self.start_angle_spin.valueChanged.connect(self._on_calibration_changed)
        control_layout.addWidget(self.start_angle_spin)
        
        control_layout.addWidget(QLabel("Sweep Angle (max value):"))
        self.sweep_angle_spin = QSpinBox()
        self.sweep_angle_spin.setRange(0, 360)
        self.sweep_angle_spin.setValue(270)
        self.sweep_angle_spin.setSuffix("°")
        self.sweep_angle_spin.valueChanged.connect(self._on_calibration_changed)
        control_layout.addWidget(self.sweep_angle_spin)
        
        # Test values
        control_layout.addWidget(QLabel("\n🧪 Test Needle Position:"))
        control_layout.addWidget(QLabel("Test fraction (0.0 to 1.0):"))
        self.test_fraction_spin = QSpinBox()
        self.test_fraction_spin.setRange(0, 100)
        self.test_fraction_spin.setValue(0)
        self.test_fraction_spin.setSuffix("%")
        self.test_fraction_spin.valueChanged.connect(self._on_test_fraction_changed)
        control_layout.addWidget(self.test_fraction_spin)
        
        # Info display
        control_layout.addWidget(QLabel("\n📍 Current Settings:"))
        self.info_label = QLabel(
            "Background: None\n"
            "Needle: None\n"
            "Angle: 0°"
        )
        self.info_label.setStyleSheet("background-color: #f0f0f0; padding: 8px; border-radius: 4px;")
        control_layout.addWidget(self.info_label)
        
        # Copy calibration
        control_layout.addWidget(QLabel("\n💾 Use These Values In Code:"))
        self.calibration_label = QLabel(
            "start_angle = 270  # Angle for min value\n"
            "sweep_angle = 270  # Range to max value"
        )
        self.calibration_label.setStyleSheet(
            "background-color: #ffffcc; padding: 8px; border-radius: 4px; "
            "font-family: monospace; font-size: 10px;"
        )
        control_layout.addWidget(self.calibration_label)
        
        control_layout.addStretch()
        control_widget.setLayout(control_layout)
        control_widget.setMaximumWidth(300)
        
        # Right: Preview
        self.preview_label = QLabel()
        self.preview_label.setScaledContents(False)
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet("border: 1px solid #ccc; background-color: #f5f5f5;")
        
        main_layout.addWidget(control_widget)
        main_layout.addWidget(self.preview_label, 1)
        
        central.setLayout(main_layout)
        self.setCentralWidget(central)
    
    def load_default_images(self):
        """Load default gauge images if they exist"""
        gauge_dir = Path(__file__).parent / "gauges"
        logger.info(f"Looking for images in: {gauge_dir.absolute()}")
        
        tach_bg = gauge_dir / "tachometer_bg.png"
        if tach_bg.exists():
            self.bg_image = Image.open(tach_bg).convert("RGBA")
            logger.info(f"✅ Loaded background: {tach_bg.name}")
        else:
            logger.warning(f"⚠️  Background not found: {tach_bg}")
        
        # Look for needle image
        needle_search = list(gauge_dir.glob("*needle*.png"))
        if needle_search:
            self.needle_image = Image.open(needle_search[0]).convert("RGBA")
            logger.info(f"✅ Loaded needle: {needle_search[0].name}")
        else:
            logger.warning(f"⚠️  No needle images found in {gauge_dir}")
        
        self._update_preview()
    
    def _load_background(self):
        """Load background image"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Background Image", str(Path.home()),
            "Image Files (*.png *.jpg *.jpeg)"
        )
        if file_path:
            self.bg_image = Image.open(file_path).convert("RGBA")
            logger.info(f"Loaded background: {file_path}")
            self._update_preview()
    
    def _load_needle(self):
        """Load needle image"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Needle Image", str(Path.home()),
            "Image Files (*.png *.jpg *.jpeg)"
        )
        if file_path:
            self.needle_image = Image.open(file_path).convert("RGBA")
            logger.info(f"Loaded needle: {file_path}")
            self._update_preview()
    
    def _on_gauge_changed(self, gauge_name):
        """Switch between gauge presets"""
        presets = {
            "Tachometer": (270, 279),
            "Speedometer": (240, 300),
            "Fuel": (180, 90),
        }
        start, sweep = presets.get(gauge_name, (270, 270))
        self.start_angle_spin.setValue(start)
        self.sweep_angle_spin.setValue(sweep)
    
    def _on_angle_changed(self, value):
        """Update angle from slider"""
        self.angle_spinbox.blockSignals(True)
        self.angle_spinbox.setValue(value)
        self.angle_spinbox.blockSignals(False)
        self.current_angle = value
        self._update_preview()
    
    def _on_spinbox_changed(self, value):
        """Update angle from spinbox"""
        self.angle_slider.blockSignals(True)
        self.angle_slider.setValue(value)
        self.angle_slider.blockSignals(False)
        self.current_angle = value
        self._update_preview()
    
    def _on_calibration_changed(self):
        """Update calibration display"""
        start = self.start_angle_spin.value()
        sweep = self.sweep_angle_spin.value()
        self.calibration_label.setText(
            f"start_angle = {start}  # Angle at minimum value\n"
            f"sweep_angle = {sweep}  # Total rotation range\n\n"
            f"Current needle at: {self.current_angle}°"
        )
    
    def _on_test_fraction_changed(self, percent_value):
        """Test needle position at percentage"""
        fraction = percent_value / 100.0
        start = self.start_angle_spin.value()
        sweep = self.sweep_angle_spin.value()
        
        # Calculate angle for this fraction
        test_angle = start - sweep * fraction
        
        self.angle_slider.blockSignals(True)
        self.angle_spinbox.blockSignals(True)
        self.angle_slider.setValue(int(test_angle))
        self.angle_spinbox.setValue(int(test_angle))
        self.angle_slider.blockSignals(False)
        self.angle_spinbox.blockSignals(False)
        
        self.current_angle = test_angle
        self._update_preview()
    
    def _update_preview(self):
        """Update preview image"""
        if not self.bg_image or not self.needle_image:
            self.preview_label.setText("Load background and needle images")
            return
        
        try:
            # Create composite
            width, height = self.bg_image.size
            composite = self.bg_image.copy()
            
            # Rotate needle
            rotated_needle = self.needle_image.rotate(
                self.current_angle,
                expand=False,
                resample=Image.BILINEAR
            )
            
            # Center needle
            needle_x = (width - rotated_needle.width) // 2
            needle_y = (height - rotated_needle.height) // 2
            composite.paste(rotated_needle, (needle_x, needle_y), rotated_needle)
            
            # Convert to QPixmap
            pixmap = self._pil_to_qimage(composite)
            
            # Scale for display
            display_size = 500
            scaled = pixmap.scaledToHeight(display_size, Qt.SmoothTransformation)
            self.preview_label.setPixmap(scaled)
            
            # Update info
            self.info_label.setText(
                f"Background: {self.bg_image.size[0]}x{self.bg_image.size[1]}\n"
                f"Needle: {self.needle_image.size[0]}x{self.needle_image.size[1]}\n"
                f"Rotation: {self.current_angle}°"
            )
            
            self._on_calibration_changed()
            
        except Exception as e:
            logger.error(f"Error updating preview: {e}")
            self.preview_label.setText(f"Error: {e}")
    
    @staticmethod
    def _pil_to_qimage(pil_image):
        """Convert PIL image to QPixmap - workaround for broken Pillow ImageQt"""
        pil_rgba = pil_image.convert("RGBA")
        
        # Convert via PNG bytes to avoid broken Pillow ImageQt
        png_data = io.BytesIO()
        pil_rgba.save(png_data, format="PNG")
        png_data.seek(0)
        
        pixmap = QPixmap()
        pixmap.loadFromData(png_data.read(), "PNG")
        return pixmap


def main():
    try:
        logger.info("Creating QApplication...")
        app = QApplication(sys.argv)
        logger.info("QApplication created successfully")
        
        logger.info("Creating NeedleAlignmentTool window...")
        window = NeedleAlignmentTool()
        logger.info("Window created successfully")
        
        logger.info("Showing window...")
        window.show()
        logger.info("Window shown, starting event loop...")
        
        sys.exit(app.exec_())
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
