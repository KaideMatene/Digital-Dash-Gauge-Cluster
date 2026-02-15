#!/usr/bin/env python3
"""
Thermal Manager - PWM Fan Control for Orange Pi 6 Plus

Monitors SoC temperature and scales PWM fan speed to prevent throttling.
Critical for maintaining 60 FPS rendering stability.
"""

import logging
import threading
import time
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class ThermalManager:
    """
    Manages temperature monitoring and PWM fan control.
    
    Reads SoC temperature from sysfs thermal zone and scales GPIO PWM 
    accordingly to maintain target temperature <70°C.
    """
    
    def __init__(self, pwm_pin: int = 21, poll_interval: float = 2.0,
                 target_temp: float = 70.0, max_temp: float = 80.0,
                 min_temp: float = 40.0):
        """
        Initialize thermal manager.
        
        Args:
            pwm_pin: GPIO pin number for PWM fan (BCM numbering)
            poll_interval: Seconds between temperature checks
            target_temp: Target SoC temperature in °C
            max_temp: Maximum temperature before 100% fan
            min_temp: Temperature below which fan is off
        """
        self.pwm_pin = pwm_pin
        self.poll_interval = poll_interval
        self.target_temp = target_temp
        self.max_temp = max_temp
        self.min_temp = min_temp
        
        # Thermal zone path (Orange Pi 6 Plus uses thermal_zone0)
        self.thermal_zone_path = Path("/sys/class/thermal/thermal_zone0/temp")
        
        # PWM control paths
        self.pwm_chip = f"/sys/class/pwm/pwmchip0/pwm{pwm_pin}"
        self.pwm_duty_path = Path(self.pwm_chip) / "duty_cycle"
        self.pwm_period_path = Path(self.pwm_chip) / "period"
        self.pwm_enable_path = Path(self.pwm_chip) / "enable"
        
        self.running = False
        self.current_temp = 0.0
        self.current_pwm = 0
        self.lock = threading.Lock()
        
        self._setup_pwm()
        self._start_monitoring()
        
        logger.info(f"Thermal manager initialized (target: {target_temp}°C, pin: {pwm_pin})")
    
    def _setup_pwm(self):
        """Configure PWM for fan control."""
        try:
            # Export PWM if not already exported
            export_path = Path("/sys/class/pwm/pwmchip0/export")
            if not self.pwm_duty_path.exists():
                with open(export_path, 'w') as f:
                    f.write(str(self.pwm_pin))
                time.sleep(0.1)
            
            # Set PWM period (10 kHz for fan = 100 microseconds)
            pwm_period = 100000  # 100000 ns = 10 kHz
            with open(self.pwm_period_path, 'w') as f:
                f.write(str(pwm_period))
            
            # Enable PWM
            with open(self.pwm_enable_path, 'w') as f:
                f.write('1')
            
            # Start with 0% duty (fan off)
            self._set_pwm_duty(0)
            
            logger.info("PWM fan control initialized successfully")
        except Exception as e:
            logger.error(f"Failed to setup PWM: {e}")
            logger.warning("Fan control disabled - thermal throttling possible!")
    
    def _set_pwm_duty(self, duty_percent: int):
        """
        Set PWM duty cycle.
        
        Args:
            duty_percent: 0-100 duty cycle percentage
        """
        duty_percent = max(0, min(100, duty_percent))
        
        try:
            # Period is 100000 ns, so duty = percentage * 1000
            duty_ns = duty_percent * 1000
            with open(self.pwm_duty_path, 'w') as f:
                f.write(str(duty_ns))
            
            with self.lock:
                self.current_pwm = duty_percent
                
        except Exception as e:
            logger.error(f"Failed to set PWM duty: {e}")
    
    def _get_soc_temperature(self) -> Optional[float]:
        """
        Read SoC temperature from thermal zone.
        
        Returns:
            Temperature in °C, or None if read fails
        """
        try:
            with open(self.thermal_zone_path, 'r') as f:
                # Temperature is returned in millidegrees
                temp_milli = int(f.read().strip())
                temp_c = temp_milli / 1000.0
                return temp_c
        except Exception as e:
            logger.error(f"Failed to read temperature: {e}")
            return None
    
    def _calculate_pwm_duty(self, temp: float) -> int:
        """
        Calculate PWM duty cycle based on temperature.
        
        Linear scaling: 0% at min_temp, 100% at max_temp
        
        Args:
            temp: Current temperature in °C
            
        Returns:
            PWM duty cycle 0-100
        """
        if temp < self.min_temp:
            return 0
        elif temp > self.max_temp:
            return 100
        else:
            # Linear interpolation
            ratio = (temp - self.min_temp) / (self.max_temp - self.min_temp)
            return int(ratio * 100)
    
    def _monitoring_loop(self):
        """Background thread for temperature monitoring and fan control."""
        while self.running:
            try:
                temp = self._get_soc_temperature()
                
                if temp is not None:
                    with self.lock:
                        self.current_temp = temp
                    
                    pwm_duty = self._calculate_pwm_duty(temp)
                    self._set_pwm_duty(pwm_duty)
                    
                    # Log thermal throttling events
                    if temp > self.max_temp:
                        logger.warning(f"HIGH TEMPERATURE: {temp:.1f}°C (PWM: {pwm_duty}%)")
                    elif temp > self.target_temp:
                        logger.debug(f"Elevated temp: {temp:.1f}°C (PWM: {pwm_duty}%)")
                
                time.sleep(self.poll_interval)
                
            except Exception as e:
                logger.error(f"Error in thermal monitoring: {e}")
                time.sleep(1)
    
    def _start_monitoring(self):
        """Start background thermal monitoring thread."""
        self.running = True
        self.monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True,
            name="ThermalMonitor"
        )
        self.monitor_thread.start()
    
    def get_status(self) -> dict:
        """
        Get current thermal status.
        
        Returns:
            Dict with temperature and PWM info
        """
        with self.lock:
            return {
                'temperature_c': self.current_temp,
                'pwm_duty_percent': self.current_pwm,
                'thermal_zone': str(self.thermal_zone_path),
                'running': self.running
            }
    
    def shutdown(self):
        """Stop thermal monitoring and disable fan."""
        self.running = False
        self._set_pwm_duty(0)  # Turn off fan
        logger.info("Thermal manager shut down")


# Convenience function for single-instance usage
_thermal_manager: Optional[ThermalManager] = None


def get_thermal_manager() -> ThermalManager:
    """Get or create global thermal manager instance."""
    global _thermal_manager
    if _thermal_manager is None:
        _thermal_manager = ThermalManager()
    return _thermal_manager
