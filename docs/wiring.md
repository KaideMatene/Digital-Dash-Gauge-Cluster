# Wiring Guide

Detailed wiring diagrams and connection instructions for integrating the digital gauge cluster with the 1995 JDM Supra.

## Overview

This guide covers:
1. Power system wiring (12V → 5V)
2. CAN bus connection to Link G4X ECU
3. Fuel sender integration
4. GPIO inputs (headlights, high beam, warning, dimmer)
5. Display connections

## Safety First

⚠️ **CRITICAL SAFETY WARNINGS:**
- Disconnect battery negative terminal before working on wiring
- NEVER connect 12V directly to Raspberry Pi GPIO pins
- Always use proper fuses on 12V circuits
- Double-check polarity before connecting power
- Use heat shrink or electrical tape on all connections
- Route wires away from hot exhaust components

## 1. Power System Wiring

### 12V Input from Vehicle

**Source:** Ignition-switched 12V circuit (powers on with key, off when engine stops)

**Recommended Tap Point:** Accessory power circuit behind dash

```
Vehicle 12V Circuit
  │
  ├── 10A Blade Fuse ────┐
  │                       │
  └─────────────────────GND (Chassis)

Tracopower TSR 2-2450 Input
  ├── +Vin (12V)
  ├── GND
  └── +Vout (5V @ 9A) ──→ Raspberry Pi 5 (45W USB-C PSU)
```

**Wiring Steps:**
1. Locate ignition-switched 12V wire (use multimeter: 0V key off, 12V key on)
2. Install inline 10A blade fuse holder
3. Connect fused 12V to Tracopower +Vin
4. Connect chassis ground to Tracopower GND
5. Connect Tracopower 5V output to Pi 5 official PSU input (or USB-C adapter)

**Wire Gauge:** 18 AWG for 12V input, 16 AWG for 5V output

## 2. CAN Bus Wiring

### Link G4X Fury ECU Connection

**CAN Bus Standards:**
- Baud rate: 500 kbps
- Twisted-pair cable required
- 120Ω termination at each end

**Link ECU CAN Connector:**
Locate CAN output on Link G4X ECU connector (refer to Link ECU manual for your specific pinout)

```
Link G4X ECU
  ├── CAN_H (Pin XX) ──┐
  ├── CAN_L (Pin XX) ──┤
  └── GND   (Pin XX) ──┤
                        │
                  Twisted Pair Cable
                  (Shielded, automotive-grade)
                        │
Waveshare CAN HAT       │
  ├── CAN_H ────────────┘
  ├── CAN_L ─────────────┘
  └── GND ───────────────┘
```

**Wiring Steps:**
1. Obtain twisted-pair shielded CAN cable (minimum 2 wires + shield)
2. Solder/crimp to Link ECU CAN_H and CAN_L pins
3. Route cable through firewall grommet to interior
4. Connect to Waveshare CAN HAT terminals:
   - Yellow wire → CAN_H
   - Green wire → CAN_L
   - Black wire → GND
