"""
CAN Bus Handler for Link G4X Fury ECU

Manages CAN bus communication and message parsing.
"""

import can
import logging
import threading
import time
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class CANHandler:
    """Handles CAN bus communication with Link G4X Fury ECU"""
    
    def __init__(self, channel='can0', bitrate=500000):
        self.channel = channel
        self.bitrate = bitrate
        self.bus: Optional[can.Bus] = None
        self.running = False
        self.latest_data = {
            'rpm': 0,
            'speed': 0,
            'coolant_temp': 0,
            'boost': 0
        }
        self.lock = threading.Lock()
        
        # Initialize CAN bus
        self._setup_can()
        
        # Start background thread for receiving messages
        self.receiver_thread = threading.Thread(target=self._receive_loop, daemon=True)
        self.receiver_thread.start()
        
        logger.info(f"CAN handler initialized on {channel} at {bitrate} bps")
    
    def _setup_can(self):
        """Configure and initialize CAN interface."""
        try:
            # Check if interface is already up
            import socket
            import struct
            
            # Try to bring up interface if needed (requires systemd-networkd or manual config)
            # This assumes /etc/systemd/network/can0.network is pre-configured
            # Alternative: use 'ip link set can0 type can bitrate 500000' in system scripts
            
            # Create bus instance using SocketCAN
            self.bus = can.interface.Bus(
                channel=self.channel,
                bustype='socketcan',
                receive_own_messages=False,
                can_filters=[
                    {"can_id": 0x100, "can_mask": 0x7FF},  # RPM message
                    {"can_id": 0x101, "can_mask": 0x7FF},  # Speed message
                    {"can_id": 0x102, "can_mask": 0x7FF},  # Temp message
                    {"can_id": 0x103, "can_mask": 0x7FF},  # Boost message
                ]
            )
            
            # Verify interface is up
            import subprocess
            result = subprocess.run(['ip', 'link', 'show', self.channel], 
                                  capture_output=True, text=True)
            if 'UP' not in result.stdout:
                logger.warning(f"CAN interface {self.channel} may not be up. "
                              f"Run: sudo ip link set up {self.channel}")
            
            self.running = True
            logger.info(f"CAN bus initialized on {self.channel} at {self.bitrate} bps")
            logger.info(f"Applied message filters for Link G4X messages")
            
        except Exception as e:
            logger.error(f"Failed to initialize CAN bus: {e}")
            logger.error(f"Ensure CAN interface is configured: "
                        f"sudo ip link set {self.channel} type can bitrate {self.bitrate}")
            self.running = False
    
    def _receive_loop(self):
        """Background thread to receive and parse CAN messages"""
        while self.running:
            try:
                if self.bus is None:
                    time.sleep(1)
                    continue
                
                # Receive message with timeout
                message = self.bus.recv(timeout=0.1)
                if message:
                    self._parse_message(message)
            except Exception as e:
                logger.error(f"Error receiving CAN message: {e}")
                time.sleep(0.1)
    
    def _parse_message(self, msg: can.Message):
        """
        Parse Link G4X CAN message
        
        TODO: Update message IDs and parsing based on Link G4X CAN protocol documentation
        These are placeholder examples - verify with actual Link ECU configuration
        """
        try:
            msg_id = msg.arbitration_id
            data = msg.data
            
            with self.lock:
                # Example parsing (VERIFY WITH LINK G4X DOCUMENTATION)
                if msg_id == 0x100:  # Engine RPM
                    rpm = int.from_bytes(data[0:2], byteorder='big')
                    self.latest_data['rpm'] = rpm
                    
                elif msg_id == 0x101:  # Vehicle Speed
                    speed = int.from_bytes(data[0:2], byteorder='big')
                    self.latest_data['speed'] = speed
                    
                elif msg_id == 0x102:  # Coolant Temperature
                    temp = data[0]  # Assuming single byte, degrees C
                    self.latest_data['coolant_temp'] = temp
                    
                elif msg_id == 0x103:  # MAP/Boost Pressure
                    # Convert kPa to PSI
                    map_kpa = int.from_bytes(data[0:2], byteorder='big')
                    boost_psi = (map_kpa - 101.325) * 0.145038  # Subtract atmospheric, convert to PSI
                    self.latest_data['boost'] = round(boost_psi, 1)
                    
        except Exception as e:
            logger.error(f"Error parsing CAN message {msg.arbitration_id:X}: {e}")
    
    def get_latest_data(self) -> Dict[str, float]:
        """Get latest parsed CAN data thread-safely"""
        with self.lock:
            return self.latest_data.copy()
    
    def shutdown(self):
        """Clean shutdown of CAN bus"""
        logger.info("Shutting down CAN handler...")
        self.running = False
        if self.receiver_thread.is_alive():
            self.receiver_thread.join(timeout=2)
        if self.bus:
            self.bus.shutdown()
        logger.info("CAN handler shutdown complete")
