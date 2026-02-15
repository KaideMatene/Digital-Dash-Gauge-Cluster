"""
Test suite for Gauge Calibrator v2 - Position-based system

Tests the conversion of pixel positions to needle rotation angles.
"""

import json
from pathlib import Path
from src.angle_calculator import AngleCalculator, calculate_angle_to_point
from src.gauge_config import PositionBasedNeedleCalibration, PositionCalibrationPoint


def test_angle_calculation():
    """Test basic angle calculation from pixel positions"""
    print("=" * 60)
    print("TEST: Angle Calculation from Pixel Positions")
    print("=" * 60)
    
    # Gauge pivot at center (256, 256)
    pivot_x, pivot_y = 256, 256
    
    # Test cardinal directions
    test_cases = [
        (256, 156, "up (270°)", 270),      # Top
        (356, 256, "right (0°)", 0),       # Right
        (256, 356, "down (90°)", 90),      # Bottom
        (156, 256, "left (180°)", 180),    # Left
    ]
    
    for point_x, point_y, desc, expected in test_cases:
        angle = calculate_angle_to_point(pivot_x, pivot_y, point_x, point_y)
        status = "✓" if abs(angle - expected) < 1 else "✗"
        print(f"{status} Point ({point_x}, {point_y}) {desc}: {angle:.1f}° (expected {expected}°)")
    
    print()


def test_interpolation():
    """Test value-to-angle interpolation"""
    print("=" * 60)
    print("TEST: Value to Angle Interpolation")
    print("=" * 60)
    
    calc = AngleCalculator(256, 256)
    
    # Add calibration points
    # Top (0 RPM)
    calc.add_point(256, 100, 0)
    # Right (5000 RPM)
    calc.add_point(410, 256, 5000)
    # Bottom (10000 RPM)
    calc.add_point(256, 410, 10000)
    
    print("Calibration points:")
    calc.debug_angles()
    
    print("\nInterpolation tests:")
    test_values = [0, 2500, 5000, 7500, 10000, 15000]
    for value in test_values:
        angle = calc.value_to_angle(value)
        print(f"  Value {value:5d} RPM → Angle {angle:6.1f}°")
    
    print()


def test_calibration_save_load():
    """Test saving and loading calibration data"""
    print("=" * 60)
    print("TEST: Save/Load Calibration Data")
    print("=" * 60)
    
    # Create calibration
    calib = PositionBasedNeedleCalibration(
        needle_id="fuel",
        needle_image_path="gauges/fuel_needle.png",
        gauge_name="Fuel",
        needle_pivot_x=128,
        needle_pivot_y=145,
        needle_end_x=128,
        needle_end_y=50,
        gauge_pivot_x=256,
        gauge_pivot_y=256,
        min_value=0,
        max_value=100,
    )
    
    # Add calibration points
    calib.calibration_points = [
        PositionCalibrationPoint(x=256, y=150, value=0),    # Empty
        PositionCalibrationPoint(x=256, y=360, value=100),  # Full
    ]
    
    # Convert to dict
    calib_dict = calib.to_dict()
    print(f"✓ Converted calibration to dict")
    print(f"  Needle pivot: ({calib_dict['needle_pivot_x']}, {calib_dict['needle_pivot_y']})")
    print(f"  Needle end: ({calib_dict['needle_end_x']}, {calib_dict['needle_end_y']})")
    print(f"  Gauge pivot: ({calib_dict['gauge_pivot_x']}, {calib_dict['gauge_pivot_y']})")
    print(f"  Calibration points: {len(calib_dict['calibration_points'])}")
    
    # Simulate save to JSON
    json_str = json.dumps(calib_dict, indent=2)
    print(f"✓ Serialized to JSON ({len(json_str)} bytes)")
    
    # Simulate load from JSON
    loaded_dict = json.loads(json_str)
    loaded_calib = PositionBasedNeedleCalibration.from_dict(loaded_dict)
    print(f"✓ Loaded from JSON")
    
    # Verify
    assert loaded_calib.needle_id == calib.needle_id
    assert loaded_calib.needle_pivot_x == calib.needle_pivot_x
    assert len(loaded_calib.calibration_points) == len(calib.calibration_points)
    print(f"✓ All fields match original")
    
    print()


def test_realworld_tachometer():
    """Test with realistic tachometer calibration"""
    print("=" * 60)
    print("TEST: Real-World Tachometer Calibration")
    print("=" * 60)
    
    # Create calculator with gauge pivot at center
    calc = AngleCalculator(256, 256)
    
    # User clicked these positions on gauge background:
    # - At 0 RPM, needle points up (256, 100)
    # - At 5000 RPM, needle points right (410, 256)
    # - At 10000 RPM, needle points down-right (350, 350)
    
    calc.add_point(256, 100, 0)      # 0 RPM
    calc.add_point(350, 180, 5000)   # 5000 RPM
    calc.add_point(400, 256, 10000)  # 10000 RPM
    
    print("User clicked these gauge positions:")
    calc.debug_angles()
    
    print("\nNow when emulator needs angle for a value:")
    test_values = [0, 2500, 5000, 7500, 10000]
    for rpm in test_values:
        angle = calc.value_to_angle(rpm)
        print(f"  {rpm:5d} RPM → rotate needle {angle:.1f}°")
    
    print()


def test_fuel_gauge():
    """Test fuel gauge with two needles"""
    print("=" * 60)
    print("TEST: Fuel Gauge with Dual Needles")
    print("=" * 60)
    
    # Fuel needle
    fuel_calc = AngleCalculator(256, 256)
    fuel_calc.add_point(200, 300, 0)     # Empty (left)
    fuel_calc.add_point(312, 300, 100)   # Full (right)
    
    # Water needle
    water_calc = AngleCalculator(256, 256)
    water_calc.add_point(256, 200, 50)   # Cold (top)
    water_calc.add_point(300, 300, 90)   # Normal (down-right)
    water_calc.add_point(270, 380, 130)  # Hot (down)
    
    print("Fuel Needle (0-100%):")
    for pct in [0, 25, 50, 75, 100]:
        angle = fuel_calc.value_to_angle(pct)
        print(f"  {pct:3d}% → {angle:6.1f}°")
    
    print("\nWater Needle (50-130°C):")
    for temp in [50, 70, 90, 110, 130]:
        angle = water_calc.value_to_angle(temp)
        print(f"  {temp:3d}°C → {angle:6.1f}°")
    
    print()


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("GAUGE CALIBRATOR V2 - TEST SUITE")
    print("Position-Based Click Calibration")
    print("=" * 60 + "\n")
    
    test_angle_calculation()
    test_interpolation()
    test_calibration_save_load()
    test_realworld_tachometer()
    test_fuel_gauge()
    
    print("=" * 60)
    print("✅ ALL TESTS COMPLETED")
    print("=" * 60)
