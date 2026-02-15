# MK4 Supra Digital Gauge Cluster System

Build a triple round-display (1080x1080) digital gauge cluster replicating authentic TRD/JDM Supra analog gauge styling using Orange Pi 5 Plus with native 3-display support and active thermal management. Single board at 60 FPS with ~NZ$950 total cost, prioritizing display reliability for critical drivability.

## Project Requirements

- **Displays:** 3x 5-inch round 1080x1080 IPS displays
- **Data Sources:**
  - Link G4X Fury ECU via CAN bus (RPM, speed, coolant temp, boost/MAP)
  - Stock 1995 JDM Supra fuel level sensor (240Ω empty, 10-20Ω full)
  - Existing harness: headlight signal, high beam, warning light, dimmer switch
- **Gauges:** Tachometer (0-8000 RPM), Speedometer (0-260 km/h), Fuel, Engine Temp (0-120°C), Boost PSI
- **Styling:** TRD manual gauges (km/h) with cream/beige face, thin black needles, simple analog design
- **Features:** Night mode (headlight-triggered), high beam indicator, warning light, dimmer control

## Hardware Architecture

See full hardware details in [hardware.md](hardware.md)

**Key Components:**
- **Orange Pi 6 Plus 16GB** (CIX P1 SoC) with native 3-display support (2x HDMI 2.1 + 1x USB-C DP)
  - ✓ Superior thermal design vs 5 Plus
  - ✓ 16GB DDR5 RAM for multi-display rendering headroom
  - ✓ Cooler included (~50 NZD value)
- Active cooling: **Included cooler + 40mm PWM fan** (temperature-controlled via GPIO)
  - Thermal monitoring via sysfs (/sys/class/thermal)
  - Automatic throttle prevention
- Waveshare RS485 CAN HAT for Link G4X ECU communication
- Tracopower TSR 2-2450 automotive DC/DC converter
- GPIO integration for headlights, high beam, warning, dimmer
- **Total cost: ~NZ$400** (SBC only, within budget)

## Software Architecture

- **Language:** Python 3.11+
- **OS:** Armbian (Debian-based, optimized for Orange Pi 6 Plus)
- **GUI:** PyQt5 with **QOpenGLWidget for GPU-accelerated rendering**
  - CRITICAL: CPU-only QPainter cannot achieve stable 60 FPS on 3x 1080x1080 displays
  - Mali GPU tile-based rendering requires OpenGL shaders (see performance_tuning.md)
- **CAN Bus:** python-can with SocketCAN (message filters + direct socket API)
  - Replaces shell-based setup for security and deterministic timing
- **Update Rate:** 50 FPS (20ms frame time budget)
  - Per-display: 6.67ms rendering budget with 3 displays
  - Imperceptibly smooth needle motion on gauges
- **Thermal Management:** Active PWM fan control
  - Sysfs thermal zone monitoring (/sys/class/thermal)
  - GPIO PWM scaling (0-100%) based on SoC temperature
  - Keeps system <65°C for extended lifespan

### Project Structure

```
src/
├── main.py              # Entry point and main loop
├── can_handler.py       # Link G4X CAN decoder
├── fuel_reader.py       # Fuel sensor interface
├── gpio_handler.py      # Harness signal inputs
├── gauge_renderer.py    # TRD-style gauge widgets
└── display_manager.py   # Multi-display layout
```

## Installation

See [README.md](../README.md) for detailed installation instructions.

Quick start:
```bash
cd /home/pi/supra-cluster
pip3 install -r requirements.txt
sudo systemctl enable config/supra-cluster.service
```

## Configuration

Edit [config/config.yaml](../config/config.yaml) to customize:
- Display assignments (HDMI0, HDMI1, DSI0)
- CAN message IDs (verify with Link G4X docs)
- Fuel sender calibration
- GPIO pin assignments
- Gauge styling and colors
- Night mode behavior

## Outstanding Questions

### 1. Fuel Sender - RESOLVED ✓
**Solution:** Wire stock fuel sender to Link G4X ECU analog input, read fuel level via CAN bus.

