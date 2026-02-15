# Orange Pi 6 Plus Setup Guide

**This is your first deployment target. Follow exactly.**

## Hardware Verification

- [ ] Orange Pi 6 Plus 16GB confirmed received
- [ ] Cooler assembled and mounted (included)
- [ ] 40mm PWM fan connected to GPIO pin 21 (BCM numbering)
- [ ] All 3 displays connected (HDMI-1, HDMI-2, USB-C DP)
- [ ] Power supply rated 45W minimum

## OS Installation (Armbian)

```bash
# Download Armbian for Orange Pi 6 Plus
wget https://www.orangepi.org/official-images/armbian-orangepi-6-plus.img.gz

# Flash to microSD card (8GB minimum recommended)
gunzip -c armbian-orangepi-6-plus.img.gz | sudo dd of=/dev/sdX bs=4M status=progress

# Boot and login
# Default: root/orangepi
```

## Armbian First Boot Configuration

```bash
# Update system
sudo apt update
sudo apt upgrade -y

# Install required packages
sudo apt install -y \
  python3-pip \
  python3-pyqt5 \
  python3-pyqt5.qtopengl \
  python3-opengl \
  can-utils \
  python3-dev \
  build-essential \
  libssl-dev \
  libffi-dev \
  git

# Install Python dependencies
cd /home/orangepi
git clone <your-repo-url> supra-cluster
cd supra-cluster
pip3 install -r requirements.txt
```

## CAN Bus Configuration (Armbian systemd)

**Create `/etc/systemd/network/can0.network`:**

```ini
[Match]
Name=can0

[CAN]
BitRate=500000
```

**Enable and bring up CAN interface:**

```bash
sudo systemctl enable systemd-networkd
sudo systemctl restart systemd-networkd

# Verify CAN is up
ip link show can0  # Should show "UP"
```

**Test CAN communication:**

```bash
# Monitor CAN traffic
candump can0

# You should see Link G4X messages (verify IDs match your ECU config):
# can0  100   [8]  XX XX XX XX XX XX XX XX
# can0  101   [8]  XX XX XX XX XX XX XX XX
```

## Display Configuration (Armbian)

```bash
# Check detected displays
xrandr -q

# Example output:
# HDMI-1 connected (1080x1080)
# HDMI-2 connected (1080x1080)
# DP-1 connected (1080x1080)

# Configure 3-display layout (left-to-right):
xrandr --output HDMI-1 --primary --mode 1080x1080 \
       --output HDMI-2 --mode 1080x1080 --right-of HDMI-1 \
       --output DP-1 --mode 1080x1080 --right-of HDMI-2
```

**Persist display config in `/etc/X11/xorg.conf.d/50-display.conf`:**

```conf
Section "Monitor"
    Identifier "HDMI-1"
    Modeline "1080x1080_60.00" 150.00 1080 1120 1200 1320 1080 1100 1110 1150 -hsync +vsync
    Option "PreferredMode" "1080x1080_60.00"
EndSection

Section "Monitor"
    Identifier "HDMI-2"
    Modeline "1080x1080_60.00" 150.00 1080 1120 1200 1320 1080 1100 1110 1150 -hsync +vsync
    Option "PreferredMode" "1080x1080_60.00"
EndSection

Section "Monitor"
    Identifier "DP-1"
    Modeline "1080x1080_60.00" 150.00 1080 1120 1200 1320 1080 1100 1110 1150 -hsync +vsync
    Option "PreferredMode" "1080x1080_60.00"
EndSection
```

## GPIO/PWM Configuration for Thermal Fan

```bash
# Export PWM pin 21 for fan control
echo 21 > /sys/class/pwm/pwmchip0/export

# Configure as 10 kHz (standard for computer fans)
echo 100000 > /sys/class/pwm/pwmchip0/pwm21/period

# Enable PWM
echo 1 > /sys/class/pwm/pwmchip0/pwm21/enable

# Test fan (50% speed = 50000 ns duty cycle)
echo 50000 > /sys/class/pwm/pwmchip0/pwm21/duty_cycle

# You should hear the fan spin up
```

**Persist GPIO/PWM configuration:**

Create `/etc/udev/rules.d/99-pwm-fan.rules`:

```bash
SUBSYSTEM=="pwm", ACTION=="add", DEVPATH=="*/pwmchip0", RUN+="/bin/bash -c 'echo 21 > /sys/class/pwm/pwmchip0/export'"
```

## Thermal Manager Verification

```bash
# Monitor SoC temperature in real-time
watch -n 1 'cat /sys/class/thermal/thermal_zone0/temp | awk "{print \$1/1000}"'

# Run gauge at 60 FPS
cd /home/orangepi/supra-cluster
python3 src/main.py &

# In another terminal, monitor temperature rise
# Expected: Idle ~45°C, Under load ~60-65°C
```

