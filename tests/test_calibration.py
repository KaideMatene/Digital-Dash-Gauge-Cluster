#!/usr/bin/env python3
"""
Test script for calibration utilities

Verifies that angle calculations work correctly for all gauge types.
Run with: python test_calibration.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from calibration_utils import (
    NeedleAngleCalculator,
    CalibrationPoint,
    tachometer_calibration,
    speedometer_calibration,
    fuel_gauge_calibration,
    water_temp_calibration
)


def test_tachometer():
    """Test tachometer calibration"""
    print("\n" + "="*60)
    print("TACHOMETER CALIBRATION TEST")
    print("="*60)
    
    calc = tachometer_calibration()
    print(calc.get_calibration_info())
    
    test_values = [0, 1000, 2500, 5000, 7500, 10000, 15000]  # 15000 tests extrapolation
    print("\nValue → Angle Mapping:")
    print("-" * 40)
    for val in test_values:
        angle = calc.value_to_angle(val)
        print(f"  {val:6.0f} RPM  →  {angle:7.1f}°")
    
    # Verify specific points
    assert abs(calc.value_to_angle(0) - 270) < 0.1, "0 RPM should be 270°"
    assert abs(calc.value_to_angle(5000) - 135) < 0.1, "5000 RPM should be 135°"
    assert abs(calc.value_to_angle(10000) - 0) < 0.1, "10000 RPM should be 0°"
    
    # Verify interpolation
    angle_2500 = calc.value_to_angle(2500)
    assert 200 < angle_2500 < 210, f"2500 RPM should be ~202°, got {angle_2500}"
    
    print("\n✅ Tachometer tests PASSED")


def test_speedometer():
    """Test speedometer calibration"""
    print("\n" + "="*60)
    print("SPEEDOMETER CALIBRATION TEST")
    print("="*60)
    
    calc = speedometer_calibration()
    print(calc.get_calibration_info())
    
    test_values = [0, 40, 80, 120, 160, 200, 240, 280, 320, 400]
    print("\nValue → Angle Mapping:")
    print("-" * 40)
    for val in test_values:
        angle = calc.value_to_angle(val)
        print(f"  {val:3.0f} km/h  →  {angle:7.1f}°")
    
    # Verify specific points
    assert abs(calc.value_to_angle(0) - 240) < 0.1, "0 km/h should be 240°"
    assert abs(calc.value_to_angle(160) - 90) < 0.1, "160 km/h should be 90°"
    assert abs(calc.value_to_angle(320) - (-60)) < 0.1, "320 km/h should be -60°"
    
    print("\n✅ Speedometer tests PASSED")


def test_fuel():
    """Test fuel gauge calibration"""
    print("\n" + "="*60)
    print("FUEL GAUGE CALIBRATION TEST")
    print("="*60)
    
    calc = fuel_gauge_calibration()
    print(calc.get_calibration_info())
    
    test_values = [0, 25, 50, 75, 100, 150]
    print("\nValue → Angle Mapping:")
    print("-" * 40)
    for val in test_values:
        angle = calc.value_to_angle(val)
        print(f"  {val:3.0f}%  →  {angle:7.1f}°")
    
    # Verify specific points
    assert abs(calc.value_to_angle(0) - 180) < 0.1, "0% should be 180°"
    assert abs(calc.value_to_angle(100) - 90) < 0.1, "100% should be 90°"
    
    # Verify interpolation
    angle_50 = calc.value_to_angle(50)
    assert 130 < angle_50 < 140, f"50% should be ~135°, got {angle_50}"
    
    print("\n✅ Fuel gauge tests PASSED")


def test_water_temp():
    """Test water temperature calibration"""
    print("\n" + "="*60)
    print("WATER TEMPERATURE CALIBRATION TEST")
    print("="*60)
    
    calc = water_temp_calibration()
    print(calc.get_calibration_info())
    
    test_values = [40, 50, 70, 90, 110, 130, 150]
    print("\nValue → Angle Mapping:")
    print("-" * 40)
    for val in test_values:
        angle = calc.value_to_angle(val)
        print(f"  {val:3.0f}°C  →  {angle:7.1f}°")
    
    # Verify specific points
    assert abs(calc.value_to_angle(50) - 180) < 0.1, "50°C should be 180°"
    assert abs(calc.value_to_angle(90) - 90) < 0.1, "90°C should be 90°"
    assert abs(calc.value_to_angle(130) - 0) < 0.1, "130°C should be 0°"
    
    print("\n✅ Water temperature tests PASSED")


def test_manual_calibration():
    """Test manually created calibration"""
    print("\n" + "="*60)
    print("MANUAL CALIBRATION TEST")
    print("="*60)
    
    calc = NeedleAngleCalculator()
    
    print("Adding custom points...")
    calc.add_point(100, 30)
    calc.add_point(200, 150)
    calc.add_point(300, 270)
    
    print(calc.get_calibration_info())
    
    print("\nValue → Angle Mapping:")
    print("-" * 40)
    for val in [50, 100, 150, 200, 250, 300, 350]:
        angle = calc.value_to_angle(val)
        print(f"  {val:3.0f}  →  {angle:7.1f}°")
    
    # Verify points
    assert abs(calc.value_to_angle(100) - 30) < 0.1
    assert abs(calc.value_to_angle(200) - 150) < 0.1
    assert abs(calc.value_to_angle(300) - 270) < 0.1
    
    # Verify interpolation
    angle_150 = calc.value_to_angle(150)
    assert 80 < angle_150 < 100, f"150 should be between 30° and 150°, got {angle_150}"
    
    print("\n✅ Manual calibration tests PASSED")


def test_edge_cases():
    """Test edge cases"""
    print("\n" + "="*60)
    print("EDGE CASES TEST")
    print("="*60)
    
    # Empty calculator
    calc = NeedleAngleCalculator()
    angle = calc.value_to_angle(100)
    print(f"Empty calculator returns: {angle}° (should be 0°)")
    assert angle == 0.0
    
    # Single point
    calc.add_point(0, 270)
    angle = calc.value_to_angle(5000)
    print(f"Single point for any value returns: {angle}° (should be 270°)")
    assert angle == 270.0
    
    # Negative angles
    calc = NeedleAngleCalculator()
    calc.add_point(0, -90)
    calc.add_point(100, 90)
    angle = calc.value_to_angle(50)
    print(f"Interpolation across 0° line: 50 → {angle}°")
    
    print("\n✅ Edge cases handled correctly")


def main():
    """Run all tests"""
    print("\n" + "🧪 GAUGE CALIBRATION SYSTEM - TEST SUITE" + "\n")
    
    try:
        test_tachometer()
        test_speedometer()
        test_fuel()
        test_water_temp()
        test_manual_calibration()
        test_edge_cases()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60)
        print("\nCalibration system is working correctly.")
        print("\nYou can now use the calibrator:")
        print("  python gauge_calibrator_app.py")
        print("\n")
        return 0
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
