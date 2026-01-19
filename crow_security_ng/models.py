"""Data models for the Crow Security NG library."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class AreaState(str, Enum):
    """Alarm area states."""
    DISARMED = "disarmed"
    ARMED = "armed"
    STAY_ARMED = "stay_armed"
    ARM_IN_PROGRESS = "arm in progress"
    STAY_ARM_IN_PROGRESS = "stay arm in progress"
    TRIGGERED = "triggered"
    PENDING = "pending"
    
    @classmethod
    def from_api(cls, value: str) -> "AreaState":
        """Convert API state string to enum."""
        value_lower = value.lower() if value else ""
        for state in cls:
            if state.value == value_lower:
                return state
        return cls.DISARMED


class AreaCommand(str, Enum):
    """Commands for changing area state."""
    ARM = "arm"
    STAY = "stay"
    DISARM = "disarm"


class ZoneState(str, Enum):
    """Zone states."""
    OK = "ok"
    OPEN = "open"
    TAMPER = "tamper"
    ALARM = "alarm"
    TROUBLE = "trouble"
    BYPASSED = "bypassed"
    LOW_BATTERY = "low_battery"


@dataclass
class Zone:
    """Represents an alarm zone/sensor."""
    
    id: str
    name: str
    state: str = "ok"
    zone_type: str = "generic"
    bypassed: bool = False
    battery: int | None = None
    signal_strength: int | None = None
    tamper: bool = False
    raw_data: dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "Zone":
        """Create Zone from API response data."""
        zone_id = data.get("id") or data.get("_id", {}).get("device_id") or str(data.get("device_id", ""))
        return cls(
            id=str(zone_id),
            name=data.get("name", f"Zone {zone_id}"),
            state=data.get("state", data.get("status", "ok")),
            zone_type=data.get("type", data.get("zone_type", "generic")),
            bypassed=data.get("bypassed", data.get("bypass", False)),
            battery=data.get("battery", data.get("batteryLevel")),
            signal_strength=data.get("signal", data.get("rssi")),
            tamper=data.get("tamper", False),
            raw_data=data,
        )
    
    @property
    def is_open(self) -> bool:
        """Check if zone is open/triggered."""
        return self.state.lower() in ("open", "alarm", "triggered", "violated", "1", "active")
    
    @property
    def has_low_battery(self) -> bool:
        """Check if zone has low battery."""
        if self.battery is not None:
            return self.battery < 20
        return False


@dataclass
class Area:
    """Represents an alarm area/partition."""
    
    id: str
    name: str
    state: AreaState = AreaState.DISARMED
    raw_data: dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "Area":
        """Create Area from API response data."""
        area_id = data.get("id") or data.get("_id", {}).get("device_id") or str(data.get("area_id", ""))
        state_str = data.get("state", data.get("status", "disarmed"))
        return cls(
            id=str(area_id),
            name=data.get("name", f"Area {area_id}"),
            state=AreaState.from_api(state_str),
            raw_data=data,
        )
    
    @property
    def is_armed(self) -> bool:
        """Check if area is armed (any mode)."""
        return self.state in (AreaState.ARMED, AreaState.STAY_ARMED)
    
    @property
    def is_arming(self) -> bool:
        """Check if area is in the process of arming."""
        return self.state in (AreaState.ARM_IN_PROGRESS, AreaState.STAY_ARM_IN_PROGRESS)


@dataclass
class Output:
    """Represents a controllable output."""
    
    id: str
    name: str
    state: bool = False
    output_type: str | None = None
    raw_data: dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "Output":
        """Create Output from API response data."""
        output_id = data.get("id") or data.get("_id", {}).get("device_id") or str(data.get("output_id", ""))
        
        # Parse state from various formats
        state_val = data.get("state", data.get("status", False))
        if isinstance(state_val, bool):
            state = state_val
        elif isinstance(state_val, int):
            state = state_val == 1
        elif isinstance(state_val, str):
            state = state_val.lower() in ("on", "1", "true", "active", "activated")
        else:
            state = False
            
        return cls(
            id=str(output_id),
            name=data.get("name", f"Output {output_id}"),
            state=state,
            output_type=data.get("type", data.get("outputType")),
            raw_data=data,
        )


@dataclass
class Measurement:
    """Represents a sensor measurement (temperature, humidity, etc.)."""
    
    id: str
    name: str
    value: float | int | str | None = None
    unit: str | None = None
    measurement_type: str | None = None
    zone_id: str | None = None
    raw_data: dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "Measurement":
        """Create Measurement from API response data."""
        measurement_id = data.get("id") or data.get("_id", {}).get("device_id") or str(data.get("measurement_id", ""))
        
        # Try to convert value to number
        raw_value = data.get("value", data.get("currentValue"))
        if raw_value is not None:
            try:
                value: float | int | str | None = float(raw_value)
            except (ValueError, TypeError):
                value = str(raw_value)
        else:
            value = None
            
        return cls(
            id=str(measurement_id),
            name=data.get("name", f"Measurement {measurement_id}"),
            value=value,
            unit=data.get("unit"),
            measurement_type=data.get("type"),
            zone_id=data.get("zoneId", data.get("zone_id")),
            raw_data=data,
        )


@dataclass
class Event:
    """Represents an alarm event."""
    
    id: str
    event_type: str
    description: str
    timestamp: datetime | None = None
    zone_id: str | None = None
    zone_name: str | None = None
    user_id: str | None = None
    raw_data: dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "Event":
        """Create Event from API response data."""
        event_id = data.get("id") or data.get("_id") or ""
        
        # Parse timestamp
        ts_raw = data.get("timestamp", data.get("time", data.get("date")))
        timestamp = None
        if ts_raw:
            if isinstance(ts_raw, (int, float)):
                timestamp = datetime.fromtimestamp(ts_raw)
            elif isinstance(ts_raw, str):
                for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]:
                    try:
                        timestamp = datetime.strptime(ts_raw[:len(fmt.replace("%", ""))], fmt)
                        break
                    except ValueError:
                        continue
        
        return cls(
            id=str(event_id),
            event_type=data.get("type", data.get("eventType", "unknown")),
            description=data.get("description", data.get("message", "")),
            timestamp=timestamp,
            zone_id=data.get("zoneId", data.get("zone_id")),
            zone_name=data.get("zoneName", data.get("zone_name")),
            user_id=data.get("userId", data.get("user_id", data.get("user"))),
            raw_data=data,
        )


@dataclass
class Panel:
    """Represents a Crow alarm panel."""
    
    mac: str
    name: str
    model: str | None = None
    firmware_version: str | None = None
    raw_data: dict[str, Any] = field(default_factory=dict)
    
    # These will be populated by the client
    _client: Any = field(default=None, repr=False)
    
    @classmethod
    def from_api(cls, data: dict[str, Any], mac: str, client: Any = None) -> "Panel":
        """Create Panel from API response data."""
        return cls(
            mac=mac,
            name=data.get("name", data.get("panelName", f"Panel {mac[-6:]}")),
            model=data.get("model", data.get("panelModel")),
            firmware_version=data.get("firmwareVersion", data.get("firmware_version")),
            raw_data=data,
            _client=client,
        )
    
    async def get_areas(self) -> list[Area]:
        """Get all areas/partitions for this panel."""
        if not self._client:
            raise RuntimeError("Panel not connected to client")
        return await self._client.get_areas(self.mac)
    
    async def get_area(self, area_id: str) -> Area | None:
        """Get a specific area by ID."""
        if not self._client:
            raise RuntimeError("Panel not connected to client")
        return await self._client.get_area(self.mac, area_id)
    
    async def set_area_state(self, area_id: str, command: str | AreaCommand) -> Area | None:
        """Set the arm state of an area."""
        if not self._client:
            raise RuntimeError("Panel not connected to client")
        if isinstance(command, AreaCommand):
            command = command.value
        return await self._client.set_area_state(self.mac, area_id, command)
    
    async def get_zones(self) -> list[Zone]:
        """Get all zones for this panel."""
        if not self._client:
            raise RuntimeError("Panel not connected to client")
        return await self._client.get_zones(self.mac)
    
    async def get_outputs(self) -> list[Output]:
        """Get all outputs for this panel."""
        if not self._client:
            raise RuntimeError("Panel not connected to client")
        return await self._client.get_outputs(self.mac)
    
    async def set_output_state(self, output_id: str, state: bool) -> bool:
        """Set the state of an output."""
        if not self._client:
            raise RuntimeError("Panel not connected to client")
        return await self._client.set_output_state(self.mac, output_id, state)
    
    async def get_measurements(self) -> list[Measurement]:
        """Get all measurements for this panel."""
        if not self._client:
            raise RuntimeError("Panel not connected to client")
        return await self._client.get_measurements(self.mac)
    
    async def capture_cam_image(self, zone_id: str) -> bytes | None:
        """Capture an image from a camera zone."""
        if not self._client:
            raise RuntimeError("Panel not connected to client")
        return await self._client.capture_cam_image(self.mac, zone_id)
