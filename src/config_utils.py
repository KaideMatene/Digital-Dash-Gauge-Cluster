"""
Configuration utilities for gauge system
Ensures default configs exist and provides helpers
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)


def ensure_default_configs():
    """Create default gauge config files if they don't exist"""
    config_dir = Path(__file__).parent.parent / "config"
    config_dir.mkdir(exist_ok=True)
    
    default_configs = {
        "tachometer.json": {
            "name": "Tachometer",
            "gauge_type": "tachometer",
            "needle_calibrations": {}
        },
        "speedometer.json": {
            "name": "Speedometer",
            "gauge_type": "speedometer",
            "needle_calibrations": {}
        },
        "fuel.json": {
            "name": "Fuel",
            "gauge_type": "fuel",
            "needle_calibrations": {}
        }
    }
    
    for filename, default_data in default_configs.items():
        config_path = config_dir / filename
        if not config_path.exists():
            with open(config_path, 'w') as f:
                json.dump(default_data, f, indent=2)
            logger.info(f"✅ Created default config: {filename}")
        else:
            # Ensure needle_calibrations key exists
            try:
                with open(config_path, 'r') as f:
                    data = json.load(f)
                if 'needle_calibrations' not in data:
                    data['needle_calibrations'] = {}
                    with open(config_path, 'w') as f:
                        json.dump(data, f, indent=2)
                    logger.info(f"✅ Updated config with needle_calibrations: {filename}")
            except Exception as e:
                logger.error(f"❌ Failed to update config {filename}: {e}")


def get_needle_image_path(default="gauges/needle.svg") -> str:
    """Get the standard needle image path"""
    needle_path = Path(__file__).parent.parent / default
    if needle_path.exists():
        return str(needle_path)
    # Try PNG version
    png_path = Path(str(needle_path).replace('.svg', '.png'))
    if png_path.exists():
        return str(png_path)
    return default


def load_gauge_config(config_path: Path) -> Dict[str, Any]:
    """Load gauge config, ensuring it has required structure"""
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        if 'needle_calibrations' not in config:
            config['needle_calibrations'] = {}
        return config
    except FileNotFoundError:
        # Return default structure
        return {
            "name": config_path.stem.capitalize(),
            "gauge_type": config_path.stem,
            "needle_calibrations": {}
        }
    except Exception as e:
        logger.error(f"❌ Failed to load config {config_path}: {e}")
        return {"name": "Unknown", "gauge_type": "unknown", "needle_calibrations": {}}


def save_gauge_config(config_path: Path, config: Dict[str, Any]):
    """Save gauge config"""
    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        logger.info(f"✅ Saved config: {config_path.name}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to save config {config_path}: {e}")
        return False
