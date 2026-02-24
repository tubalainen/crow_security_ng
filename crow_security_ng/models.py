"""Data models for the Crow Security NG library."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class AreaState(str, Enum):
    """Alarm area states as returned by the Crow Cloud API."""

    DISARMED = "disarmed"
    ARMED = "armed"
    STAY_ARMED = "stay_armed"
    ARM_IN_PROGRESS = "arm in progress"
    STAY_ARM_IN_PROGRESS = "stay arm in progress"
    TRIGGERED = "triggered"
    PENDING = "pending"

    @classmethod
    def from_api(cls, value: str) -> "AreaState":
        """Convert API state string to enum, defaulting to DISARMED."""
        value_lower = (value or "").lower()
        for state in cls:
            if state.value == value_lower:
                return state
        return cls.DISARMED


class AreaCommand(str, Enum):
    """Commands for changing area arm state."""

    ARM = "arm"
    STAY = "stay"
    DISARM = "disarm"


class ZoneState(str, Enum):
    """Zone state string values (kept for backwards compatibility)."""

    OK = "ok"
    OPEN = "open"
    TAMPER = "tamper"
    ALARM = "alarm"
    TROUBLE = "trouble"
    BYPASSED = "bypassed"
    LOW_BATTERY = "low_battery"


# ---------------------------------------------------------------------------
# Area
# ---------------------------------------------------------------------------

@dataclass
class Area:
    """Represents an alarm area/partition."""

    id: int
    name: str
    state: AreaState = AreaState.DISARMED
    exit_delay: int = 0
    stay_exit_delay: int = 0
    zone_alarm: bool = False
    zone24H_alarm: bool = False
    ready_to_arm: bool = False
    ready_to_stay: bool = False
    raw_data: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "Area":
        """Create Area from API response data."""
        area_id = data.get("id") or data.get("area_id") or 0
        state_str = data.get("state", "disarmed")
        return cls(
            id=int(area_id),
            name=data.get("name", f"Area {area_id}"),
            state=AreaState.from_api(state_str),
            exit_delay=data.get("exit_delay", 0) or 0,
            stay_exit_delay=data.get("stay_exit_delay", 0) or 0,
            zone_alarm=data.get("zone_alarm", False) or False,
            zone24H_alarm=data.get("zone24H_alarm", False) or False,
            ready_to_arm=data.get("ready_to_arm", False) or False,
            ready_to_stay=data.get("ready_to_stay", False) or False,
            raw_data=data,
        )

    @property
    def is_armed(self) -> bool:
        """True if area is fully or stay-armed."""
        return self.state in (AreaState.ARMED, AreaState.STAY_ARMED)

    @property
    def is_arming(self) -> bool:
        """True if area is in the process of arming."""
        return self.state in (AreaState.ARM_IN_PROGRESS, AreaState.STAY_ARM_IN_PROGRESS)


# ---------------------------------------------------------------------------
# Zone
# ---------------------------------------------------------------------------

@dataclass
class Zone:
    """Represents an alarm zone/sensor."""

    id: int
    name: str
    device_id: int = 0
    state: bool = False         # boolean — True means open/triggered
    bypass: bool = False
    battery_low: bool = False
    battery_voltage: float | None = None    # V  (raw API millivolts ÷ 1000; None if wired/absent)
    tamper_alarm: bool = False
    zone_type: int = 0          # numeric zone type (55 = smart cam)
    active: bool = False
    rssi: int | None = None
    raw_data: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "Zone":
        """Create Zone from API response data."""
        zone_id = data.get("id") or data.get("zone_id") or 0

        # state is a boolean in the API
        state_val = data.get("state", False)
        if isinstance(state_val, bool):
            state = state_val
        elif isinstance(state_val, int):
            state = bool(state_val)
        elif isinstance(state_val, str):
            state = state_val.lower() in ("true", "1", "open", "active", "alarm")
        else:
            state = False

        _batt = data.get("battery")
        return cls(
            id=int(zone_id),
            name=data.get("name", f"Zone {zone_id}"),
            device_id=int(data.get("device_id", 0) or 0),
            state=state,
            bypass=data.get("bypass", False) or False,
            battery_low=data.get("battery_low", False) or False,
            battery_voltage=float(_batt) / 1000.0 if _batt else None,
            tamper_alarm=data.get("tamper_alarm", False) or False,
            zone_type=int(data.get("zone_type", 0) or 0),
            active=data.get("active", False) or False,
            rssi=data.get("rssi"),
            raw_data=data,
        )

    @property
    def is_open(self) -> bool:
        """True if zone is open/triggered."""
        return self.state or self.active

    @property
    def has_low_battery(self) -> bool:
        """True if zone has a low battery condition."""
        return self.battery_low

    @property
    def is_camera(self) -> bool:
        """True if this zone is a smart-cam (zone_type == 55)."""
        return self.zone_type == 55


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

@dataclass
class Output:
    """Represents a controllable output."""

    id: int
    name: str
    device_id: int = 0
    state: bool = False
    tamper_alarm: bool = False
    battery_low: bool = False
    battery_voltage: float | None = None    # V  (raw API millivolts ÷ 1000; None if wired/absent)
    output_type: int | None = None
    rssi: int | None = None
    raw_data: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "Output":
        """Create Output from API response data."""
        output_id = data.get("id") or data.get("output_id") or 0

        state_val = data.get("state", False)
        if isinstance(state_val, bool):
            state = state_val
        elif isinstance(state_val, int):
            state = bool(state_val)
        elif isinstance(state_val, str):
            state = state_val.lower() in ("true", "1", "on", "active")
        else:
            state = False

        _batt = data.get("battery")
        return cls(
            id=int(output_id),
            name=data.get("name", f"Output {output_id}"),
            device_id=int(data.get("device_id", 0) or 0),
            state=state,
            tamper_alarm=data.get("tamper_alarm", False) or False,
            battery_low=data.get("battery_low", False) or False,
            battery_voltage=float(_batt) / 1000.0 if _batt else None,
            output_type=data.get("output_type") or data.get("type"),
            rssi=data.get("rssi"),
            raw_data=data,
        )


# ---------------------------------------------------------------------------
# Measurement
# ---------------------------------------------------------------------------

# dect_interface type IDs from InfoData spec
_DECT_HUMIDITY = 32532
_DECT_TEMPERATURE = 32533
_DECT_AIR_PRESSURE = 32535
_DECT_GAS_LEVEL = 61


def _parse_dt(value: Any) -> datetime | None:
    """Try to parse a datetime from various API formats."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value)
    if isinstance(value, str):
        for fmt in (
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
        ):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
    return None


