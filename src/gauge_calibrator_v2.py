"""
Gauge Calibrator v2 - Position-Based Click Calibration

Three step process:
1. Click needle pivot point on needle image
2. Click where needle pivot sits on gauge
3. Click calibration marks on gauge (start, end, optional midpoints)

System calculates angles automatically from pixel positions.
"""

import json
import logging
import math
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Tuple, Optional
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QMessageBox, QGroupBox, QFrame,
    QSpinBox, QDoubleSpinBox, QToolBox, QLineEdit, QFileDialog
)
from PyQt5.QtGui import QPixmap, QPainter, QPen, QColor, QFont, QImage
from PyQt5.QtCore import Qt, QSize, QRectF, QTimer
from PyQt5.QtSvg import QSvgRenderer
from PIL import Image

logger = logging.getLogger(__name__)


@dataclass
class CalibrationPoint:
    """Calibration point with pixel position and value"""
    x: float
    y: float
    value: float
    
    def to_dict(self):
        return {"x": self.x, "y": self.y, "value": self.value}
    
    @classmethod
    def from_dict(cls, data):
        return cls(**data)


@dataclass
class NeedleType:
    """Needle type = reusable geometry definition from SVG file"""
    type_name: str  # "default", "toyota", etc.
    svg_path: str
    pivot_x: float = 0
    pivot_y: float = 0
    end_x: float = 0
    end_y: float = 0

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        return cls(**data)


@dataclass
class NeedleInstance:
    """Instance = one use of a needle type on a gauge, with its own calibration"""
    instance_id: str  # "instance1", "instance2", etc.
    needle_type: str  # Reference to type name
    gauge_name: str

    # Each instance has its OWN gauge pivot (where needle sits on gauge)
    gauge_pivot_x: float = 0
    gauge_pivot_y: float = 0

    # Each instance has its OWN calibration points
    calibration_points: List[CalibrationPoint] = field(default_factory=list)

    # Gauge value range
    min_value: float = 0
    max_value: float = 100

    def to_dict(self):
        return {
            "instance_id": self.instance_id,
            "needle_type": self.needle_type,
            "gauge_name": self.gauge_name,
            "gauge_pivot_x": self.gauge_pivot_x,
            "gauge_pivot_y": self.gauge_pivot_y,
            "calibration_points": [p.to_dict() for p in self.calibration_points],
            "min_value": self.min_value,
            "max_value": self.max_value,
        }

    @classmethod
    def from_dict(cls, data):
        data = data.copy()
        points_data = data.pop("calibration_points", [])
        instance = cls(**data)
        instance.calibration_points = [CalibrationPoint.from_dict(p) for p in points_data]
        return instance


@dataclass
class NeedleCalibration:
    """Complete needle calibration data"""
    needle_id: str
    needle_image_path: str
    gauge_name: str
    
    # Step 1: Needle geometry (on needle image itself)
    needle_pivot_x: float = 0
    needle_pivot_y: float = 0
    needle_end_x: float = 0      # Tip/end of needle
    needle_end_y: float = 0
    
    # Step 2: Where needle pivot sits on gauge
    gauge_pivot_x: float = 0
    gauge_pivot_y: float = 0
    
    # Step 3: Calibration marks (pixel positions on gauge with values)
    calibration_points: List[CalibrationPoint] = field(default_factory=list)
    
    # Gauge value range
    min_value: float = 0
    max_value: float = 100
    
    def to_dict(self):
        return {
            "needle_id": self.needle_id,
            "needle_image_path": self.needle_image_path,
            "gauge_name": self.gauge_name,
            "needle_pivot_x": self.needle_pivot_x,
            "needle_pivot_y": self.needle_pivot_y,
            "needle_end_x": self.needle_end_x,
            "needle_end_y": self.needle_end_y,
            "gauge_pivot_x": self.gauge_pivot_x,
            "gauge_pivot_y": self.gauge_pivot_y,
            "calibration_points": [p.to_dict() for p in self.calibration_points],
            "min_value": self.min_value,
            "max_value": self.max_value,
        }
    
    @classmethod
    def from_dict(cls, data):
        data = data.copy()
        points_data = data.pop("calibration_points", [])
        
        # Filter to only valid fields (ignore needle_scale, scale, etc.)
        valid_fields = {
            'needle_id', 'needle_image_path', 'gauge_name',
            'needle_pivot_x', 'needle_pivot_y', 'needle_end_x', 'needle_end_y',
            'gauge_pivot_x', 'gauge_pivot_y', 'min_value', 'max_value'
        }
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        
        calib = cls(**filtered_data)
        calib.calibration_points = [CalibrationPoint.from_dict(p) for p in points_data]
        return calib


@dataclass
class VisibilityCondition:
    """Defines when a symbol should be visible"""
    condition_type: str = "always"  # "always", "bool", "threshold"
    data_key: str = ""  # Key in telemetry data (e.g., "high_beam", "fuel_level")
    show_when: bool = True  # For bool conditions
    operator: str = ""  # "less_than", "greater_than", "equals"
    value: float = 0.0  # For threshold conditions

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        return cls(**data)


@dataclass
class Symbol:
    """Visual symbol/icon overlay (warning lights, indicators, etc.)"""
    symbol_id: str
    image_path: str = ""
    display_name: str = ""  # User-friendly name (e.g., "Check Engine", "Oil Pressure")

    # Position (pixels from origin)
    position_x: float = 0
    position_y: float = 0
    scale: float = 1.0  # Size multiplier
    anchor: str = "center"  # "top_left", "center", "bottom_right"
    visible: bool = False  # Visibility toggle for preview

    # Visibility and behavior
    visibility_condition: VisibilityCondition = field(default_factory=VisibilityCondition)

    # Layer order
    z_index: int = 0  # Higher = rendered on top

    def to_dict(self):
        data = asdict(self)
        data["visibility_condition"] = self.visibility_condition.to_dict()
        return data

    @classmethod
    def from_dict(cls, data):
        data = data.copy()
        vis_data = data.pop("visibility_condition", {})
        vis_condition = VisibilityCondition.from_dict(vis_data)
        return cls(**data, visibility_condition=vis_condition)


