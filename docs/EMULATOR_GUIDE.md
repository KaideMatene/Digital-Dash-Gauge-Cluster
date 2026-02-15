# Supra Digital Cluster - Emulator Guide

Complete testing environment without hardware!

---

## Quick Start

### 1. Install Dependencies

```powershell
cd "c:\Projects\Supra Digital Cluster"

# Install PyQt5 (required for GUI)
pip install PyQt5

# Or install all project dependencies
pip install -r requirements.txt
```

### 2. Run the Emulator

**Option A: Default (50 FPS, windowed)**
```powershell
python emulator.py
```

**Option B: Custom FPS**
```powershell
python emulator.py --fps 60
```

**Option C: Fullscreen**
```powershell
python emulator.py --fullscreen
```

**Option D: Test CAN data only (no GUI)**
```powershell
python emulator.py --mock-can-only
```

### 3. Watch the Gauges

You should see:
- 3 round gauge displays (Tachometer, Speedometer, Fuel Gauge)
- Simulated engine data animating smoothly
- FPS counter in title bar
- Real-time statistics in console

---

## What the Emulator Does

### ✅ Simulates

- **3x 1080x1080 round displays** - Tachometer, Speedometer, Temperature/Fuel
- **Mock CAN bus data** - Realistic driving patterns (idle → accel → cruise → brake)
- **All gauge animations** - Smooth needle movement at 50/60 FPS
- **Night mode** - Dark theme switching
- **Indicators** - High beam, warning lights
- **Brightness control** - Simulates dashboard brightness dimming
- **Performance stats** - Real FPS, frame times, CPU/GPU load

### ❌ Does NOT Require

- Orange Pi board
- Physical displays
- CAN interface hardware
- GPIO pins
- Automotive ECU

---

## Controls

### Driving Mode Selection (Number Keys)

| Key | Driving Mode | Behavior |
|-----|-----|----------|
| **0** | IDLE | Engine idling, no movement (1000 RPM ± variation) |
| **1** | SLOW REV | Gentle acceleration to 3000 RPM over 10 seconds |
| **2** | MEDIUM REV | Moderate acceleration to 5000 RPM over 8 seconds |
| **3** | FAST REV | Aggressive acceleration to 7000 RPM over 6 seconds with boost |
| **4** | HIGHWAY | Steady highway cruise at 130 km/h |
| **5** | REDLINE | Bouncing off redline (6500-8000 RPM) |
| **6** | REALISTIC | Full 30-second realistic driving cycle (idle → accel → cruise → brake) |

### General Controls

| Key | Action |
|-----|--------|
| **SPACEBAR** | Pause/resume simulation |
| **n** | Toggle night mode (dark theme) |
| **h** | Toggle high beam indicator |
| **w** | Toggle warning indicator |
| **+** | Increase brightness (+10%) |
| **-** | Decrease brightness (-10%) |
| **?** | Show help with all controls |
| **q** or **ESC** | Quit emulator |

---

## Example Runs

### Test at 50 FPS (Project Default)

```powershell
python emulator.py --fps 50
```

Expected console output:
```
2026-02-07 14:32:15,123 - root - INFO - 🎮 Emulator initialized - Target FPS: 50
2026-02-07 14:32:15,456 - root - INFO - ✅ Emulator ready!
2026-02-07 14:32:17,234 - root - INFO - Frame 30 | FPS: 50.2/50 | Frame: 19.50ms | RPM:  1500 | Speed:   0 km/h | Temp: 80.5°C | Boost: 0.00 bar | Fuel: 74.9%
2026-02-07 14:32:19,876 - root - INFO - Frame 60 | FPS: 50.1/50 | Frame: 19.47ms | RPM:  4200 | Speed:  45 km/h | Temp: 82.1°C | Boost: 0.45 bar | Fuel: 74.8%
```

### Test Performance at Different FPS

```powershell
# Test at 50 FPS (project target)
python emulator.py --fps 50

# Test at 60 FPS (Apple/gaming standard)
python emulator.py --fps 60

# Test at 30 FPS (minimum for automotive)
python emulator.py --fps 30
```

### Test CAN Data Only

```powershell
python emulator.py --mock-can-only
```