@dataclass
class Measurement:
    """Represents a DECT sensor measurement (temperature, humidity, etc.).

    Values for temperature, humidity, and air_pressure are pre-divided by 1000
    as per the Crow InfoData specification (raw API values are integer milliUnits).
    """

    device_id: int
    device_type: str                    # "zone" or "output"
    dect_interface: int                 # 32532=humidity, 32533=temp, 32535=pressure, 61=gas
    panel_time: datetime | None = None
    temperature: float | None = None    # °C  (raw / 1000)
    humidity: float | None = None       # %RH (raw / 1000)
    air_pressure: float | None = None   # atm (raw / 1000)
    gas_value: int | None = None
    gas_level: int | None = None        # 0-4 scale
    amperage: int | None = None
    voltage: int | None = None
    energy: int | None = None
    instantaneous_power: int | None = None
    raw_data: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "Measurement":
        """Create Measurement from the dect/measurements/latest/by_zone/ API response."""
        device_id = int(data.get("device_id", 0) or 0)
        device_type = data.get("device_type", "zone")
        dect_interface = int(data.get("dect_interface", 0) or 0)
        panel_time = _parse_dt(data.get("panel_time"))

        def _divide(key: str) -> float | None:
            raw = data.get(key)
            if raw is None:
                return None
            try:
                return float(raw) / 1000.0
            except (TypeError, ValueError):
                return None

        return cls(
            device_id=device_id,
            device_type=device_type,
            dect_interface=dect_interface,
            panel_time=panel_time,
            temperature=_divide("temperature"),
            humidity=_divide("humidity"),
            air_pressure=_divide("air_pressure"),
            gas_value=data.get("gas_value"),
            gas_level=data.get("gas_level"),
            amperage=data.get("amperage"),
            voltage=data.get("voltage"),
            energy=data.get("energy"),
            instantaneous_power=data.get("instantaneous_power"),
            raw_data=data,
        )


# ---------------------------------------------------------------------------
# Picture
# ---------------------------------------------------------------------------

@dataclass
class Picture:
    """Represents a camera picture captured by a smart-cam zone."""

    id: int
    zone: int
    zone_name: str = ""
    url: str = ""
    key: str = ""
    pic_total: int = 1
    pic_index: int = 0
    picture_type: int = 0       # 0 = manual, 1 = alarm-triggered
    created: datetime | None = None
    panel_time: datetime | None = None
    raw_data: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "Picture":
        """Create Picture from API response data."""
        return cls(
            id=int(data.get("id", 0) or 0),
            zone=int(data.get("zone", 0) or 0),
            zone_name=data.get("zone_name", "") or "",
            url=data.get("url", "") or "",
            key=data.get("key", "") or "",
            pic_total=int(data.get("pic_total", 1) or 1),
            pic_index=int(data.get("pic_index", 0) or 0),
            picture_type=int(data.get("picture_type", 0) or 0),
            created=_parse_dt(data.get("created")),
            panel_time=_parse_dt(data.get("panel_time")),
            raw_data=data,
        )


# ---------------------------------------------------------------------------
# Event
# ---------------------------------------------------------------------------

