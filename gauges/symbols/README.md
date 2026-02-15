# Symbol Images

This directory contains warning lights, indicators, and symbol images for the digital cluster.

## Directory Structure

```
gauges/symbols/
├── README.md                    # This file
├── check_engine.png             # Check engine light
├── oil_pressure.png             # Oil pressure warning
├── battery.png                  # Battery/charging warning
├── abs.png                      # ABS warning
├── airbag.png                   # Airbag warning
├── traction_control.png         # Traction control indicator
├── high_beam.png                # High beam indicator
├── low_fuel.png                 # Low fuel warning
└── ...                          # Add more symbols as needed
```

## File Naming Convention

Use lowercase letters with underscores for symbol filenames:
- `check_engine.png`
- `oil_pressure.png`
- `battery.png`
- `abs.png`

## Image Format

- **Format**: PNG (with transparency)
- **Recommended size**: 64x64 to 128x128 pixels
- **Color**: Design symbols with full color - the code can handle day/night mode switching
- **Background**: Transparent (alpha channel)

## Usage in Code

Symbols can be controlled from the gauge preview UI under the "⚠️ Symbols & Warnings" section.

To programmatically add a new symbol:

```python
window.add_symbol_toggle("symbol_id", "Symbol Display Name", default_visible=False)
```

To set symbol visibility:

```python
window.set_symbol_visible("symbol_id", True)
```

## Example Symbols

Common automotive warning lights and indicators:
- Check Engine (MIL)
- Oil Pressure
- Battery/Charging System
- ABS
- Airbag
- Traction Control
- Stability Control
- High Beam
- Turn Signals
- Low Fuel
- Coolant Temperature
- Tire Pressure
- Fog Lights
- Cruise Control
- Sport Mode
- ECO Mode

Place your PNG files here and they'll be ready for integration with the cluster system.