Output:
```
t=0.0s | RPM:  1237 | Speed:   0 km/h | Temp:  80.0°C | Boost: 0.00 bar | Fuel: 75.0%
t=1.0s | RPM:  2124 | Speed:  12 km/h | Temp:  80.4°C | Boost: 0.08 bar | Fuel: 75.0%
t=2.0s | RPM:  3456 | Speed:  34 km/h | Temp:  81.3°C | Boost: 0.28 bar | Fuel: 74.9%
...
```

---

## What You Can Test

### Display & Graphics

✅ Gauge rendering is smooth and responsive  
✅ Colors/themes are correct in day/night mode  
✅ All 3 gauges update simultaneously without lag  
✅ Needle animations are fluid (no stuttering)  
✅ Text/labels are readable and positioned correctly  

### Performance

✅ Actual FPS matches target FPS  
✅ Frame times are consistent (no spikes)  
✅ Brightness controls work smoothly  
✅ Indicators (high beam, warning) toggle instantly  

### Data Handling

✅ Gauge values update in real-time  
✅ Values clamp correctly at limits (0-8000 RPM, etc.)  
✅ Smooth interpolation between values  
✅ Fuel consumption simulation is realistic  

### Code Quality

✅ No crashes or exceptions  
✅ PyQt5 rendering is smooth  
✅ Multi-threading doesn't cause flicker  
✅ Update cycle matches FPS setting  

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'PyQt5'"

**Fix:** Install PyQt5
```powershell
pip install PyQt5
```

### "No module named 'src' or 'gauge_renderer'"

**Fix:** Make sure you're running from project root
```powershell
# Correct location
cd "c:\Projects\Supra Digital Cluster"
python emulator.py

# Wrong location (don't do this)
cd "c:\Projects\Supra Digital Cluster\src"
python ..\emulator.py
```

### Emulator runs but gauges don't show

**Check:**
1. Window is visible (check taskbar, may be positioned off-screen)
2. PyQt5 is properly installed (`pip install PyQt5`)
3. Try running in windowed mode (not fullscreen)
4. Try test: `python emulator.py --mock-can-only`

### Very low FPS (20-30 instead of 50)

**Possible causes:**
- Windows is running other heavy programs (close them)
- GPU drivers need update (install latest graphics drivers)
- Antivirus scanning files (disable temporarily)

**Note:** This is OK - it's just Windows performance. Orange Pi will be faster.

### Gauges move too fast or too slow

**This is a simulation speed setting, not FPS:**
- Edit `emulator.py` line ~71: `cycle_time = 30  # Change this value`
- Lower = faster car simulation
- Higher = slower car simulation

---

## Next Steps

### After Emulator Testing

1. ✅ Confirmed gauges render smoothly
2. ✅ Confirmed animations work properly
3. ✅ Confirmed all features function correctly
4. ✅ Optimized any rendering issues

### Deploy to Orange Pi

```powershell
# Once you have the Orange Pi board:

# 1. Flash Armbian OS to microSD
# 2. Copy project to Orange Pi
scp -r . orangepi@orangepi-ip:/home/orangepi/supra-cluster

# 3. Connect physical displays to Orange Pi
# 4. Configure CAN bus
# 5. Update main.py to use real CAN data (not mock)
# 6. Run
python /home/orangepi/supra-cluster/src/main.py
```

---

## Emulator Limitations (vs Real Hardware)

| Feature | Emulator | Real Hardware |
|---------|----------|---------------|
| **Display resolution** | Windows desktop resolution | 1080x1080 per display |
| **GPU** | Intel/NVIDIA/AMD in PC | Mali GPU in Orange Pi |
| **Actual CAN data** | Mock/simulated | Real Link G4X ECU |
| **GPIO/PWM** | Simulated only | Real pin control |
| **Thermal driver** | No thermal mgmt needed | FAN PWM control |
| **Real performance** | Depends on PC specs | Consistent OPi performance |

---

## Tips for Testing

1. **Test at 50 FPS first** - This is the project target
2. **Try night mode** - Verify dark theme renders correctly
3. **Pause simulation** - Check that gauges are responsive
4. **Watch frame times** - Should be consistent (±2ms)
5. **Monitor FPS counter** - Should match target FPS closely
6. **Try fullscreen** - Makes sure display layout works on larger screens

---

## Testing Driving Modes

