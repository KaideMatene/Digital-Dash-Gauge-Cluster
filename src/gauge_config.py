"""
Gauge Configuration System

Stores all gauge parameters and provides save/load functionality.
Each gauge can be independently configured and saved to JSON.
"""

import json
import logging
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import Dict, Optional, List

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
class NeedleCalibration:
    """Calibration data for a single needle (can have multiple per gauge)"""
    needle_id: str = "main"  # e.g., "fuel", "water"
    needle_image_path: Optional[str] = None  # Path to needle PNG
    rotation_center_x: float = 0  # Pixel coordinates on needle image
    rotation_center_y: float = 0
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


@dataclass
class PositionCalibrationPoint:
    """Calibration point with pixel position (new format)"""
    x: float
    y: float
    value: float
    
    def to_dict(self):
        return {"x": self.x, "y": self.y, "value": self.value}
    
    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


@dataclass
class PositionBasedNeedleCalibration:
    """Position-based calibration (v2) - pixel clicks instead of angles"""
    needle_id: str = "main"
    needle_image_path: Optional[str] = None
    gauge_name: Optional[str] = None
    
    # Needle geometry
    needle_pivot_x: float = 0
    needle_pivot_y: float = 0
    needle_end_x: float = 0
    needle_end_y: float = 0
    
    # Gauge geometry
    gauge_pivot_x: float = 0
    gauge_pivot_y: float = 0
    
    # Calibration marks
    calibration_points: List[PositionCalibrationPoint] = field(default_factory=list)
    
    # Value range
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
    def from_dict(cls, data: dict):
        data = data.copy()
        points_data = data.pop("calibration_points", [])
        calib = cls(**data)
        calib.calibration_points = [PositionCalibrationPoint.from_dict(p) for p in points_data]
        return calib


@dataclass
class NeedleConfig:
    """Configuration for a single needle"""
    name: str = "Needle"
    color_r: int = 255  # Red needle by default
    color_g: int = 0
    color_b: int = 0
    thickness: float = 3.0
    length_offset: float = 40  # Distance from edge (needle_length = radius - this)
    center_cap_size: float = 15  # Radius of center cap in mm
    style: str = "3d_pointer"  # "line", "3d_pointer", "arrow"
    enabled: bool = True
    
    def to_dict(self):
        return asdict(self)


@dataclass
class GaugeConfig:
    """Configuration for a single gauge display"""
    name: str = "Gauge"
    gauge_type: str = "tachometer"  # "tachometer", "speedometer", "fuel"
    
    # Position and sweep
    start_angle: float = 270  # Degrees (6 o'clock = 270)
    sweep_angle: float = 270  # Degrees (clockwise)
    
    # Value ranges
    min_value: float = 0
    max_value: float = 8000  # RPM
    
    # Gauge appearance
    background_color_r: int = 245
    background_color_g: int = 235
    background_color_b: int = 215
    
    # Needles (can have multiple)
    needles: Dict[str, NeedleConfig] = field(default_factory=lambda: {
        "main": NeedleConfig(name="Main", color_r=255, color_g=0, color_b=0)
    })
    
    # Background image
    background_image: Optional[str] = None
    image_offset_x: float = 0
    image_offset_y: float = 0
    
    # Text display
    show_numbers: bool = True
    number_interval: int = 1000  # Every 1000 RPM
    text_size: int = 10
    
    # Night mode colors
    night_mode_bg_r: int = 30
    night_mode_bg_g: int = 30
    night_mode_bg_b: int = 30
    night_mode_text_r: int = 255
    night_mode_text_g: int = 255
    night_mode_text_b: int = 255
    
    # Calibration data per needle (supports multiple needles per gauge)
    needle_calibrations: Dict[str, NeedleCalibration] = field(default_factory=dict)
    # Legacy single-needle support (backward compatibility)
    rotation_center_x: float = 0
    rotation_center_y: float = 0
    calibration_points: List[CalibrationPoint] = field(default_factory=list)
    needle_image_path: Optional[str] = None
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        # Convert NeedleConfig objects to dicts
        data['needles'] = {k: v.to_dict() if hasattr(v, 'to_dict') else v 
                          for k, v in self.needles.items()}
        # Convert calibration_points to dicts
        data['calibration_points'] = [p.to_dict() for p in self.calibration_points]
        # Convert needle_calibrations to dicts
        data['needle_calibrations'] = {
            k: v.to_dict() if hasattr(v, 'to_dict') else v 
            for k, v in self.needle_calibrations.items()
        }
        return data
    
    @classmethod
    def from_dict(cls, data: dict):
        """Create from dictionary (JSON deserialization)"""
        # Reconstruct NeedleConfig objects
        needles = {}
        if 'needles' in data:
            for key, needle_data in data.get('needles', {}).items():
                needles[key] = NeedleConfig(**needle_data)
            data['needles'] = needles
        
        # Reconstruct CalibrationPoint objects (legacy single-needle)
        if 'calibration_points' in data:
            calib_points = []
            for point_data in data.get('calibration_points', []):
                calib_points.append(CalibrationPoint.from_dict(point_data))
            data['calibration_points'] = calib_points
        
        # Reconstruct NeedleCalibration objects (multi-needle)
        if 'needle_calibrations' in data:
            needle_calihs = {}
            for key, calib_data in data.get('needle_calibrations', {}).items():
                needle_calihs[key] = NeedleCalibration.from_dict(calib_data)
            data['needle_calibrations'] = needle_calihs
        
        return cls(**data)


