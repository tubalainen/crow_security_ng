# Crow Security NG

A modern, async Python library for the Crow Cloud API - Next Generation.

This library provides a clean, type-hinted interface for interacting with Crow Security alarm systems (Shepherd panels) through the Crow Cloud API.

## Features

- **Fully async** - Built on `aiohttp` for efficient async I/O
- **Type hints** - Complete type annotations for better IDE support
- **Modern Python** - Requires Python 3.10+, uses dataclasses and enums
- **Proper error handling** - Dedicated exception classes for different error types
- **MAC address normalization** - Accepts any MAC format (with/without separators)
- **WebSocket support** - Real-time updates from your alarm panel
- **Backwards compatible** - Provides `Session` class compatible with original `crow_security`
- **Retry logic** - Automatic retries with exponential backoff
- **Context managers** - Proper resource cleanup with async context managers

## Installation

```bash
pip install crow_security_ng
```

## Quick Start

### Basic Usage

```python
import asyncio
from crow_security_ng import Session

async def main():
    # Create a session
    session = Session("your-email@example.com", "your-password")
    
    # Get your panel (MAC address can be in any format)
    panel = await session.get_panel("AABBCCDDEEFF")
    # or: await session.get_panel("AA:BB:CC:DD:EE:FF")
    # or: await session.get_panel("aa-bb-cc-dd-ee-ff")
    
    print(f"Panel: {panel.name}")
    
    # Get alarm areas
    areas = await panel.get_areas()
    for area in areas:
        print(f"Area: {area.name}, State: {area.state}")
    
    # Arm the alarm
    await panel.set_area_state(areas[0].id, "arm")
    
    # Get zones
    zones = await panel.get_zones()
    for zone in zones:
        print(f"Zone: {zone.name}, Open: {zone.is_open}")
    
    # Clean up
    await session.close()

asyncio.run(main())
```

### Using Context Manager

```python
import asyncio
from crow_security_ng import Session

async def main():
    async with Session("email@example.com", "password") as session:
        panel = await session.get_panel("AABBCCDDEEFF")
        areas = await panel.get_areas()
        print(areas)

asyncio.run(main())
```

### Advanced Client Usage

```python
import asyncio
from crow_security_ng import CrowClient

async def main():
    async with CrowClient(
        email="email@example.com",
        password="password",
        timeout=60,
        retry_count=5,
    ) as client:
        # Get all panels
        panels = await client.get_panels()
        
        # Work with a specific panel
        panel = await client.get_panel("AABBCCDDEEFF")
        
        # Control outputs
        outputs = await client.get_outputs(panel.mac)
        await client.set_output_state(panel.mac, outputs[0].id, True)
        
        # Get measurements (temperature, humidity, etc.)
        measurements = await client.get_measurements(panel.mac)
        for m in measurements:
            print(f"{m.name}: {m.value} {m.unit}")

asyncio.run(main())
```

### WebSocket Real-time Updates

```python
import asyncio
from crow_security_ng import Session

async def handle_message(msg: dict):
    print(f"Received: {msg}")

async def main():
    session = Session("email@example.com", "password")
    panel = await session.get_panel("AABBCCDDEEFF")
    
    # This will run indefinitely, receiving real-time updates
    await session.ws_connect(panel.mac, handle_message)

asyncio.run(main())
```

## API Reference

### Session

The `Session` class provides a simple interface compatible with the original `crow_security` library.

```python
session = Session(email, password)
panel = await session.get_panel(mac)
await session.close()
```

### CrowClient

The `CrowClient` class provides full access to all API features.

```python
client = CrowClient(
    email="...",
    password="...",
    api_base="https://api.crowcloud.com",  # optional
    timeout=30,  # optional
    retry_count=3,  # optional
)
```

### Models

#### Panel
```python
panel.mac          # MAC address
panel.name         # Panel name
panel.model        # Panel model
panel.firmware_version  # Firmware version
```

#### Area
```python
area.id            # Area ID
area.name          # Area name
area.state         # AreaState enum
area.is_armed      # True if armed
area.is_arming     # True if arming in progress
```

#### Zone
```python
zone.id            # Zone ID
zone.name          # Zone name
zone.state         # Zone state string
zone.zone_type     # Zone type
zone.is_open       # True if triggered/open
zone.battery       # Battery level (0-100)
zone.has_low_battery  # True if battery < 20%
```

#### Output
```python
output.id          # Output ID
output.name        # Output name
output.state       # True if on
output.output_type # Output type
```

#### Measurement
```python
measurement.id     # Measurement ID
measurement.name   # Measurement name
measurement.value  # Current value
measurement.unit   # Unit (°C, %, etc.)
measurement.measurement_type  # Type (temperature, humidity, etc.)
```

### Exceptions

```python
from crow_security_ng import (
    CrowError,           # Base exception
    AuthenticationError, # Invalid credentials
    ConnectionError,     # Connection failed
    ResponseError,       # API error response
    PanelNotFoundError,  # Panel not found
    RateLimitError,      # Rate limit exceeded
    TimeoutError,        # Request timeout
)
```

## Migrating from crow_security

This library is designed to be a drop-in replacement for `crow_security`. Simply change your import:

```python
# Before
import crow_security as crow
session = crow.Session(email, password)

# After
from crow_security_ng import Session
session = Session(email, password)
```

### Key improvements over crow_security

1. **Better exception handling** - Specific exception classes instead of generic `ResponseError`
2. **MAC address normalization** - No need to manually format MAC addresses
3. **Type hints** - Full type annotations for better IDE support
4. **Dataclass models** - Structured data models instead of raw dictionaries
5. **Resource cleanup** - Proper async context manager support
6. **Retry logic** - Automatic retries with configurable backoff
7. **Modern Python** - Uses Python 3.10+ features

## Home Assistant Integration

This library is designed to work with the Crow Shepherd Home Assistant integration. See the integration documentation for setup instructions.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Credits

- Inspired by the original [crow_security](https://pypi.org/project/crow-security/) library by Shprota
- Thanks to the Crow Group for the Shepherd alarm system