The emulator includes 7 preset driving scenarios for comprehensive testing:

### 1. Idle Mode (Press `0`)
```
Engine: 1000 RPM (±200 RPM variation)
Speed: 0 km/h
Use case: Test idle stability, no flickering
Expected: Steady RPM needle with slight wobble
```

### 2. Slow Rev (Press `1`)
```
Acceleration pattern: 1000 → 3000 RPM over 10 seconds
Speed: 0 → 40 km/h
Boost: 0.0 → 0.1 bar
Use case: Test gentle acceleration, smooth needle movement
Expected: Smooth upward needle sweep, repeats every 10 seconds
```

### 3. Medium Rev (Press `2`)
```
Acceleration pattern: 1000 → 5000 RPM over 8 seconds
Speed: 0 → 80 km/h
Boost: 0.0 → 0.3 bar
Use case: Test moderate acceleration with boost gauge
Expected: Faster needle sweep, visible boost indicator
```

### 4. Fast Rev (Press `3`)
```
Acceleration pattern: 1000 → 7000 RPM over 6 seconds
Speed: 0 → 150 km/h
Boost: 0.0 → 0.8 bar
Use case: Test aggressive acceleration, high FPS demand
Expected: Very fast needle movement, high boost values
```

### 5. Highway Mode (Press `4`)
```
Steady cruise: 3500 ± 300 RPM
Speed: 130 ± 20 km/h
Boost: 0 bar (no boost)
Use case: Test steady-state operation, fuel consumption
Expected: Gentle oscillating needle at cruise RPM, stable speed
```

### 6. Redline Mode (Press `5`)
```
Bouncing: 6500 → 8000 RPM in 4-second cycles
Speed: 0 → 180 km/h
Boost: Up to 1.2 bar
Use case: Test redline zone, warning indicators
Expected: Rapid bouncing in red zone, high visual activity
```

### 7. Realistic Mode (Press `6`)
```
Complete driving cycle (30 seconds):
  - 0-3s: Idle (1000 RPM)
  - 3-9s: Acceleration (1500 → 7500 RPM)
  - 9-21s: Cruising (3500 ± 500 RPM, 100-150 km/h)
  - 21-30s: Braking (deceleration)
Use case: Test realistic vehicle operation
Expected: Smooth transitions through all states
```

### Testing Workflow

1. **Start emulator:**
   ```powershell
   python emulator.py --fps 50
   ```

2. **Test each mode for 10-15 seconds:**
   - Press `0` for idle → wait 10 seconds → observe
   - Press `1` for slow rev → watch 2-3 cycles
   - Press `2` for medium rev → verify boost gauge
   - Press `3` for fast rev → confirm redline zone
   - Press `4` for highway → test fuel consumption
   - Press `5` for redline → watch red zone behavior
   - Press `6` for realistic → watch full cycle

3. **For each mode, verify:**
   - ✅ Tachometer needle moves smoothly
   - ✅ Speedometer updates correctly
   - ✅ Fuel gauge decreases realistically
   - ✅ Temperature rises with load, falls at idle
   - ✅ FPS stays at target (no stuttering)

---

## Command Quick Reference

```powershell
# Show help
python emulator.py --help

# Run at 50 FPS (default, recommended for testing)
python emulator.py

# Run at 60 FPS
python emulator.py --fps 60

# Run fullscreen (test large display layout)
python emulator.py --fullscreen

# Run at 60 FPS fullscreen
python emulator.py --fps 60 --fullscreen

# Test CAN data only (no GUI)
python emulator.py --mock-can-only

# Test CAN data and show more details
python emulator.py --mock-can-only 2>&1 | More
```

---

## Mock CAN Data Simulation

The emulator simulates a realistic driving cycle:

```
0-10% of cycle (3 sec):   Engine startup/idle
10-30% of cycle (6 sec):  Acceleration 0→100 km/h
30-70% of cycle (12 sec): Cruising at ~100-150 km/h
70-100% of cycle (9 sec): Braking to stop

Then repeats every 30 seconds...
```

This creates natural transitions you'd see on actual road data.

---

**Ready to test?** 

```powershell
python emulator.py
```

🎮 The emulator will open 3 gauge displays and start simulating! Press **[n]** for night mode, **[spacebar]** to pause, **[q]** to quit.
