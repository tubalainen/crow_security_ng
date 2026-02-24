# Crow Security NG

A modern, async Python library for the Crow Cloud API — Next Generation.

Provides a clean, type-hinted interface for interacting with Crow Shepherd alarm panels
through the Crow Cloud API at `api.crowcloud.xyz`.

## Features

- **Fully async** — built on `aiohttp` for efficient async I/O
- **Type hints** — complete type annotations for better IDE support
- **Modern Python** — requires Python 3.10+, uses dataclasses and enums
- **Proper error handling** — dedicated exception classes for different error types
- **MAC address normalization** — accepts any MAC format (with/without separators)
- **WebSocket support** — real-time updates from your alarm panel
- **Backwards compatible** — provides a `Session` class compatible with the original `crow_security`
- **Token refresh** — automatic OAuth2 token refresh with fallback to full re-login
- **Context managers** — proper resource cleanup with async context managers

## Installation

```bash
pip install crow_security_ng
```

## Authentication

The library uses **OAuth2 Resource Owner Password Credentials** (ROPC) against
`https://api.crowcloud.xyz/o/token/`. Application credentials (`CLIENT_ID` and
`CLIENT_SECRET`) are embedded in the library — you only need your Crow Cloud
email and password.

The access token is sent as `Authorization: Bearer {token}` on every request.
The library refreshes expired tokens automatically.

## Quick Start

### Basic Usage

```python
import asyncio
from crow_security_ng import Session

async def main():
    async with Session("your-email@example.com", "your-password") as session:
        panel = await session.get_panel("AABBCCDDEEFF")
        print(f"Panel: {panel.name}  (id={panel.id})")

        areas = await panel.get_areas()
        for area in areas:
            print(f"  Area: {area.name}, State: {area.state.value}")

        zones = await panel.get_zones()
        for zone in zones:
            print(f"  Zone: {zone.name}, Open: {zone.is_open}")

asyncio.run(main())
```

### Advanced Client Usage

```python
import asyncio
from crow_security_ng import CrowClient

async def main():
    async with CrowClient(email="email@example.com", password="password") as client:
        panels = await client.get_panels()
        panel = panels[0]
        print(f"Panel: {panel.name}, id={panel.id}, mac={panel.mac}")

        # Sub-resources use the numeric panel.id — not the MAC
        areas = await client.get_areas(panel.id)
        zones = await client.get_zones(panel.id)
        outputs = await client.get_outputs(panel.id)

        # Arm an area (sends X-Crow-CP-Remote header automatically via Panel.set_area_state)
        area = await panel.set_area_state(areas[0].id, "arm")
        print(f"Armed: {area.is_armed}")

        # Control an output
        await client.set_output_state(
            panel.id, outputs[0].id, True,
            remote_password=panel.remote_access_password,
        )

asyncio.run(main())
```

### WebSocket Real-time Updates

```python
import asyncio
from crow_security_ng import Session

async def handle_message(msg: dict):
    print(f"Event: {msg}")

async def main():
    async with Session("email@example.com", "password") as session:
        panel = await session.get_panel("AABBCCDDEEFF")
        # Runs indefinitely, calling handle_message for every event
        await session.ws_connect(panel.mac, handle_message)

asyncio.run(main())
```

## API Reference

### Session

Simple interface compatible with the original `crow_security` library.

```python
session = Session(email, password)
panel   = await session.get_panel(mac)   # MAC in any format
panels  = await session.get_panels()
await session.ws_connect(mac, callback)
await session.close()
```

### CrowClient

Full access to all API features.

```python
client = CrowClient(
    email="...",
    password="...",
    timeout=30,       # optional, default 30 s
)
```

All sub-resource methods take the **numeric panel ID** (not MAC):

```python
await client.get_areas(panel_id)
await client.get_area(panel_id, area_id)
await client.set_area_state(panel_id, area_id, state, force=False,
                             remote_password=..., user_code=...)

await client.get_zones(panel_id)
await client.get_zone(panel_id, zone_id)
await client.set_zone_bypass(panel_id, zone_id, bypass,
                              remote_password=..., user_code=...)

await client.get_outputs(panel_id)
await client.get_output(panel_id, output_id)
await client.set_output_state(panel_id, output_id, state,
                               remote_password=..., user_code=...)

await client.get_measurements(panel_id)
await client.get_zone_pictures(panel_id, zone_id)
await client.capture_picture(panel_id, zone_id, remote_password=..., user_code=...)
await client.download_picture(picture, "/path/to/file.jpg")
```

