# Implementation Checklist - Best Practices Alignment

**Project:** Supra Digital Cluster  
**Date:** February 6, 2026  

---

## 1. Display Management (Orange Pi 6 Plus - Multi-Display)

### Current State Assessment
- ✓ Config specifies 1080x1080 per display @ 60 FPS
- ✓ GPIO pin assignments documented (config.yaml)
- ⚠️ No explicit GPU memory configuration (RK3588 != BCM, uses dynamic allocation)
- ⚠️ Display manager implementation not reviewed

### Action Items

#### Configuration
- [ ] Verify Armbian kernel supports RK3588 DRM/KMS
- [ ] Check `/sys/class/drm/` for detected displays
- [ ] Test hot-plug detection (unplug/replug HDMI)
- [ ] Disable DPMS: Add to `/etc/X11/xorg.conf.d/` or systemd service
- [ ] Measure display latency with `glxgears` or `glmark2`

#### GPU Memory
- [ ] RK3588 allocates GPU memory dynamically (not fixed)
- [ ] Monitor actual usage: `watch -n 1 "cat /sys/class/devfreq/*/load"`
- [ ] Check for GPU memory fragmentation under sustained load

#### Thermal Monitoring
- [ ] Set up temperature monitoring via `thermal_zone`
- [ ] Implement automatic throttle detection
- [ ] Connect PWM fan (see Section 4 below)

**Status:** 🟡 PARTIAL - Display works, optimization needed

---

## 2. Gauge Rendering Performance

### Current State Assessment

**Critical Issue:** Need to profile current FPS

```bash
# Quick test on device
cd /opt/supra-cluster
python3 -c "
from src.gauge_renderer import BaseGauge
from PyQt5.QtWidgets import QApplication
import time

app = QApplication([])
gauge = BaseGauge()
gauge.show()

start = time.time()
for i in range(300):
    gauge.value = (i * 100) % 8000
    gauge.update()
    app.processEvents()
elapsed = time.time() - start

fps = 300 / elapsed
print(f'Measured FPS: {fps:.1f}')
print(f'Target: 60.0 FPS')
print(f'Status: {'✓ PASS' if fps >= 58 else '✗ FAIL - GPU migration needed'}')"
```

### Action Items - Immediate

- [ ] **MEASURE CURRENT FPS** on device (see profiling command above)
- [ ] Profile gauge rendering time: `python -m cProfile -s cumulative main.py | head -20`
- [ ] Check GPU availability:
  ```bash
  lsmod | grep mali  # Should show mali_kbase loaded
  ```

### Action Items - If FPS < 50

- [ ] Migrate `BaseGauge` → `GaugeOpenGL` (QOpenGLWidget-based)
- [ ] Pre-compile GLSL shaders for Mali (lowp, mediump precision)
- [ ] Create VBO/VAO for gauge geometry
- [ ] Test individual gauge FPS target: ~5-6ms per display

### Optimization Checklist (Current CPU Approach)

- [ ] Cache static gauge face to QPixmap (in `__init__`)
- [ ] Disable QPainter antialiasing: `painter.setRenderHint(QPainter.SmoothPixmapTransform, False)`
- [ ] Use fast color lookup (numpy array, not dict):
  ```python
  self.color_map = np.array([[245, 235, 215], ...], dtype=np.uint8)  # RGB
  ```
- [ ] Profile text rendering - consider texture atlas instead of per-frame rasterization
- [ ] Measure transformation matrix computation time
- [ ] Remove unnecessary `update()` calls - only on value changes

**Status:** 🔴 CRITICAL - FPS verification required before optimization

---

## 3. SocketCAN Implementation

### Current State Assessment

**From your can_handler.py:**
```python
os.system(f'sudo ip link set {self.channel} type can bitrate {self.bitrate}')  # ✗ Anti-pattern
self.bus: Optional[can.Bus] = None  # Using python-can (acceptable)
```