5. Enable 120Ω termination DIP switch on Waveshare HAT (if Link ECU doesn't provide termination)

**Cable Length:** Keep under 5 meters for reliability

**Testing:**
```bash
sudo ip link set can0 type can bitrate 500000
sudo ip link set up can0
candump can0
```
You should see CAN messages streaming when engine is running.

## 3. Fuel Sender Wiring

### Stock Supra Fuel Sender

**Sender Location:** Inside fuel tank, accessible via gauge cluster harness

**Sender Type:** Variable resistor
- Empty: ~240Ω
- Full: ~10-20Ω

### Connection via VDO Fuel Gauge Module

```
Stock Fuel Sender (in tank)
  │
  └── Signal Wire (single wire + ground) ──┐
                                            │
VDO Fuel Gauge Module                       │
  ├── Input ────────────────────────────────┘
  ├── Ground ──→ Chassis GND
  └── Output (0-5V) ──┐
                      │
MCP3008 ADC           │
  ├── CH0 ────────────┘
  ├── VDD ──→ 3.3V (Pi)
  ├── GND ──→ GND (Pi)
  ├── MOSI ──→ GPIO 10 (Pi SPI0 MOSI)
  ├── MISO ──→ GPIO 9  (Pi SPI0 MISO)
  ├── SCLK ──→ GPIO 11 (Pi SPI0 SCLK)
  └── CS ────→ GPIO 8  (Pi SPI0 CE0)
```

**Wiring Steps:**
1. Locate fuel sender wire at gauge cluster connector (behind stock dash)
2. Use splice connector to tap wire (don't cut original)
3. Connect tapped wire to VDO module input
4. Connect VDO module ground to chassis
5. Wire VDO module 0-5V output to MCP3008 CH0 pin
6. Wire MCP3008 to Raspberry Pi SPI pins (see diagram above)

**Alternative:** If Link G4X ECU already reads fuel level, skip this and use CAN data instead

## 4. GPIO Input Wiring

### Voltage Divider Circuit (12V → 3.3V)

**FOR EACH GPIO INPUT (Headlight, High Beam, Warning):**

```
12V Vehicle Signal
  │
  ├── TVS Diode (15V) ──→ GND (spike protection)
  │
  └── 3.9kΩ Resistor ──┬── To Raspberry Pi GPIO
                       │
                     1kΩ Resistor
                       │
                      GND
```

**Output Voltage Calculation:**
- V_out = V_in × (R2 / (R1 + R2))
- V_out = 12V × (1kΩ / (3.9kΩ + 1kΩ)) = 2.45V ✓ (safe for 3.3V GPIO)

### With Optocoupler Isolation (Recommended for Critical Signals)

```
12V Vehicle Signal
  │
  └── 1kΩ Current-Limiting Resistor ──┬── 6N137 Anode (LED side)
                                       │
                                     6N137 Cathode ──→ GND
                                       
                                     6N137 Collector ──→ 3.3V (Pi) via 10kΩ pull-up
                                     6N137 Emitter ──→ To GPIO
```

### GPIO Pin Assignments

| Vehicle Signal | GPIO Pin (BCM) | Circuit Type | Notes |
|----------------|----------------|--------------|-------|
| Headlight ON   | GPIO 17        | Voltage divider | Night mode trigger |
| High Beam ON   | GPIO 27        | Voltage divider | High beam indicator |
| Warning Light  | GPIO 22        | Voltage divider | Warning lamp signal |
| Dimmer Pot     | MCP3008 CH1    | ADC reading | Brightness control |

### Headlight Signal Wiring

**Source:** Tap headlight switch output (12V when headlights ON)

```
Headlight Switch Output (12V when ON)
  │
  ├── TVS Diode ──→ GND
  │
  └── 3.9kΩ ──┬── To GPIO 17 (Pi)
              │
            1kΩ
              │
             GND
```

**Test:** Turn headlights on → `gpio -g read 17` should return 1

### High Beam Signal Wiring

**Source:** Tap high beam indicator wire (12V when high beams ON)

```
High Beam Indicator (12V when ON)
  │
  └── Voltage Divider ──→ GPIO 27 (Pi)
```

### Warning Light Signal Wiring

**Source:** Stock warning light output (12V when warning active)

```
Warning Light Output (12V when active)
  │
  └── Voltage Divider ──→ GPIO 22 (Pi)
```

### Dimmer Potentiometer Wiring

**Source:** Stock dimmer rheostat (variable resistor for dash brightness)

**Option 1: Direct Potentiometer Reading**
```
3.3V (Pi) ──┬── Potentiometer ──┬── MCP3008 CH1
            │                   │
           GND                 GND
```

**Option 2: Tap Stock Dimmer Output**
```
Stock Dimmer Output (0-12V variable)
  │
  └── Voltage Divider ──→ MCP3008 CH1
```

**ADC Reading:** 0 = minimum brightness (20%), 1023 = maximum brightness (100%)

## 5. Display Connections

### HDMI Displays (Left & Center)

```
Raspberry Pi 5
  ├── micro-HDMI 0 ──→ Left Display (Tachometer + Boost)
  └── micro-HDMI 1 ──→ Center Display (Speedometer + Temp)
```

**Cable Recommendations:**
- Use short cables (< 1 meter) to minimize interference
- Filtered HDMI cables for automotive noise rejection
- Secure cables with zip ties to prevent disconnection

### DSI Display (Right)

```
Raspberry Pi 5
  └── DISP0 (DSI connector) ──→ Right Display (Fuel + Indicators)
```

**Ribbon Cable:**
- 6-inch DSI ribbon cable (15-pin or 22-pin, depending on display)
- Route through flexible corrugated conduit for vibration protection
- Avoid sharp bends (minimum 5mm radius)

## 6. Complete System Wiring Diagram

```
                          SUPRA DIGITAL GAUGE CLUSTER
                                WIRING DIAGRAM

┌─────────────────────────────────────────────────────────────────────┐
│ VEHICLE 12V SYSTEM                                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  [12V Ignition] ───[10A Fuse]─── Tracopower TSR 2-2450              │
│       │                                │                              │
│       │                                ├──→ 5V @ 9A ──→ [Pi 5 PSU]  │
│       │                                └──→ GND                       │
│       │                                                               │
│  [Headlight] ────[Voltage Div]────→ GPIO 17 (Night Mode)            │
│  [High Beam] ────[Voltage Div]────→ GPIO 27 (HB Indicator)          │
│  [Warning Lt]────[Voltage Div]────→ GPIO 22 (Warning)               │
│  [Dimmer Pot]────[MCP3008 CH1]────→ SPI (Brightness)                │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ LINK G4X FURY ECU                                                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  [CAN_H] ────[Twisted Pair]────→ Waveshare CAN HAT (CAN_H)          │
│  [CAN_L] ────[Twisted Pair]────→ Waveshare CAN HAT (CAN_L)          │
│  [GND]   ─────────────────────→ Waveshare CAN HAT (GND)             │
│                                                                       │
│  Data: RPM, Speed, Coolant Temp, MAP/Boost @ 500 kbps               │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ FUEL SENDER (IN TANK)                                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  [Signal] ────→ VDO Module Input (240Ω empty, 10Ω full)             │
│  [Ground] ────→ Chassis GND                                          │
│                     │                                                │
│                     └──→ 0-5V Output ──→ MCP3008 CH0                │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ RASPBERRY PI 5 & DISPLAYS                                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  [Pi 5 micro-HDMI 0] ──→ Left Display (Tach + Boost)                │
│  [Pi 5 micro-HDMI 1] ──→ Center Display (Speedo + Temp)             │
│  [Pi 5 DSI DISP0]    ──→ Right Display (Fuel + Indicators)          │
│                                                                       │
│  [Waveshare CAN HAT] ── SPI Interface                                │
│  [MCP3008 ADC]       ── SPI Interface (Fuel + Dimmer)                │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

## Pin Reference Tables

### Raspberry Pi GPIO (BCM Numbering)

| Pin # | GPIO # | Function |
|-------|--------|----------|
| 11    | 17     | Headlight input (night mode) |
| 13    | 27     | High beam input |
| 15    | 22     | Warning light input |
| 19    | 10     | SPI0 MOSI (MCP3008) |
| 21    | 9      | SPI0 MISO (MCP3008) |
| 23    | 11     | SPI0 SCLK (MCP3008) |
| 24    | 8      | SPI0 CE0 (MCP3008 fuel) |
| 26    | 7      | SPI0 CE1 (Reserved) |

### MCP3008 ADC Pinout

| Pin | Name | Connection |
|-----|------|------------|
| 1   | CH0  | Fuel sender (0-5V from VDO module) |
| 2   | CH1  | Dimmer potentiometer |
| 3-8 | CH2-7| Reserved |
| 9   | DGND | Ground |
| 10  | CS   | GPIO 8 (SPI0 CE0) |
| 11  | DIN  | GPIO 10 (SPI0 MOSI) |
| 12  | DOUT | GPIO 9 (SPI0 MISO) |
| 13  | CLK  | GPIO 11 (SPI0 SCLK) |
| 14  | AGND | Ground |
| 15  | VREF | 3.3V |
| 16  | VDD  | 3.3V |

## Testing Procedures

### Power System Test
1. Disconnect Pi, connect only 12V input to Tracopower
2. Measure output: should be 5.0V ±0.1V
3. Connect Pi and boot
4. Monitor voltage under load: should remain >4.75V

### CAN Bus Test
```bash
# Bring up CAN interface
sudo ip link set can0 type can bitrate 500000
sudo ip link set up can0

# Monitor messages
candump can0

# Expected output: Continuous CAN messages when engine running
# can0  100   [8]  0F A0 00 00 00 00 00 00  (example)
```

### GPIO Input Test
```bash
# Read headlight input (lights off = 0, lights on = 1)
gpio -g read 17

# Read high beam (off = 0, on = 1)
gpio -g read 27

# Read warning (inactive = 0, active = 1)
gpio -g read 22
```

### Fuel Sender Test
```python
import spidev
spi = spidev.SpiDev()
spi.open(0, 0)
adc = spi.xfer2([1, (8 + 0) << 4, 0])  # Read CH0
data = ((adc[1] & 3) << 8) + adc[2]
voltage = (data * 3.3) / 1024
print(f"Fuel voltage: {voltage}V")
```

## Troubleshooting

### No Power to Pi
- Check 12V input at Tracopower (should be 12-14V)
- Verify fuse not blown
- Check Tracopower 5V output with multimeter
- Ensure USB-C cable capable of 45W power delivery

### No CAN Data
- Verify CAN_H and CAN_L not reversed
- Check twisted-pair cable for breaks
- Enable 120Ω termination on Waveshare HAT
- Confirm Link ECU CAN stream enabled in ECU config

### GPIO Always Reading 0
- Check voltage divider output (should be ~2.4V when 12V input)
- Verify 12V signal present at source
- Test GPIO pin: `gpio -g mode 17 in; gpio -g read 17`

### Fuel Reading Stuck
- Check fuel sender resistance with multimeter (disconnect from module)
- Verify VDO module powered (5V input)
- Test MCP3008: manually apply 0-3.3V to CH0 and read value

## Wire Color Standards (Recommended)

| Function | Color |
|----------|-------|
| +12V Power | Red |
| Ground | Black |
| CAN_H | Yellow |
| CAN_L | Green |
| Headlight Signal | Blue |
| High Beam Signal | Light Blue |
| Warning Light | Orange |
| Fuel Sender | Brown |
| Dimmer Signal | Gray |

## Additional Resources

- [Link ECU Wiring Information](https://www.linkecu.com/)
- [Raspberry Pi GPIO Pinout](https://pinout.xyz/)
- [MCP3008 Datasheet](https://ww1.microchip.com/downloads/en/DeviceDoc/21295d.pdf)
- [CAN Bus Basics](https://www.ti.com/lit/an/sloa101b/sloa101b.pdf)