**Implementation:**
- Connect fuel sender signal to spare ECU analog input
- Configure as "Fuel Level" in PCLink (240Ω empty, 10Ω full)
- Enable CAN transmission
- Read fuel percentage from CAN message alongside RPM/speed/temp

### 2. Warning Light Behavior - RESOLVED ✓
**Solution:** Dual warning system - both stock signals AND ECU warnings

**Implementation:**
- Wire handbrake/seatbelt ground signals to GPIO (pull-up resistors)
- Monitor ECU critical warnings via CAN (high temp, low oil pressure, faults)
- Display red warning indicator when ANY condition is true
- Comprehensive coverage without single point of failure

### 3. Thermal Management - CRITICAL IMPLEMENTATION ⚠️
**Solution:** Orange Pi 6 Plus with mandatory active PWM fan control

**Implementation:**
- **Hardware:** Included cooler + 40mm PWM fan on GPIO pin (configurable)
- **Software:** Thermal daemon monitoring /sys/class/thermal/thermal_zone0/temp
- **Strategy:**
  - Baseline SoC temp: ~45°C (idle, climate controlled dash)
  - At 60 FPS rendering: +15-20°C increase expected
  - Target max: 70°C (prevents throttling, extends component lifespan)
  - PWM scaling: Linear from 0% (40°C) to 100% (80°C)
- **Monitoring:**
  ```bash
  cat /sys/class/thermal/thermal_zone0/temp  # Returns temp in millidegrees C
  ```
- **Test procedure:** Run gauges at 60 FPS for 30 min, log thermal curve

**If thermal target not met:**
- Implement GPU shaders to reduce CPU load
- Add external cooling solution (not recommended for automotive)
- Reduce display refresh rate to 50 FPS (barely acceptable)
- Migrate to Rock 5B+ (higher TDP handling)

## Wiring

See [wiring.md](wiring.md) for complete diagrams.

**Safety:**
- All 12V inputs use voltage dividers (3.9kΩ/1kΩ) to 3.3V
- Optocoupler isolation (6N137) on critical signals
- TVS diodes for transient protection
- Inline fuses on all 12V taps
 (CRITICAL - requires GPU acceleration)
  - Frame time budget: 16.67 ms total, ~5.5 ms per display
  - Profiling mandatory before deployment (use frame timing in QOpenGL)
- **CAN Update:** 100 Hz (10ms interval, no latency jitter)
  - Requires SocketCAN message filters to prevent interrupt flooding
- **Thermal Headroom:** SoC <65°C at 50 FPS (active cooling recommended)
  - Temperature-controlled PWM fan keeps system cool
  - Monitor via sysfs during testing
- **Boot Time:** <5 seconds to gauges active
- **Power:** ~45-48W at 50 FPS + active fan
- CAN bus message verification
- Fuel sender resistance mapping
- Display alignment and color calibration
- GPIO signal testing

## Performance Targets

- **Display Resolution:** 1080x1080 per display
- **Frame Rate:** 60 FPS sustained
- **CAN Update:** 100 Hz (10ms interval)
- **Boot Time:** <5 seconds to gauges active
- **Power:** ~46W at full load

## Development

Run in development mode:
```bash
python3 src/main.py
```

Monitor CAN bus:
```bash
candump can0
```

View logs:
```bash
journalctl -u supra-cluster.service -f
```

## Bill of Materials

See complete BOM with suppliers and costs in [hardware.md](hardware.md)

**Estimated Total:** ~£315 ($390 USD)

## References

- [Link ECU G4X Documentation](https://www.linkecu.com/)
- [Raspberry Pi 5 Documentation](https://www.raspberrypi.com/documentation/)
- [python-can Documentation](https://python-can.readthedocs.io/)
- [MCP2515 CAN Controller Datasheet](https://ww1.microchip.com/downloads/en/DeviceDoc/MCP2515-Stand-Alone-CAN-Controller-with-SPI-20001801J.pdf)
