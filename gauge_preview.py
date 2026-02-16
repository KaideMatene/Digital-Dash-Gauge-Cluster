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
    QScrollArea, QMessageBox, QToolBox, QCheckBox
)
from PyQt5.QtCore import Qt, QTimer

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from image_gauge import ImageTachometer, ImageSpeedometer, ImageFuelGauge
from config_utils import ensure_default_configs, load_gauge_config
from src.gauge_calibrator_v2 import GaugeCalibratorV2

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

        # Right: Controls (organized in collapsible toolbox)
        control_layout = QVBoxLayout()

        # Refresh button at top
        refresh_btn = QPushButton("🔄 Reload Calibrations from Disk")
        refresh_btn.setStyleSheet("font-size: 11pt; padding: 8px; background-color: #2196F3; color: white; font-weight: bold; border-radius: 4px;")
        refresh_btn.clicked.connect(self._reload_all_calibrations)
        control_layout.addWidget(refresh_btn)

        # Toolbox for organized sections
        toolbox = QToolBox()

        # ===== SECTION 1: Gauge Values =====
        values_widget = QWidget()
        values_layout = QVBoxLayout()

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
        values_layout.addWidget(tach_group)

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
        values_layout.addWidget(speed_group)

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
        values_layout.addWidget(fuel_group)

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
        values_layout.addWidget(temp_group)

        values_widget.setLayout(values_layout)
        toolbox.addItem(values_widget, "📊 Gauge Values")

        # ===== SECTION 2: Display Settings =====
        display_widget = QWidget()
        display_layout = QVBoxLayout()

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
        display_layout.addWidget(night_group)

        # Gauge visibility toggles
        visibility_group = QGroupBox("Gauge Visibility")
        visibility_layout = QVBoxLayout()

        self.tach_visible_check = QCheckBox("Show Tachometer")
        self.tach_visible_check.setChecked(True)
        self.tach_visible_check.stateChanged.connect(lambda state: self.tach.setVisible(state == Qt.Checked))
        visibility_layout.addWidget(self.tach_visible_check)

        self.speed_visible_check = QCheckBox("Show Speedometer")
        self.speed_visible_check.setChecked(True)
        self.speed_visible_check.stateChanged.connect(lambda state: self.speed.setVisible(state == Qt.Checked))
        visibility_layout.addWidget(self.speed_visible_check)

        self.fuel_visible_check = QCheckBox("Show Fuel Gauge")
        self.fuel_visible_check.setChecked(True)
        self.fuel_visible_check.stateChanged.connect(lambda state: self.fuel.setVisible(state == Qt.Checked))
        visibility_layout.addWidget(self.fuel_visible_check)

        visibility_group.setLayout(visibility_layout)
        display_layout.addWidget(visibility_group)

        display_widget.setLayout(display_layout)
        toolbox.addItem(display_widget, "🎨 Display Settings")

        # ===== SECTION 2.5: Symbol Visibility =====
        symbol_widget = QWidget()
        symbol_layout = QVBoxLayout()

        symbol_info = QLabel("Toggle and configure warning lights")
        symbol_info.setStyleSheet("font-style: italic; color: #666; font-size: 10pt;")
        symbol_layout.addWidget(symbol_info)

        # Symbol scale control
        symbol_scale_group = QGroupBox("Symbol Scale")
        symbol_scale_layout = QVBoxLayout()

        symbol_scale_layout.addWidget(QLabel("Adjust warning light size:"))
        symbol_scale_row = QHBoxLayout()
        self.symbol_scale_spin = QDoubleSpinBox()
        self.symbol_scale_spin.setRange(0.1, 3.0)
        self.symbol_scale_spin.setSingleStep(0.1)
        self.symbol_scale_spin.setDecimals(1)
        self.symbol_scale_spin.setValue(1.0)
        self.symbol_scale_spin.valueChanged.connect(self._on_symbol_scale_changed)
        symbol_scale_row.addWidget(self.symbol_scale_spin)
        self.symbol_scale_label = QLabel("1.0x")
        symbol_scale_row.addWidget(self.symbol_scale_label)
        symbol_scale_layout.addLayout(symbol_scale_row)

        symbol_scale_group.setLayout(symbol_scale_layout)
        symbol_layout.addWidget(symbol_scale_group)

        # Dictionary to store symbol checkboxes and scale spinboxes for dynamic updates
        self.symbol_checkboxes = {}
        self.symbol_scale_spinboxes = {}  # Per-symbol scale controls
        self.symbol_row_widgets = {}  # Container widgets for each symbol row
        self.symbol_group_layout = None  # Store reference for dynamic updates

        # Symbol visibility toggles (populated dynamically from gauge configs)
        symbol_group = QGroupBox("Symbol Visibility Toggles")
        symbol_grid_layout = QVBoxLayout()
        self.symbol_group_layout = symbol_grid_layout  # Store reference

        # Symbols will be populated dynamically in _populate_symbol_checkboxes()

        # Add refresh symbols button
        refresh_symbols_btn = QPushButton("🔄 Refresh Symbol List")
        refresh_symbols_btn.setStyleSheet("font-size: 9pt; padding: 6px;")
        refresh_symbols_btn.clicked.connect(self._refresh_symbol_list)
        symbol_grid_layout.addWidget(refresh_symbols_btn)

        symbol_group.setLayout(symbol_grid_layout)
        symbol_layout.addWidget(symbol_group)

        # Save button for symbols
        save_symbol_btn = QPushButton("💾 Save Symbol Settings")
        save_symbol_btn.setStyleSheet("font-weight: bold; padding: 8px;")
        save_symbol_btn.clicked.connect(self._save_symbol_settings)
        symbol_layout.addWidget(save_symbol_btn)

        symbol_widget.setLayout(symbol_layout)
        toolbox.addItem(symbol_widget, "⚠️ Symbols & Warnings")

        # ===== SECTION 3: DEMO Mode =====
        demo_widget = QWidget()
        demo_layout = QVBoxLayout()

        self.demo_button = QPushButton("▶️ START DEMO")
        self.demo_button.setStyleSheet("font-size: 14pt; padding: 12px; background-color: #4CAF50; color: white; font-weight: bold; border-radius: 6px;")
        self.demo_button.clicked.connect(self._start_demo)
        demo_layout.addWidget(self.demo_button)

        self.demo_status_label = QLabel("Press START DEMO to begin")
        self.demo_status_label.setStyleSheet("font-size: 11pt; color: #666; font-style: italic;")
        demo_layout.addWidget(self.demo_status_label)

        demo_widget.setLayout(demo_layout)
        toolbox.addItem(demo_widget, "🎬 DEMO Mode")

        # ===== SECTION 4: Needle Positioning (Advanced) =====
        needle_pos_widget = QWidget()
        needle_pos_layout = QVBoxLayout()

        needle_pos_layout.addWidget(QLabel("Select Gauge:"))
        self.gauge_select = QComboBox()
        self.gauge_select.addItems(["Tachometer", "Speedometer", "Fuel"])
        self.gauge_select.currentIndexChanged.connect(self._on_gauge_select_changed)
        needle_pos_layout.addWidget(self.gauge_select)

        needle_pos_layout.addWidget(QLabel("Center X (0.0-1.0):"))
        self.needle_x_spin = QDoubleSpinBox()
        self.needle_x_spin.setRange(0.0, 1.0)
        self.needle_x_spin.setSingleStep(0.001)
        self.needle_x_spin.setDecimals(3)
        self.needle_x_spin.setValue(0.5)
        self.needle_x_spin.valueChanged.connect(self._on_needle_center_changed)
        needle_pos_layout.addWidget(self.needle_x_spin)

        needle_pos_layout.addWidget(QLabel("Center Y (0.0-1.0):"))
        self.needle_y_spin = QDoubleSpinBox()
        self.needle_y_spin.setRange(0.0, 1.0)
        self.needle_y_spin.setSingleStep(0.001)
        self.needle_y_spin.setDecimals(3)
        self.needle_y_spin.setValue(0.5)
        self.needle_y_spin.valueChanged.connect(self._on_needle_center_changed)
        needle_pos_layout.addWidget(self.needle_y_spin)

        needle_pos_layout.addWidget(QLabel("Needle Pivot X (0.0-1.0):"))
        self.needle_pivot_x_spin = QDoubleSpinBox()
        self.needle_pivot_x_spin.setRange(0.0, 1.0)
        self.needle_pivot_x_spin.setSingleStep(0.001)
        self.needle_pivot_x_spin.setDecimals(3)
        self.needle_pivot_x_spin.setValue(0.5)
        self.needle_pivot_x_spin.valueChanged.connect(self._on_needle_pivot_changed)
        needle_pos_layout.addWidget(self.needle_pivot_x_spin)

        needle_pos_layout.addWidget(QLabel("Needle Pivot Y (0.0-1.0):"))
        self.needle_pivot_y_spin = QDoubleSpinBox()
        self.needle_pivot_y_spin.setRange(0.0, 1.0)
        self.needle_pivot_y_spin.setSingleStep(0.001)
        self.needle_pivot_y_spin.setDecimals(3)
        self.needle_pivot_y_spin.setValue(1.0)
        self.needle_pivot_y_spin.valueChanged.connect(self._on_needle_pivot_changed)
        needle_pos_layout.addWidget(self.needle_pivot_y_spin)

        needle_pos_widget.setLayout(needle_pos_layout)
        toolbox.addItem(needle_pos_widget, "⚙️ Needle Positioning")

        # ===== SECTION 5: Needle Scale (Advanced) =====
        scale_widget = QWidget()
        scale_layout = QVBoxLayout()

        scale_layout.addWidget(QLabel("Tachometer Needle Scale:"))
        tach_scale_row = QHBoxLayout()
        self.tach_scale_spin = QDoubleSpinBox()
        self.tach_scale_spin.setRange(0.5, 4.0)
        self.tach_scale_spin.setSingleStep(0.01)
        self.tach_scale_spin.setDecimals(2)
        tach_scale = tach_cal.get('needle_scale', 1.0) if tach_cal else 1.0
        self.tach_scale_spin.setValue(tach_scale)
        self.tach_scale_spin.valueChanged.connect(lambda v: self._on_needle_scale_changed_spin(0, v))
        tach_scale_row.addWidget(self.tach_scale_spin)
        self.tach_scale_label = QLabel(f"{tach_scale:.2f}x")
        tach_scale_row.addWidget(self.tach_scale_label)
        scale_layout.addLayout(tach_scale_row)

        scale_layout.addWidget(QLabel("Speedometer Needle Scale:"))
        speed_scale_row = QHBoxLayout()
        self.speed_scale_spin = QDoubleSpinBox()
        self.speed_scale_spin.setRange(0.5, 4.0)
        self.speed_scale_spin.setSingleStep(0.01)
        self.speed_scale_spin.setDecimals(2)
        speed_scale = speed_cal.get('needle_scale', 1.0) if speed_cal else 1.0
        self.speed_scale_spin.setValue(speed_scale)
        self.speed_scale_spin.valueChanged.connect(lambda v: self._on_needle_scale_changed_spin(1, v))
        speed_scale_row.addWidget(self.speed_scale_spin)
        self.speed_scale_label = QLabel(f"{speed_scale:.2f}x")
        speed_scale_row.addWidget(self.speed_scale_label)
        scale_layout.addLayout(speed_scale_row)

        scale_layout.addWidget(QLabel("Fuel Needle Scale:"))
        fuel_scale_row = QHBoxLayout()
        self.fuel_scale_spin = QDoubleSpinBox()
        self.fuel_scale_spin.setRange(0.5, 4.0)
        self.fuel_scale_spin.setSingleStep(0.01)
        self.fuel_scale_spin.setDecimals(2)
        fuel_scale = fuel_cal.get('needle_scale', 1.0) if fuel_cal else 1.0
        self.fuel_scale_spin.setValue(fuel_scale)
        self.fuel_scale_spin.valueChanged.connect(lambda v: self._on_needle_scale_changed_spin(2, v))
        fuel_scale_row.addWidget(self.fuel_scale_spin)
        self.fuel_scale_label = QLabel(f"{fuel_scale:.2f}x")
        fuel_scale_row.addWidget(self.fuel_scale_label)
        scale_layout.addLayout(fuel_scale_row)

        scale_layout.addWidget(QLabel("Water Needle Scale:"))
        water_scale_row = QHBoxLayout()
        self.water_scale_spin = QDoubleSpinBox()
        self.water_scale_spin.setRange(0.5, 4.0)
        self.water_scale_spin.setSingleStep(0.01)
        self.water_scale_spin.setDecimals(2)
        water_scale = water_cal.get('needle_scale', 1.0) if water_cal else 1.0
        self.water_scale_spin.setValue(water_scale)
        self.water_scale_spin.valueChanged.connect(self._on_water_scale_changed_spin)
        water_scale_row.addWidget(self.water_scale_spin)
        self.water_scale_label = QLabel(f"{water_scale:.2f}x")
        water_scale_row.addWidget(self.water_scale_label)
        scale_layout.addLayout(water_scale_row)

        save_scale_btn = QPushButton("💾 Save Needle Scales")
        save_scale_btn.clicked.connect(self._save_needle_scales)
        scale_layout.addWidget(save_scale_btn)

        scale_widget.setLayout(scale_layout)
        toolbox.addItem(scale_widget, "📏 Needle Scale")

        # Set default open section
        toolbox.setCurrentIndex(0)

        control_layout.addWidget(toolbox)
        
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
        
        # Tab 2: Calibration Tool (directly instantiated, auto-loaded on first tab switch)
        self.calibrator_tab = GaugeCalibratorV2()
        self.calibrator_initialized = False  # Track if auto-load has been triggered
        tabs.addTab(self.calibrator_tab.centralWidget(), "Calibration Tool")

        # Connect tab change signal to detect when calibration tab is activated
        tabs.currentChanged.connect(self._on_tab_changed)
        
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
        self.symbol_config_path = config_dir / "symbols.json"

        # Load symbol config
        self._load_symbol_config()

        # Load symbols from gauge configs
        self.gauge_symbols = {
            'tachometer': {},
            'speedometer': {},
            'fuel': {}
        }
        self._load_gauge_symbols()
    
    def _on_tab_changed(self, index):
        """Handle tab switch - auto-load calibrator on first switch to calibration tab"""
        tabs = self.centralWidget().findChild(QTabWidget)
        tab_name = tabs.tabText(index)

        if tab_name == "Calibration Tool" and not self.calibrator_initialized:
            # First time switching to calibration tab - trigger auto-load
            self.calibrator_tab.auto_load_default_gauge()
            self.calibrator_initialized = True
            logger.info("✅ Calibration tool auto-initialized")
        elif tab_name == "Preview & Settings":
            # Switched back to preview - reload calibrations
            self._reload_all_calibrations()
            logger.info("🔄 Preview tab activated - calibrations reloaded")

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
    
    def _on_needle_scale_changed_spin(self, gauge_index, value):
        """Update needle scale for selected gauge using spinbox"""
        gauges = [self.tach, self.speed, self.fuel]
        labels = [self.tach_scale_label, self.speed_scale_label, self.fuel_scale_label]

        gauges[gauge_index].needle_scale = value
        labels[gauge_index].setText(f"{value:.2f}x")

    def _on_water_scale_changed_spin(self, value):
        """Update water needle scale using spinbox"""
        self.fuel.water_needle_scale = value
        self.water_scale_label.setText(f"{value:.2f}x")
    
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

        # Reload configurations to apply changes immediately
        if saved_configs:
            self._reload_gauge_configs()
            logger.info("✅ Configurations reloaded")

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
                f"Saved scales to: {', '.join(saved_configs)}\nChanges applied immediately."
            )

    def _reload_all_calibrations(self):
        """Reload ALL calibrations from disk and update gauges"""
        try:
            # Reload all gauge configurations
            self._reload_gauge_configs()

            # Force all gauges to reload their calibrations from files
            if self.tach_config_path.exists():
                self.tach.load_all_needles_from_file(str(self.tach_config_path), "main")
                logger.info("✅ Reloaded tachometer calibration")

            if self.speed_config_path.exists():
                self.speed.load_all_needles_from_file(str(self.speed_config_path), "main")
                logger.info("✅ Reloaded speedometer calibration")

            if self.fuel_config_path.exists():
                fuel_config = self._load_config(self.fuel_config_path)
                needle_calibrations = fuel_config.get('needle_calibrations', {})
                self.fuel.load_dual_v2_calibration(needle_calibrations)
                logger.info("✅ Reloaded fuel gauge calibrations")

            # Reload symbols
            self._load_gauge_symbols()
            logger.info("✅ Reloaded symbols")

            QMessageBox.information(
                self,
                "Calibrations Reloaded",
                "All gauge calibrations and symbols have been reloaded from disk."
            )

        except Exception as e:
            logger.error(f"❌ Failed to reload calibrations: {e}")
            QMessageBox.warning(
                self,
                "Reload Failed",
                f"Failed to reload calibrations: {str(e)}"
            )

    def _reload_gauge_configs(self):
        """Reload gauge configurations from disk to apply saved changes"""
        try:
            # Reload tachometer config
            tach_config = self._load_config(self.tach_config_path)
            tach_cal = self._get_needle_calibration(tach_config, "main")
            if tach_cal:
                tach_scale = tach_cal.get('needle_scale', 1.0)
                self.tach.needle_scale = tach_scale
                # Update spinbox
                self.tach_scale_spin.blockSignals(True)
                self.tach_scale_spin.setValue(tach_scale)
                self.tach_scale_spin.blockSignals(False)
                self.tach_scale_label.setText(f"{tach_scale:.2f}x")

            # Reload speedometer config
            speed_config = self._load_config(self.speed_config_path)
            speed_cal = self._get_needle_calibration(speed_config, "main")
            if speed_cal:
                speed_scale = speed_cal.get('needle_scale', 1.0)
                self.speed.needle_scale = speed_scale
                # Update spinbox
                self.speed_scale_spin.blockSignals(True)
                self.speed_scale_spin.setValue(speed_scale)
                self.speed_scale_spin.blockSignals(False)
                self.speed_scale_label.setText(f"{speed_scale:.2f}x")

            # Reload fuel config
            fuel_config = self._load_config(self.fuel_config_path)
            fuel_cal = self._get_needle_calibration(fuel_config, "fuel")
            water_cal = self._get_needle_calibration(fuel_config, "water")
            if fuel_cal:
                fuel_scale = fuel_cal.get('needle_scale', 1.0)
                self.fuel.needle_scale = fuel_scale
                # Update spinbox
                self.fuel_scale_spin.blockSignals(True)
                self.fuel_scale_spin.setValue(fuel_scale)
                self.fuel_scale_spin.blockSignals(False)
                self.fuel_scale_label.setText(f"{fuel_scale:.2f}x")
            if water_cal:
                water_scale = water_cal.get('needle_scale', 1.0)
                self.fuel.water_needle_scale = water_scale
                # Update spinbox
                self.water_scale_spin.blockSignals(True)
                self.water_scale_spin.setValue(water_scale)
                self.water_scale_spin.blockSignals(False)
                self.water_scale_label.setText(f"{water_scale:.2f}x")

        except Exception as e:
            logger.error(f"❌ Failed to reload configurations: {e}")

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

    def _on_symbol_scale_changed(self, value):
        """Update symbol scale"""
        self.symbol_scale_label.setText(f"{value:.1f}x")
        logger.info(f"Symbol scale changed to {value:.1f}x")
        # TODO: Apply scale to actual symbols when rendering system is implemented

    def _load_symbol_config(self):
        """Load symbol configuration from file"""
        if not self.symbol_config_path.exists():
            # Create default config
            default_config = {
                "symbol_scale": 1.0,
                "symbol_positions": {},
                "symbol_visibility": {}
            }
            with open(self.symbol_config_path, 'w') as f:
                json.dump(default_config, f, indent=2)
            logger.info("✅ Created default symbols config")
            return

        try:
            config = self._load_config(self.symbol_config_path)
            symbol_scale = config.get('symbol_scale', 1.0)

            # Update UI
            self.symbol_scale_spin.blockSignals(True)
            self.symbol_scale_spin.setValue(symbol_scale)
            self.symbol_scale_spin.blockSignals(False)
            self.symbol_scale_label.setText(f"{symbol_scale:.1f}x")

            # Load visibility states
            symbol_visibility = config.get('symbol_visibility', {})
            for symbol_id, visible in symbol_visibility.items():
                if symbol_id in self.symbol_checkboxes:
                    checkbox = self.symbol_checkboxes[symbol_id]
                    checkbox.blockSignals(True)
                    checkbox.setChecked(visible)
                    checkbox.blockSignals(False)

            logger.info(f"✅ Loaded symbol config: scale={symbol_scale:.1f}x")
        except Exception as e:
            logger.error(f"❌ Failed to load symbol config: {e}")

    def _save_symbol_settings(self):
        """Save symbol settings to gauge config files"""
        try:
            saved_files = []
            errors = []

            # Save visibility to each gauge config file
            for gauge_name in ['tachometer', 'speedometer', 'fuel']:
                config_path_map = {
                    'tachometer': self.tach_config_path,
                    'speedometer': self.speed_config_path,
                    'fuel': self.fuel_config_path
                }

                config_path = config_path_map.get(gauge_name)
                if not config_path or not config_path.exists():
                    continue

                try:
                    # Load config
                    with open(config_path, 'r') as f:
                        config = json.load(f)

                    # Update all symbols for this gauge
                    if 'symbols' in config:
                        for symbol_id in config['symbols']:
                            # Get visibility from in-memory state
                            if gauge_name in self.gauge_symbols and symbol_id in self.gauge_symbols[gauge_name]:
                                visible = self.gauge_symbols[gauge_name][symbol_id]['visible']
                                config['symbols'][symbol_id]['visible'] = visible

                        # Save back to file
                        with open(config_path, 'w') as f:
                            json.dump(config, f, indent=2)

                        saved_files.append(config_path.name)
                        logger.info(f"✅ Saved symbols to {config_path.name}")

                except Exception as e:
                    errors.append(f"{config_path.name}: {e}")
                    logger.error(f"❌ Failed to save {config_path.name}: {e}")

            # Also save scale to symbols.json (global preference)
            try:
                scale_config = {
                    "symbol_scale": self.symbol_scale_spin.value(),
                    "symbol_positions": {},
                    "symbol_visibility": {}  # Deprecated - now stored in gauge configs
                }
                with open(self.symbol_config_path, 'w') as f:
                    json.dump(scale_config, f, indent=2)
                logger.info(f"💾 Saved symbol scale to symbols.json")
            except Exception as e:
                logger.warning(f"⚠️ Failed to save symbols.json: {e}")

            # Show result
            if errors:
                saved_text = ", ".join(saved_files) if saved_files else "None"
                error_text = "\n".join(errors)
                QMessageBox.warning(
                    self,
                    "Symbol Save Issues",
                    f"Saved: {saved_text}\nErrors:\n{error_text}"
                )
            elif saved_files:
                QMessageBox.information(
                    self,
                    "Symbol Settings Saved",
                    f"Symbol visibility saved to: {', '.join(saved_files)}\nSymbol scale: {self.symbol_scale_spin.value():.1f}x"
                )
            else:
                QMessageBox.information(
                    self,
                    "No Changes",
                    "No symbols to save."
                )

        except Exception as e:
            logger.error(f"❌ Failed to save symbol settings: {e}")
            QMessageBox.warning(
                self,
                "Save Failed",
                f"Failed to save symbol settings: {str(e)}"
            )

    def _load_gauge_symbols(self):
        """Load symbols from each gauge config file"""
        gauge_configs = {
            'tachometer': self.tach_config_path,
            'speedometer': self.speed_config_path,
            'fuel': self.fuel_config_path
        }

        for gauge_name, config_path in gauge_configs.items():
            if not config_path.exists():
                continue

            try:
                config = self._load_config(config_path)
                symbols = config.get('symbols', {})

                for symbol_id, symbol_data in symbols.items():
                    # Store symbol with gauge reference
                    full_symbol_id = f"{gauge_name}_{symbol_id}"
                    self.gauge_symbols[gauge_name][symbol_id] = {
                        'id': symbol_id,
                        'gauge': gauge_name,
                        'display_name': symbol_data.get('display_name', ''),
                        'image_path': symbol_data.get('image_path', ''),
                        'position_x': symbol_data.get('position_x', 0),
                        'position_y': symbol_data.get('position_y', 0),
                        'scale': symbol_data.get('scale', 1.0),
                        'visible': symbol_data.get('visible', False)  # Read from config, default False
                    }
                    logger.info(f"   📍 {symbol_id}: pos=({symbol_data.get('position_x', 0)}, {symbol_data.get('position_y', 0)}), visible={symbol_data.get('visible', False)}")

                logger.info(f"✅ Loaded {len(symbols)} symbol(s) for {gauge_name}")

            except Exception as e:
                logger.error(f"Failed to load symbols for {gauge_name}: {e}")

        # Populate checkboxes
        self._populate_symbol_checkboxes()

        # Sync symbols to gauge widgets
        self._sync_symbols_to_gauges()

    def _populate_symbol_checkboxes(self):
        """Populate symbol checkboxes from loaded symbols"""
        # Clear existing checkboxes (except refresh button)
        for symbol_id in list(self.symbol_checkboxes.keys()):
            self.remove_symbol_toggle(symbol_id)

        # Add checkboxes for each loaded symbol
        for gauge_name in ['tachometer', 'speedometer', 'fuel']:
            symbols = self.gauge_symbols[gauge_name]
            if not symbols:
                continue

            # Add gauge label
            gauge_label = QLabel(f"<b>{gauge_name.capitalize()}:</b>")
            gauge_label.setStyleSheet("margin-top: 8px;")
            insert_position = self.symbol_group_layout.count() - 1
            self.symbol_group_layout.insertWidget(insert_position, gauge_label)

            for symbol_id, symbol_data in symbols.items():
                full_id = f"{gauge_name}_{symbol_id}"
                # Use actual visibility and scale from loaded config
                default_visible = symbol_data.get('visible', False)
                default_scale = symbol_data.get('scale', 1.0)
                # Use display_name if available, otherwise use symbol_id
                display_label = symbol_data.get('display_name', '') or symbol_id
                self.add_symbol_toggle(full_id, f"  {display_label}", default_visible=default_visible, default_scale=default_scale)

        if not any(self.gauge_symbols.values()):
            no_symbols_label = QLabel("<i>No symbols configured yet.<br>Use Calibration Tool to add symbols.</i>")
            no_symbols_label.setStyleSheet("color: #999; padding: 10px;")
            insert_position = self.symbol_group_layout.count() - 1
            self.symbol_group_layout.insertWidget(insert_position, no_symbols_label)

        logger.info("✅ Symbol checkboxes populated")

    def _sync_symbols_to_gauges(self):
        """Sync loaded symbols to gauge widgets for rendering"""
        # Map gauge names to gauge objects
        gauge_map = {
            'tachometer': self.tach,
            'speedometer': self.speed,
            'fuel': self.fuel
        }

        for gauge_name, gauge_widget in gauge_map.items():
            # Convert symbol dict to list format expected by ImageBasedGauge
            symbols_list = []
            for symbol_id, symbol_data in self.gauge_symbols[gauge_name].items():
                symbols_list.append(symbol_data)

            # Set symbols on gauge widget
            gauge_widget.set_symbols(symbols_list)

        logger.info("✅ Synced symbols to gauge widgets")

    def _on_symbol_visibility_changed(self, symbol_id, state):
        """Handle symbol visibility toggle"""
        visible = state == Qt.Checked

        # Parse gauge_symbol_id format
        parts = symbol_id.split('_', 1)
        if len(parts) != 2:
            logger.warning(f"Invalid symbol ID format: {symbol_id}")
            return

        gauge_name, sym_id = parts

        if gauge_name not in self.gauge_symbols or sym_id not in self.gauge_symbols[gauge_name]:
            logger.warning(f"Symbol not found: {symbol_id}")
            return

        # Update visibility in memory
        self.gauge_symbols[gauge_name][sym_id]['visible'] = visible
        logger.info(f"Symbol '{symbol_id}' visibility: {visible}")

        # Immediately save visibility to gauge config file
        self._save_symbol_visibility_to_gauge_config(gauge_name, sym_id, visible)

        # Sync to gauge widget so it knows about the visibility change
        self._sync_symbols_to_gauges()

        # Trigger gauge update to show/hide symbol
        self._update_display()

    def _on_symbol_scale_changed(self, symbol_id: str, scale: float):
        """Handle symbol scale adjustment"""
        # Parse gauge_symbol_id format
        parts = symbol_id.split('_', 1)
        if len(parts) != 2:
            logger.warning(f"Invalid symbol ID format: {symbol_id}")
            return

        gauge_name, sym_id = parts

        if gauge_name not in self.gauge_symbols or sym_id not in self.gauge_symbols[gauge_name]:
            logger.warning(f"Symbol not found: {symbol_id}")
            return

        # Update scale in memory
        self.gauge_symbols[gauge_name][sym_id]['scale'] = scale
        logger.info(f"Symbol '{symbol_id}' scale: {scale:.1f}x")

        # Immediately save scale to gauge config file
        self._save_symbol_scale_to_gauge_config(gauge_name, sym_id, scale)

        # Sync to gauge widget so it knows about the scale change
        self._sync_symbols_to_gauges()

        # Trigger gauge update to re-render symbol at new scale
        self._update_display()

    def _save_symbol_visibility_to_gauge_config(self, gauge_name: str, symbol_id: str, visible: bool):
        """Save symbol visibility to the appropriate gauge config file"""
        try:
            # Determine config file
            config_path_map = {
                'tachometer': self.tach_config_path,
                'speedometer': self.speed_config_path,
                'fuel': self.fuel_config_path
            }

            config_path = config_path_map.get(gauge_name)
            if not config_path or not config_path.exists():
                logger.warning(f"Config file not found for gauge: {gauge_name}")
                return

            # Load config
            with open(config_path, 'r') as f:
                config = json.load(f)

            # Update symbol visibility
            if 'symbols' in config and symbol_id in config['symbols']:
                config['symbols'][symbol_id]['visible'] = visible

                # Save back to file
                with open(config_path, 'w') as f:
                    json.dump(config, f, indent=2)

                logger.info(f"✅ Saved {symbol_id} visibility ({visible}) to {config_path.name}")
            else:
                logger.warning(f"Symbol {symbol_id} not found in {config_path.name}")

        except Exception as e:
            logger.error(f"❌ Failed to save symbol visibility: {e}")

    def _save_symbol_scale_to_gauge_config(self, gauge_name: str, symbol_id: str, scale: float):
        """Save symbol scale to the appropriate gauge config file"""
        try:
            # Determine config file
            config_path_map = {
                'tachometer': self.tach_config_path,
                'speedometer': self.speed_config_path,
                'fuel': self.fuel_config_path
            }

            config_path = config_path_map.get(gauge_name)
            if not config_path or not config_path.exists():
                logger.warning(f"Config file not found for gauge: {gauge_name}")
                return

            # Load config
            with open(config_path, 'r') as f:
                config = json.load(f)

            # Update symbol scale
            if 'symbols' in config and symbol_id in config['symbols']:
                config['symbols'][symbol_id]['scale'] = scale

                # Save back to file
                with open(config_path, 'w') as f:
                    json.dump(config, f, indent=2)

                logger.info(f"✅ Saved {symbol_id} scale ({scale:.1f}x) to {config_path.name}")
            else:
                logger.warning(f"Symbol {symbol_id} not found in {config_path.name}")

        except Exception as e:
            logger.error(f"❌ Failed to save symbol scale: {e}")

    def _refresh_symbol_list(self):
        """Refresh the list of available symbols from gauge configs"""
        logger.info("Refreshing symbol list from configs...")
        self._load_gauge_symbols()
        QMessageBox.information(
            self,
            "Symbols Refreshed",
            "Symbol list reloaded from gauge configuration files."
        )

    def add_symbol_toggle(self, symbol_id: str, symbol_name: str, default_visible: bool = False, default_scale: float = 1.0):
        """
        Dynamically add a new symbol toggle to the UI with scale control

        Args:
            symbol_id: Unique identifier for the symbol
            symbol_name: Display name for the symbol
            default_visible: Initial visibility state
            default_scale: Initial scale value
        """
        if symbol_id in self.symbol_checkboxes:
            logger.warning(f"Symbol '{symbol_id}' already exists in UI")
            return

        # Create horizontal layout for checkbox + scale
        row_layout = QHBoxLayout()

        # Checkbox for visibility
        checkbox = QCheckBox(symbol_name)
        checkbox.setChecked(default_visible)
        checkbox.stateChanged.connect(lambda state, sid=symbol_id: self._on_symbol_visibility_changed(sid, state))
        row_layout.addWidget(checkbox)

        # Add stretch to push scale control to the right
        row_layout.addStretch()

        # Scale spinbox
        scale_label = QLabel("Scale:")
        scale_label.setStyleSheet("margin-left: 10px;")
        row_layout.addWidget(scale_label)

        scale_spin = QDoubleSpinBox()
        scale_spin.setRange(0.1, 3.0)
        scale_spin.setSingleStep(0.01)
        scale_spin.setValue(default_scale)
        scale_spin.setDecimals(2)
        scale_spin.setSuffix("x")
        scale_spin.setMaximumWidth(90)
        scale_spin.valueChanged.connect(lambda value, sid=symbol_id: self._on_symbol_scale_changed(sid, value))
        row_layout.addWidget(scale_spin)

        # Create container widget for the row
        row_widget = QWidget()
        row_widget.setLayout(row_layout)

        # Insert before the refresh button (last item)
        insert_position = self.symbol_group_layout.count() - 1
        self.symbol_group_layout.insertWidget(insert_position, row_widget)

        self.symbol_checkboxes[symbol_id] = checkbox
        self.symbol_scale_spinboxes[symbol_id] = scale_spin
        self.symbol_row_widgets[symbol_id] = row_widget
        logger.info(f"Added symbol toggle: {symbol_name} ({symbol_id}) with scale {default_scale}x")

    def remove_symbol_toggle(self, symbol_id: str):
        """
        Remove a symbol toggle from the UI

        Args:
            symbol_id: Unique identifier for the symbol to remove
        """
        if symbol_id not in self.symbol_checkboxes:
            logger.warning(f"Symbol '{symbol_id}' not found in UI")
            return

        # Remove the container widget (which contains checkbox and scale spinbox)
        if symbol_id in self.symbol_row_widgets:
            row_widget = self.symbol_row_widgets[symbol_id]
            self.symbol_group_layout.removeWidget(row_widget)
            row_widget.deleteLater()
            del self.symbol_row_widgets[symbol_id]

        # Clean up references
        del self.symbol_checkboxes[symbol_id]
        if symbol_id in self.symbol_scale_spinboxes:
            del self.symbol_scale_spinboxes[symbol_id]

        logger.info(f"Removed symbol toggle: {symbol_id}")

    def set_symbol_visible(self, symbol_id: str, visible: bool):
        """
        Programmatically set a symbol's visibility

        Args:
            symbol_id: Unique identifier for the symbol
            visible: Visibility state
        """
        if symbol_id not in self.symbol_checkboxes:
            logger.warning(f"Symbol '{symbol_id}' not found in UI")
            return

        checkbox = self.symbol_checkboxes[symbol_id]
        checkbox.blockSignals(True)
        checkbox.setChecked(visible)
        checkbox.blockSignals(False)
    
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