@dataclass
class Event:
    """Represents a Crow alarm event received via WebSocket or event log."""

    id: int
    created: datetime | None = None
    panel_time: datetime | None = None
    zone: int | None = None
    area: int | None = None
    cid: int | None = None
    account: str | None = None
    groups: list[str] = field(default_factory=list)
    raw_data: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "Event":
        """Create Event from API/WebSocket payload."""
        return cls(
            id=int(data.get("id", 0) or 0),
            created=_parse_dt(data.get("created")),
            panel_time=_parse_dt(data.get("panel_time")),
            zone=data.get("zone"),
            area=data.get("area"),
            cid=data.get("cid"),
            account=data.get("account"),
            groups=list(data.get("groups", [])),
            raw_data=data,
        )


# ---------------------------------------------------------------------------
# Panel
# ---------------------------------------------------------------------------

@dataclass
class Panel:
    """Represents a Crow Shepherd alarm panel.

    IMPORTANT: Two different identifiers are used by the API:
    - ``mac``  — 12-char hex string, used for panel lookup (GET /panels/{mac}/)
      and WebSocket subscribe
    - ``id``   — numeric database integer, used for ALL sub-resource URLs
      (areas, zones, outputs, measurements, pictures)
    """

    mac: str
    id: int
    name: str
    remote_access_password: str | None = None   # → X-Crow-CP-Remote header
    user_code: str | None = None                # → X-Crow-CP-User header
    state: str | None = None
    state_full: int | None = None
    firmware_version: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    raw_data: dict[str, Any] = field(default_factory=dict)
    _client: Any = field(default=None, repr=False)

    @classmethod
    def from_api(cls, data: dict[str, Any], client: Any = None) -> "Panel":
        """Create Panel from API response data."""
        return cls(
            mac=data.get("mac", ""),
            id=int(data.get("id") or data.get("panel_id") or 0),
            name=data.get("name", ""),
            remote_access_password=data.get("remote_access_password"),
            user_code=data.get("user_code"),
            state=data.get("state"),
            state_full=data.get("state_full"),
            firmware_version=data.get("version"),
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
            raw_data=data,
            _client=client,
        )

    # ------------------------------------------------------------------
    # Delegation helpers — all use self.id (numeric) for sub-resource URLs
    # ------------------------------------------------------------------

    def _require_client(self) -> Any:
        if self._client is None:
            raise RuntimeError("Panel is not connected to a CrowClient instance")
        return self._client

    async def get_areas(self) -> list[Area]:
        """Fetch all alarm areas for this panel."""
        return await self._require_client().get_areas(self.id)

    async def get_area(self, area_id: int) -> Area:
        """Fetch a single area by ID."""
        return await self._require_client().get_area(self.id, area_id)

    async def set_area_state(
        self, area_id: int, state: str | AreaCommand, force: bool = False
    ) -> Area:
        """Arm, stay-arm, or disarm an area."""
        if isinstance(state, AreaCommand):
            state = state.value
        return await self._require_client().set_area_state(
            self.id,
            area_id,
            state,
            force=force,
            remote_password=self.remote_access_password,
            user_code=self.user_code,
        )

    async def get_zones(self) -> list[Zone]:
        """Fetch all zones for this panel."""
        return await self._require_client().get_zones(self.id)

    async def get_zone(self, zone_id: int) -> Zone:
        """Fetch a single zone by ID."""
        return await self._require_client().get_zone(self.id, zone_id)

    async def set_zone_bypass(self, zone_id: int, bypass: bool) -> Zone:
        """Bypass or un-bypass a zone."""
        return await self._require_client().set_zone_bypass(
            self.id,
            zone_id,
            bypass,
            remote_password=self.remote_access_password,
            user_code=self.user_code,
        )

    async def get_outputs(self) -> list[Output]:
        """Fetch all outputs for this panel."""
        return await self._require_client().get_outputs(self.id)

    async def get_output(self, output_id: int) -> Output:
        """Fetch a single output by ID."""
        return await self._require_client().get_output(self.id, output_id)

    async def set_output_state(self, output_id: int, state: bool) -> Output:
        """Turn an output on or off."""
        return await self._require_client().set_output_state(
            self.id,
            output_id,
            state,
            remote_password=self.remote_access_password,
            user_code=self.user_code,
        )

    async def get_measurements(self) -> list[Measurement]:
        """Fetch the latest DECT sensor measurements for this panel."""
        return await self._require_client().get_measurements(self.id)

    async def get_zone_pictures(
        self, zone_id: int, page_size: int = 10, page: int = 1
    ) -> list[Picture]:
        """Fetch pictures captured by a smart-cam zone."""
        return await self._require_client().get_zone_pictures(
            self.id, zone_id, page_size=page_size, page=page
        )

    async def capture_picture(self, zone_id: int) -> None:
        """Trigger a new picture capture on a smart-cam zone."""
        return await self._require_client().capture_picture(
            self.id,
            zone_id,
            remote_password=self.remote_access_password,
            user_code=self.user_code,
        )

    async def get_picture_bytes(self, picture: "Picture") -> bytes:
        """Fetch a picture as raw JPEG bytes (for HA camera entities)."""
        return await self._require_client().get_picture_bytes(picture)