class ConfigManager:
    """Manage gauge configuration files"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
    
    def save_gauge(self, gauge_config: GaugeConfig) -> bool:
        """Save gauge configuration to JSON file"""
        try:
            filename = self.config_dir / f"{gauge_config.name.lower()}.json"
            with open(filename, 'w') as f:
                json.dump(gauge_config.to_dict(), f, indent=2)
            logger.info(f"Saved gauge config: {filename}")
            return True
        except Exception as e:
            logger.error(f"Error saving gauge config: {e}")
            return False
    
    def load_gauge(self, gauge_name: str) -> Optional[GaugeConfig]:
        """Load gauge configuration from JSON file"""
        try:
            filename = self.config_dir / f"{gauge_name.lower()}.json"
            if not filename.exists():
                logger.warning(f"Gauge config not found: {filename}")
                return None
            
            with open(filename, 'r') as f:
                data = json.load(f)
            
            config = GaugeConfig.from_dict(data)
            logger.info(f"Loaded gauge config: {filename}")
            return config
        except Exception as e:
            logger.error(f"Error loading gauge config: {e}")
            return None
    
    def get_default_tachometer(self) -> GaugeConfig:
        """Default tachometer configuration"""
        return GaugeConfig(
            name="Tachometer",
            gauge_type="tachometer",
            start_angle=270,
            sweep_angle=279,
            min_value=0,
            max_value=8000,
            number_interval=1000,
            needles={
                "main": NeedleConfig(
                    name="RPM Needle",
                    color_r=255,
                    color_g=0,
                    color_b=0,
                    thickness=3.0,
                    length_offset=40,
                    center_cap_size=15,
                    style="3d_pointer"
                )
            }
        )
    
    def get_default_speedometer(self) -> GaugeConfig:
        """Default speedometer configuration"""
        return GaugeConfig(
            name="Speedometer",
            gauge_type="speedometer",
            start_angle=240,
            sweep_angle=300,
            min_value=0,
            max_value=260,
            number_interval=40,
            needles={
                "main": NeedleConfig(
                    name="Speed Needle",
                    color_r=255,
                    color_g=0,
                    color_b=0,
                    thickness=3.0,
                    length_offset=40,
                    center_cap_size=15,
                    style="3d_pointer"
                )
            }
        )
    
    def get_default_fuel(self) -> GaugeConfig:
        """Default fuel gauge configuration"""
        return GaugeConfig(
            name="Fuel",
            gauge_type="fuel",
            start_angle=180,
            sweep_angle=90,
            min_value=0,
            max_value=100,
            number_interval=0,  # No numbers on fuel gauge
            needles={
                "fuel": NeedleConfig(
                    name="Fuel Level",
                    color_r=255,
                    color_g=0,
                    color_b=0,
                    thickness=3.0,
                    length_offset=30,
                    center_cap_size=15,
                    style="3d_pointer"
                ),
                "water": NeedleConfig(
                    name="Water Temp",
                    color_r=0,
                    color_g=100,
                    color_b=255,
                    thickness=2.0,
                    length_offset=50,
                    center_cap_size=8,
                    style="3d_pointer",
                    enabled=True
                )
            }
        )


if __name__ == '__main__':
    """Generate default gauge configurations"""
    manager = ConfigManager()
    
    # Create and save defaults
    manager.save_gauge(manager.get_default_tachometer())
    manager.save_gauge(manager.get_default_speedometer())
    manager.save_gauge(manager.get_default_fuel())
    
    print("Default gauge configurations created in config/ folder")