**Issues:**
- ✗ Shell command setup (timing, security, error handling)
- ✗ No CAN filters (all frames cause interrupts)
- ⚠️ Daemon thread without error propagation
- ⚠️ No bus error monitoring

### Action Items - Pre-deployment

#### System Configuration
- [ ] Create persistent CAN config (move from runtime setup):
  ```bash
  # /etc/systemd/network/99-can.link
  [Match]
  Driver=mcp251x
  
  [CAN]
  BitRate=500000
  SamplePoint=0.875
  RestartMs=100
  ```
  
  Then test:
  ```bash
  sudo systemctl restart systemd-networkd
  ip link show can0  # Verify it's UP
  ```

#### Code Refactoring
- [ ] Replace `os.system()` calls with native SocketCAN
- [ ] Add CAN filter setup (reduce interrupt load):
  ```python
  # Only listen to Link ECU message IDs
  filters = [0x100, 0x101, 0x102, 0x103]
  sock.setsockopt(SOL_CAN_RAW, CAN_RAW_FILTER, ...)
  ```
- [ ] Add error frame monitoring:
  ```python
  err_mask = (can.CAN_ERR_TX_TIMEOUT | can.CAN_ERR_BUSOFF | can.CAN_ERR_BUSOFF)
  sock.setsockopt(SOL_CAN_RAW, CAN_RAW_ERR_FILTER, struct.pack('I', err_mask))
  ```
- [ ] Implement non-blocking socket or separate RX thread
- [ ] Add logging for bus errors (CAN_ERR_BUSOFF, CAN_ERR_TX_TIMEOUT)

#### Testing
- [ ] Verify can0 interface status:
  ```bash
  ip -d link show can0
  ```
- [ ] Test CAN loopback (no hardware needed):
  ```bash
  candump can0
  # In another terminal:
  cansend can0 100#11223344
  ```
- [ ] Monitor interrupt load:
  ```bash
  watch -n 1 "cat /proc/interrupts | grep can"
  ```

**Status:** 🟡 PARTIAL - Functional but not optimized

---

## 4. PWM Fan Control

### Current State Assessment

**From config.yaml:**
```yaml
gpio:
  headlights: 17
  high_beam: 27
  warning_light: 22
  dimmer_cs: 8
  # NO FAN CONTROL CONFIGURED ✗
```

**From main.py:**
```python
self.gpio_handler = GPIOHandler()  # Exists, but no fan control
```

**Critical Issue:** No thermal management = system will throttle under sustained 60 FPS load

### Action Items - URGENT

#### Implementation
- [ ] Create PWM controller class (see best_practices_research.md Section 4)
- [ ] Allocate GPIO pin for PWM (check available in `/sys/class/pwm/`)
- [ ] Implement thermal monitoring loop:
  ```python
  # In main.py SupraCluster.__init__
  self.thermal_controller = ThermalController(
      pwm_pin=... ,  # Choose available pin
      fan_curve={50: 0, 60: 30, 70: 60, 85: 100}
  )
  ```

#### Hardware Verification
- [ ] Check Rockchip PWM pin mapping (GPIO pin → PWM controller)
  ```bash
  cat /sys/kernel/debug/gpio | grep pwm
  ```
- [ ] Test PWM export:
  ```bash
  echo 0 | sudo tee /sys/class/pwm/pwmchip0/export
  echo 10000000 | sudo tee /sys/class/pwm/pwmchip0/pwm0/period
  ```
- [ ] Measure fan response time with temperature ramp
- [ ] Verify no performance regression from thermal control thread

#### Thermal Zones
- [ ] Identify correct `/sys/class/thermal/thermal_zone*/` paths:
  ```bash
  for zone in /sys/class/thermal/thermal_zone*/; do
    echo "$(basename $zone): $(cat $zone/type)"
  done
  ```
- [ ] Log thermal throttle events (look for frequency drops):
  ```bash
  watch -n 1 "cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq"
  ```

**Status:** 🔴 CRITICAL - Not implemented

---

## 5. Multi-threaded Real-Time Architecture

