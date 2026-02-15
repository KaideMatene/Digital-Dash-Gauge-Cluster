# Hardware Setup Guide

Complete hardware specifications and assembly instructions for the Supra Digital Gauge Cluster.

## Bill of Materials

### Core Electronics (~NZ$735 total)

| Component | Specification | Quantity | Unit Cost (NZD) | Total (NZD) | Supplier |
|-----------|---------------|----------|-----------------|-------------|----------|
| **Orange Pi 6 Plus** | 16GB LPDDR5, CD8180/CD8160, 28.8T NPU, 5 displays | 1 | $368 | $368 | [AliExpress](https://www.aliexpress.com/item/1005010157378785.html) |
| **Power Supply** | 100W USB-C PD 20V | 1 | Included | - | orangepios |
| **Automotive PSU** | Tracopower TSR 2-2450 (12V→20V) | 1 | $66 | $66 | Mouser/DigiKey |
| **CAN Interface** | Waveshare RS485 CAN HAT | 1 | $23 | $23 | Waveshare |
| **Round Display (HDMI)** | ES050YMM-A00, 1080x1080 IPS 5" | 3 | $96 | $288 | [AliExpress](https://www.aliexpress.com/item/1005003249756249.html) |
| **HDMI Cables** | Filtered automotive-grade | 2 | $9 | $18 | Amazon |
| **DisplayPort to HDMI Adapter** | DP male to HDMI female | 1 | $12 | $12 | Amazon |
| **USB-C to HDMI Adapter** | DisplayPort Alt Mode support | 1 | $15 | $15 | Amazon |
| **5V Buck Converter** | DC-DC 12V→5V, 5A | 1 | $10 | $10 | AliExpress/Amazon |
| **Relay Module** | 4-channel 5V | 1 | $13 | $13 | Amazon |
| **Heatsink** | Passive aluminum for Pi 5 | 1 | $13 | $13 | - |
| **Cooling Fan** | 5V PWM 40mm | 1 | $12 | $12 | - |
| **Thermal Paste** | High quality | 1 | $8 | $8 | - |

### Components & Wiring (~NZ$115)

| Component | Specification | Quantity | Cost (NZD) |
|-----------|---------------|----------|------------|
| **Optocouplers** | 6N137 high-speed | 4 | $7 |
| **TVS Diodes** | 15V automotive | 4 | $5 |
| **Resistors** | 3.9kΩ, 1kΩ voltage dividers | 8 | $3 |
| **MCP3008** | 10-bit 8-channel ADC | 1 | $8 |
| **Wire** | 22 AWG automotive (red/black) | 10m | $17 |
| **Connectors** | Weatherproof terminals | 20 | $13 |
| **Fuses** | 5A, 10A blade fuses | 6 | $8 |
| **Fuse Holders** | Inline automotive | 3 | $8 |
| **Heat Shrink** | Assorted sizes | 1 kit | $13 |
| **Wire Loom** | Corrugated flexible | 2m | $13 |
| **M2.5 Standoffs** | For Pi mounting | 1 set | $13 |
| **Breadboard** | Prototyping breakout | 1 | $8 |

**Total Hardware Cost: ~NZ$850**

*Fuel level read via ECU CAN bus - no separate fuel module needed*

## Component Details

### Orange Pi 6 Plus (16GB)

**Why Orange Pi 6 Plus?**
- CIX CD8180/CD8160 SoC (12-core 64-bit) with integrated graphics
- **5 display outputs:** HDMI 1.4 + DP 1.4 + 2x Type-C DP + eDP
- Supports 4K @ 120Hz on DisplayPort (easily handles 3x 1080x1080 @ 60 FPS)
- 16GB LPDDR5 RAM with 128-bit memory bus (4x more than original Pi 5 plan)
- 12-core 64-bit processor (powerful multi-threaded performance)
- 28.8 TOPS NPU + hardware ray tracing GPU (45 TOPS combined)
- 8K video decode capability
- 2x M.2 KEY-M 2280 NVMe slots (PCIe 4.0, 4-lane) for dual SSD setup
- Dual 5G Ethernet ports (useful for remote monitoring/tuning)
- M.2 KEY-E slot for Wi-Fi modules
- 2x USB Type-C 3.0 full-function ports

**Purchased Model:**
- Model: OPi6 Plus 16G
- Includes: Active cooling (heatsink + PWM fan)
- Power: 2x Type-C PD 20V inputs, 100W adapter included
- Dimensions: 115x100mm (fits dashboard enclosure)
- Weight: 132g

**Display Connection Plan:**
- HDMI 1.4 → Display 1 (Left - Tachometer)
- DisplayPort 1.4 → Display 2 (Center - Speedometer)
- USB-C DP #1 → Display 3 (Right - Temp/Boost)
- *Available:* USB-C DP #2 (future 4th gauge or settings screen)
- *Available:* eDP (embedded panel for always-on display)

### Displays - ES050YMM-A00 Round 1080x1080 IPS

**Purchased Model (3x):**
- Model: ES050YMM-A00 (Wisecoco 5" Dual Round Display)
- Source: [AliExpress Link](https://www.aliexpress.com/item/1005003249756249.html)

**Specifications:**
- Resolution: 1080x1080 pixels (1080 RGB x 1080)
- Panel: IPS, Normally Black, 16.7M colors
- Size: 5 inches diagonal
- Active Area: 127.008mm x 127.008mm
- Pixel Pitch: 0.1176mm
- Color Gamut: 70% typical
- Viewing Direction: Free (U/D/L/R)
- Interface: **HDMI** (via included driver board)
  - Note: Panel uses MIPI internally, but driver board accepts HDMI input
- Includes: Driver board with HDMI + power connectors per display

**Why These Displays:**
- Perfect for circular tachometer/speedometer gauges
- True 1:1 aspect ratio (square) ideal for round gauge rendering
- IPS panel = wide viewing angles for driver visibility
- Pre-assembled with HDMI driver boards (plug-and-play)

### Waveshare RS485 CAN HAT

**Features:**
- MCP2515 CAN controller (industry standard)
- SPI interface to Raspberry Pi
- 500 kbps baud rate support
- Hardware 120Ω termination (DIP switch)
- TVS diode protection
- 3.3V/5V compatible

**Pinout:**
- CAN_H: Yellow wire to ECU CAN_H
- CAN_L: Green wire to ECU CAN_L
- GND: Black wire to chassis ground

### Tracopower TSR 2-2450

**Specifications:**
- Input: 6.5-32V DC (automotive 12V)
- Output: 5V @ 9A (45W)
- Efficiency: >90%
- Isolation: 2kV
- Operating temp: -40°C to +85°C
- Protection: Short circuit, over-current, over-temp

**Why This PSU?**
- Automotive-grade reliability
- Handles voltage fluctuations (alternator ripple)
- Isolation prevents ground loops
- Wide temperature range

### VDO Fuel Gauge Module

**Function:**
- Converts variable resistance (240-10Ω) to 0-5V output
- Built-in noise filtering
- Calibrated for standard automotive fuel senders

**Alternatives:**
- DIY voltage divider + MCP3008 ADC (less reliable)
- Read fuel level from Link ECU via CAN (if available)

## Assembly Instructions

### 1. Orange Pi 6 Plus Setup

**Verify Cooling:**
1. Confirm heatsink and fan are pre-installed (included with your unit)
2. Fan should be connected to PWM-capable GPIO pin
3. Verify fan spins on boot (should hear it)

**Mount CAN HAT:**
1. Align Waveshare CAN HAT with GPIO header
2. Press firmly to seat all pins
3. Secure with standoffs (avoid shorts)
4. Set DIP switches (enable 120Ω termination if needed)

### 2. Display Connections (All HDMI)

**Display 1 - Left Gauge (Tachometer):**
1. Connect HDMI cable from Orange Pi **HDMI port** to display driver board
2. Connect display driver board power (5V, check included cable)
3. Secure cable strain relief with zip ties

**Display 2 - Center Gauge (Speedometer):**
1. Connect DisplayPort to HDMI cable/adapter from Orange Pi **DP port** to display driver board
2. Connect display driver board power
3. Secure cables

**Display 3 - Right Gauge (Temperature/Boost):**
1. Connect **USB-C to HDMI adapter** to Orange Pi USB-C port
2. Connect HDMI cable from adapter to display driver board
3. Connect display driver board power
4. Adapter supports DisplayPort Alt Mode (confirmed on OPi6 Plus)

**Required Cables/Adapters:**
- 1x HDMI cable (for Display 1)
- 1x DisplayPort to HDMI cable OR adapter (for Display 2)
- 1x USB-C to HDMI adapter with DP Alt Mode support (for Display 3)
- 1x HDMI cable for USB-C adapter to Display 3

**Important Notes:**
- All three displays use HDMI input (driver boards convert to MIPI for the panel)
- Each display driver board needs individual 5V power
- Use filtered/shielded HDMI cables in automotive environment
- Route cables through corrugated loom for vibration protection

### 3. Power System

**Automotive 12V Input:**
1. Tap 12V ignition-switched circuit (fused at 10A)
2. Connect to Tracopower TSR 2-2450 input
3. Connect ground to chassis ground point

**Raspberry Pi Power:**
1. Connect Tracopower 5V output to Pi 5 official 45W PSU input
2. Or use USB-C adapter cable (verify 5V regulation)

### 4. CAN Bus Wiring

**Link G4X ECU Connection:**
1. Locate CAN_H and CAN_L pins on ECU connector
2. Use twisted-pair shielded cable (automotive grade)
3. Wire:
   - ECU CAN_H → Waveshare CAN_H (yellow)
   - ECU CAN_L → Waveshare CAN_L (green)
   - Chassis GND → Waveshare GND
4. Enable 120Ω termination on Waveshare HAT if ECU doesn't provide it

### 5. Fuel Sender Integration

**Locate Fuel Sender Signal:**
1. Find fuel sender wire at gauge cluster harness (typically single wire + ground)
2. Toyota Supra: Check connector behind stock gauge cluster

**Connect to Module:**
1. Tap fuel sender signal wire (don't cut - use splice connector)
2. Connect to VDO module input
3. Connect module ground to chassis
4. Wire module 0-5V output to MCP3008 ADC CH0
5. Connect MCP3008 to Pi 5 SPI pins

### 6. Harness Integration (GPIO Inputs)

**Build Voltage Divider Board:**

For each 12V input (headlights, high beam, warning):

```
12V Input ──┬── 3.9kΩ ──┬── To GPIO (3.3V)
            │           │
          TVS Diode   1kΩ
            │           │
           GND         GND
```

**Optocoupler Isolation (Recommended):**

```
12V Input ── Resistor ── 6N137 LED ──┐
                                     │
                        6N137 Collector ── To GPIO
                        6N137 Emitter ── GND
```

**Wire Connections:**
1. **Headlight Signal** → Voltage divider → GPIO 17
2. **High Beam Signal** → Voltage divider → GPIO 27
3. **Warning Light** → Voltage divider → GPIO 22
4. **Dimmer Potentiometer** → MCP3008 CH1

**GPIO Pin Assignments (BCM):**
- GPIO 17: Headlight input (night mode)
- GPIO 27: High beam indicator
- GPIO 22: Warning light
- SPI pins: MCP3008 ADC (CE0, MOSI, MISO, SCLK)

### 7. Thermal Management

**Cooling Strategy:**
- Passive heatsink for baseline cooling
- Active 40mm fan for sustained operation
- Mount Pi in ventilated area
- Avoid direct sun exposure in vehicle

**Temperature Monitoring:**
```bash
vcgencmd measure_temp
```

## Testing & Verification

### Power System Test
1. Connect 12V input (ignition on)
2. Verify 5V output from Tracopower (multimeter)
3. Connect Pi 5 and verify boot

### CAN Bus Test
1. Start vehicle (ECU powered)
2. On Pi: `candump can0`
3. Verify CAN messages streaming
4. Check message IDs match Link G4X protocol

### Display Test
1. Boot Pi with all 3 displays connected
2. Verify all displays show output
3. Check resolution: `xrandr` or `tvservice -s`

### GPIO Test
1. Toggle headlights → verify GPIO 17 changes
2. Toggle high beam → verify GPIO 27 changes
3. Trigger warning light → verify GPIO 22 changes
4. Test dimmer potentiometer → verify ADC reading

## Mounting & Installation

### Display Mounting
- Design 3D-printed bezels to match dash contours
- Secure displays in original gauge cluster location
- Route cables cleanly through dash

### Pi Mounting Location Options

**Option 1: Interior Cabin (Recommended)**
- Behind dash, away from engine heat
- Easier access for maintenance
- Requires 2-3m CAN cable extension

**Option 2: Engine Bay**
- Shorter CAN cables
- Requires robust thermal management
- Higher risk of heat damage

## Troubleshooting

### Displays Not Detected
- Check HDMI cable connections
- Verify DSI ribbon seated properly
- Check config.txt settings

### No CAN Data
- Verify CAN_H and CAN_L not swapped
- Check 120Ω termination enabled
- Confirm ECU CAN stream enabled
- Test with `cansend can0 123#DEADBEEF`

### Fuel Reading Incorrect
- Check fuel sender resistance with multimeter
- Verify sender wiring not shorted
- Calibrate module for Supra's resistance curve

### GPIO Inputs Not Working
- Verify voltage divider output is 3.3V (not 12V!)
- Check optocoupler orientation
- Test GPIO with `gpio readall`

## Safety Notes

- **NEVER connect 12V directly to Raspberry Pi GPIO** (instant damage)
- Always use voltage dividers or optocouplers
- Fuse all 12V taps appropriately
- Use heat shrink on all solder connections
- Route cables away from hot exhaust components
- Disconnect battery before wiring into vehicle harness
