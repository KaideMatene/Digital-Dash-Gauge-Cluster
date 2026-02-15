"""
Angle Calculator - Convert pixel positions to needle rotations

Given:
- Gauge pivot point (x, y) on gauge background
- Calibration points: list of {x, y, value}
- A value to calculate angle for

Calculate:
- Angle to rotate needle for that value
"""

import math
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class CalibrationPoint:
    """Calibration point: pixel position with associated value"""
    x: float
    y: float
    value: float


def calculate_angle_to_point(gauge_pivot_x: float, gauge_pivot_y: float,
                            point_x: float, point_y: float) -> float:
    """
    Calculate angle from gauge pivot to a point.
    
    Returns angle in degrees (0-360).
    - 0° = right (positive X)
    - 90° = down (positive Y)
    - 180° = left (negative X)
    - 270° = up (negative Y)
    """
    dy = point_y - gauge_pivot_y
    dx = point_x - gauge_pivot_x
    
    angle = math.atan2(dy, dx)
    angle_degrees = math.degrees(angle)
    
    # Normalize to 0-360
    if angle_degrees < 0:
        angle_degrees += 360
    
    return angle_degrees


class AngleCalculator:
    """Calculate needle rotation angle from gauge values"""
    
    def __init__(self, gauge_pivot_x: float, gauge_pivot_y: float):
        """
        Initialize calculator with gauge pivot location.
        
        Args:
            gauge_pivot_x: X coordinate of gauge pivot on gauge background
            gauge_pivot_y: Y coordinate of gauge pivot on gauge background
        """
        self.gauge_pivot_x = gauge_pivot_x
        self.gauge_pivot_y = gauge_pivot_y
        self.calibration_points: List[CalibrationPoint] = []
    
    def add_point(self, x: float, y: float, value: float):
        """Add a calibration point"""
        self.calibration_points.append(CalibrationPoint(x, y, value))
        # Sort by value for interpolation
        self.calibration_points.sort(key=lambda p: p.value)
    
    def points_from_list(self, points: List[dict]):
        """Load points from list of {x, y, value} dicts"""
        self.calibration_points = []
        for p in points:
            self.add_point(p['x'], p['y'], p['value'])
    
    def value_to_angle(self, value: float) -> float:
        """
        Convert a gauge value to needle rotation angle.
        
        Returns:
            Angle in degrees (0-360)
        """
        if not self.calibration_points:
            return 0

        # Precompute and unwrap angles to ensure continuous rotation
        points = self.calibration_points
        angles = [
            calculate_angle_to_point(
                self.gauge_pivot_x, self.gauge_pivot_y,
                p.x, p.y
            )
            for p in points
        ]

        # Unwrap angles to avoid jumps across 0/360
        for i in range(1, len(angles)):
            while angles[i] - angles[i - 1] > 180:
                angles[i] -= 360
            while angles[i] - angles[i - 1] < -180:
                angles[i] += 360
        
        # Value is at or before first point
        if value <= points[0].value:
            return angles[0] % 360
        
        # Value is at or after last point
        if value >= points[-1].value:
            return angles[-1] % 360
        
        # Find bracketing points
        for i in range(len(points) - 1):
            if points[i].value <= value <= points[i + 1].value:
                p1 = points[i]
                p2 = points[i + 1]
                
                # Linear interpolation
                if p2.value == p1.value:
                    # Same value, return angle of first point
                    return angles[i] % 360
                
                # Interpolate angle between p1 and p2
                t = (value - p1.value) / (p2.value - p1.value)
                interp_angle = angles[i] + t * (angles[i + 1] - angles[i])
                return interp_angle % 360
        
        # Shouldn't reach here
        return angles[-1] % 360
    
    def debug_angles(self):
        """Print all calibration point angles for debugging"""
        print(f"Gauge Pivot: ({self.gauge_pivot_x}, {self.gauge_pivot_y})")
        print("\nCalibration Points → Angles:")
        for point in self.calibration_points:
            angle = calculate_angle_to_point(
                self.gauge_pivot_x, self.gauge_pivot_y,
                point.x, point.y
            )
            print(f"  Value: {point.value:6.1f} → Pos: ({point.x:4.0f}, {point.y:4.0f}) → Angle: {angle:6.1f}°")


if __name__ == '__main__':
    # Test the calculator
    calc = AngleCalculator(256, 256)
    
    # Add some test points (gauge coordinates)
    calc.add_point(256, 100, 0)      # Top (0 value)
    calc.add_point(256, 450, 100)    # Bottom (100 value)
    calc.add_point(350, 256, 50)     # Right (50 value)
    
    print("Test Calculation:")
    calc.debug_angles()
    
    print("\nInterpolation test:")
    print(f"  Value 25 → Angle: {calc.value_to_angle(25):.1f}°")
    print(f"  Value 75 → Angle: {calc.value_to_angle(75):.1f}°")
    print(f"  Value 150 → Angle: {calc.value_to_angle(150):.1f}° (extrapolated)")
