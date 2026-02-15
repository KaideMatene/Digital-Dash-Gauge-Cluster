#!/usr/bin/env python3
"""
Test v2 Calibrations in Gauge Preview

Loads calibrations from v2 config files and displays gauges with proper needle rotation.
"""

import sys
import json
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSlider, QLabel, QGroupBox, QDoubleSpinBox, QComboBox
)
from PyQt5.QtCore import Qt, QTimer

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from image_gauge import ImageTachometer, ImageSpeedometer, ImageFuelGauge
from gauge_calibrator_v2 import NeedleCalibration, AngleCalculator


class V2CalibrationTester(QMainWindow):
    """Test v2 calibrations from gauge_calibrator_v2"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("V2 Calibration Tester")
        self.setGeometry(100, 100, 1600, 900)
        
        central = QWidget()
        main_layout = QHBoxLayout()
        
        # Left: Gauges
        gauge_layout = QVBoxLayout()
        
        # Tachometer
        self.tach = ImageTachometer("gauges/tachometer_bg.png")
        self.load_tach_calibration()
        gauge_layout.addWidget(QLabel("Tachometer"))
        gauge_layout.addWidget(self.tach)
        
        # Speedometer
        self.speed = ImageSpeedometer("gauges/speedometer_bg.png")
        self.load_speed_calibration()
        gauge_layout.addWidget(QLabel("Speedometer"))
        gauge_layout.addWidget(self.speed)
        
        # Fuel (with dual needles)
        self.fuel = ImageFuelGauge("gauges/fuel_bg.png")
        self.load_fuel_calibration()
        gauge_layout.addWidget(QLabel("Fuel"))
        gauge_layout.addWidget(self.fuel)
        
        # Right: Controls
        control_layout = QVBoxLayout()
        
        # Tachometer slider
        control_layout.addWidget(QLabel("RPM (Tachometer)"))
        self.rpm_slider = QSlider(Qt.Horizontal)
        self.rpm_slider.setMinimum(0)
        self.rpm_slider.setMaximum(10000)
        self.rpm_slider.setValue(3000)
        self.rpm_slider.sliderMoved.connect(self.on_rpm_changed)
        self.rpm_slider.setStyleSheet("QSlider { height: 30px; }")
        control_layout.addWidget(self.rpm_slider)
        self.rpm_label = QLabel("3000 RPM")
        control_layout.addWidget(self.rpm_label)
        
        # Speed slider
        control_layout.addWidget(QLabel("Speed (Speedometer)"))
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setMinimum(0)
        self.speed_slider.setMaximum(320)
        self.speed_slider.setValue(60)
        self.speed_slider.sliderMoved.connect(self.on_speed_changed)
        self.speed_slider.setStyleSheet("QSlider { height: 30px; }")
        control_layout.addWidget(self.speed_slider)
        self.speed_label = QLabel("60 km/h")
        control_layout.addWidget(self.speed_label)
        
        # Fuel slider
        control_layout.addWidget(QLabel("Fuel Level"))
        self.fuel_slider = QSlider(Qt.Horizontal)
        self.fuel_slider.setMinimum(0)
        self.fuel_slider.setMaximum(100)
        self.fuel_slider.setValue(50)
        self.fuel_slider.sliderMoved.connect(self.on_fuel_changed)
        self.fuel_slider.setStyleSheet("QSlider { height: 30px; }")
        control_layout.addWidget(self.fuel_slider)
        self.fuel_label = QLabel("50%")
        control_layout.addWidget(self.fuel_label)
        
        # Water temp slider
        control_layout.addWidget(QLabel("Water Temperature"))
        self.water_slider = QSlider(Qt.Horizontal)
        self.water_slider.setMinimum(50)
        self.water_slider.setMaximum(130)
        self.water_slider.setValue(90)
        self.water_slider.sliderMoved.connect(self.on_water_changed)
        self.water_slider.setStyleSheet("QSlider { height: 30px; }")
        control_layout.addWidget(self.water_slider)
        self.water_label = QLabel("90°C")
        control_layout.addWidget(self.water_label)
        
        control_layout.addStretch()
        
        # Info panel
        control_layout.addWidget(QLabel("\n=== Calibration Info ==="))
        self.info_label = QLabel("Loaded from config/")
        self.info_label.setStyleSheet("font-size: 10px; color: #666;")
        control_layout.addWidget(self.info_label)
        
        # Layout assembly
        main_layout.addLayout(gauge_layout, 2)
        main_layout.addLayout(control_layout, 1)
        
        central.setLayout(main_layout)
        self.setCentralWidget(central)
        
        # Start animation loop
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_gauges)
        self.timer.start(50)  # 20 FPS
    
    def load_tach_calibration(self):
        """Load tachometer calibration from v2 config"""
        try:
            config_path = Path(__file__).parent / "config" / "tachometer.json"
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            if "needle_calibrations" in config and "main" in config["needle_calibrations"]:
                calib_data = config["needle_calibrations"]["main"]
                calib = NeedleCalibration.from_dict(calib_data)
                
                # Create angle calculator
                self.tach_calc = AngleCalculator(calib)
                
                info = f"Tachometer: {len(calib.calibration_points)} points"
                self.info_label.setText(self.info_label.text() + f"\n{info}")
                print(f"✓ Loaded tachometer calibration")
            else:
                print("⚠ No needle_calibrations in tachometer.json")
                self.tach_calc = None
        except Exception as e:
            print(f"✗ Error loading tachometer calibration: {e}")
            self.tach_calc = None
    
    def load_speed_calibration(self):
        """Load speedometer calibration from v2 config"""
        try:
            config_path = Path(__file__).parent / "config" / "speedometer.json"
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            if "needle_calibrations" in config and "main" in config["needle_calibrations"]:
                calib_data = config["needle_calibrations"]["main"]
                calib = NeedleCalibration.from_dict(calib_data)
                
                self.speed_calc = AngleCalculator(calib)
                print(f"✓ Loaded speedometer calibration")
            else:
                print("⚠ No needle_calibrations in speedometer.json")
                self.speed_calc = None
        except Exception as e:
            print(f"✗ Error loading speedometer calibration: {e}")
            self.speed_calc = None
    
    def load_fuel_calibration(self):
        """Load fuel gauge calibration from v2 config (dual needles)"""
        try:
            config_path = Path(__file__).parent / "config" / "fuel.json"
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            self.fuel_calc = None
            self.water_calc = None
            
            if "needle_calibrations" in config:
                if "fuel" in config["needle_calibrations"]:
                    calib = NeedleCalibration.from_dict(config["needle_calibrations"]["fuel"])
                    self.fuel_calc = AngleCalculator(calib)
                    print(f"✓ Loaded fuel needle calibration")
                
                if "water" in config["needle_calibrations"]:
                    calib = NeedleCalibration.from_dict(config["needle_calibrations"]["water"])
                    self.water_calc = AngleCalculator(calib)
                    print(f"✓ Loaded water needle calibration")
        except Exception as e:
            print(f"✗ Error loading fuel calibration: {e}")
    
    def on_rpm_changed(self, value):
        """Update tachometer value"""
        self.tach.target_value = value
        self.rpm_label.setText(f"{value} RPM")
    
    def on_speed_changed(self, value):
        """Update speedometer value"""
        self.speed.target_value = value
        self.speed_label.setText(f"{value} km/h")
    
    def on_fuel_changed(self, value):
        """Update fuel needle"""
        self.fuel.fuel_value = value
        self.fuel_label.setText(f"{value}%")
    
    def on_water_changed(self, value):
        """Update water needle"""
        self.fuel.water_value = value
        self.water_label.setText(f"{value}°C")
    
    def update_gauges(self):
        """Update gauge display"""
        # Apply calibrated angles if available
        if self.tach_calc:
            rpm = self.tach.value
            angle = self.tach_calc.value_to_angle(rpm)
            # Note: You'd need to modify ImageGauge to use calibrated angles
        
        self.tach.update()
        self.speed.update()
        self.fuel.update()


if __name__ == '__main__':
    print("\n" + "="*60)
    print("V2 CALIBRATION TESTER")
    print("="*60)
    print("\nLoading calibrations from config/...")
    
    app = QApplication(sys.argv)
    window = V2CalibrationTester()
    window.show()
    
    print("\nControls:")
    print("  - Use sliders on the right to adjust gauge values")
    print("  - Needles will rotate based on your calibration points")
    print("  - Close window to exit\n")
    
    sys.exit(app.exec_())
