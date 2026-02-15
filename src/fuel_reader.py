"""
Fuel Level Sensor Reader

Reads fuel level from stock Supra fuel sender via dedicated gauge module.
"""

import logging
import time
from collections import deque
from typing import Optional

logger = logging.getLogger(__name__)


class FuelReader:
    """Reads fuel level from stock Supra sender via VDO-compatible module"""
    
    def __init__(self, samples=5):
        self.samples = samples
        self.readings = deque(maxlen=samples)
        self.fuel_level = 0.0
        
        # TODO: Initialize communication with fuel gauge module
        # Options:
        # 1. ADC reading (0-5V from module)
        # 2. I2C interface if module supports it
        # 3. Direct resistance reading with voltage divider + MCP3008
        
        logger.info("Fuel reader initialized")
    
    def _read_raw(self) -> Optional[float]:
        """
        Read raw value from fuel gauge module
        
        TODO: Implement based on actual module interface
        Returns voltage (0-5V) or percentage (0-100)
        """
        try:
            # Placeholder - replace with actual implementation
            # Example for ADC reading:
            # import board
            # import busio
            # import adafruit_mcp3xxx.mcp3008 as MCP
            # from adafruit_mcp3xxx.analog_in import AnalogIn
            # 
            # spi = busio.SPI(clock=board.SCK, MISO=board.MISO, MOSI=board.MOSI)
            # cs = digitalio.DigitalInOut(board.D5)
            # mcp = MCP.MCP3008(spi, cs)
            # chan = AnalogIn(mcp, MCP.P0)
            # return chan.voltage
            
            return 2.5  # Placeholder: 2.5V = ~50% fuel
        except Exception as e:
            logger.error(f"Error reading fuel sensor: {e}")
            return None
    
    def _voltage_to_percentage(self, voltage: float) -> float:
        """
        Convert module voltage output to fuel percentage
        
        Typical VDO module: 0V = empty, 5V = full
        Adjust based on actual module specifications
        """
        # Linear mapping: 0-5V -> 0-100%
        percentage = (voltage / 5.0) * 100.0
        return max(0.0, min(100.0, percentage))
    
    def get_fuel_level(self) -> float:
        """
        Get current fuel level with smoothing
        
        Returns: Fuel level as percentage (0-100)
        """
        raw = self._read_raw()
        if raw is not None:
            percentage = self._voltage_to_percentage(raw)
            self.readings.append(percentage)
            
            # Moving average smoothing
            if len(self.readings) > 0:
                self.fuel_level = sum(self.readings) / len(self.readings)
        
        return round(self.fuel_level, 1)
    
    def shutdown(self):
        """Cleanup resources"""
        logger.info("Shutting down fuel reader...")
        # TODO: Cleanup ADC/I2C connections if needed
        logger.info("Fuel reader shutdown complete")
