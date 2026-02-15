# Quick Reference - Supra Digital Cluster

## Hardware Summary

| Component | Specification | Cost (NZD) | Status |
|-----------|---------------|-----------|--------|
| **Orange Pi 6 Plus** | 16GB DDR5, CIX P1 SoC | ~400 | ✓ Recommended |
| **3x Displays** | 1080x1080 IPS, 5" round | ~300 | 🔄 Pending order |
| **CAN HAT** | Waveshare RS485 MCP2515 | ~50 | 🔄 Pending |
| **PSU** | Tracopower TSR 2-2450 | ~70 | 🔄 Pending |
| **Cooling** | Included + PWM fan | ~50 | ✓ Included |
| **Total** | Complete system | ~870 | - |

## Critical Implementation Path

```
1. Order Hardware (Orange Pi 6 Plus 16GB from Xunlong)
   └─ ETA: 2-3 weeks

2. Setup OS & Hardware (See orange_pi_6_plus_setup.md)
   ├─ Armbian installation
   ├─ CAN bus configuration
   ├─ Display setup (3x 1080x1080)
   └─ Thermal manager verification
   └─ Duration: 1 week

3. GPU Acceleration Migration 🔴 CRITICAL
   ├─ Current: CPU QPainter (18-22 ms/frame = FAIL)
   ├─ Target: GPU OpenGL (5 ms/frame @ 60 FPS)
   ├─ Implement: QOpenGLWidget + shaders
   ├─ Profile: Frame timing verification
   └─ Duration: 2-3 weeks

4. Validation & Testing
   ├─ Thermal curve (30 min @ 60 FPS)
   ├─ Link G4X CAN verification
   ├─ GPIO signal testing
   └─ Duration: 1-2 weeks

5. Vehicle Integration
   └─ Final installation & calibration
```

## Performance Requirements

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| **Frame Rate** | 50 FPS | ~48 FPS | 🟡 Tight (GPU recommended) |
| **Frame Time** | <20 ms | 18-22 ms | 🟡 Tight (GPU recommended) |
| **SoC Temp @ 50 FPS** | <65°C | 75-80°C | 🟡 Managed (PWM helps) |
| **CAN Latency** | <10 ms | Variable | 🟡 Fixed (added filters) |

## Critical Files to Review

1. **[performance_tuning.md](docs/performance_tuning.md)**
   - Why GPU acceleration is mandatory
   - GPU optimization techniques
   - FPS profiling methodology

2. **[orange_pi_6_plus_setup.md](docs/orange_pi_6_plus_setup.md)**
   - Step-by-step hardware setup
   - CAN bus configuration
   - Display configuration
   - Thermal testing procedures

3. **[IMPLEMENTATION_CHANGES.md](docs/IMPLEMENTATION_CHANGES.md)**
   - Complete change log
   - Risk assessment
   - Success criteria

## Testing Checklist

### Before Vehicle Deployment
```bash
# 1. Verify CAN bus
candump can0  # Should see Link G4X messages

# 2. Check displays
xrandr -q  # Should show 3x connected 1080x1080

# 3. Test thermal management
while true; do cat /sys/class/thermal/thermal_zone0/temp; sleep 2; done

# 4. Run gauges at 60 FPS
python3 src/main.py

# 5. Monitor frame timing (add to code)
# Expected: <16.67 ms with GPU acceleration
# Expected: >18 ms with CPU-only (UNACCEPTABLE)
```

### Thermal Stability Test (MANDATORY)
```bash
# Run for 30 minutes minimum
# Expected temperature curve:
# - 0-5 min: 45°C → 55°C (ramp-up)
# - 5-30 min: 60-65°C (stable)
# - PWM fan: 30-50% duty
# - NO thermal throttling events in logs
```

### Link G4X Verification (MANDATORY)
```bash
# In PCLink software on Windows/Mac:
1. Open CAN Setup
2. Verify these messages are transmitted:
   - RPM (message ID 0x??? - verify)
   - Speed (message ID 0x??? - verify)
   - Temperature (message ID 0x??? - verify)
   - Boost (message ID 0x??? - verify)

# Update can_handler.py filter IDs with actual values
```

## Quick Commands

```bash
# Monitor SoC temperature
watch -n 1 'cat /sys/class/thermal/thermal_zone0/temp | awk "{print \$1/1000 \"°C\"}"'

# Check display configuration
xrandr --query

# Monitor CAN messages
candump -c can0

# Run application in foreground
python3 src/main.py

# View systemd logs
journalctl -u supra-cluster.service -f

# Measure GPIO PWM duty (thermal fan)
cat /sys/class/pwm/pwmchip0/pwm21/duty_cycle

# Check CPU frequency (for thermal throttling detection)
watch -n 1 'cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq'
```

## Common Issues & Fixes

| Issue | Cause | Fix |
|-------|-------|-----|
| **FPS <50** | CPU-based rendering | GPU acceleration required (critical path) |
| **Thermal throttling** | No active cooling | Verify PWM fan working, check thermal_manager.py |
| **CAN not visible** | Interface down | `sudo ip link set up can0`, check systemd config |
| **Gauge freezing** | Message flooding | Verify CAN filters applied in can_handler.py |
| **Displays not detected** | HDMI/DP issues | Check cables, run `xrandr -q` |

## Key Contacts & Resources

- **Orange Pi Support:** http://www.orangepi.org/
- **Armbian Docs:** https://docs.armbian.com/
- **Link ECU:** https://www.linkecu.com/
- **PyQt5 OpenGL:** https://doc.qt.io/qt-5/qopenglwidget.html

## Budget Summary

| Category | Amount (NZD) | Notes |
|----------|-----------|-------|
| Orange Pi 6 Plus | 400 | APPROVED |
| Displays | 300 | Pending |
| CAN/PSU/Cooling | 120 | Pending |
| Wiring/Connectors | 50 | Have stock |
| **TOTAL** | **870** | Under 950 target ✓ |

## Deployment Readiness Checklist

- [ ] GPU acceleration implemented & profiled
- [ ] Thermal stability verified (30 min test)
- [ ] CAN bus messages confirmed in PCLink
- [ ] All 3 displays operational & synced
- [ ] Systemd service tested
- [ ] PWM fan responding to temperature
- [ ] GPIO inputs tested (headlights, warnings)
- [ ] Fuel sender calibrated
- [ ] Vehicle integration plan finalized

---

**Last Updated:** February 6, 2026  
**Next Milestone:** Hardware Arrival + Armbian Setup