## Systemd Service Setup

**Create `/etc/systemd/system/supra-cluster.service`:**

```ini
[Unit]
Description=Supra Digital Gauge Cluster
After=multi-user.target
Wants=network-online.target

[Service]
Type=simple
User=orangepi
WorkingDirectory=/home/orangepi/supra-cluster
ExecStart=/usr/bin/python3 /home/orangepi/supra-cluster/src/main.py
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**Enable and start service:**

```bash
sudo systemctl enable supra-cluster.service
sudo systemctl start supra-cluster.service

# Monitor logs
journalctl -u supra-cluster.service -f
```

## Performance Profiling (CRITICAL)

Before field deployment, you MUST profile FPS and thermal behavior:

```bash
# Terminal 1: Run gauges
python3 src/main.py

# Terminal 2: Monitor thermal profile for 30 minutes
while true; do
  temp=$(cat /sys/class/thermal/thermal_zone0/temp | awk '{print $1/1000}')
  pwm=$(cat /sys/class/pwm/pwmchip0/pwm21/duty_cycle | awk '{print int($1/1000) "%"}')
  echo "$(date '+%H:%M:%S') Temp: ${temp}°C PWM: ${pwm}"
  sleep 2
done > /tmp/thermal_profile.log

# Check results after 30 minutes
# Expected: Temperature stable 60-68°C, PWM 40-60%, NO throttling
tail -20 /tmp/thermal_profile.log
```

## Link G4X ECU Configuration (PCLink)

**MUST verify before field test:**

1. Open Link PCLink software on Windows/Mac
2. Connect to Link G4X ECU
3. Navigate to **CAN Setup**
4. Verify the following messages are being transmitted:
   - **Message 1:** RPM (0-8000)
   - **Message 2:** Vehicle Speed (0-260 km/h)
   - **Message 3:** Coolant Temperature (0-120°C)
   - **Message 4:** Boost/MAP Pressure
5. Note the **Message IDs** (e.g., 0x100, 0x101, 0x102, 0x103)
6. Update [can_handler.py](../src/can_handler.py) line 65 with correct IDs:

```python
can_filters=[
    {"can_id": 0x100, "can_mask": 0x7FF},  # Replace with actual RPM ID
    {"can_id": 0x101, "can_mask": 0x7FF},  # Replace with actual Speed ID
    ...
]
```

## Pre-Deployment Checklist

- [ ] CAN interface up and receiving Link G4X messages
- [ ] All 3 displays detected and configured (xrandr -q shows 3x 1080x1080)
- [ ] Thermal manager running with PWM fan responding to temperature
- [ ] 30-min performance profile: Temp <70°C, stable 60 FPS
- [ ] systemd service starts without errors
- [ ] Gauges render without freezing or visual glitches
- [ ] Link G4X CAN IDs verified in PCLink
- [ ] Fuel sender calibrated (if using analog input)
- [ ] GPIO inputs tested (headlights, warnings, dimmer)

## Troubleshooting

### CAN Interface Not Up

```bash
# Check actual error
sudo ip link set up can0  # Should show error if not configured

# Verify systemd-networkd has can0.network file
ls -la /etc/systemd/network/can0.network

# Manual workaround (temporary)
sudo ip link set can0 type can bitrate 500000
sudo ip link set up can0
```

### Gauges Rendering Slowly (<60 FPS)

**Likely cause:** CPU-based rendering without GPU acceleration

1. Verify GPU acceleration is enabled in gauge_renderer.py
2. Profile FPS with frame timing (see performance_tuning.md)
3. If FPS <50 with CPU-only rendering: GPU acceleration migration required

### Thermal Throttling (Temperature >80°C)

1. Verify PWM fan is spinning: `cat /sys/class/pwm/pwmchip0/pwm21/duty_cycle`
2. Check cooler is properly mounted
3. Increase PWM max temp threshold in thermal_manager.py
4. Consider additional external cooling

### Freezing/Stuttering Gauges

1. Check CAN message filters applied (avoid interrupt flooding)
2. Verify SocketCAN is configured with message IDs
3. Monitor CAN message timestamps with: `candump -c -t a can0`
4. Profile CPU usage during rendering

## Support Resources

- [Orange Pi 6 Plus Official Wiki](http://www.orangepi.org/)
- [Armbian Documentation](https://docs.armbian.com/)
- [python-can Docs](https://python-can.readthedocs.io/)
- [Link ECU CAN Documentation](https://www.linkecu.com/)