### Models

#### Panel
```python
panel.mac                      # 12-char hex MAC (lookup + WebSocket subscribe)
panel.id                       # numeric database ID (sub-resource URLs)
panel.name
panel.remote_access_password   # → X-Crow-CP-Remote header
panel.user_code                # → X-Crow-CP-User header (may be None)
panel.firmware_version
```

Panel also exposes convenience delegation methods:
```python
areas = await panel.get_areas()
await panel.set_area_state(area_id, "arm")
zones = await panel.get_zones()
await panel.set_zone_bypass(zone_id, True)
outputs = await panel.get_outputs()
await panel.set_output_state(output_id, True)
measurements = await panel.get_measurements()
pictures = await panel.get_zone_pictures(zone_id)
await panel.capture_picture(zone_id)
```

#### Area
```python
area.id
area.name
area.state          # AreaState enum
area.is_armed       # True if ARMED or STAY_ARMED
area.is_arming      # True if ARM_IN_PROGRESS or STAY_ARM_IN_PROGRESS
area.exit_delay
area.ready_to_arm
area.zone_alarm
```

#### Zone
```python
zone.id
zone.name
zone.state          # bool — True = open/triggered
zone.bypass         # True if bypassed
zone.battery_low    # True if low battery
zone.tamper_alarm
zone.zone_type      # int (55 = smart cam)
zone.is_open        # True if state or active
zone.has_low_battery
```

#### Output
```python
output.id
output.name
output.state        # bool — True = on
output.tamper_alarm
output.battery_low
```

#### Measurement
```python
measurement.device_id
measurement.dect_interface   # 32533=temp, 32532=humidity, 32535=pressure, 61=gas
measurement.temperature      # °C  (raw API value ÷ 1000)
measurement.humidity         # %RH (raw API value ÷ 1000)
measurement.air_pressure     # atm (raw API value ÷ 1000)
measurement.gas_level        # 0-4 scale
```

#### Picture
```python
picture.id
picture.zone          # zone ID
picture.zone_name
picture.url           # pre-signed download URL (no auth needed)
picture.picture_type  # 0 = manual, 1 = alarm-triggered
picture.created       # datetime
```

### Exceptions

```python
from crow_security_ng import (
    CrowError,           # Base exception
    AuthenticationError, # OAuth2 login failed / credentials rejected
    ConnectionError,     # Network-level failure
    ResponseError,       # Unexpected HTTP error (status_code, response_text attrs)
    PanelNotFoundError,  # Panel MAC not found (mac attr)
    RateLimitError,      # HTTP 429 (retry_after attr)
    TimeoutError,        # Request timed out
    InvalidMacError,     # Malformed MAC address (mac attr)
    WebSocketError,      # WebSocket auth or subscribe failure
)
```

## Migrating from crow_security

Change your import — everything else stays the same:

```python
# Before
import crow_security as crow
session = crow.Session(email, password)

# After
from crow_security_ng import Session
session = Session(email, password)
```

### Key differences

| | crow_security 0.3.0 | crow_security_ng |
|---|---|---|
| Return types | Raw `dict` | Typed dataclass objects |
| `panel.id` | Present | Present — **used for all sub-resource URLs** |
| `Zone.state` | Mixed | `bool` (True = open) |
| Exceptions | `CrowLoginError`, `ResponseError` | Richer hierarchy |
| Type hints | None | Full Python 3.10+ annotations |
| Token refresh | Manual | Automatic on 401 |
| Context manager | Partial (bug in `__aexit__`) | Full async context manager |
| Python version | 3.2+ | 3.10+ |

Backward-compatibility aliases are provided so existing exception handlers continue to work:
- `CrowSecurityError` → `CrowError`
- `CrowSecurityAuthenticationError` → `AuthenticationError`
- `CrowSecurityConnectionError` → `ConnectionError`
- `CrowSecurityClient` → `CrowClient`

## Home Assistant Integration

This library is designed to work with the Crow Shepherd Home Assistant integration.

## License

MIT License — see [LICENSE](LICENSE) for details.

## Credits

- Inspired by the original [crow_security](https://pypi.org/project/crow-security/) library by Shprota
- Thanks to the Crow Group for the Shepherd alarm system