### Current State Assessment

**From main.py:**
```python
class SupraCluster:
    def __init__(self):
        self.app = QApplication(sys.argv)
        # Single-threaded event loop
        self.receiver_thread = threading.Thread(target=self._receive_loop, daemon=True)
        # CAN thread exists but GUI single-threaded
```

**Issues:**
- ⚠️ CAN handler runs in daemon thread (errors lost)
- ⚠️ GPIO reads on main thread (can block display)
- ⚠️ 3 displays on single QApplication (may not parallelize)
- ⚠️ No synchronization between threads (possible race conditions)

### Action Items

#### Thread Architecture
- [ ] Implement thread-safe queue for CAN data:
  ```python
  from queue import Queue
  
  self.can_data_queue = Queue(maxsize=10)  # Drop old data if slow
  self.can_handler.subscribe(self.can_data_queue)
  ```
- [ ] Separate thermal control thread (already daemon, good)
- [ ] Evaluate per-display rendering threads (if GPU-accelerated)
- [ ] Implement graceful shutdown:
  ```python
  def on_close(self):
      self.running = False
      self.can_handler.stop()
      self.thermal_controller.stop()
  ```

#### Error Propagation
- [ ] Don't use daemon threads for critical services
- [ ] Log all thread exceptions to syslog
- [ ] Implement watchdog timer (QTimer monitoring thread health)

#### Performance Monitoring
- [ ] Add frame rate monitor:
  ```python
  self.frame_timer = QTimer()
  self.frame_counter = 0
  self.frame_timer.timeout.connect(self._log_fps)
  ```
- [ ] Log to syslog every 5 seconds
- [ ] Alert if FPS drops below 50

**Status:** 🟡 PARTIAL - Basic threading exists, needs hardening

---

## Pre-Deployment Testing Checklist

### Performance Validation

- [ ] Sustained 60 FPS for 30 minutes (thermal stability)
- [ ] All 3 displays update synchronously
- [ ] No tearing visible on any display
- [ ] CPU/GPU usage within budget:
  - [ ] CPU < 50%
  - [ ] GPU < 70%
  - [ ] Thermal < 80°C
  
### CAN Bus Validation

- [ ] Receive all expected messages from Link ECU
- [ ] No frame drops (watch `ip -d link show can0`)
- [ ] Verify message latency < 50ms (from ECU to display)
- [ ] Test error handling (disconnect CAN, verify recovery)

### GPIO/Thermal Validation

- [ ] Fan ramps speed smoothly (no sudden changes)
- [ ] Temperature stable under load (±2°C oscillation)
- [ ] No thermal throttle events in dmesg:
  ```bash
  dmesg | grep -i throttle
  ```

### Sysfs/Systemd Validation

- [ ] Service auto-starts on boot
- [ ] Service logs to `/var/log/supra-cluster.log`
- [ ] Service respawn on crash (RestartSec=5)
- [ ] Clean shutdown on `systemctl stop supra-cluster`

---

## Deployment Checklist

- [ ] Update to latest Armbian kernel (security patches)
- [ ] Test on actual hardware (Orange Pi 6 Plus with displays)
- [ ] Measure actual power consumption (12V supply)
- [ ] Document exact GPIO pin mapping (Rockchip vs BCM)
- [ ] Create backup of working config
- [ ] Test systemd service persistence:
  ```bash
  sudo systemctl enable supra-cluster
  sudo reboot
  systemctl status supra-cluster
  ```

---

## Documentation TODO

- [ ] Update README.md with thermal requirements
- [ ] Document GPU acceleration migration path
- [ ] Add troubleshooting section (FPS drops, CAN errors, thermal issues)
- [ ] Create performance baseline spreadsheet (FPS, CPU%, Temp)

---

**Priority:** 🔴🔴🔴 - Thermal control is CRITICAL  
**Effort:** 2-3 hours for core issues, 1-2 days for optimization  
**Risk:** Medium (GPU migration may introduce new bugs)