class ImageDisplayWidget(QFrame):
    """Widget to display image and handle click events"""

    # Class-level image cache to avoid reloading the same images
    _image_cache = {}  # {path: PIL.Image}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.original_image = None
        self.scaled_pixmap = None
        self.click_callback = None
        self.drag_callback = None  # For dragging existing points
        self.display_points = []  # List of (x, y, color, label) for overlay
        self.dragging_index = None  # Index of point being dragged

        self.setMinimumSize(500, 500)
        self.setStyleSheet("border: 2px solid #333;")
        self.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.setMouseTracking(True)  # Enable mouse tracking for cursor changes
    
    def load_image(self, image_path: str) -> bool:
        """Load image from path (supports PNG and SVG) with caching"""
        try:
            if not Path(image_path).exists():
                self.original_image = None
                self.update()
                return False

            # Check cache first
            if image_path in self._image_cache:
                self.original_image = self._image_cache[image_path].copy()
                self._scale_and_display()
                return True

            # Not in cache - load from disk
            # Check if it's an SVG file
            if image_path.lower().endswith('.svg'):
                # Render SVG to PIL Image
                svg_renderer = QSvgRenderer(image_path)
                if not svg_renderer.isValid():
                    logger.error(f"Invalid SVG file: {image_path}")
                    return False

                # Get SVG default size
                svg_size = svg_renderer.defaultSize()
                width = svg_size.width()
                height = svg_size.height()

                # Create QImage with correct format for RGBA
                qimage = QImage(width, height, QImage.Format_RGBA8888)
                qimage.fill(Qt.transparent)

                painter = QPainter(qimage)
                painter.setRenderHint(QPainter.Antialiasing, True)
                painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
                svg_renderer.render(painter, QRectF(0, 0, width, height))
                painter.end()

                # Convert QImage to PIL Image
                ptr = qimage.constBits()
                ptr.setsize(qimage.byteCount())
                pil_image = Image.frombytes('RGBA', (width, height), ptr.asstring())
                self.original_image = pil_image
            else:
                # Load PNG/JPG with PIL
                self.original_image = Image.open(image_path).convert("RGBA")

            # Cache the loaded image
            self._image_cache[image_path] = self.original_image.copy()

            self._scale_and_display()
            return True
        except Exception as e:
            logger.error(f"Error loading image: {e}")
            import traceback
            traceback.print_exc()
            return False

    @classmethod
    def clear_image_cache(cls):
        """Clear the image cache (useful if images change on disk)"""
        cls._image_cache.clear()
        logger.info("🗑️ Image cache cleared")

    def set_click_callback(self, callback):
        """Set callback: callback(original_x, original_y)"""
        self.click_callback = callback
    
    def set_drag_callback(self, callback):
        """Set drag callback: callback(point_index, original_x, original_y)"""
        self.drag_callback = callback
    
    def add_display_point(self, x: float, y: float, color: str = "red", label: str = "", point_type: str = None):
        """Add point to display overlay"""
        color_map = {
            "red": (255, 0, 0),
            "green": (0, 255, 0),
            "blue": (0, 0, 255),
            "yellow": (255, 255, 0),
            "cyan": (0, 255, 255),
            "orange": (255, 165, 0),
        }
        self.display_points.append({
            "x": x, "y": y,
            "color": color_map.get(color, (255, 0, 0)),
            "label": label,
            "point_type": point_type  # 'needle_pivot', 'needle_end', 'gauge_pivot', or 'calibration'
        })
        self._scale_and_display()
    
    def clear_display_points(self):
        """Clear all overlay points"""
        self.display_points = []
        self._scale_and_display()
    
    def _scale_and_display(self):
        """Scale image to widget maintaining aspect ratio"""
        if not self.original_image:
            self.scaled_pixmap = None
            self.update()
            return
        
        # Get widget size
        widget_width = self.width() - 4
        widget_height = self.height() - 4
        if widget_width <= 0 or widget_height <= 0:
            return
        
        # Calculate scale to fit widget while maintaining aspect ratio
        img_w, img_h = self.original_image.size
        scale_w = widget_width / img_w
        scale_h = widget_height / img_h
        scale = min(scale_w, scale_h)  # Use smaller scale to fit without distortion
        
        # Calculate new dimensions
        new_w = int(img_w * scale)
        new_h = int(img_h * scale)
        
        # Resize maintaining aspect ratio
        pil_scaled = self.original_image.resize(
            (new_w, new_h),
            Image.Resampling.LANCZOS
        )
        
        # Convert to QPixmap
        qimg = QImage(pil_scaled.tobytes(), pil_scaled.width, pil_scaled.height,
                      QImage.Format_RGBA8888)
        self.scaled_pixmap = QPixmap.fromImage(qimg)
        
        # Store scale factor for coordinate conversion
        self.scale_factor = scale
        
        self.update()
    
    def resizeEvent(self, event):
        """Handle resize"""
        super().resizeEvent(event)
        self._scale_and_display()
    
    def _find_closest_point_index(self, x: float, y: float, threshold: int = 15) -> int:
        """Find closest display point within threshold distance. Returns -1 if none found."""
        for i, point in enumerate(self.display_points):
            px = int(point["x"] * self.scale_factor) + 2
            py = int(point["y"] * self.scale_factor) + 2
            dist = ((x - px) ** 2 + (y - py) ** 2) ** 0.5
            if dist <= threshold:
                return i
        return -1
    
    def mousePressEvent(self, event):
        """Handle mouse click - checks for existing points to drag first"""
        if not self.original_image:
            return
        
        # Convert widget coordinates to original image coordinates
        # Account for border offset (images drawn at +2, +2)
        border = 2
        click_x = event.x() - border
        click_y = event.y() - border
        
        # Check if clicking on an existing point (drag it)
        point_index = self._find_closest_point_index(click_x, click_y, threshold=15)
        if point_index >= 0 and self.drag_callback:
            self.dragging_index = point_index
            self.setCursor(Qt.ClosedHandCursor)
            return
        
        # Otherwise, treat as new click
        if not self.click_callback:
            return
        
        # Convert from scaled display coords back to original image coords
        orig_x = int(click_x / self.scale_factor)
        orig_y = int(click_y / self.scale_factor)
        
        # Clamp to image bounds
        orig_x = max(0, min(orig_x, self.original_image.width - 1))
        orig_y = max(0, min(orig_y, self.original_image.height - 1))
        
        self.click_callback(orig_x, orig_y)
    
    def mouseMoveEvent(self, event):
        """Handle mouse move - update cursor and drag if dragging"""
        if not self.original_image:
            return
        
        border = 2
        click_x = event.x() - border
        click_y = event.y() - border
        
        # If currently dragging, update the point
        if self.dragging_index is not None and self.drag_callback:
            orig_x = int(click_x / self.scale_factor)
            orig_y = int(click_y / self.scale_factor)
            
            # Clamp to image bounds
            orig_x = max(0, min(orig_x, self.original_image.width - 1))
            orig_y = max(0, min(orig_y, self.original_image.height - 1))
            
            self.drag_callback(self.dragging_index, orig_x, orig_y)
            self.update()
        else:
            # Update cursor based on proximity to existing points
            point_index = self._find_closest_point_index(click_x, click_y, threshold=15)
            if point_index >= 0:
                self.setCursor(Qt.OpenHandCursor)
            else:
                self.setCursor(Qt.CrossCursor)
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release - end dragging"""
        if self.dragging_index is not None:
            self.dragging_index = None
            self.setCursor(Qt.ArrowCursor)
            self.update()
    
    def paintEvent(self, event):
        """Paint image and overlay"""
        super().paintEvent(event)
        
        if not self.scaled_pixmap:
            return
        
        painter = QPainter(self)
        painter.drawPixmap(2, 2, self.scaled_pixmap)
        
        # Draw display points
        if self.display_points:
            for point in self.display_points:
                x = int(point["x"] * self.scale_factor) + 2
                y = int(point["y"] * self.scale_factor) + 2
                color = point["color"]
                label = point["label"]
                
                # Draw crosshair
                painter.setPen(QPen(QColor(*color), 2))
                size = 15
                painter.drawLine(x - size, y, x + size, y)
                painter.drawLine(x, y - size, x, y + size)
                
                # Draw circle
                painter.setPen(QPen(QColor(*color), 2))
                painter.drawEllipse(x - 8, y - 8, 16, 16)
                
                # Draw label
                if label:
                    painter.setFont(QFont("Arial", 9, QFont.Bold))
                    painter.setPen(QColor(*color))
                    painter.drawText(x + 20, y - 10, label)


class GaugeCalibratorV2(QMainWindow):
    """Main calibrator window - position-based workflow"""

    # Color palette for needle instances
    INSTANCE_COLORS = ["red", "blue", "green", "yellow", "cyan", "orange"]
    CALIBRATION_SET_COLORS = INSTANCE_COLORS  # Alias for backward compatibility

    GAUGE_PRESETS = {
        "Tachometer": {"min": 0, "max": 10000, "bg_image": "gauges/tachometer_bg.png"},
        "Speedometer": {"min": 0, "max": 320, "bg_image": "gauges/speedometer_bg.png"},
        "Fuel": {"min": 0, "max": 100, "bg_image": "gauges/fuel_bg.png"},
    }
    
    NEEDLE_TYPES = {
        "Tachometer": ["main"],
        "Speedometer": ["main"],
        "Fuel": ["fuel", "water"],
    }
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Calibration Tool")
        self.setGeometry(100, 100, 1400, 700)

        self.current_calibration = None
        self.has_unsaved_changes = False  # Track unsaved changes for save prompts

        # Track calibration sets for current needle
        self.calibration_sets = {}  # {set_name: NeedleCalibration}
        self.current_set_name = "set1"
        self.next_color_index = 0

        # Track symbols (warning lights, indicators, etc.)
        self.symbols = {}  # {symbol_id: Symbol}
        self.current_symbol_id = None
        self.positioning_symbol = False  # Flag for symbol positioning mode

        # Use absolute path based on project root (parent of src/)
        self.config_dir = Path(__file__).parent.parent / "config"
        self.config_dir.mkdir(exist_ok=True)
        
        # Load existing needles from config files
        self._load_existing_needles_from_config()

        self._setup_ui()

        # Load symbols after UI is set up
        self._load_symbols()

        self._autosave_timer = QTimer(self)
        self._autosave_timer.setInterval(500)
        self._autosave_timer.setSingleShot(True)
        self._autosave_timer.timeout.connect(self._autosave_current_calibration)
        self._autosave_suspended = False
    
    def _load_existing_needles_from_config(self):
        """Load needle names from existing config files"""
        for gauge_name in ["Tachometer", "Speedometer", "Fuel"]:
            config_file = self.config_dir / f"{gauge_name.lower()}.json"
            if config_file.exists():
                try:
                    with open(config_file, 'r') as f:
                        config = json.load(f)

                    # Get all needle IDs from needle_calibrations
                    if 'needle_calibrations' in config:
                        needle_ids = list(config['needle_calibrations'].keys())
                        if needle_ids:
                            # Update NEEDLE_TYPES with loaded needles
                            self.NEEDLE_TYPES[gauge_name] = needle_ids
                            logger.info(f"📋 Loaded needles for {gauge_name}: {needle_ids}")
                except Exception as e:
                    logger.warning(f"⚠️ Could not load needles from {gauge_name}: {e}")

    def _scan_needle_types(self):
        """Scan gauges/ folder for available needle SVG files"""
        gauges_dir = Path(__file__).parent.parent / "gauges"
        needle_types = []

        if not gauges_dir.exists():
            logger.warning(f"⚠️ Gauges directory not found: {gauges_dir}")
            return ["default"]

        for needle_file in gauges_dir.glob("needle*.svg"):
            # Extract type name (e.g., "needle.svg" → "default", "needle_toyota.svg" → "toyota")
            name = needle_file.stem
            if name == "needle":
                needle_types.append("default")
            else:
                # Remove "needle_" prefix
                type_name = name.replace("needle_", "")
                needle_types.append(type_name)

        if not needle_types:
            needle_types = ["default"]  # Fallback

        return sorted(needle_types)

    def _setup_ui(self):
        """Setup user interface with collapsible sections"""
        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        layout = QHBoxLayout()

        # Left: Image display
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("Image Display"))
        self.image_widget = ImageDisplayWidget()
        self.image_widget.set_drag_callback(self.on_point_dragged)
        left_layout.addWidget(self.image_widget)

        # Right: Controls (using QToolBox for collapsible sections)
        right_layout = QVBoxLayout()

        # Create collapsible toolbox
        self.tool_box = QToolBox()

        # Add each section as a collapsible page
        self.tool_box.addItem(self._create_gauge_selection_section(), "1. Select Gauge & Needle")
        self.tool_box.addItem(self._create_calibration_sets_section(), "2. Calibration Sets (Multiple Instances)")
        self.tool_box.addItem(self._create_needle_geometry_section(), "3. Needle Geometry (2 clicks)")
        self.tool_box.addItem(self._create_gauge_pivot_section(), "4. Gauge Pivot Location")
        self.tool_box.addItem(self._create_calibration_points_section(), "5. Calibration Marks")
        self.tool_box.addItem(self._create_symbols_section(), "6. Symbols (Warning Lights & Indicators)")

        right_layout.addWidget(self.tool_box)

        # Action buttons (always visible at bottom)
        button_layout = QHBoxLayout()

        save_needle_btn = QPushButton("💾 Save Needle")
        save_needle_btn.clicked.connect(self.save_needle_configuration)
        button_layout.addWidget(save_needle_btn)

        save_gauge_btn = QPushButton("💾 Save Full Config")
        save_gauge_btn.clicked.connect(self.save_gauge_configuration)
        button_layout.addWidget(save_gauge_btn)

        button_layout2 = QHBoxLayout()

        load_btn = QPushButton("📁 Load Configuration")
        load_btn.clicked.connect(self.load_configuration)
        button_layout2.addWidget(load_btn)

        reset_btn = QPushButton("🔄 Reset Gauge")
        reset_btn.clicked.connect(self.reset_current_gauge)
        button_layout2.addWidget(reset_btn)

        add_needle_btn = QPushButton("➕ Add Needle")
        add_needle_btn.clicked.connect(self.add_new_needle)
        button_layout2.addWidget(add_needle_btn)

        rename_needle_btn = QPushButton("✏️ Rename Needle")
        rename_needle_btn.clicked.connect(self.rename_needle)
        button_layout2.addWidget(rename_needle_btn)

        delete_needle_btn = QPushButton("🗑️ Delete Needle")
        delete_needle_btn.clicked.connect(self.delete_needle)
        delete_needle_btn.setStyleSheet("background-color: #ff6b6b; color: white; font-weight: bold;")
        button_layout2.addWidget(delete_needle_btn)

        right_layout.addLayout(button_layout)
        right_layout.addLayout(button_layout2)
        right_layout.addStretch()

        # Combine layouts
        layout.addLayout(left_layout, 2)
        layout.addLayout(right_layout, 1)
        main_widget.setLayout(layout)

        # Initialize
        self.on_gauge_changed(self.gauge_combo.currentText())

    def _create_gauge_selection_section(self):
        """Create gauge and needle selection section"""
        widget = QWidget()
        layout = QVBoxLayout()

        layout.addWidget(QLabel("Gauge:"))
        self.gauge_combo = QComboBox()
        self.gauge_combo.addItems(self.GAUGE_PRESETS.keys())
        self.gauge_combo.currentTextChanged.connect(self.on_gauge_changed)
        layout.addWidget(self.gauge_combo)

        layout.addWidget(QLabel("Needle:"))
        self.needle_combo = QComboBox()
        self.needle_combo.currentTextChanged.connect(self.on_needle_changed)
        layout.addWidget(self.needle_combo)

        # Current needle indicator
        self.current_needle_label = QLabel("Working on: None")
        self.current_needle_label.setStyleSheet("background-color: #4CAF50; color: white; padding: 8px; font-weight: bold; font-size: 12pt; border-radius: 4px;")
        layout.addWidget(self.current_needle_label)

        # Point type selector (for clarity when adding calibration data)
        layout.addWidget(QLabel("\nWhat am I setting?"))
        self.point_type_combo = QComboBox()
        self.point_type_combo.addItems([
            "Step 1a: Needle PIVOT Point",
            "Step 1b: Needle END Point",
            "Step 2: Gauge PIVOT Point",
            "Step 3: Calibration Point"
        ])
        self.point_type_combo.currentIndexChanged.connect(self.on_point_type_changed)
        layout.addWidget(self.point_type_combo)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def _create_calibration_sets_section(self):
        """Create calibration sets management section"""
        widget = QWidget()
        layout = QVBoxLayout()

        # Current set selector
        layout.addWidget(QLabel("Select Calibration Set:"))
        self.calibration_set_combo = QComboBox()
        self.calibration_set_combo.currentTextChanged.connect(self.on_calibration_set_changed)
        layout.addWidget(self.calibration_set_combo)

        # Add/Delete set buttons
        btn_layout = QHBoxLayout()
        self.add_set_btn = QPushButton("➕ Add New Set")
        self.add_set_btn.clicked.connect(self.add_calibration_set)
        btn_layout.addWidget(self.add_set_btn)

        self.delete_set_btn = QPushButton("🗑️ Delete Set")
        self.delete_set_btn.clicked.connect(self.delete_calibration_set)
        btn_layout.addWidget(self.delete_set_btn)
        layout.addLayout(btn_layout)

        # Color indicator
        self.set_color_label = QLabel("Set Color: Red")
        self.set_color_label.setStyleSheet("color: red; font-weight: bold; font-size: 11pt;")
        layout.addWidget(self.set_color_label)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def _create_needle_geometry_section(self):
        """Create needle geometry calibration section"""
        widget = QWidget()
        layout = QVBoxLayout()

        layout.addWidget(QLabel("Click needle PIVOT POINT (rotation center)"))
        layout.addWidget(QLabel("Then click needle TIP/END POINT"))

        self.needle_pivot_label = QLabel("Pivot: Not set")
        self.needle_pivot_label.setStyleSheet("color: #FF6600; font-weight: bold;")
        layout.addWidget(self.needle_pivot_label)

        self.needle_end_label = QLabel("End: Not set")
        self.needle_end_label.setStyleSheet("color: #0088FF; font-weight: bold;")
        layout.addWidget(self.needle_end_label)

        self.load_needle_btn = QPushButton("Load Needle Image")
        self.load_needle_btn.clicked.connect(self.load_needle_image)
        layout.addWidget(self.load_needle_btn)

        self.reset_needle_btn = QPushButton("🔄 Reset Needle Geometry")
        self.reset_needle_btn.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold; padding: 5px;")
        self.reset_needle_btn.clicked.connect(self.reset_needle_geometry)
        layout.addWidget(self.reset_needle_btn)

        # Coordinate spinboxes hidden per user request (visual-only calibration)
        # Keep spinbox attributes for internal state tracking but don't display them
        self.needle_pivot_x_spin = QSpinBox()
        self.needle_pivot_x_spin.setRange(0, 2000)
        self.needle_pivot_x_spin.setVisible(False)  # Hidden

        self.needle_pivot_y_spin = QSpinBox()
        self.needle_pivot_y_spin.setRange(0, 2000)
        self.needle_pivot_y_spin.setVisible(False)  # Hidden

        self.needle_end_x_spin = QSpinBox()
        self.needle_end_x_spin.setRange(0, 2000)
        self.needle_end_x_spin.setVisible(False)  # Hidden

        self.needle_end_y_spin = QSpinBox()
        self.needle_end_y_spin.setRange(0, 2000)
        self.needle_end_y_spin.setVisible(False)  # Hidden

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def _create_gauge_pivot_section(self):
        """Create gauge pivot location section"""
        widget = QWidget()
        layout = QVBoxLayout()

        layout.addWidget(QLabel("Click on GAUGE IMAGE where needle pivot sits"))
        self.gauge_pivot_label = QLabel("Not set")
        self.gauge_pivot_label.setStyleSheet("color: #0088FF; font-weight: bold;")
        layout.addWidget(self.gauge_pivot_label)

        self.load_gauge_btn = QPushButton("Load Gauge Image")
        self.load_gauge_btn.clicked.connect(self.load_gauge_image)
        layout.addWidget(self.load_gauge_btn)

        self.reset_gauge_pivot_btn = QPushButton("🔄 Reset Gauge Pivot")
        self.reset_gauge_pivot_btn.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold; padding: 5px;")
        self.reset_gauge_pivot_btn.clicked.connect(self.reset_gauge_pivot)
        layout.addWidget(self.reset_gauge_pivot_btn)

        # Coordinate spinboxes hidden per user request (visual-only calibration)
        # Keep spinbox attributes for internal state tracking but don't display them
        self.gauge_pivot_x_spin = QSpinBox()
        self.gauge_pivot_x_spin.setRange(0, 2000)
        self.gauge_pivot_x_spin.setVisible(False)  # Hidden

        self.gauge_pivot_y_spin = QSpinBox()
        self.gauge_pivot_y_spin.setRange(0, 2000)
        self.gauge_pivot_y_spin.setVisible(False)  # Hidden

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def _create_calibration_points_section(self):
        """Create calibration marks section"""
        widget = QWidget()
        layout = QVBoxLayout()

        layout.addWidget(QLabel("Click on GAUGE IMAGE + enter value"))

        point_input_layout = QHBoxLayout()
        point_input_layout.addWidget(QLabel("Value:"))
        self.point_value_spin = QDoubleSpinBox()
        self.point_value_spin.setRange(-500, 20000)
        self.point_value_spin.setValue(0)
        point_input_layout.addWidget(self.point_value_spin)

        add_point_btn = QPushButton("Add Point (click then press)")
        add_point_btn.clicked.connect(self.add_calibration_point)
        point_input_layout.addWidget(add_point_btn)

        layout.addLayout(point_input_layout)

        # Simple calibration summary (just count, no table)
        self.calib_summary_label = QLabel("0 calibration points")
        self.calib_summary_label.setStyleSheet("font-weight: bold; font-size: 11pt;")
        layout.addWidget(self.calib_summary_label)

        # Delete last point button (simplified)
        delete_last_btn = QPushButton("🗑️ Delete Last Point")
        delete_last_btn.clicked.connect(self.delete_last_calibration_point)
        layout.addWidget(delete_last_btn)

        # Clear all points button
        clear_all_btn = QPushButton("Clear All Points")
        clear_all_btn.clicked.connect(self.clear_all_calibration_points)
        layout.addWidget(clear_all_btn)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def _create_symbols_section(self):
        """Create symbols (warning lights & indicators) section"""
        widget = QWidget()
        layout = QVBoxLayout()

        # Info label
        info_label = QLabel("Position warning lights, indicators, etc.")
        info_label.setStyleSheet("font-size: 9pt; color: #666;")
        layout.addWidget(info_label)

        # Symbol selection
        layout.addWidget(QLabel("Choose Symbol to Position:"))
        self.symbol_combo = QComboBox()
        self.symbol_combo.currentTextChanged.connect(self.on_symbol_changed)
        layout.addWidget(self.symbol_combo)

        # Display name field
        layout.addWidget(QLabel("Display Name:"))
        self.symbol_display_name_edit = QLineEdit()
        self.symbol_display_name_edit.setPlaceholderText("e.g., Check Engine, Oil Pressure, etc.")
        self.symbol_display_name_edit.textChanged.connect(self.on_symbol_display_name_changed)
        layout.addWidget(self.symbol_display_name_edit)

        # Add/Delete symbol buttons
        btn_layout = QHBoxLayout()
        self.add_symbol_btn = QPushButton("➕ Add Symbol")
        self.add_symbol_btn.clicked.connect(self.add_symbol)
        btn_layout.addWidget(self.add_symbol_btn)

        self.delete_symbol_btn = QPushButton("🗑️ Delete")
        self.delete_symbol_btn.clicked.connect(self.delete_symbol)
        btn_layout.addWidget(self.delete_symbol_btn)
        layout.addLayout(btn_layout)

        # Load symbol image button
        self.load_symbol_image_btn = QPushButton("📁 Load Symbol Image (SVG/PNG)")
        self.load_symbol_image_btn.clicked.connect(self.load_symbol_image)
        layout.addWidget(self.load_symbol_image_btn)

        # Position symbol button
        self.position_symbol_btn = QPushButton("📍 Click to Position Symbol on Gauge")
        self.position_symbol_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 8px;")
        self.position_symbol_btn.clicked.connect(self.start_positioning_symbol)
        layout.addWidget(self.position_symbol_btn)

        # Position display label
        self.symbol_position_label = QLabel("Position: Not set")
        self.symbol_position_label.setStyleSheet("color: #0088FF; font-weight: bold;")
        layout.addWidget(self.symbol_position_label)

        # Position & scale controls
        layout.addWidget(QLabel("Scale:"))
        self.symbol_scale_spin = QDoubleSpinBox()
        self.symbol_scale_spin.setRange(0.1, 5.0)
        self.symbol_scale_spin.setSingleStep(0.1)
        self.symbol_scale_spin.setValue(1.0)
        self.symbol_scale_spin.valueChanged.connect(self.on_symbol_scale_changed)
        layout.addWidget(self.symbol_scale_spin)

        # Visibility condition
        layout.addWidget(QLabel("Visibility:"))
        self.visibility_type_combo = QComboBox()
        self.visibility_type_combo.addItems(["Always Visible", "Boolean (True/False)", "Threshold (Value)"])
        self.visibility_type_combo.currentIndexChanged.connect(self.on_visibility_type_changed)
        layout.addWidget(self.visibility_type_combo)

        # Data key input
        layout.addWidget(QLabel("Data Key (e.g., high_beam):"))
        self.visibility_key_input = QLineEdit()
        self.visibility_key_input.setPlaceholderText("telemetry_data_key")
        self.visibility_key_input.textChanged.connect(self.on_visibility_key_changed)
        self.visibility_key_input.setEnabled(False)
        layout.addWidget(self.visibility_key_input)

        # Bool condition
        self.visibility_bool_combo = QComboBox()
        self.visibility_bool_combo.addItems(["Show when True", "Show when False"])
        self.visibility_bool_combo.currentIndexChanged.connect(self.on_visibility_bool_changed)
        self.visibility_bool_combo.setEnabled(False)
        layout.addWidget(self.visibility_bool_combo)

        # Threshold condition
        threshold_layout = QHBoxLayout()
        self.visibility_operator_combo = QComboBox()
        self.visibility_operator_combo.addItems(["<", ">", "="])
        self.visibility_operator_combo.currentTextChanged.connect(self.on_visibility_operator_changed)
        self.visibility_operator_combo.setEnabled(False)
        threshold_layout.addWidget(self.visibility_operator_combo)

        self.visibility_value_spin = QDoubleSpinBox()
        self.visibility_value_spin.setRange(-10000, 10000)
        self.visibility_value_spin.valueChanged.connect(self.on_visibility_value_changed)
        self.visibility_value_spin.setEnabled(False)
        threshold_layout.addWidget(self.visibility_value_spin)
        layout.addLayout(threshold_layout)

        # Save symbols button
        save_symbols_btn = QPushButton("💾 Save Symbols")
        save_symbols_btn.clicked.connect(self.save_symbols)
        layout.addWidget(save_symbols_btn)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def on_gauge_changed(self, gauge_name: str):
        """Handle gauge selection - auto-load everything"""

        # Check for unsaved changes first
        if self.current_calibration and self.has_unsaved_changes:
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                f"Save calibration changes for {self.current_calibration.gauge_name}?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
            )

            if reply == QMessageBox.Save:
                self.save_gauge_configuration()
            elif reply == QMessageBox.Cancel:
                # Revert gauge selection
                self.gauge_combo.blockSignals(True)
                prev_gauge_names = list(self.GAUGE_PRESETS.keys())
                if self.current_calibration.gauge_name in prev_gauge_names:
                    prev_index = prev_gauge_names.index(self.current_calibration.gauge_name)
                    self.gauge_combo.setCurrentIndex(prev_index)
                self.gauge_combo.blockSignals(False)
                return

            self.has_unsaved_changes = False

        # Update needle dropdown
        needles = self.NEEDLE_TYPES.get(gauge_name, ["main"])

        self.needle_combo.blockSignals(True)
        self.needle_combo.clear()
        self.needle_combo.addItems(needles)
        self.needle_combo.blockSignals(False)

        # Create new calibration for this gauge
        preset = self.GAUGE_PRESETS.get(gauge_name, {"min": 0, "max": 100})
        self.current_calibration = NeedleCalibration(
            needle_id=needles[0],
            needle_image_path="",
            gauge_name=gauge_name,
            min_value=preset.get("min", 0),
            max_value=preset.get("max", 100)
        )

        # Auto-load gauge background image
        self._auto_load_gauge_image(gauge_name)

        # Auto-load first needle
        self.on_needle_changed(needles[0])

        # Reload symbols for this gauge
        self._load_symbols()

    def auto_load_default_gauge(self):
        """Auto-load tachometer gauge + needle + calibration on first load"""
        try:
            # Set to tachometer (index 0)
            self.gauge_combo.setCurrentIndex(0)

            # This will trigger on_gauge_changed and on_needle_changed
            # which will auto-load everything

            logger.info("✅ Auto-loaded tachometer gauge")
        except Exception as e:
            logger.error(f"❌ Failed to auto-load gauge: {e}")

    def _auto_load_gauge_image(self, gauge_name: str):
        """Auto-load gauge background image"""
        preset = self.GAUGE_PRESETS.get(gauge_name, {})
        bg_image = preset.get("bg_image", "")

        if not bg_image:
            return

        gauge_path = Path(__file__).parent.parent / bg_image
        if gauge_path.exists():
            success = self.image_widget.load_image(str(gauge_path))
            if success:
                # Set callback for gauge clicks (pivot, calibration points)
                self.image_widget.set_click_callback(self.on_gauge_click)
                logger.info(f"✅ Auto-loaded gauge: {gauge_path.name}")
                # Redraw existing calibration points if any
                if self.calibration_sets:
                    self._redraw_all_points()
            else:
                logger.warning(f"⚠️ Failed to load gauge: {gauge_path}")
        else:
            logger.warning(f"⚠️ Gauge image not found: {gauge_path}")

    def _auto_load_needle_image(self, needle_id: str):
        """Auto-load needle image for selected needle"""
        if not self.current_calibration:
            return

        gauge_name = self.current_calibration.gauge_name.lower()

        # Try standard paths (prefer SVG over PNG)
        gauges_dir = Path(__file__).parent.parent / "gauges"

        # Check for needle.svg (shared needle)
        needle_path = gauges_dir / "needle.svg"
        if not needle_path.exists():
            # Try needle ID with SVG
            needle_path = gauges_dir / f"{needle_id}_needle.svg"
        if not needle_path.exists():
            # Try gauge name with SVG
            needle_path = gauges_dir / f"{gauge_name}_needle.svg"
        if not needle_path.exists():
            # Fall back to PNG
            needle_path = gauges_dir / f"{needle_id}_needle.png"
        if not needle_path.exists():
            needle_path = gauges_dir / f"{gauge_name}_needle.png"

        if needle_path.exists():
            success = self.image_widget.load_image(str(needle_path))
            if success:
                self.current_calibration.needle_image_path = str(needle_path)
                self.image_widget.set_click_callback(self.on_needle_pivot_click)
                logger.info(f"✅ Auto-loaded needle: {needle_path.name}")
            else:
                logger.warning(f"⚠️ Failed to load needle: {needle_path}")
        else:
            logger.info(f"ℹ️ No needle image found for {needle_id}, will need to load manually")

    def _auto_load_configuration(self):
        """Auto-load saved calibration from config file"""
        if not self.current_calibration:
            return

        gauge_name = self.current_calibration.gauge_name.lower()
        needle_id = self.current_calibration.needle_id

        # Load all calibration sets for this needle
        self.load_calibration_sets_for_needle(gauge_name, needle_id)

        # Update UI with first set's values
        if self.calibration_sets:
            self._update_ui_from_calibration()
            logger.info(f"✅ Auto-loaded {len(self.calibration_sets)} calibration set(s): {gauge_name}/{needle_id}")

    def _update_ui_from_calibration(self):
        """Update all UI elements from current_calibration"""
        if not self.current_calibration:
            return

        # Update step 1 (needle geometry)
        self.needle_pivot_x_spin.blockSignals(True)
        self.needle_pivot_y_spin.blockSignals(True)
        self.needle_end_x_spin.blockSignals(True)
        self.needle_end_y_spin.blockSignals(True)

        self.needle_pivot_x_spin.setValue(int(self.current_calibration.needle_pivot_x))
        self.needle_pivot_y_spin.setValue(int(self.current_calibration.needle_pivot_y))
        self.needle_end_x_spin.setValue(int(self.current_calibration.needle_end_x))
        self.needle_end_y_spin.setValue(int(self.current_calibration.needle_end_y))

        self.needle_pivot_x_spin.blockSignals(False)
        self.needle_pivot_y_spin.blockSignals(False)
        self.needle_end_x_spin.blockSignals(False)
        self.needle_end_y_spin.blockSignals(False)

        # Update step 2 (gauge pivot)
        self.gauge_pivot_x_spin.blockSignals(True)
        self.gauge_pivot_y_spin.blockSignals(True)

        self.gauge_pivot_x_spin.setValue(int(self.current_calibration.gauge_pivot_x))
        self.gauge_pivot_y_spin.setValue(int(self.current_calibration.gauge_pivot_y))

        self.gauge_pivot_x_spin.blockSignals(False)
        self.gauge_pivot_y_spin.blockSignals(False)

        # Update labels
        if self.current_calibration.needle_pivot_x > 0:
            self.needle_pivot_label.setText(
                f"✓ Pivot: ({int(self.current_calibration.needle_pivot_x)}, "
                f"{int(self.current_calibration.needle_pivot_y)})"
            )

        if self.current_calibration.needle_end_x > 0:
            self.needle_end_label.setText(
                f"✓ End: ({int(self.current_calibration.needle_end_x)}, "
                f"{int(self.current_calibration.needle_end_y)})"
            )

        if self.current_calibration.gauge_pivot_x > 0:
            self.gauge_pivot_label.setText(
                f"✓ ({int(self.current_calibration.gauge_pivot_x)}, "
                f"{int(self.current_calibration.gauge_pivot_y)})"
            )

        # Refresh calibration table
        self._refresh_calibration_table()

        # Redraw points on image
        self._redraw_all_points()

    def _redraw_all_points(self):
        """Redraw all calibration points for all sets with color coding"""
        if not self.calibration_sets:
            return

        self.image_widget.clear_display_points()

        # Draw points from all calibration sets (with different colors)
        for set_name, calibration in self.calibration_sets.items():
            # Get color for this set
            color_index = list(self.calibration_sets.keys()).index(set_name)
            color = self.CALIBRATION_SET_COLORS[color_index % len(self.CALIBRATION_SET_COLORS)]

            # Determine if this is the active set
            is_active = (set_name == self.current_set_name)

            # Draw needle geometry (only for active set)
            if is_active:
                if calibration.needle_pivot_x > 0:
                    self.image_widget.add_display_point(
                        calibration.needle_pivot_x, calibration.needle_pivot_y,
                        color=color, label="Pivot", point_type="needle_pivot"
                    )

                if calibration.needle_end_x > 0:
                    self.image_widget.add_display_point(
                        calibration.needle_end_x, calibration.needle_end_y,
                        color=color, label="End", point_type="needle_end"
                    )

            # Draw gauge pivot (for all sets)
            if calibration.gauge_pivot_x > 0:
                display_color = color if is_active else "gray"
                label = f"Pivot" if is_active else f"Pivot ({set_name})"
                self.image_widget.add_display_point(
                    calibration.gauge_pivot_x, calibration.gauge_pivot_y,
                    color=display_color, label=label, point_type="gauge_pivot"
                )

            # Draw calibration points (all sets, color-coded)
            for i, point in enumerate(calibration.calibration_points):
                display_color = color if is_active else "gray"
                label = f"{point.value}"
                if not is_active:
                    label = f"{set_name}: {point.value}"

                self.image_widget.add_display_point(
                    point.x, point.y,
                    color=display_color, label=label, point_type="calibration"
                )

        # Draw symbols for current gauge
        self._redraw_symbol_markers()

    def _redraw_symbol_markers(self):
        """Redraw position markers for all symbols"""
        if not self.symbols:
            return

        for symbol_id, symbol in self.symbols.items():
            if symbol.position_x > 0 and symbol.position_y > 0:
                self.image_widget.add_display_point(
                    symbol.position_x,
                    symbol.position_y,
                    color="magenta",
                    label=symbol_id,
                    point_type="symbol"
                )

    def load_calibration_sets_for_needle(self, gauge_name: str, needle_id: str):
        """Load all calibration sets for a needle from config"""
        config_file = self.config_dir / f"{gauge_name.lower()}.json"

        if not config_file.exists():
            # Start with default set
            self.calibration_sets = {
                "set1": NeedleCalibration(
                    needle_id=needle_id,
                    needle_image_path="",
                    gauge_name=gauge_name
                )
            }
            self._update_calibration_set_combo()
            return

        try:
            with open(config_file, 'r') as f:
                config = json.load(f)

            needle_calibrations = config.get("needle_calibrations", {})
            self.calibration_sets = {}

            # Find all calibrations for this needle (look for needle_id matching)
            for key, cal_data in needle_calibrations.items():
                if cal_data.get("needle_id") == needle_id:
                    set_name = cal_data.get("calibration_set", "set1")
                    self.calibration_sets[set_name] = NeedleCalibration.from_dict(cal_data)

            if not self.calibration_sets:
                # No sets found, create default
                self.calibration_sets["set1"] = NeedleCalibration(
                    needle_id=needle_id,
                    needle_image_path="",
                    gauge_name=gauge_name
                )

            self._update_calibration_set_combo()

        except Exception as e:
            logger.error(f"Failed to load calibration sets: {e}")

    def _update_calibration_set_combo(self):
        """Update calibration set dropdown"""
        self.calibration_set_combo.blockSignals(True)
        self.calibration_set_combo.clear()
        self.calibration_set_combo.addItems(sorted(self.calibration_sets.keys()))

        if self.current_set_name in self.calibration_sets:
            self.calibration_set_combo.setCurrentText(self.current_set_name)
        else:
            self.current_set_name = list(self.calibration_sets.keys())[0]
            self.calibration_set_combo.setCurrentText(self.current_set_name)

        self.calibration_set_combo.blockSignals(False)

        # Update current calibration
        self.current_calibration = self.calibration_sets[self.current_set_name]

    def on_calibration_set_changed(self, set_name: str):
        """Handle calibration set change"""
        if set_name not in self.calibration_sets:
            return

        self.current_set_name = set_name
        self.current_calibration = self.calibration_sets[set_name]

        # Update UI
        self._update_ui_from_calibration()

        # Update color indicator
        color = self.CALIBRATION_SET_COLORS[list(self.calibration_sets.keys()).index(set_name) % len(self.CALIBRATION_SET_COLORS)]
        self.set_color_label.setText(f"Set Color: {color.capitalize()}")
        self.set_color_label.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 11pt;")

    def add_calibration_set(self):
        """Add new calibration set for current needle"""
        # Generate new set name
        i = len(self.calibration_sets) + 1
        while f"set{i}" in self.calibration_sets:
            i += 1

        new_set_name = f"set{i}"

        # Assign color
        color = self.CALIBRATION_SET_COLORS[self.next_color_index % len(self.CALIBRATION_SET_COLORS)]
        self.next_color_index += 1

        # Create new calibration (copy geometry from current)
        new_cal = NeedleCalibration(
            needle_id=self.current_calibration.needle_id,
            needle_image_path=self.current_calibration.needle_image_path,
            gauge_name=self.current_calibration.gauge_name,
            needle_pivot_x=self.current_calibration.needle_pivot_x,
            needle_pivot_y=self.current_calibration.needle_pivot_y,
            needle_end_x=self.current_calibration.needle_end_x,
            needle_end_y=self.current_calibration.needle_end_y,
            min_value=self.current_calibration.min_value,
            max_value=self.current_calibration.max_value
        )

        self.calibration_sets[new_set_name] = new_cal
        self.current_set_name = new_set_name
        self.current_calibration = new_cal

        self._update_calibration_set_combo()

        # Update color indicator
        self.set_color_label.setText(f"Set Color: {color.capitalize()}")
        self.set_color_label.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 11pt;")

        logger.info(f"✅ Added new calibration set: {new_set_name} ({color})")
        QMessageBox.information(self, "Set Added", f"Added calibration set '{new_set_name}' with color {color}")

    def delete_calibration_set(self):
        """Delete current calibration set"""
        if len(self.calibration_sets) <= 1:
            QMessageBox.warning(self, "Cannot Delete", "Cannot delete the last calibration set")
            return

        reply = QMessageBox.question(
            self, "Delete Set",
            f"Delete calibration set '{self.current_set_name}'?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            del self.calibration_sets[self.current_set_name]

            # Switch to first remaining set
            self.current_set_name = list(self.calibration_sets.keys())[0]
            self.current_calibration = self.calibration_sets[self.current_set_name]

            self._update_calibration_set_combo()

            logger.info(f"🗑️ Deleted calibration set")
            QMessageBox.information(self, "Deleted", "Calibration set deleted")

    def on_needle_changed(self, needle_name: str):
        """Handle needle selection - auto-load needle image and calibration"""
        self._autosave_suspended = True
        try:
            gauge_name = self.gauge_combo.currentText()
            preset = self.GAUGE_PRESETS.get(gauge_name, {})

            # Update current needle indicator
            self.current_needle_label.setText(f"🎯 Working on: {gauge_name} → {needle_name}")

            # Update current calibration
            self.current_calibration.needle_id = needle_name
            self.current_calibration.gauge_name = gauge_name
            self.current_calibration.min_value = preset.get("min", 0)
            self.current_calibration.max_value = preset.get("max", 100)

            # Don't auto-load needle image - user loads manually for Step 1
            # self._auto_load_needle_image(needle_name)

            # Auto-load calibration config
            self._auto_load_configuration()

            # If auto-load didn't find anything, reset UI
            if (self.current_calibration.needle_pivot_x == 0 and
                self.current_calibration.gauge_pivot_x == 0 and
                not self.current_calibration.calibration_points):

                self.needle_pivot_label.setText("Pivot: Not set")
                self.needle_end_label.setText("End: Not set")
                self.gauge_pivot_label.setText("Not set")
                # Update summary label
                if hasattr(self, 'calib_summary_label'):
                    self.calib_summary_label.setText("0 calibration points")

                # Reset spinboxes to zero
                self.needle_pivot_x_spin.blockSignals(True)
                self.needle_pivot_y_spin.blockSignals(True)
                self.needle_end_x_spin.blockSignals(True)
                self.needle_end_y_spin.blockSignals(True)
                self.gauge_pivot_x_spin.blockSignals(True)
                self.gauge_pivot_y_spin.blockSignals(True)

                self.needle_pivot_x_spin.setValue(0)
                self.needle_pivot_y_spin.setValue(0)
                self.needle_end_x_spin.setValue(0)
                self.needle_end_y_spin.setValue(0)
                self.gauge_pivot_x_spin.setValue(0)
                self.gauge_pivot_y_spin.setValue(0)

                self.needle_pivot_x_spin.blockSignals(False)
                self.needle_pivot_y_spin.blockSignals(False)
                self.needle_end_x_spin.blockSignals(False)
                self.needle_end_y_spin.blockSignals(False)
                self.gauge_pivot_x_spin.blockSignals(False)
                self.gauge_pivot_y_spin.blockSignals(False)

            # Reset point type selector to step 1a
            self.point_type_combo.blockSignals(True)
            self.point_type_combo.setCurrentIndex(0)
            self.point_type_combo.blockSignals(False)

            # Track which needle point we're waiting for (pivot or end)
            self.waiting_for_needle_pivot = True
            self.waiting_for_needle_end = False
        finally:
            self._autosave_suspended = False
    
    def on_point_type_changed(self, index):
        """User selected a point type to add"""
        if index == 0:
            # Needle PIVOT
            self.waiting_for_needle_pivot = True
            self.waiting_for_needle_end = False
        elif index == 1:
            # Needle END
            self.waiting_for_needle_pivot = False
            self.waiting_for_needle_end = True
        # index 2 and 3 are gauge pivot and calibration points, handled elsewhere

    
    def on_needle_pivot_edit(self):
        """Handle manual edit of needle pivot spinboxes"""
        if not self.current_calibration:
            return
        
        self.current_calibration.needle_pivot_x = self.needle_pivot_x_spin.value()
        self.current_calibration.needle_pivot_y = self.needle_pivot_y_spin.value()
        
        if self.current_calibration.needle_pivot_x > 0 or self.current_calibration.needle_pivot_y > 0:
            self.needle_pivot_label.setText(
                f"✓ Pivot: ({self.current_calibration.needle_pivot_x}, "
                f"{self.current_calibration.needle_pivot_y})"
            )
        self._schedule_autosave()
    
    def on_needle_end_edit(self):
        """Handle manual edit of needle end spinboxes"""
        if not self.current_calibration:
            return
        
        self.current_calibration.needle_end_x = self.needle_end_x_spin.value()
        self.current_calibration.needle_end_y = self.needle_end_y_spin.value()
        
        if self.current_calibration.needle_end_x > 0 or self.current_calibration.needle_end_y > 0:
            self.needle_end_label.setText(
                f"✓ End: ({self.current_calibration.needle_end_x}, "
                f"{self.current_calibration.needle_end_y})"
            )
        self._schedule_autosave()
    
    def on_gauge_pivot_edit(self):
        """Handle manual edit of gauge pivot spinboxes"""
        if not self.current_calibration:
            return
        
        self.current_calibration.gauge_pivot_x = self.gauge_pivot_x_spin.value()
        self.current_calibration.gauge_pivot_y = self.gauge_pivot_y_spin.value()
        
        if self.current_calibration.gauge_pivot_x > 0 or self.current_calibration.gauge_pivot_y > 0:
            self.gauge_pivot_label.setText(
                f"✓ Gauge Pivot: ({self.current_calibration.gauge_pivot_x}, "
                f"{self.current_calibration.gauge_pivot_y})"
            )
        self._schedule_autosave()
    
    def load_needle_image(self):
        """Load needle image and prepare for clicking"""
        if not self.current_calibration:
            QMessageBox.warning(self, "Error", "Select gauge first")
            return
        
        gauge_name = self.current_calibration.gauge_name.lower()
        needle_id = self.current_calibration.needle_id
        
        # Try standard paths (prefer SVG over PNG)
        gauges_dir = Path(__file__).parent.parent / "gauges"
        
        # Check for needle.svg (shared needle)
        needle_path = gauges_dir / "needle.svg"
        if not needle_path.exists():
            # Try needle ID with SVG
            needle_path = gauges_dir / f"{needle_id}_needle.svg"
        if not needle_path.exists():
            # Try gauge name with SVG
            needle_path = gauges_dir / f"{gauge_name}_needle.svg"
        if not needle_path.exists():
            # Fall back to PNG
            needle_path = gauges_dir / f"{needle_id}_needle.png"
        if not needle_path.exists():
            needle_path = gauges_dir / f"{gauge_name}_needle.png"
        
        if not needle_path.exists():
            QMessageBox.warning(self, "Error", f"Needle image not found. Expected: gauges/needle.svg or {needle_id}_needle.png")
            return
        
        if self.image_widget.load_image(str(needle_path)):
            self.current_calibration.needle_image_path = str(needle_path)
            self.image_widget.clear_display_points()
            self.image_widget.set_click_callback(self.on_needle_pivot_click)
            
            status = f"Ready: click needle pivot point on {needle_path.name}"
            self.needle_pivot_label.setText(status)
            QMessageBox.information(self, "Step 1", "Click the PIVOT POINT on the needle image")
            self._schedule_autosave()
    
    def on_needle_pivot_click(self, x: float, y: float):
        """Handle click on needle image - first for pivot, second for end point"""
        if not self.current_calibration:
            return
        
        if self.waiting_for_needle_pivot:
            # First click: set pivot point
            self.current_calibration.needle_pivot_x = x
            self.current_calibration.needle_pivot_y = y
            
            self.image_widget.add_display_point(x, y, "red", "PIVOT", "needle_pivot")
            self.needle_pivot_label.setText(f"✓ Pivot: ({int(x)}, {int(y)})")
            
            self.waiting_for_needle_pivot = False
            self.waiting_for_needle_end = True
            
            QMessageBox.information(self, "Step 1a Complete", 
                                  f"Pivot set at ({int(x)}, {int(y)})\n\n"
                                  f"Now click the NEEDLE TIP/END POINT")
            self._schedule_autosave()
        
        elif self.waiting_for_needle_end:
            # Second click: set end point
            self.current_calibration.needle_end_x = x
            self.current_calibration.needle_end_y = y
            
            self.image_widget.add_display_point(x, y, "blue", "END", "needle_end")
            self.needle_end_label.setText(f"✓ End: ({int(x)}, {int(y)})")
            
            self.waiting_for_needle_end = False
            
            # Draw line from pivot to end to show needle
            pivot_x = self.current_calibration.needle_pivot_x
            pivot_y = self.current_calibration.needle_pivot_y
            length = ((x - pivot_x)**2 + (y - pivot_y)**2) ** 0.5
            
            QMessageBox.information(self, "Step 1 Complete",
                                  f"End point set at ({int(x)}, {int(y)})\n"
                                  f"Needle length: {length:.1f} pixels\n\n"
                                  f"Ready to save or continue to Step 2")
            self._schedule_autosave()

    def reset_needle_geometry(self):
        """Reset needle pivot and end points to allow re-clicking"""
        if not self.current_calibration:
            QMessageBox.warning(self, "Error", "Select gauge first")
            return

        reply = QMessageBox.question(
            self,
            "Reset Needle Geometry",
            "This will clear the needle pivot and end points. Continue?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.current_calibration.needle_pivot_x = 0
            self.current_calibration.needle_pivot_y = 0
            self.current_calibration.needle_end_x = 0
            self.current_calibration.needle_end_y = 0

            self.needle_pivot_label.setText("Pivot: Not set")
            self.needle_end_label.setText("End: Not set")

            # Reset waiting flags
            self.waiting_for_needle_pivot = True
            self.waiting_for_needle_end = False

            # Clear needle points from display
            self._redraw_all_points()

            logger.info("✅ Reset needle geometry")
            QMessageBox.information(self, "Reset Complete", "Needle geometry cleared. Click 'Load Needle Image' to set new pivot and end points.")

    def reset_gauge_pivot(self):
        """Reset gauge pivot to allow re-clicking"""
        if not self.current_calibration:
            QMessageBox.warning(self, "Error", "Select gauge first")
            return

        reply = QMessageBox.question(
            self,
            "Reset Gauge Pivot",
            "This will clear the gauge pivot point. Continue?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.current_calibration.gauge_pivot_x = 0
            self.current_calibration.gauge_pivot_y = 0

            self.gauge_pivot_label.setText("Not set")

            # Clear gauge pivot from display
            self._redraw_all_points()

            logger.info("✅ Reset gauge pivot")
            QMessageBox.information(self, "Reset Complete", "Gauge pivot cleared. Click on the gauge image to set new pivot point.")

    def load_gauge_image(self):
        """Load gauge background image"""
        if not self.current_calibration:
            QMessageBox.warning(self, "Error", "Select gauge first")
            return
        
        gauge_name = self.current_calibration.gauge_name.lower()
        gauge_path = Path(__file__).parent.parent / "gauges" / f"{gauge_name}_bg.png"
        
        if not gauge_path.exists():
            QMessageBox.warning(self, "Error", f"Gauge image not found: {gauge_path}")
            return
        
        if self.image_widget.load_image(str(gauge_path)):
            self.image_widget.clear_display_points()
            
            # First show gauge pivot location
            if self.current_calibration.gauge_pivot_x > 0:
                self.image_widget.add_display_point(
                    self.current_calibration.gauge_pivot_x,
                    self.current_calibration.gauge_pivot_y,
                    "blue", "GAUGE PIVOT", "gauge_pivot"
                )
            
            # Show existing calibration points
            for point in self.current_calibration.calibration_points:
                self.image_widget.add_display_point(
                    point.x, point.y, "green", f"{point.value}", "calibration"
                )
            
            self.image_widget.set_click_callback(self.on_gauge_click)
            QMessageBox.information(self, "Gauge Image Loaded", 
                                  "Click to set gauge pivot or add calibration points")
    
    def on_gauge_click(self, x: float, y: float):
        """Handle click on gauge image - set pivot or calibration point"""
        if not self.current_calibration.gauge_pivot_x:
            # First click sets gauge pivot
            self.current_calibration.gauge_pivot_x = x
            self.current_calibration.gauge_pivot_y = y
            self.gauge_pivot_label.setText(f"✓ Gauge Pivot: ({int(x)}, {int(y)})")
            
            self.image_widget.add_display_point(x, y, "blue", "GAUGE PIVOT", "gauge_pivot")
            QMessageBox.information(self, "Success", 
                                  f"Gauge pivot set at ({int(x)}, {int(y)})\nNow add calibration points")
            self._schedule_autosave()
        else:
            # Store last click location for next "Add Point" button press
            self.last_click_x = x
            self.last_click_y = y
            self.image_widget.add_display_point(x, y, "yellow", "pending", "calibration")
            QMessageBox.information(self, "Point Captured",
                                  f"Click location: ({int(x)}, {int(y)})\nNow enter value and press Add Point")
    
    def on_point_dragged(self, point_index: int, x: float, y: float):
        """Handle dragging an existing point"""
        if not self.current_calibration or point_index < 0 or point_index >= len(self.image_widget.display_points):
            return
        
        point_info = self.image_widget.display_points[point_index]
        point_type = point_info.get("point_type")
        
        # Update the point in display_points
        point_info["x"] = x
        point_info["y"] = y
        
        # Update corresponding calibration data
        if point_type == "needle_pivot":
            self.current_calibration.needle_pivot_x = x
            self.current_calibration.needle_pivot_y = y
            self.needle_pivot_x_spin.blockSignals(True)
            self.needle_pivot_y_spin.blockSignals(True)
            self.needle_pivot_x_spin.setValue(int(x))
            self.needle_pivot_y_spin.setValue(int(y))
            self.needle_pivot_x_spin.blockSignals(False)
            self.needle_pivot_y_spin.blockSignals(False)
            self.needle_pivot_label.setText(f"✓ Pivot: ({int(x)}, {int(y)})")
            
        elif point_type == "needle_end":
            self.current_calibration.needle_end_x = x
            self.current_calibration.needle_end_y = y
            self.needle_end_x_spin.blockSignals(True)
            self.needle_end_y_spin.blockSignals(True)
            self.needle_end_x_spin.setValue(int(x))
            self.needle_end_y_spin.setValue(int(y))
            self.needle_end_x_spin.blockSignals(False)
            self.needle_end_y_spin.blockSignals(False)
            self.needle_end_label.setText(f"✓ End: ({int(x)}, {int(y)})")
            
        elif point_type == "gauge_pivot":
            self.current_calibration.gauge_pivot_x = x
            self.current_calibration.gauge_pivot_y = y
            self.gauge_pivot_x_spin.blockSignals(True)
            self.gauge_pivot_y_spin.blockSignals(True)
            self.gauge_pivot_x_spin.setValue(int(x))
            self.gauge_pivot_y_spin.setValue(int(y))
            self.gauge_pivot_x_spin.blockSignals(False)
            self.gauge_pivot_y_spin.blockSignals(False)
            self.gauge_pivot_label.setText(f"✓ ({int(x)}, {int(y)})")
            
        elif point_type == "calibration":
            # Find which calibration point this is and update it
            # Count calibration points up to this display point
            calib_index = 0
            display_index = 0
            for i, dp in enumerate(self.image_widget.display_points):
                if i == point_index:
                    break
                if dp.get("point_type") == "calibration":
                    calib_index += 1
            
            if calib_index < len(self.current_calibration.calibration_points):
                self.current_calibration.calibration_points[calib_index].x = x
                self.current_calibration.calibration_points[calib_index].y = y
                self._refresh_calibration_table()
        self._schedule_autosave()
    
    def add_calibration_point(self):
        """Add calibration point from last click and entered value"""
        if not self.current_calibration:
            QMessageBox.warning(self, "Error", "Select gauge first")
            return
        
        if not hasattr(self, 'last_click_x'):
            QMessageBox.warning(self, "Error", "Click on gauge image first")
            return
        
        value = self.point_value_spin.value()
        point = CalibrationPoint(self.last_click_x, self.last_click_y, value)
        self.current_calibration.calibration_points.append(point)
        
        self._refresh_calibration_table()
        
        # Update display
        self.image_widget.clear_display_points()
        self.image_widget.add_display_point(
            self.current_calibration.gauge_pivot_x,
            self.current_calibration.gauge_pivot_y,
            "blue", "GAUGE PIVOT", "gauge_pivot"
        )
        for pt in self.current_calibration.calibration_points:
            self.image_widget.add_display_point(pt.x, pt.y, "green", f"{pt.value}", "calibration")
        self._schedule_autosave()
    
    def _refresh_calibration_table(self):
        """Update calibration summary label"""
        if not hasattr(self, 'calib_summary_label'):
            return

        num_points = len(self.current_calibration.calibration_points)
        self.calib_summary_label.setText(f"{num_points} calibration point{'s' if num_points != 1 else ''}")
    
    def delete_last_calibration_point(self):
        """Delete the last calibration point"""
        if not self.current_calibration or not self.current_calibration.calibration_points:
            QMessageBox.information(self, "No Points", "No calibration points to delete")
            return

        deleted_point = self.current_calibration.calibration_points.pop()
        self._refresh_calibration_table()
        self._redraw_all_points()
        logger.info(f"🗑️ Deleted calibration point at value {deleted_point.value}")
        self._schedule_autosave()

    def clear_all_calibration_points(self):
        """Clear all calibration points"""
        if not self.current_calibration or not self.current_calibration.calibration_points:
            return

        reply = QMessageBox.question(
            self, "Clear All",
            f"Clear all {len(self.current_calibration.calibration_points)} calibration points?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.current_calibration.calibration_points.clear()
            self._refresh_calibration_table()
            self._redraw_all_points()
            logger.info("🗑️ Cleared all calibration points")
            self._schedule_autosave()

    def delete_point(self, row: int):
        """Delete calibration point"""
        if 0 <= row < len(self.current_calibration.calibration_points):
            del self.current_calibration.calibration_points[row]
            self._refresh_calibration_table()
            self._schedule_autosave()
    
    def save_needle_configuration(self):
        """Save only needle configuration (pivot and end points)"""
        if not self.current_calibration:
            QMessageBox.warning(self, "Error", "No gauge selected")
            return
        
        if not self.current_calibration.needle_image_path:
            QMessageBox.warning(self, "Error", "Load needle image first")
            return
        
        if self.current_calibration.needle_pivot_x == 0 and self.current_calibration.needle_pivot_y == 0:
            QMessageBox.warning(self, "Error", "Set needle PIVOT point first (click on center)")
            return
        
        if self.current_calibration.needle_end_x == 0 and self.current_calibration.needle_end_y == 0:
            QMessageBox.warning(self, "Error", "Set needle END point (click on tip)")
            return
        
        # Load or create gauge config
        try:
            gauge_name = self.current_calibration.gauge_name.lower()
            config_file = self.config_dir / f"{gauge_name}.json"
            
            if config_file.exists():
                with open(config_file, 'r') as f:
                    config = json.load(f)
                # Handle old format: if it has "needles" instead of "needle_calibrations", migrate it
                if "needles" in config and "needle_calibrations" not in config:
                    config["needle_calibrations"] = {}
                # Ensure config is a dict
                if not isinstance(config, dict):
                    config = {"name": self.current_calibration.gauge_name, "needle_calibrations": {}}
            else:
                config = {"name": self.current_calibration.gauge_name, "needle_calibrations": {}}
            
            # Ensure needle_calibrations key exists
            if "needle_calibrations" not in config:
                config["needle_calibrations"] = {}
            
            # Ensure it's a dict
            if not isinstance(config["needle_calibrations"], dict):
                config["needle_calibrations"] = {}
            
            # Save ONLY needle geometry, no gauge/calibration points
            needle_config = {
                "needle_id": self.current_calibration.needle_id,
                "needle_image_path": self.current_calibration.needle_image_path,
                "gauge_name": self.current_calibration.gauge_name,
                "needle_pivot_x": self.current_calibration.needle_pivot_x,
                "needle_pivot_y": self.current_calibration.needle_pivot_y,
                "needle_end_x": self.current_calibration.needle_end_x,
                "needle_end_y": self.current_calibration.needle_end_y,
                "gauge_pivot_x": 0,  # Not set yet
                "gauge_pivot_y": 0,
                "calibration_points": [],  # Not set yet
                "min_value": self.current_calibration.min_value,
                "max_value": self.current_calibration.max_value,
            }
            
            config["needle_calibrations"][self.current_calibration.needle_id] = needle_config
            
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            QMessageBox.information(self, "Success", 
                                  f"✓ Needle configuration saved!\n\n"
                                  f"Needle: {self.current_calibration.needle_id}\n"
                                  f"Pivot: ({int(self.current_calibration.needle_pivot_x)}, "
                                  f"{int(self.current_calibration.needle_pivot_y)})\n"
                                  f"End: ({int(self.current_calibration.needle_end_x)}, "
                                  f"{int(self.current_calibration.needle_end_y)})\n"
                                  f"File: {config_file}")
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            QMessageBox.critical(self, "Error", 
                               f"Failed to save 'needle_calibrations':\n\n{e}\n\n{error_details}")
    
    def save_gauge_configuration(self):
        """Save all calibration sets to config file"""
        if not self.current_calibration:
            QMessageBox.warning(self, "Error", "No gauge selected")
            return

        if self.current_calibration.gauge_pivot_x == 0:
            QMessageBox.warning(self, "Error", "Set gauge pivot location first")
            return

        if not self.current_calibration.calibration_points:
            QMessageBox.warning(self, "Error", "Add at least one calibration point")
            return

        # Load or create gauge config
        try:
            gauge_name = self.current_calibration.gauge_name.lower()
            config_file = self.config_dir / f"{gauge_name}.json"

            if config_file.exists():
                with open(config_file, 'r') as f:
                    config = json.load(f)
                # Handle old format: if it has "needles" instead of "needle_calibrations", migrate it
                if "needles" in config and "needle_calibrations" not in config:
                    config["needle_calibrations"] = {}
                # Ensure config is a dict
                if not isinstance(config, dict):
                    config = {"name": self.current_calibration.gauge_name, "needle_calibrations": {}}
            else:
                config = {"name": self.current_calibration.gauge_name, "needle_calibrations": {}}

            # Ensure needle_calibrations key exists
            if "needle_calibrations" not in config:
                config["needle_calibrations"] = {}

            # Ensure it's a dict
            if not isinstance(config["needle_calibrations"], dict):
                config["needle_calibrations"] = {}

            # Save all calibration sets for current needle
            for set_name, calibration in self.calibration_sets.items():
                # Generate key: needle_id_setname (e.g., "main_set1")
                key = f"{calibration.needle_id}_{set_name}"

                cal_dict = calibration.to_dict()
                cal_dict["calibration_set"] = set_name

                # Assign color if not present
                color_index = list(self.calibration_sets.keys()).index(set_name)
                cal_dict["calibration_set_color"] = self.CALIBRATION_SET_COLORS[
                    color_index % len(self.CALIBRATION_SET_COLORS)
                ]

                config["needle_calibrations"][key] = cal_dict

            # Write config
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)

            self.has_unsaved_changes = False

            logger.info(f"💾 Saved {len(self.calibration_sets)} calibration set(s) to {config_file.name}")

            QMessageBox.information(
                self, "Saved",
                f"✓ Saved {len(self.calibration_sets)} calibration set(s)!\n\n"
                f"Gauge: {self.current_calibration.gauge_name}\n"
                f"Needle: {self.current_calibration.needle_id}\n"
                f"Sets: {', '.join(self.calibration_sets.keys())}"
            )
        except KeyError as e:
            import traceback
            error_details = traceback.format_exc()
            QMessageBox.critical(self, "Error",
                               f"KeyError saving configuration:\n\nMissing key: {e}\n\n"
                               f"This usually means the JSON file structure is corrupted.\n\n"
                               f"{error_details}")
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            QMessageBox.critical(self, "Error",
                               f"Failed to save configuration:\n\n{e}\n\n{error_details}")
    
    def save_configuration(self):
        """Legacy - kept for backward compatibility"""
        self.save_gauge_configuration()
    
    def load_configuration(self):
        """Load calibration from config file"""
        if not self.current_calibration:
            QMessageBox.warning(self, "Error", "Select gauge first")
            return

        self._autosave_suspended = True
        try:
            gauge_name = self.current_calibration.gauge_name.lower()
            config_file = self.config_dir / f"{gauge_name}.json"
            
            if not config_file.exists():
                QMessageBox.information(self, "New Gauge", f"No existing configuration for {gauge_name}.\n\nThis is a new gauge - start calibrating!")
                return
            
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            needle_id = self.current_calibration.needle_id
            if "needle_calibrations" not in config or needle_id not in config["needle_calibrations"]:
                QMessageBox.information(self, "New Needle", f"No existing calibration for {needle_id}.\n\nThis is a new needle - start calibrating!")
                return
            
            self.current_calibration = NeedleCalibration.from_dict(
                config["needle_calibrations"][needle_id]
            )
            
            self._refresh_calibration_table()
            
            # Update spinboxes with loaded values
            self.needle_pivot_x_spin.blockSignals(True)
            self.needle_pivot_y_spin.blockSignals(True)
            self.needle_end_x_spin.blockSignals(True)
            self.needle_end_y_spin.blockSignals(True)
            self.gauge_pivot_x_spin.blockSignals(True)
            self.gauge_pivot_y_spin.blockSignals(True)
            
            self.needle_pivot_x_spin.setValue(int(self.current_calibration.needle_pivot_x))
            self.needle_pivot_y_spin.setValue(int(self.current_calibration.needle_pivot_y))
            self.needle_end_x_spin.setValue(int(self.current_calibration.needle_end_x))
            self.needle_end_y_spin.setValue(int(self.current_calibration.needle_end_y))
            self.gauge_pivot_x_spin.setValue(int(self.current_calibration.gauge_pivot_x))
            self.gauge_pivot_y_spin.setValue(int(self.current_calibration.gauge_pivot_y))
            
            self.needle_pivot_x_spin.blockSignals(False)
            self.needle_pivot_y_spin.blockSignals(False)
            self.needle_end_x_spin.blockSignals(False)
            self.needle_end_y_spin.blockSignals(False)
            self.gauge_pivot_x_spin.blockSignals(False)
            self.gauge_pivot_y_spin.blockSignals(False)
            
            self.needle_pivot_label.setText(
                f"✓ Pivot: ({int(self.current_calibration.needle_pivot_x)}, "
                f"{int(self.current_calibration.needle_pivot_y)})"
            )
            self.needle_end_label.setText(
                f"✓ End: ({int(self.current_calibration.needle_end_x)}, "
                f"{int(self.current_calibration.needle_end_y)})"
            )
            self.gauge_pivot_label.setText(
                f"✓ ({int(self.current_calibration.gauge_pivot_x)}, "
                f"{int(self.current_calibration.gauge_pivot_y)})"
            )
            
            QMessageBox.information(self, "Loaded", f"Configuration loaded for {needle_id}\n\n{len(self.current_calibration.calibration_points)} calibration points found")
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            QMessageBox.critical(self, "Error", f"Failed to load:\n\n{e}\n\n{error_details}")
        finally:
            self._autosave_suspended = False

    def _schedule_autosave(self):
        if self._autosave_suspended or not self.current_calibration:
            return
        self._autosave_timer.start()

    def _autosave_current_calibration(self):
        if self._autosave_suspended or not self.current_calibration:
            return

        try:
            gauge_name = self.current_calibration.gauge_name.lower()
            config_file = self.config_dir / f"{gauge_name}.json"

            if config_file.exists():
                with open(config_file, 'r') as f:
                    config = json.load(f)
                if "needles" in config and "needle_calibrations" not in config:
                    config["needle_calibrations"] = {}
                if not isinstance(config, dict):
                    config = {"name": self.current_calibration.gauge_name, "needle_calibrations": {}}
            else:
                config = {"name": self.current_calibration.gauge_name, "needle_calibrations": {}}

            if "needle_calibrations" not in config or not isinstance(config["needle_calibrations"], dict):
                config["needle_calibrations"] = {}

            config["needle_calibrations"][self.current_calibration.needle_id] = \
                self.current_calibration.to_dict()

            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            logger.warning(f"⚠️ Autosave failed: {e}")
    
    def reset_current_gauge(self):
        """Reset current gauge calibration"""
        if not self.current_calibration:
            QMessageBox.warning(self, "Reset", "No active needle calibration to reset.")
            return

        reply = QMessageBox.question(
            self,
            "Reset Gauge",
            "This will clear the current calibration. Are you sure?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Clear calibration points
            self.current_calibration.calibration_points.clear()
            self.current_calibration.needle_pivot_x = 0
            self.current_calibration.needle_pivot_y = 0
            self.current_calibration.needle_end_x = 0
            self.current_calibration.needle_end_y = 0
            self.current_calibration.gauge_pivot_x = 0
            self.current_calibration.gauge_pivot_y = 0
            
            # Reset UI labels
            self.needle_pivot_label.setText("Not set")
            self.needle_end_label.setText("Not set")
            self.gauge_pivot_label.setText("Not set")

            # Update calibration summary
            if hasattr(self, 'calib_summary_label'):
                self.calib_summary_label.setText("0 calibration points")

            # Refresh display
            self.image_widget.clear_display_points()
            self.image_widget.update()
            
            logger.info("🔄 Gauge calibration reset")
            QMessageBox.information(self, "Reset", "Gauge calibration has been reset")
    
    def add_new_needle(self):
        """Add a new needle to current gauge"""
        gauge_name = self.gauge_combo.currentText()
        
        # Find next available needle number
        existing_needles = self.NEEDLE_TYPES.get(gauge_name, ["main"])
        needle_num = 1
        while f"needle_{needle_num}" in existing_needles:
            needle_num += 1
        
        new_needle_name = f"needle_{needle_num}"
        
        # Add to needle types
        if gauge_name not in self.NEEDLE_TYPES:
            self.NEEDLE_TYPES[gauge_name] = ["main"]
        
        self.NEEDLE_TYPES[gauge_name].append(new_needle_name)
        
        # Update needle combo
        self.needle_combo.blockSignals(True)
        self.needle_combo.addItem(new_needle_name)
        self.needle_combo.setCurrentText(new_needle_name)
        self.needle_combo.blockSignals(False)
        
        # Persist the needle to config file
        self._persist_needle_to_config(gauge_name, new_needle_name)
        
        logger.info(f"✅ Added needle '{new_needle_name}' to {gauge_name}")
        QMessageBox.information(self, "Needle Added", f"Added {new_needle_name} to {gauge_name}\n\nNow calibrate this needle.")
    
    def _persist_needle_to_config(self, gauge_name, needle_name):
        """Save a new needle entry to the config file"""
        config_file = self.config_dir / f"{gauge_name.lower()}.json"
        
        # Load existing config or create new
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
            except:
                config = {}
        else:
            config = {}
        
        # Ensure needle_calibrations section exists
        if 'needle_calibrations' not in config:
            config['needle_calibrations'] = {}
        
        # Add new needle with empty calibration (will be filled when user calibrates)
        if needle_name not in config['needle_calibrations']:
            config['needle_calibrations'][needle_name] = {
                "pivot_x": 0,
                "pivot_y": 0,
                "end_x": 0,
                "end_y": 0,
                "calibration_points": [],
                "scale": 1.0
            }
            
            # Save config
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            logger.info(f"💾 Persisted {needle_name} to {config_file.name}")
    
    def rename_needle(self):
        """Rename the currently selected needle"""
        from PyQt5.QtWidgets import QInputDialog
        
        gauge_name = self.gauge_combo.currentText()
        old_needle_name = self.needle_combo.currentText()
        
        if not old_needle_name:
            QMessageBox.warning(self, "No Needle", "Select a needle to rename")
            return
        
        # Ask for new name
        new_name, ok = QInputDialog.getText(
            self, "Rename Needle",
            f"Enter new name for '{old_needle_name}':",
            text=old_needle_name
        )
        
        if not ok or not new_name or new_name == old_needle_name:
            return
        
        # Check if name already exists
        if new_name in self.NEEDLE_TYPES.get(gauge_name, []):
            QMessageBox.warning(self, "Name Exists", f"Needle '{new_name}' already exists!")
            return
        
        # Update in-memory needle types
        needle_list = self.NEEDLE_TYPES.get(gauge_name, [])
        if old_needle_name in needle_list:
            idx = needle_list.index(old_needle_name)
            needle_list[idx] = new_name
        
        # Update config file
        config_file = self.config_dir / f"{gauge_name.lower()}.json"
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                
                # Rename in needle_calibrations
                if 'needle_calibrations' in config:
                    if old_needle_name in config['needle_calibrations']:
                        config['needle_calibrations'][new_name] = config['needle_calibrations'].pop(old_needle_name)
                        
                        # Update needle_id field if it exists
                        if 'needle_id' in config['needle_calibrations'][new_name]:
                            config['needle_calibrations'][new_name]['needle_id'] = new_name
                        
                        # Save
                        with open(config_file, 'w') as f:
                            json.dump(config, f, indent=2)
                        
                        logger.info(f"✏️ Renamed '{old_needle_name}' to '{new_name}'")
                
                # Update combo box
                self.needle_combo.blockSignals(True)
                self.needle_combo.clear()
                self.needle_combo.addItems(needle_list)
                self.needle_combo.setCurrentText(new_name)
                self.needle_combo.blockSignals(False)
                
                # Update current calibration
                if self.current_calibration and self.current_calibration.needle_id == old_needle_name:
                    self.current_calibration.needle_id = new_name
                
                QMessageBox.information(self, "Renamed", f"Renamed to '{new_name}'")
            except Exception as e:
                logger.error(f"❌ Failed to rename needle: {e}")
                QMessageBox.critical(self, "Error", f"Failed to rename: {e}")
    
    def delete_needle(self):
        """Delete the currently selected needle"""
        gauge_name = self.gauge_combo.currentText()
        needle_name = self.needle_combo.currentText()
        
        # Don't allow deleting ALL needles - need at least one
        needle_list = self.NEEDLE_TYPES.get(gauge_name, [])
        if len(needle_list) <= 1:
            QMessageBox.warning(self, "Cannot Delete", "Must keep at least one needle!")
            return
        
        if not needle_name:
            QMessageBox.warning(self, "No Needle", "Select a needle to delete")
            return
        
        # Confirm deletion
        reply = QMessageBox.question(
            self, "Delete Needle",
            f"Delete needle '{needle_name}' from {gauge_name}?\n\nThis cannot be undone!",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # Remove from in-memory list
        needle_list.remove(needle_name)
        
        # Remove from config file
        config_file = self.config_dir / f"{gauge_name.lower()}.json"
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                
                # Delete from needle_calibrations
                if 'needle_calibrations' in config:
                    if needle_name in config['needle_calibrations']:
                        del config['needle_calibrations'][needle_name]
                        
                        # Save
                        with open(config_file, 'w') as f:
                            json.dump(config, f, indent=2)
                        
                        logger.info(f"🗑️ Deleted needle '{needle_name}' from {gauge_name}")
                
                # Update combo box to first remaining needle
                self.needle_combo.blockSignals(True)
                self.needle_combo.clear()
                self.needle_combo.addItems(needle_list)
                self.needle_combo.blockSignals(False)
                
                # Switch to first needle
                if needle_list:
                    self.on_needle_changed(needle_list[0])
                
                QMessageBox.information(self, "Deleted", f"Deleted '{needle_name}'")
            except Exception as e:
                logger.error(f"❌ Failed to delete needle: {e}")
                QMessageBox.critical(self, "Error", f"Failed to delete: {e}")

    # ========== Symbol Management Methods ==========

    def _load_symbols(self):
        """Load symbols for current gauge from gauge config file"""
        if not self.current_calibration:
            logger.info("No gauge selected - skipping symbol load")
            self.symbols = {}
            self._update_symbol_combo()
            return

        gauge_name = self.current_calibration.gauge_name.lower()
        config_file = self.config_dir / f"{gauge_name}.json"

        if not config_file.exists():
            logger.info(f"No config file found for {gauge_name} - starting fresh")
            self.symbols = {}
            self._update_symbol_combo()
            return

        try:
            with open(config_file, 'r') as f:
                data = json.load(f)

            self.symbols = {}
            for symbol_id, symbol_data in data.get("symbols", {}).items():
                self.symbols[symbol_id] = Symbol.from_dict(symbol_data)

            if self.symbols:
                self.current_symbol_id = list(self.symbols.keys())[0]
            else:
                self.current_symbol_id = None

            self._update_symbol_combo()

            logger.info(f"✅ Loaded {len(self.symbols)} symbol(s) for {gauge_name}")

        except Exception as e:
            logger.error(f"Failed to load symbols for {gauge_name}: {e}")
            self.symbols = {}
            self.current_symbol_id = None
            self._update_symbol_combo()

    def _update_symbol_combo(self):
        """Update symbol dropdown"""
        self.symbol_combo.blockSignals(True)
        self.symbol_combo.clear()

        if self.symbols:
            sorted_symbols = sorted(self.symbols.keys())
            self.symbol_combo.addItems(sorted_symbols)
            logger.info(f"📋 Symbol dropdown updated with: {sorted_symbols}")

            if self.current_symbol_id and self.current_symbol_id in self.symbols:
                self.symbol_combo.setCurrentText(self.current_symbol_id)
                logger.info(f"🎯 Selected symbol: {self.current_symbol_id}")
            elif sorted_symbols:
                # Select first symbol if current is None or not in list
                self.current_symbol_id = sorted_symbols[0]
                self.symbol_combo.setCurrentText(self.current_symbol_id)
                logger.info(f"🎯 Auto-selected first symbol: {self.current_symbol_id}")
        else:
            self.current_symbol_id = None
            logger.info("📋 Symbol dropdown cleared (no symbols)")

        self.symbol_combo.blockSignals(False)

        # Trigger UI update for the selected symbol
        if self.current_symbol_id:
            self.on_symbol_changed(self.current_symbol_id)

    def add_symbol(self):
        """Add new symbol"""
        if not self.current_calibration:
            QMessageBox.warning(self, "No Gauge", "Select a gauge first")
            return

        # Generate unique ID
        i = 1
        while f"symbol_{i}" in self.symbols:
            i += 1

        symbol_id = f"symbol_{i}"

        new_symbol = Symbol(
            symbol_id=symbol_id,
            image_path="",
            position_x=100,
            position_y=100,
            scale=1.0
        )

        self.symbols[symbol_id] = new_symbol
        self.current_symbol_id = symbol_id

        self._update_symbol_combo()
        self.symbol_combo.setCurrentText(symbol_id)

        # Update position label
        self.symbol_position_label.setText("Position: Not set")

        logger.info(f"✅ Added {symbol_id}")
        QMessageBox.information(self, "Symbol Added", f"Added {symbol_id}\n\nNow load an image and position it on the gauge.")

    def delete_symbol(self):
        """Delete current symbol"""
        if not self.current_symbol_id or self.current_symbol_id not in self.symbols:
            QMessageBox.warning(self, "No Symbol", "No symbol selected")
            return

        reply = QMessageBox.question(
            self, "Delete Symbol",
            f"Delete symbol '{self.current_symbol_id}'?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            del self.symbols[self.current_symbol_id]

            if self.symbols:
                self.current_symbol_id = list(self.symbols.keys())[0]
            else:
                self.current_symbol_id = None

            self._update_symbol_combo()
            self._redraw_all_points()

            logger.info(f"🗑️ Deleted symbol")

    def load_symbol_image(self):
        """Load image for current symbol"""
        if not self.current_symbol_id:
            QMessageBox.warning(self, "No Symbol", "Add a symbol first")
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Symbol Image",
            str(Path(__file__).parent.parent / "symbols"),
            "Images (*.png *.svg *.jpg)"
        )

        if file_path:
            self.symbols[self.current_symbol_id].image_path = file_path
            logger.info(f"✅ Loaded symbol image: {Path(file_path).name}")
            QMessageBox.information(self, "Loaded", f"Loaded: {Path(file_path).name}")

    def start_positioning_symbol(self):
        """Start positioning mode for the current symbol"""
        if not self.current_symbol_id:
            QMessageBox.warning(self, "No Symbol", "Add a symbol first")
            return

        # Load gauge image if not already loaded
        if not hasattr(self.image_widget, 'image') or self.image_widget.image is None:
            gauge_name = self.gauge_combo.currentText().lower()
            gauge_path = Path(__file__).parent.parent / "gauges" / f"{gauge_name}_bg.png"
            if gauge_path.exists():
                self.image_widget.load_image(str(gauge_path))
            else:
                QMessageBox.warning(self, "Error", "Please load gauge image first (Step 4)")
                return

        # Set callback for symbol positioning
        self.image_widget.set_click_callback(self.on_symbol_position_click)
        self.positioning_symbol = True

        QMessageBox.information(
            self,
            "Position Symbol",
            f"Click on the gauge where you want to place {self.current_symbol_id}"
        )

    def on_symbol_position_click(self, x: float, y: float):
        """Handle click when positioning a symbol"""
        if not self.positioning_symbol or not self.current_symbol_id:
            return

        # Update symbol position
        self.symbols[self.current_symbol_id].position_x = x
        self.symbols[self.current_symbol_id].position_y = y

        # Update position label
        self.symbol_position_label.setText(f"✓ Position: ({int(x)}, {int(y)})")

        # Mark as changed
        self.has_unsaved_changes = True

        # Draw symbol position on gauge
        self.image_widget.add_display_point(x, y, "magenta", self.current_symbol_id, "symbol")

        # Reset mode
        self.positioning_symbol = False
        self.image_widget.set_click_callback(self.on_gauge_click)

        logger.info(f"✅ Positioned {self.current_symbol_id} at ({int(x)}, {int(y)})")
        QMessageBox.information(
            self,
            "Position Set",
            f"{self.current_symbol_id} positioned at ({int(x)}, {int(y)})"
        )

    def on_symbol_changed(self, symbol_id: str):
        """Handle symbol selection change"""
        if symbol_id not in self.symbols:
            return

        self.current_symbol_id = symbol_id
        symbol = self.symbols[symbol_id]

        # Update display name field
        self.symbol_display_name_edit.blockSignals(True)
        self.symbol_display_name_edit.setText(symbol.display_name if symbol.display_name else "")
        self.symbol_display_name_edit.blockSignals(False)

        # Update position label
        if symbol.position_x > 0 and symbol.position_y > 0:
            self.symbol_position_label.setText(f"✓ Position: ({int(symbol.position_x)}, {int(symbol.position_y)})")
        else:
            self.symbol_position_label.setText("Position: Not set")

        # Update UI with symbol data
        self.symbol_scale_spin.blockSignals(True)
        self.symbol_scale_spin.setValue(symbol.scale)
        self.symbol_scale_spin.blockSignals(False)

        # Update visibility condition UI
        vis = symbol.visibility_condition
        if vis.condition_type == "always":
            self.visibility_type_combo.setCurrentIndex(0)
        elif vis.condition_type == "bool":
            self.visibility_type_combo.setCurrentIndex(1)
        else:
            self.visibility_type_combo.setCurrentIndex(2)

        self.visibility_key_input.setText(vis.data_key)
        self.visibility_bool_combo.setCurrentIndex(0 if vis.show_when else 1)

        # Map operator symbols
        operator_map = {"less_than": "<", "greater_than": ">", "equals": "="}
        operator_symbol = operator_map.get(vis.operator, "<")
        self.visibility_operator_combo.setCurrentText(operator_symbol)

        self.visibility_value_spin.setValue(vis.value)

        self._redraw_all_points()

    def on_symbol_display_name_changed(self, text: str):
        """Handle display name text change"""
        if not self.current_symbol_id or self.current_symbol_id not in self.symbols:
            return

        # Update the symbol's display name
        self.symbols[self.current_symbol_id].display_name = text
        self.has_unsaved_changes = True
        logger.info(f"✏️ Updated display name for {self.current_symbol_id}: '{text}'")

    def on_symbol_scale_changed(self, value):
        """Handle symbol scale change"""
        if not self.current_symbol_id:
            return

        self.symbols[self.current_symbol_id].scale = value
        self.has_unsaved_changes = True

    def on_visibility_type_changed(self, index):
        """Handle visibility type change"""
        if not self.current_symbol_id:
            return

        # Update visibility condition type
        if index == 0:
            condition_type = "always"
            self.visibility_key_input.setEnabled(False)
            self.visibility_bool_combo.setEnabled(False)
            self.visibility_operator_combo.setEnabled(False)
            self.visibility_value_spin.setEnabled(False)
        elif index == 1:
            condition_type = "bool"
            self.visibility_key_input.setEnabled(True)
            self.visibility_bool_combo.setEnabled(True)
            self.visibility_operator_combo.setEnabled(False)
            self.visibility_value_spin.setEnabled(False)
        else:
            condition_type = "threshold"
            self.visibility_key_input.setEnabled(True)
            self.visibility_bool_combo.setEnabled(False)
            self.visibility_operator_combo.setEnabled(True)
            self.visibility_value_spin.setEnabled(True)

        self.symbols[self.current_symbol_id].visibility_condition.condition_type = condition_type
        self.has_unsaved_changes = True

    def on_visibility_key_changed(self, text):
        """Handle visibility data key change"""
        if not self.current_symbol_id:
            return

        self.symbols[self.current_symbol_id].visibility_condition.data_key = text
        self.has_unsaved_changes = True

    def on_visibility_bool_changed(self, index):
        """Handle visibility bool condition change"""
        if not self.current_symbol_id:
            return

        show_when = (index == 0)  # 0 = "Show when True", 1 = "Show when False"
        self.symbols[self.current_symbol_id].visibility_condition.show_when = show_when
        self.has_unsaved_changes = True

    def on_visibility_operator_changed(self, symbol):
        """Handle visibility operator change"""
        if not self.current_symbol_id:
            return

        # Map symbols to operator names
        operator_map = {"<": "less_than", ">": "greater_than", "=": "equals"}
        operator = operator_map.get(symbol, "less_than")

        self.symbols[self.current_symbol_id].visibility_condition.operator = operator
        self.has_unsaved_changes = True

    def on_visibility_value_changed(self, value):
        """Handle visibility threshold value change"""
        if not self.current_symbol_id:
            return

        self.symbols[self.current_symbol_id].visibility_condition.value = value
        self.has_unsaved_changes = True

    def save_symbols(self):
        """Save symbols to the current gauge's config file"""
        if not self.current_calibration:
            QMessageBox.warning(self, "No Gauge", "Select a gauge first")
            return

        gauge_name = self.current_calibration.gauge_name.lower()
        config_file = self.config_dir / f"{gauge_name}.json"

        try:
            # Load existing config
            if config_file.exists():
                with open(config_file, 'r') as f:
                    config = json.load(f)
            else:
                config = {}

            # Update symbols in config
            symbols_config = {}
            for symbol_id, symbol in self.symbols.items():
                symbols_config[symbol_id] = symbol.to_dict()

            config["symbols"] = symbols_config

            # Save back to file
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)

            logger.info(f"💾 Saved {len(self.symbols)} symbol(s) to {gauge_name}.json")
            QMessageBox.information(self, "Saved", f"Saved {len(self.symbols)} symbol(s) for {gauge_name}!")

        except Exception as e:
            logger.error(f"❌ Failed to save symbols: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save: {e}")


def main():
    import sys
    app = QApplication(sys.argv)
    window = GaugeCalibratorV2()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
