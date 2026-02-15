#!/usr/bin/env python3
"""
Supra Digital Gauge Cluster - Main Entry Point

Author: Supra Digital Cluster Project
License: MIT
"""

import sys
import signal
import logging
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

from can_handler import CANHandler
from fuel_reader import FuelReader
from gpio_handler import GPIOHandler
from display_manager import DisplayManager
from thermal_manager import get_thermal_manager


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/supra-cluster.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class SupraCluster:
    """Main application controller for the digital gauge cluster"""
    
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.running = True
        
        # Initialize thermal management (CRITICAL for 60 FPS stability)
        logger.info("Initializing thermal management...")
        self.thermal_manager = get_thermal_manager()
        
        # Initialize handlers
        logger.info("Initializing CAN bus handler...")
        self.can_handler = CANHandler()
        
        logger.info("Initializing fuel sensor reader...")
        self.fuel_reader = FuelReader()
        
        logger.info("Initializing GPIO handler...")
        self.gpio_handler = GPIOHandler()
        
        logger.info("Initializing display manager...")
        self.display_manager = DisplayManager()
        
        # Setup update timer (60 FPS = ~16ms)
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update)
        self.update_timer.start(16)
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)
        
        logger.info("Supra Digital Cluster initialized successfully")
    
    def update(self):
        """Main update loop - called at 60 FPS"""
        try:
            # Get CAN data from ECU
            can_data = self.can_handler.get_latest_data()
            
            # Get fuel level
            fuel_level = self.fuel_reader.get_fuel_level()
            
            # Get GPIO states (headlights, high beam, warning)
            gpio_states = self.gpio_handler.get_states()
            
            # Update displays with all data
            self.display_manager.update_gauges(
                rpm=can_data.get('rpm', 0),
                speed=can_data.get('speed', 0),
                coolant_temp=can_data.get('coolant_temp', 0),
                boost=can_data.get('boost', 0),
                fuel=fuel_level,
                night_mode=gpio_states.get('headlights', False),
                high_beam=gpio_states.get('high_beam', False),
                warning=gpio_states.get('warning', False),
                brightness=gpio_states.get('dimmer', 100)
            )
        except Exception as e:
            logger.error(f"Error in update loop: {e}")
    
    def run(self):
        """Start the application"""
        logger.info("Starting Supra Digital Cluster application")
        self.display_manager.show()
        return self.app.exec_()
    
    def shutdown(self, signum, frame):
        """Graceful shutdown handler"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
        
        # Cleanup resources
        self.can_handler.shutdown()
        self.fuel_reader.shutdown()
        self.gpio_handler.shutdown()
        
        logger.info("Shutdown complete")
        sys.exit(0)


if __name__ == '__main__':
    try:
        cluster = SupraCluster()
        sys.exit(cluster.run())
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
