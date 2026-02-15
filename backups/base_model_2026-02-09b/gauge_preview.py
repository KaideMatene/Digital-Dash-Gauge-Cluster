#!/usr/bin/env python3
"""
Gauge Controller (Emulator)

Combined emulator and calibration tool in tabbed interface:
- Preview & Settings: Live gauge display with value controls and needle scaling
- Calibration Tool: Position-based click calibration system

No CAN bus or hardware required - perfect for design iteration.
Supports v2 calibrations from config files.
"""

import sys
import logging
import json
import math
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSlider, QLabel, QGroupBox, QSpinBox, QComboBox, QDoubleSpinBox, QTabWidget, QPushButton,
    QScrollArea, QMessageBox
)
from PyQt5.QtCore import Qt, QTimer

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from image_gauge import ImageTachometer, ImageSpeedometer, ImageFuelGauge
from config_utils import ensure_default_configs, load_gauge_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TACH_BASE_SCALE = 2.77
SPEED_BASE_SCALE = 2.69
FUEL_BASE_SCALE = 2.76
WATER_BASE_SCALE = 2.64

# Ensure default configs exist on startup
ensure_default_configs()


class GaugePreview(QMainWindow):
    """Preview and adjust all gauges with tabbed interface"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gauge Controller")
        self.setGeometry(100, 100, 2200, 1100)
        
        # Create main widget with tabs
        central = QWidget()
        main_layout = QVBoxLayout()
        
        # Tab widget
        tabs = QTabWidget()
        
        # Tab 1: Preview
        preview_tab = QWidget()
        preview_layout = QHBoxLayout()
        
        # Left: Gauges (3x in a row)
        gauge_layout = QHBoxLayout()
        
        # Get config directory
        config_dir = Path(__file__).parent / "config"
        
        # Load calibration configs up front (for ranges + needle image paths)
        tach_config_path = config_dir / "tachometer.json"
        speed_config_path = config_dir / "speedometer.json"
        fuel_config_path = config_dir / "fuel.json"
        
        tach_config = self._load_config(tach_config_path)
        speed_config = self._load_config(speed_config_path)
        fuel_config = self._load_config(fuel_config_path)
        
        tach_cal = self._get_needle_calibration(tach_config, "main")
        speed_cal = self._get_needle_calibration(speed_config, "main")
        fuel_cal = self._get_needle_calibration(fuel_config, "fuel")
        water_cal = self._get_needle_calibration(fuel_config, "water")
        
        tach_needle_path = self._resolve_needle_image_path(
            tach_cal, "gauges/needle.svg"  # Use SVG as default
        )
        speed_needle_path = self._resolve_needle_image_path(
            speed_cal, "gauges/needle.svg"  # Use SVG as default
        )
        fuel_needle_path = self._resolve_needle_image_path(
            fuel_cal, "gauges/needle.svg"  # Use SVG as default
        )
        
        self.tach_range = self._get_calibration_range(tach_cal, 0, 8000)
        self.speed_range = self._get_calibration_range(speed_cal, 0, 280)
        self.fuel_range = self._get_calibration_range(fuel_cal, 0, 100)
        self.water_range = self._get_calibration_range(water_cal, 0, 130)
        
        # Tachometer
        self.tach = ImageTachometer("gauges/tachometer_bg.png", tach_needle_path)
        # Load ALL needle calibrations from config (not just "main")
        if tach_config_path.exists():
            self.tach.load_all_needles_from_file(str(tach_config_path), "main")
            logger.info("✅ Tachometer calibration loaded (all needles)")
        gauge_layout.addWidget(self.tach)
        
        # Speedometer
        self.speed = ImageSpeedometer("gauges/speedometer_bg.png", speed_needle_path)
        # Load ALL needle calibrations from config (not just "main")
        if speed_config_path.exists():
            self.speed.load_all_needles_from_file(str(speed_config_path), "main")
            logger.info("✅ Speedometer calibration loaded (all needles)")
        gauge_layout.addWidget(self.speed)
        
        # Fuel Gauge
        self.fuel = ImageFuelGauge("gauges/fuel_bg.png", fuel_needle_path)
        # Load v2 calibrations (fuel + water + any custom needles)
        if fuel_config_path.exists():
            try:
                needle_calibrations = fuel_config.get('needle_calibrations', {})
                # Load fuel and water using the dual calibration method
                self.fuel.load_dual_v2_calibration(needle_calibrations)
                
                # Also load any custom needles beyond fuel/water
                for needle_id in needle_calibrations:
                    if needle_id not in ['fuel', 'water']:
                        needle_cal = needle_calibrations[needle_id]
                        points = needle_cal.get('calibration_points', [])
                        
                        if points and len(points) >= 2:
                            from angle_calculator import AngleCalculator
                            angle_calc = AngleCalculator()
                            angle_calc.load_calibration_points(points)
                            
                            scale = needle_cal.get('scale', 1.0)
                            
                            self.fuel.named_needles[needle_id] = {
                                'value': 0,
                                'scale': scale,
                                'angle_calc': angle_calc
                            }
                            logger.info(f"✅ Loaded custom needle for fuel gauge: {needle_id}")
                
                logger.info("✅ Fuel gauge calibrations loaded (dual needle + custom)")
            except Exception as e:
                logger.warning(f"⚠️ Failed to load fuel calibrations: {e}")
        gauge_layout.addWidget(self.fuel)

        # Apply fixed base scales so UI 1.0x matches correct needle size
        self.tach.base_needle_scale = TACH_BASE_SCALE
        self.speed.base_needle_scale = SPEED_BASE_SCALE
        self.fuel.base_needle_scale = FUEL_BASE_SCALE
        self.fuel.water_base_needle_scale = WATER_BASE_SCALE
        self.tach.needle_scale = 1.0
        self.speed.needle_scale = 1.0
        self.fuel.needle_scale = 1.0
        self.fuel.water_needle_scale = 1.0
        
        preview_layout.addLayout(gauge_layout)
        
        # Right: Controls
        control_layout = QVBoxLayout()
        
        # Tachometer slider
        tach_group = QGroupBox("Tachometer (RPM)")
        tach_vbox = QVBoxLayout()
        self.tach_label = QLabel("0 RPM")
        self.tach_slider = QSlider(Qt.Horizontal)
        tach_min, tach_max = self.tach_range
        self.tach_slider.setRange(int(math.floor(tach_min)), int(math.ceil(tach_max)))
        tach_default = self._clamp_value(3000, tach_min, tach_max)
        self.tach_slider.setValue(int(round(tach_default)))
        self.tach.target_value = tach_default
        self.tach_slider.sliderMoved.connect(self._on_tach_changed)
        self.tach_slider.valueChanged.connect(self._on_tach_changed)
        self._on_tach_changed(self.tach_slider.value())
        tach_vbox.addWidget(QLabel("RPM"))
        tach_vbox.addWidget(self.tach_slider)
        tach_vbox.addWidget(self.tach_label)
        tach_group.setLayout(tach_vbox)
        control_layout.addWidget(tach_group)
        
        # Speedometer slider
        speed_group = QGroupBox("Speedometer (km/h)")
        speed_vbox = QVBoxLayout()
        self.speed_label = QLabel("0 km/h")
        self.speed_slider = QSlider(Qt.Horizontal)
        speed_min, speed_max = self.speed_range
        self.speed_slider.setRange(int(math.floor(speed_min)), int(math.ceil(speed_max)))
        speed_default = self._clamp_value(60, speed_min, speed_max)
        self.speed_slider.setValue(int(round(speed_default)))
        self.speed.target_value = speed_default
        self.speed_slider.sliderMoved.connect(self._on_speed_changed)
        self.speed_slider.valueChanged.connect(self._on_speed_changed)
        self._on_speed_changed(self.speed_slider.value())
        speed_vbox.addWidget(QLabel("Speed"))
        speed_vbox.addWidget(self.speed_slider)
        speed_vbox.addWidget(self.speed_label)
        speed_group.setLayout(speed_vbox)
        control_layout.addWidget(speed_group)
        
        # Fuel slider
        fuel_group = QGroupBox("Fuel Level (%)")
        fuel_vbox = QVBoxLayout()
        self.fuel_label = QLabel("75%")
        self.fuel_slider = QSlider(Qt.Horizontal)
        fuel_min, fuel_max = self.fuel_range
        self.fuel_slider.setRange(int(math.floor(fuel_min)), int(math.ceil(fuel_max)))
        fuel_default = self._clamp_value(75, fuel_min, fuel_max)
        self.fuel_slider.setValue(int(round(fuel_default)))
        self.fuel.target_value = fuel_default
        self.fuel_slider.sliderMoved.connect(self._on_fuel_changed)
        self.fuel_slider.valueChanged.connect(self._on_fuel_changed)
        self._on_fuel_changed(self.fuel_slider.value())
        fuel_vbox.addWidget(QLabel("Fuel"))
        fuel_vbox.addWidget(self.fuel_slider)
        fuel_vbox.addWidget(self.fuel_label)
        fuel_group.setLayout(fuel_vbox)
        control_layout.addWidget(fuel_group)
        
        # Coolant temp slider
        temp_group = QGroupBox("Coolant Temp (°C)")
        temp_vbox = QVBoxLayout()
        self.temp_label = QLabel("85°C")
        self.temp_slider = QSlider(Qt.Horizontal)
        water_min, water_max = self.water_range
        self.temp_slider.setRange(int(math.floor(water_min)), int(math.ceil(water_max)))
        temp_default = self._clamp_value(85, water_min, water_max)
        self.temp_slider.setValue(int(round(temp_default)))
        self.fuel.set_temperature(temp_default)
        self.temp_slider.sliderMoved.connect(self._on_temp_changed)
        self.temp_slider.valueChanged.connect(self._on_temp_changed)
        self._on_temp_changed(self.temp_slider.value())
        temp_vbox.addWidget(QLabel("Coolant"))
        temp_vbox.addWidget(self.temp_slider)
        temp_vbox.addWidget(self.temp_label)
        temp_group.setLayout(temp_vbox)
        control_layout.addWidget(temp_group)
        
        # Night mode toggle
        night_group = QGroupBox("Display Mode")
        night_vbox = QVBoxLayout()
        self.night_checkbox = QSlider(Qt.Horizontal)
        self.night_checkbox.setRange(0, 1)
        self.night_checkbox.setValue(0)
        self.night_checkbox.sliderMoved.connect(self._on_night_mode_changed)
        self.night_checkbox.valueChanged.connect(self._on_night_mode_changed)
        night_vbox.addWidget(QLabel("Day (0) / Night (1)"))
        night_vbox.addWidget(self.night_checkbox)
        night_group.setLayout(night_vbox)
        control_layout.addWidget(night_group)
        
        # DEMO Mode
        demo_group = QGroupBox("DEMO Mode")
        demo_vbox = QVBoxLayout()

        self.demo_button = QPushButton("▶️ START DEMO")
        self.demo_button.setStyleSheet("font-size: 14pt; padding: 12px; background-color: #4CAF50; color: white; font-weight: bold; border-radius: 6px;")
        self.demo_button.clicked.connect(self._start_demo)
        demo_vbox.addWidget(self.demo_button)

        self.demo_status_label = QLabel("Press START DEMO to begin")
        self.demo_status_label.setStyleSheet("font-size: 11pt; color: #666; font-style: italic;")
        demo_vbox.addWidget(self.demo_status_label)

        demo_group.setLayout(demo_vbox)
        control_layout.addWidget(demo_group)

        # Needle Center Calibration
        needle_group = QGroupBox("Needle Center Calibration")
        needle_vbox = QVBoxLayout()
        
        needle_vbox.addWidget(QLabel("Select Gauge:"))
        self.gauge_select = QComboBox()
        self.gauge_select.addItems(["Tachometer", "Speedometer", "Fuel"])
        self.gauge_select.currentIndexChanged.connect(self._on_gauge_select_changed)
        needle_vbox.addWidget(self.gauge_select)
        
        needle_vbox.addWidget(QLabel("Center X (0.0-1.0):"))
        self.needle_x_spin = QDoubleSpinBox()
        self.needle_x_spin.setRange(0.0, 1.0)
        self.needle_x_spin.setSingleStep(0.01)
        self.needle_x_spin.setValue(0.5)
        self.needle_x_spin.valueChanged.connect(self._on_needle_center_changed)
        needle_vbox.addWidget(self.needle_x_spin)
        
        needle_vbox.addWidget(QLabel("Center Y (0.0-1.0):"))
        self.needle_y_spin = QDoubleSpinBox()
        self.needle_y_spin.setRange(0.0, 1.0)
        self.needle_y_spin.setSingleStep(0.01)
        self.needle_y_spin.setValue(0.5)
        self.needle_y_spin.valueChanged.connect(self._on_needle_center_changed)
        needle_vbox.addWidget(self.needle_y_spin)
        
        needle_vbox.addWidget(QLabel("Needle Pivot X (0.0-1.0):"))
        self.needle_pivot_x_spin = QDoubleSpinBox()
        self.needle_pivot_x_spin.setRange(0.0, 1.0)
        self.needle_pivot_x_spin.setSingleStep(0.01)
        self.needle_pivot_x_spin.setValue(0.5)
        self.needle_pivot_x_spin.valueChanged.connect(self._on_needle_pivot_changed)
        needle_vbox.addWidget(self.needle_pivot_x_spin)
        
        needle_vbox.addWidget(QLabel("Needle Pivot Y (0.0-1.0):"))
        self.needle_pivot_y_spin = QDoubleSpinBox()
        self.needle_pivot_y_spin.setRange(0.0, 1.0)
        self.needle_pivot_y_spin.setSingleStep(0.01)
        self.needle_pivot_y_spin.setValue(1.0)
        self.needle_pivot_y_spin.valueChanged.connect(self._on_needle_pivot_changed)
        needle_vbox.addWidget(self.needle_pivot_y_spin)
        
        needle_group.setLayout(needle_vbox)
        control_layout.addWidget(needle_group)
        
        # Needle Scale Controls
        scale_group = QGroupBox("Needle Scale")
        scale_vbox = QVBoxLayout()
        
        scale_vbox.addWidget(QLabel("Tachometer Needle Scale:"))
        self.tach_scale_slider = QSlider(Qt.Horizontal)
        self.tach_scale_slider.setRange(50, 400)  # 0.5x to 4.0x
        tach_scale = tach_cal.get('needle_scale', 1.0) if tach_cal else 1.0
        self.tach_scale_slider.setValue(int(tach_scale * 100))
        self.tach_scale_slider.valueChanged.connect(lambda v: self._on_needle_scale_changed(0, v))
        self.tach_scale_label = QLabel(f"{self.tach_scale_slider.value() / 100:.2f}x")
        scale_vbox.addWidget(self.tach_scale_slider)
        scale_vbox.addWidget(self.tach_scale_label)
        
        scale_vbox.addWidget(QLabel("Speedometer Needle Scale:"))
        self.speed_scale_slider = QSlider(Qt.Horizontal)
        self.speed_scale_slider.setRange(50, 400)
        speed_scale = speed_cal.get('needle_scale', 1.0) if speed_cal else 1.0
        self.speed_scale_slider.setValue(int(speed_scale * 100))
        self.speed_scale_slider.valueChanged.connect(lambda v: self._on_needle_scale_changed(1, v))
        self.speed_scale_label = QLabel(f"{self.speed_scale_slider.value() / 100:.2f}x")
        scale_vbox.addWidget(self.speed_scale_slider)
        scale_vbox.addWidget(self.speed_scale_label)
        
        scale_vbox.addWidget(QLabel("Fuel Needle Scale:"))
        self.fuel_scale_slider = QSlider(Qt.Horizontal)
        self.fuel_scale_slider.setRange(50, 400)
        fuel_scale = fuel_cal.get('needle_scale', 1.0) if fuel_cal else 1.0
        self.fuel_scale_slider.setValue(int(fuel_scale * 100))
        self.fuel_scale_slider.valueChanged.connect(lambda v: self._on_needle_scale_changed(2, v))
        self.fuel_scale_label = QLabel(f"{self.fuel_scale_slider.value() / 100:.2f}x")
        scale_vbox.addWidget(self.fuel_scale_slider)
        scale_vbox.addWidget(self.fuel_scale_label)
        
        scale_vbox.addWidget(QLabel("Water Needle Scale:"))
        self.water_scale_slider = QSlider(Qt.Horizontal)
        self.water_scale_slider.setRange(50, 400)
        # Load water needle scale from fuel config
        water_scale = water_cal.get('needle_scale', 1.0) if water_cal else 1.0
        self.water_scale_slider.setValue(int(water_scale * 100))
        self.water_scale_slider.valueChanged.connect(self._on_water_scale_changed)
        self.water_scale_label = QLabel(f"{self.water_scale_slider.value() / 100:.2f}x")
        scale_vbox.addWidget(self.water_scale_slider)
        scale_vbox.addWidget(self.water_scale_label)
        
        save_scale_btn = QPushButton("Save Needle Scales")
        save_scale_btn.clicked.connect(self._save_needle_scales)
        scale_vbox.addWidget(save_scale_btn)
        
        scale_group.setLayout(scale_vbox)
        control_layout.addWidget(scale_group)
        
        control_layout.addStretch()
        
        # Wrap controls in scroll area
        control_widget = QWidget()
        control_widget.setLayout(control_layout)
        
        scroll_area = QScrollArea()
        scroll_area.setWidget(control_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumWidth(400)
        
        preview_layout.addWidget(scroll_area)
        preview_tab.setLayout(preview_layout)
        tabs.addTab(preview_tab, "Preview & Settings")
        
        # Tab 2: Calibration Tool (load when needed)
        self.calibrator_tab = None
        calibrator_tab_widget = QWidget()
        calibrator_layout = QVBoxLayout()
        load_calibrator_btn = QPushButton("Load Calibration Tool")
        load_calibrator_btn.clicked.connect(self._load_calibrator)
        calibrator_layout.addWidget(load_calibrator_btn)
        calibrator_layout.addStretch()
        calibrator_tab_widget.setLayout(calibrator_layout)
        tabs.addTab(calibrator_tab_widget, "Calibration Tool")
        
        main_layout.addWidget(tabs)
        central.setLayout(main_layout)
        self.setCentralWidget(central)
        
        # Initialize demo state
        self.demo_keyframes = self._create_demo_keyframes()
        self.demo_idle_rpm = 900
        self.demo_idle_fluct = 50
        self.demo_idle_freq_hz = 1.2
        self.demo_idle_windows = [
            (0.0, 3.0),
            (64.5, 65.0),
        ]
        self.demo_accel_windows = [
            {"start": 7.0, "end": 9.0, "rpm_start": 2000, "rpm_end": 7200, "speed_start": 0, "speed_end": 65},
            {"start": 10.5, "end": 13.5, "rpm_start": 2000, "rpm_end": 7200, "speed_start": 62, "speed_end": 105},
            {"start": 15.0, "end": 18.0, "rpm_start": 2500, "rpm_end": 7200, "speed_start": 102, "speed_end": 145},
            {"start": 19.5, "end": 22.5, "rpm_start": 3000, "rpm_end": 7200, "speed_start": 141, "speed_end": 193},
            {"start": 24.0, "end": 27.0, "rpm_start": 3500, "rpm_end": 7200, "speed_start": 189, "speed_end": 255},
            {"start": 28.5, "end": 34.5, "rpm_start": 4000, "rpm_end": 10000, "speed_start": 250, "speed_end": 320},
        ]
        self.demo_bounce_windows = [
            (8.1, 9.0, 7200),
            (12.6, 13.5, 7200),
            (17.1, 18.0, 7200),
            (21.6, 22.5, 7200),
            (26.1, 27.0, 7200),
            (33.6, 34.5, 10000),
        ]
        self.demo_running = False
        self.demo_timer = QTimer()
        self.demo_timer.timeout.connect(self._update_demo)
        self.demo_elapsed_time = 0.0
        self.demo_frame_interval = 50  # ms
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_display)
        self.timer.start(16)  # ~60 FPS
        
        # Store config paths
        self.tach_config_path = config_dir / "tachometer.json"
        self.speed_config_path = config_dir / "speedometer.json"
        self.fuel_config_path = config_dir / "fuel.json"
    
    def _load_calibrator(self):
        """Lazy load the calibration tool"""
        if self.calibrator_tab is not None:
            return  # Already loaded
        
        try:
            from src.gauge_calibrator_v2 import GaugeCalibratorV2
            
            # Find the calibrator tab
            for i in range(self.centralWidget().findChild(QTabWidget).count()):
                if self.centralWidget().findChild(QTabWidget).tabText(i) == "Calibration Tool":
                    # Replace the placeholder with actual calibrator
                    self.calibrator_tab = GaugeCalibratorV2()
                    tabs = self.centralWidget().findChild(QTabWidget)
                    tabs.removeTab(i)
                    tabs.insertTab(i, self.calibrator_tab.centralWidget(), "Calibration Tool")
                    logger.info("✅ Calibration tool loaded")
                    break
        except Exception as e:
            logger.error(f"❌ Failed to load calibrator: {e}")

    def _load_config(self, config_path: Path):
        if not config_path.exists():
            return {}
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"⚠️ Failed to load config {config_path}: {e}")
            return {}

    def _get_needle_calibration(self, config: dict, needle_id: str):
        return config.get("needle_calibrations", {}).get(needle_id, {})

    def _resolve_needle_image_path(self, needle_cal: dict, default_path: str) -> str:
        """Resolve needle image path, preferring SVG over PNG"""
        if not needle_cal:
            # Check if SVG version of default exists
            svg_path = default_path.replace('.png', '.svg')
            if Path(svg_path).exists():
                return svg_path
            return default_path
        
        needle_path = needle_cal.get("needle_image_path")
        if not needle_path:
            # Check if SVG version of default exists
            svg_path = default_path.replace('.png', '.svg')
            if Path(svg_path).exists():
                return svg_path
            return default_path
        
        path = Path(needle_path)
        if not path.is_absolute():
            path = (Path(__file__).parent / path).resolve()
        
        # If path exists, return it
        if path.exists():
            return str(path)
        
        # Try SVG version
        svg_path = Path(str(path).replace('.png', '.svg'))
        if svg_path.exists():
            return str(svg_path)
        
        # Check if SVG version of default exists
        svg_default = default_path.replace('.png', '.svg')
        if Path(svg_default).exists():
            return svg_default
        
        return default_path

    def _get_calibration_range(self, needle_cal: dict, fallback_min: float, fallback_max: float):
        min_value = needle_cal.get("min_value") if needle_cal else None
        max_value = needle_cal.get("max_value") if needle_cal else None

        points = needle_cal.get("calibration_points", []) if needle_cal else []
        values = [p.get("value") for p in points if isinstance(p, dict) and "value" in p]
        if values:
            min_points = min(values)
            max_points = max(values)
            if min_value is None or min_value > min_points:
                min_value = min_points
            if max_value is None or max_value < max_points:
                max_value = max_points

        if min_value is None:
            min_value = fallback_min
        if max_value is None:
            max_value = fallback_max
        if max_value < min_value:
            min_value, max_value = max_value, min_value

        return min_value, max_value

    def _clamp_value(self, value: float, min_value: float, max_value: float) -> float:
        return max(min_value, min(value, max_value))
        
    
    def _on_gauge_select_changed(self, index):
        """Update needle center controls for selected gauge"""
        gauges = [self.tach, self.speed, self.fuel]
        gauge = gauges[index]
        
        self.needle_x_spin.blockSignals(True)
        self.needle_y_spin.blockSignals(True)
        self.needle_pivot_x_spin.blockSignals(True)
        self.needle_pivot_y_spin.blockSignals(True)
        
        self.needle_x_spin.setValue(gauge.needle_center_offset[0])
        self.needle_y_spin.setValue(gauge.needle_center_offset[1])
        self.needle_pivot_x_spin.setValue(gauge.needle_pivot[0])
        self.needle_pivot_y_spin.setValue(gauge.needle_pivot[1])
        
        self.needle_x_spin.blockSignals(False)
        self.needle_y_spin.blockSignals(False)
        self.needle_pivot_x_spin.blockSignals(False)
        self.needle_pivot_y_spin.blockSignals(False)
    
    def _on_needle_pivot_changed(self, value):
        """Update needle pivot for selected gauge"""
        index = self.gauge_select.currentIndex()
        gauges = [self.tach, self.speed, self.fuel]
        gauge = gauges[index]
        
        x = self.needle_pivot_x_spin.value()
        y = self.needle_pivot_y_spin.value()
        gauge.set_needle_pivot(x, y)
    
    def _on_needle_center_changed(self, value):
        """Update needle center for selected gauge"""
        index = self.gauge_select.currentIndex()
        gauges = [self.tach, self.speed, self.fuel]
        gauge = gauges[index]
        
        x = self.needle_x_spin.value()
        y = self.needle_y_spin.value()
        gauge.set_needle_center(x, y)
    
    def _on_needle_scale_changed(self, gauge_index, value):
        """Update needle scale for selected gauge"""
        gauges = [self.tach, self.speed, self.fuel]
        labels = [self.tach_scale_label, self.speed_scale_label, self.fuel_scale_label]
        
        scale = value / 100.0
        gauges[gauge_index].needle_scale = scale
        labels[gauge_index].setText(f"{scale:.2f}x")
    
    def _on_water_scale_changed(self, value):
        """Update water needle scale"""
        scale = value / 100.0
        self.fuel.water_needle_scale = scale
        self.water_scale_label.setText(f"{scale:.2f}x")
    
    def _save_needle_scales(self):
        """Save needle scales to gauge config files"""
        configs = [
            (self.tach_config_path, "main", self.tach.needle_scale, self.tach, None),
            (self.speed_config_path, "main", self.speed.needle_scale, self.speed, None),
            (self.fuel_config_path, "fuel", self.fuel.needle_scale, self.fuel, self.fuel.water_needle_scale),
        ]
        
        saved_configs = []
        errors = []

        for config_path, needle_id, scale, gauge, water_scale in configs:
            try:
                if config_path.exists():
                    with open(config_path, 'r') as f:
                        data = json.load(f)
                    
                    # Save primary needle scale
                    if 'needle_calibrations' in data and needle_id in data['needle_calibrations']:
                        data['needle_calibrations'][needle_id]['needle_scale'] = scale
                        logger.info(f"✅ Saved {needle_id} needle scale ({scale:.2f}x) to {config_path.name}")
                    
                    # Save water needle scale (fuel gauge only)
                    if water_scale is not None and 'water' in data.get('needle_calibrations', {}):
                        data['needle_calibrations']['water']['needle_scale'] = water_scale
                        logger.info(f"✅ Saved water needle scale ({water_scale:.2f}x) to {config_path.name}")
                    
                    # Save custom named needle scales
                    if hasattr(gauge, 'named_needles'):
                        for custom_needle_name, needle_data in gauge.named_needles.items():
                            custom_scale = needle_data.get('scale', 1.0)
                            if custom_needle_name in data['needle_calibrations']:
                                data['needle_calibrations'][custom_needle_name]['needle_scale'] = custom_scale
                                logger.info(f"✅ Saved {custom_needle_name} scale ({custom_scale:.2f}x) to {config_path.name}")
                    
                    with open(config_path, 'w') as f:
                        json.dump(data, f, indent=2)

                    saved_configs.append(config_path.name)
                        
            except Exception as e:
                logger.error(f"❌ Failed to save {config_path.name}: {e}")
                errors.append(f"{config_path.name}: {e}")
        
        logger.info("💾 All needle scales saved")

        if errors:
            saved_text = ", ".join(saved_configs) if saved_configs else "None"
            error_text = "\n".join(errors)
            QMessageBox.warning(
                self,
                "Needle Scale Save Issues",
                f"Saved: {saved_text}\nErrors:\n{error_text}"
            )
        elif saved_configs:
            QMessageBox.information(
                self,
                "Needle Scales Saved",
                f"Saved scales to: {', '.join(saved_configs)}"
            )

    
    def _on_tach_changed(self, value):
        self.tach.target_value = value
        self.tach_label.setText(f"{value} RPM")
    
    def _on_speed_changed(self, value):
        self.speed.target_value = value
        self.speed_label.setText(f"{value} km/h")
    
    def _on_fuel_changed(self, value):
        self.fuel.target_value = value
        self.fuel_label.setText(f"{value}%")
    
    def _on_temp_changed(self, value):
        self.fuel.set_temperature(value)
        self.temp_label.setText(f"{value}°C")
    
    def _on_night_mode_changed(self, value):
        night_mode = value == 1
        self.tach.night_mode = night_mode
        self.speed.night_mode = night_mode
        self.fuel.night_mode = night_mode
    
    def _update_display(self):
        """Update gauge display"""
        self.tach.update()
        self.speed.update()
        self.fuel.update()
    
    def _create_demo_keyframes(self):
        """Create demo animation keyframes: (time_sec, rpm, speed, fuel, water)"""
        keyframes = [
            # Idle phase (0-3s): sitting at 900 rpm
            (0.0, 900, 0, 100, 50),
            (3.0, 900, 0, 100, 50),
            
            # Rev testing (3-7s): quick revs to demonstrate tach
            (3.3, 3000, 0, 100, 50),    # Rev to 3000 in 0.3s
            (4.3, 900, 0, 100, 50),     # Fall to 900 in 1s
            (4.6, 4000, 0, 100, 50),    # Rev to 4000 in 0.3s
            (5.6, 900, 0, 100, 50),     # Fall to 900 in 1s
            (5.9, 6000, 0, 100, 50),    # Rev to 6000 in 0.3s
            (6.9, 900, 0, 100, 50),     # Fall to 900 in 1s
            (7.0, 2000, 0, 100, 50),    # Ready for 1st gear
            
            # 1st Gear (7-9s): 2000→7200 rpm in 2s, 0→65 km/h
            (7.0, 2000, 0, 100, 50),
            (8.1, 7200, 36, 89, 62),
            (9.0, 7200, 65, 80, 71),
            
            # Rev downfall (9-10.5s): 7000→2000 rpm over 1.5s
            (10.5, 2000, 62, 81, 70),
            
            # 2nd Gear (10.5-13.5s): 2000→7200 rpm in 3s, 62→105 km/h
            (10.5, 2000, 62, 81, 70),
            (12.6, 7200, 92, 71, 80),
            (13.5, 7200, 105, 67, 84),
            
            # Rev downfall (13.5-15s): 7500→2500 rpm over 1.5s
            (15.0, 2500, 102, 68, 83),
            
            # 3rd Gear (15-18s): 2500→7200 rpm in 3s, 102→145 km/h
            (15.0, 2500, 102, 68, 83),
            (17.1, 7200, 132, 59, 92),
            (18.0, 7200, 145, 55, 96),
            
            # Rev downfall (18-19.5s): 7500→3000 rpm over 1.5s
            (19.5, 3000, 141, 56, 95),
            
            # 4th Gear (19.5-22.5s): 3000→7200 rpm in 3s, 141→193 km/h
            (19.5, 3000, 141, 56, 95),
            (21.6, 7200, 177, 45, 107),
            (22.5, 7200, 193, 40, 112),
            
            # Rev downfall (22.5-24s): 7500→3500 rpm over 1.5s
            (24.0, 3500, 189, 41, 110),
            
            # 5th Gear (24-27s): 3500→7200 rpm in 3s, 189→255 km/h
            (24.0, 3500, 189, 41, 110),
            (26.1, 7200, 235, 26, 124),
            (27.0, 7200, 255, 20, 130),
            
            # Rev downfall (27-28.5s): 8000→4000 rpm over 1.5s
            (28.5, 4000, 250, 22, 130),
            
            # 6th Gear (28.5-34.5s): 4000→10000 rpm in 6s, 250→320 km/h
            (28.5, 4000, 250, 22, 130),
            (33.6, 10000, 310, 3, 130),
            (34.5, 10000, 320, 0, 130),
            
            # Deceleration (34.5-65s): constant rate down to 0
            (34.5, 10000, 320, 0, 130),
            (65.0, 0, 0, 0, 130),
        ]
        return keyframes

    
    def _interpolate_value(self, keyframes, time, value_index):
        """Interpolate a value at a given time between keyframes"""
        if time <= keyframes[0][0]:
            return keyframes[0][value_index]
        if time >= keyframes[-1][0]:
            return keyframes[-1][value_index]
        
        # Find surrounding keyframes
        for i in range(len(keyframes) - 1):
            kf1 = keyframes[i]
            kf2 = keyframes[i + 1]
            t1 = kf1[0]
            t2 = kf2[0]
            
            if t1 <= time <= t2:
                # Linear interpolation
                if t2 == t1:
                    return kf1[value_index]
                ratio = (time - t1) / (t2 - t1)
                v1 = kf1[value_index]
                v2 = kf2[value_index]
                return v1 + (v2 - v1) * ratio
        
        return keyframes[-1][value_index]

    def _apply_idle_fluctuation(self, time, rpm):
        for start, end in self.demo_idle_windows:
            if start <= time <= end:
                return self.demo_idle_rpm + self.demo_idle_fluct * math.sin(2 * math.pi * self.demo_idle_freq_hz * time)
        return rpm

    def _apply_redline_soft_ramp(self, time, rpm, speed):
        return rpm, speed

    def _apply_limiter_bounce(self, time, rpm):
        for start, end, limit in self.demo_bounce_windows:
            if start <= time <= end:
                duration = end - start
                if duration <= 0:
                    return rpm
                bounce_count = 4
                bounce_period = duration / bounce_count
                phase = (time - start) / bounce_period
                frac = phase - math.floor(phase)
                triangle = 1.0 - abs(2.0 * frac - 1.0)
                return limit - 200.0 * (1.0 - triangle)
        return rpm
    
    def _start_demo(self):
        """Start the demo mode"""
        if self.demo_running:
            # Stop demo
            self.demo_timer.stop()
            self.demo_running = False
            self.demo_button.setText("▶️ START DEMO")
            self.demo_button.setStyleSheet("font-size: 14pt; padding: 12px; background-color: #4CAF50; color: white; font-weight: bold; border-radius: 6px;")
            self.demo_status_label.setText("Demo stopped")
        else:
            # Start demo
            self.demo_running = True
            self.demo_elapsed_time = 0.0
            self.fuel.named_needles.pop("water", None)
            self.demo_button.setText("⏹️ STOP DEMO")
            self.demo_button.setStyleSheet("font-size: 14pt; padding: 12px; background-color: #f44336; color: white; font-weight: bold; border-radius: 6px;")
            self.demo_timer.start(self.demo_frame_interval)
            logger.info("🎬 Demo started")
    
    def _update_demo(self):
        """Update demo state at each timer tick"""
        self.demo_elapsed_time += self.demo_frame_interval / 1000.0
        
        # Get current values by interpolating keyframes
        rpm = self._interpolate_value(self.demo_keyframes, self.demo_elapsed_time, 1)
        speed = self._interpolate_value(self.demo_keyframes, self.demo_elapsed_time, 2)
        fuel = self._interpolate_value(self.demo_keyframes, self.demo_elapsed_time, 3)
        water = self._interpolate_value(self.demo_keyframes, self.demo_elapsed_time, 4)

        rpm, speed = self._apply_redline_soft_ramp(self.demo_elapsed_time, rpm, speed)
        rpm = self._apply_limiter_bounce(self.demo_elapsed_time, rpm)
        rpm = self._apply_idle_fluctuation(self.demo_elapsed_time, rpm)
        
        # Update gauges
        self.tach.target_value = rpm
        self.tach_slider.blockSignals(True)
        self.tach_slider.setValue(int(rpm))
        self.tach_slider.blockSignals(False)
        self.tach_label.setText(f"{int(rpm)} RPM")
        self.tach.update()
        
        self.speed.target_value = speed
        self.speed_slider.blockSignals(True)
        self.speed_slider.setValue(int(speed))
        self.speed_slider.blockSignals(False)
        self.speed_label.setText(f"{int(speed)} km/h")
        self.speed.update()
        
        self.fuel.target_value = fuel
        self.fuel_slider.blockSignals(True)
        self.fuel_slider.setValue(int(fuel))
        self.fuel_slider.blockSignals(False)
        self.fuel_label.setText(f"{int(fuel)}%")
        self.fuel.update()
        
        # Update water gauge
        self.fuel.set_temperature(water)
        self.temp_slider.blockSignals(True)
        self.temp_slider.setValue(int(water))
        self.temp_slider.blockSignals(False)
        self.temp_label.setText(f"{int(water)}°C")
        
        # Update status
        total_time = self.demo_keyframes[-1][0]
        progress = (self.demo_elapsed_time / total_time) * 100 if total_time > 0 else 0
        self.demo_status_label.setText(f"Time: {self.demo_elapsed_time:.1f}s | Progress: {progress:.0f}%")
        
        # Stop demo when finished
        if self.demo_elapsed_time >= total_time:
            self.demo_timer.stop()
            self.demo_running = False
            self.demo_button.setText("▶️ START DEMO")
            self.demo_button.setStyleSheet("font-size: 14pt; padding: 12px; background-color: #4CAF50; color: white; font-weight: bold; border-radius: 6px;")
            self.demo_status_label.setText("Demo complete!")
            logger.info("✅ Demo finished")


def main():
    app = QApplication(sys.argv)
    window = GaugePreview()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
