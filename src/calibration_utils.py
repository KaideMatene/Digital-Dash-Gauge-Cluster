"""
Gauge Calibration Utilities

Converts gauge values to needle angles using calibration points.
Supports linear interpolation and extrapolation.
"""

import logging
from typing import List, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CalibrationPoint:
    """A calibration point: value -> angle mapping"""
    value: float
    angle: float


class NeedleAngleCalculator:
    """Calculate needle rotation angle from gauge value using calibration points"""
    
    def __init__(self, calibration_points: List[CalibrationPoint] = None):
        """
        Initialize with calibration points
        
        Args:
            calibration_points: List of CalibrationPoint objects
        """
        self.calibration_points = calibration_points or []
        self._validate_points()
    
    def _validate_points(self):
        """Ensure calibration points are sorted by value"""
        if self.calibration_points:
            self.calibration_points.sort(key=lambda p: p.value)
    
    def add_point(self, value: float, angle: float):
        """Add a calibration point"""
        self.calibration_points.append(CalibrationPoint(value, angle))
        self._validate_points()
    
    def set_points(self, points: List[Tuple[float, float]]):
        """Set calibration points from list of (value, angle) tuples"""
        self.calibration_points = [
            CalibrationPoint(value, angle) for value, angle in points
        ]
        self._validate_points()
    
    def value_to_angle(self, value: float) -> float:
        """
        Convert a gauge value to needle angle using linear interpolation
        
        Args:
            value: The gauge value (RPM, km/h, %, °C, etc.)
        
        Returns:
            Needle angle in degrees
        """
        if not self.calibration_points:
            logger.warning("No calibration points defined, returning 0°")
            return 0.0
        
        # Handle value outside range - use endpoint
        if value <= self.calibration_points[0].value:
            return self.calibration_points[0].angle
        
        if value >= self.calibration_points[-1].value:
            return self.calibration_points[-1].angle
        
        # Find surrounding points for interpolation
        for i in range(len(self.calibration_points) - 1):
            p1 = self.calibration_points[i]
            p2 = self.calibration_points[i + 1]
            
            if p1.value <= value <= p2.value:
                # Linear interpolation
                value_range = p2.value - p1.value
                angle_range = p2.angle - p1.angle
                
                # Handle angle wraparound (e.g., 350° to 10° is only 20° not 340°)
                if angle_range > 180:
                    angle_range -= 360
                elif angle_range < -180:
                    angle_range += 360
                
                fraction = (value - p1.value) / value_range
                angle = p1.angle + (angle_range * fraction)
                
                # Normalize to 0-360 range
                angle = angle % 360
                if angle < 0:
                    angle += 360
                
                return angle
        
        # Should not reach here if points are valid
        logger.warning(f"Could not interpolate angle for value {value}")
        return self.calibration_points[0].angle
    
    def get_calibration_info(self) -> str:
        """Get human-readable calibration info"""
        if not self.calibration_points:
            return "No calibration points"
        
        info = "Calibration Points:\n"
        for i, point in enumerate(self.calibration_points, 1):
            info += f"  {i}. Value: {point.value:,.1f} → Angle: {point.angle:.1f}°\n"
        return info


# Common preset calibrations

def tachometer_calibration() -> NeedleAngleCalculator:
    """Standard tachometer (0-10000 RPM)"""
    calc = NeedleAngleCalculator()
    calc.set_points([
        (0, 270),      # 0 RPM at 12 o'clock
        (5000, 135),   # 5000 RPM at 4:30
        (10000, 0),    # 10000 RPM at 3 o'clock
    ])
    return calc


def speedometer_calibration() -> NeedleAngleCalculator:
    """Standard speedometer (0-320 km/h)"""
    calc = NeedleAngleCalculator()
    calc.set_points([
        (0, 240),      # 0 km/h at 8 o'clock
        (160, 90),     # 160 km/h at 6 o'clock (midpoint)
        (320, -60),    # 320 km/h past 3 o'clock
    ])
    return calc


def fuel_gauge_calibration() -> NeedleAngleCalculator:
    """Standard fuel gauge (Empty to Full)"""
    calc = NeedleAngleCalculator()
    calc.set_points([
        (0, 180),      # Empty (E) at 9 o'clock
        (100, 90),     # Full (F) at 6 o'clock
    ])
    return calc


def water_temp_calibration() -> NeedleAngleCalculator:
    """Standard water temperature (50-130°C)"""
    calc = NeedleAngleCalculator()
    calc.set_points([
        (50, 180),     # Cold (50°C) at 9 o'clock
        (90, 90),      # Normal (90°C) at 6 o'clock
        (130, 0),      # Hot (130°C) at 3 o'clock
    ])
    return calc


if __name__ == '__main__':
    """Test calibration calculations"""
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Test tachometer
    print("=== TACHOMETER CALIBRATION ===")
    tach = tachometer_calibration()
    print(tach.get_calibration_info())
    
    test_values = [0, 2500, 5000, 7500, 10000]
    for val in test_values:
        angle = tach.value_to_angle(val)
        print(f"{val:5d} RPM → {angle:6.1f}°")
    
    # Test speedometer
    print("\n=== SPEEDOMETER CALIBRATION ===")
    speed = speedometer_calibration()
    print(speed.get_calibration_info())
    
    test_speeds = [0, 80, 160, 240, 320]
    for val in test_speeds:
        angle = speed.value_to_angle(val)
        print(f"{val:3d} km/h → {angle:6.1f}°")
    
    # Test fuel
    print("\n=== FUEL GAUGE CALIBRATION ===")
    fuel = fuel_gauge_calibration()
    print(fuel.get_calibration_info())
    
    test_fuel = [0, 25, 50, 75, 100]
    for val in test_fuel:
        angle = fuel.value_to_angle(val)
        print(f"{val:3d}% → {angle:6.1f}°")
