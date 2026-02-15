#!/usr/bin/env python3
"""
Test script to verify needle persistence.

Tests:
1. Add needles to config files
2. Verify they persist in JSON
3. Verify they load in gauge objects
"""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Import PyQt5 for QApplication
from PyQt5.QtWidgets import QApplication

from image_gauge import ImageTachometer, ImageSpeedometer

def test_needle_persistence():
    print("=" * 60)
    print("NEEDLE PERSISTENCE TEST")
    print("=" * 60)
    
    config_dir = Path(__file__).parent / "config"
    tach_config_path = config_dir / "tachometer.json"
    
    # 1. Check what needles exist in tachometer config
    print("\n1. Checking tachometer.json...")
    if tach_config_path.exists():
        with open(tach_config_path, 'r') as f:
            tach_config = json.load(f)
        
        needle_cals = tach_config.get('needle_calibrations', {})
        print(f"   Found {len(needle_cals)} needles in config:")
        for needle_id in needle_cals:
            points = needle_cals[needle_id].get('calibration_points', [])
            scale = needle_cals[needle_id].get('scale', 1.0)
            print(f"     - {needle_id}: {len(points)} calibration points, scale={scale}")
    else:
        print("   ⚠️ tachometer.json not found")
    
    # 2. Create a gauge and load all needles
    print("\n2. Creating ImageTachometer and loading needles...")
    
    # Create QApplication (required for QWidget)
    app = QApplication(sys.argv)
    
    tach = ImageTachometer("gauges/tachometer_bg.png", "gauges/needle.svg")
    
    if tach_config_path.exists():
        tach.load_all_needles_from_file(str(tach_config_path), "main")
        
        print(f"   Main needle angle calculator: {tach.angle_calculator is not None}")
        print(f"   Named needles loaded: {len(tach.named_needles)}")
        
        for needle_name in tach.named_needles:
            needle_data = tach.named_needles[needle_name]
            has_calc = 'angle_calc' in needle_data and needle_data['angle_calc'] is not None
            scale = needle_data.get('scale', 1.0)
            print(f"     - {needle_name}: angle_calc={has_calc}, scale={scale}")
    else:
        print("   ⚠️ Cannot load - config not found")
    
    # 3. Test adding a needle programmatically
    print("\n3. Testing manual needle addition...")
    test_needle_name = "test_needle"
    
    # Add to config
    if tach_config_path.exists():
        with open(tach_config_path, 'r') as f:
            config = json.load(f)
        
        if 'needle_calibrations' not in config:
            config['needle_calibrations'] = {}
        
        # Only add if doesn't exist
        if test_needle_name not in config['needle_calibrations']:
            config['needle_calibrations'][test_needle_name] = {
                "pivot_x": 0,
                "pivot_y": 0,
                "end_x": 0,
                "end_y": 0,
                "calibration_points": [],
                "scale": 1.5
            }
            
            with open(tach_config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            print(f"   ✅ Added {test_needle_name} to config")
            
            # Reload and verify
            with open(tach_config_path, 'r') as f:
                reloaded = json.load(f)
            
            if test_needle_name in reloaded.get('needle_calibrations', {}):
                print(f"   ✅ Verified {test_needle_name} persisted in JSON")
            else:
                print(f"   ❌ {test_needle_name} NOT found after save!")
        else:
            print(f"   ℹ️ {test_needle_name} already exists in config")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Run gauge_preview.py")
    print("2. Go to Calibration Tool tab")
    print("3. Click '➕ Add Needle' button")
    print("4. Check that new needle appears in dropdown")
    print("5. Switch to Preview tab and back")
    print("6. Verify needle still exists in dropdown")
    print("=" * 60)

if __name__ == '__main__':
    test_needle_persistence()
