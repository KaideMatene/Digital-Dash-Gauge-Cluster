#!/usr/bin/env python3
"""
Test script to verify configuration loading works properly
"""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from config_utils import ensure_default_configs, load_gauge_config

def test_config_loading():
    """Test that all gauge configurations can be loaded"""
    
    print("=" * 60)
    print("Testing Configuration Loading")
    print("=" * 60)
    
    # Ensure default configs exist
    print("\n1. Ensuring default configs exist...")
    ensure_default_configs()
    print("✅ Default configs ensured")
    
    # Test loading each gauge config
    config_dir = Path(__file__).parent / "config"
    gauge_files = ["tachometer.json", "speedometer.json", "fuel.json"]
    
    all_passed = True
    
    for gauge_file in gauge_files:
        print(f"\n2. Testing {gauge_file}...")
        config_path = config_dir / gauge_file
        
        if not config_path.exists():
            print(f"   ❌ File does not exist: {config_path}")
            all_passed = False
            continue
        
        # Load config
        try:
            config = load_gauge_config(config_path)
            print(f"   ✅ Loaded successfully")
            
            # Check structure
            if 'needle_calibrations' not in config:
                print(f"   ⚠️  Missing 'needle_calibrations' key")
                all_passed = False
            else:
                num_needles = len(config['needle_calibrations'])
                print(f"   📊 Found {num_needles} needle calibration(s)")
                
                # List needles
                for needle_id, needle_data in config['needle_calibrations'].items():
                    num_points = len(needle_data.get('calibration_points', []))
                    scale = needle_data.get('needle_scale', 1.0)
                    print(f"      - {needle_id}: {num_points} points, scale {scale:.2f}x")
        
        except Exception as e:
            print(f"   ❌ Failed to load: {e}")
            all_passed = False
    
    # Test direct JSON loading
    print("\n3. Testing direct JSON loading...")
    for gauge_file in gauge_files:
        config_path = config_dir / gauge_file
        try:
            with open(config_path, 'r') as f:
                data = json.load(f)
            print(f"   ✅ {gauge_file}: Valid JSON")
        except json.JSONDecodeError as e:
            print(f"   ❌ {gauge_file}: Invalid JSON - {e}")
            all_passed = False
        except Exception as e:
            print(f"   ❌ {gauge_file}: Error - {e}")
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ALL TESTS PASSED - Configuration loading works!")
    else:
        print("❌ SOME TESTS FAILED - Check errors above")
    print("=" * 60)
    
    return all_passed


if __name__ == "__main__":
    success = test_config_loading()
    sys.exit(0 if success else 1)
