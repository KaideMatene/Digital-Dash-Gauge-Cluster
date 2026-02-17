# MK4 Supra Digital Gauge Cluster

A triple-display digital gauge cluster system for a modified 1995 JDM Toyota Supra, running on **Orange Pi 6 Plus 16GB** with authentic TRD/JDM gauge styling.

**NOTE:** GPU-accelerated rendering is recommended for thermal efficiency and future headroom. See [performance_tuning.md](docs/performance_tuning.md).

## Features

- **3x 5-inch round 1080x1080 displays** at 50 FPS (smooth gauge rendering)
- **Real-time gauges:** Tachometer (0-8000 RPM), Speedometer (0-260 km/h), Fuel, Engine Temp, Boost PSI
- **Data sources:** Link G4X Fury ECU via CAN bus (RPM, speed, temp, boost, fuel level)
- **Authentic styling:** TRD manual gauge design with cream/beige face and thin needles
- **Night mode:** Auto-activated by headlight signal
- **Thermal management:** Active PWM fan control prevents throttling
- **Integration:** High beam indicator, warning light, dimmer control

## Hardware Requirements

- Orange Pi 6 Plus 16GB (CIX P1 SoC, includes cooler)
- 3x Round 1080x1080 displays (2x HDMI 2.1, 1x USB-C DisplayPort)
- Waveshare RS485 CAN HAT (MCP2515)
- Tracopower TSR 2-2450 (12V→5V converter)
- 40mm PWM fan (GPIO-controlled thermal management)
- Supporting components (see BOM in docs)

**Total Cost: ~NZ$400 (SBC only)** | **~NZ$800 (complete system)**

## Quick Start

### Installation

```bash
# On Orange Pi 6 Plus (Armbian)
cd /home/orangepi
git clone <repository-url> supra-cluster
cd supra-cluster

# Install dependencies
sudo apt update
sudo apt install -y python3-pip python3-pyqt5 python3-pyqt5.qtopengl python3-opengl can-utils
pip3 install -r requirements.txt

# Configure CAN interface (follow orange_pi_6_plus_setup.md)
sudo systemctl start systemd-networkd

# Run gauges
python3 src/main.py
```

### Pre-Deployment Checklist

- [ ] Read [performance_tuning.md](docs/performance_tuning.md) for GPU acceleration requirements
- [ ] Follow [orange_pi_6_plus_setup.md](docs/orange_pi_6_plus_setup.md) for complete setup
- [ ] Verify CAN bus messages: `candump can0`
- [ ] Profile FPS stability: Run at 60 FPS for 30 minutes
- [ ] Validate thermal stability: SoC <70°C with active PWM fan
- [ ] Verify all 3 displays connected and configured: `xrandr -q`

### Configuration

Edit `config/config.yaml` to customize:
- Display resolution and layout
- CAN message IDs (Link G4X protocol)
- Fuel sender calibration
- GPIO pin assignments
- Night mode settings

## Project Structure

```
supra-cluster/
├── src/                    # Application source code
│   ├── main.py            # Entry point
│   ├── can_handler.py     # CAN bus interface
│   ├── fuel_reader.py     # Fuel sensor reader
│   ├── gpio_handler.py    # GPIO inputs
│   ├── gauge_renderer.py  # Gauge widgets
│   └── display_manager.py # Multi-display manager
├── config/                 # Configuration files
│   ├── config.yaml        # Main configuration
│   ├── link_g4x_can.json  # CAN protocol mapping
│   └── supra-cluster.service # systemd service
├── assets/                 # Images and resources
│   ├── fonts/             # Gauge fonts
│   └── gauges/            # SVG gauge faces
├── docs/                   # Documentation
│   ├── plan.md            # Full project plan
│   ├── hardware.md        # Hardware setup guide
│   ├── wiring.md          # Wiring diagrams
│   └── calibration.md     # Calibration procedures
├── tests/                  # Unit tests
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## Documentation

- [Full Project Plan](docs/plan.md) - Complete specifications and implementation details
- [Digital Gauge FAQ & Research Resources](docs/DIGITAL_GAUGE_FAQ_RESEARCH.md) - **Comprehensive Q&A with internet-researched answers**
- [Internet Research Guide](docs/INTERNET_RESEARCH_GUIDE.md) - **How to research and find answers for digital gauge questions**
- [Hardware Setup](docs/hardware.md) - Component assembly instructions
- [Wiring Guide](docs/wiring.md) - Harness integration and connections
- [Calibration](docs/calibration.md) - Sensor calibration procedures

## Development

```bash
# Run in development mode (no systemd)
python3 src/main.py

# View CAN bus messages
candump can0

# Monitor system logs
journalctl -u supra-cluster.service -f
```

## License

MIT License - See LICENSE file for details

## Acknowledgments

- Link ECU for G4X CAN protocol documentation
- Toyota/TRD for original gauge design inspiration
