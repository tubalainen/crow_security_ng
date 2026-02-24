"""Tests for data models."""
from datetime import datetime

import pytest

from crow_security_ng.models import (
    Area,
    AreaCommand,
    AreaState,
    Event,
    Measurement,
    Output,
    Panel,
    Picture,
    Zone,
    ZoneState,
)


# ---------------------------------------------------------------------------
# AreaState
# ---------------------------------------------------------------------------

class TestAreaState:
    def test_from_api_disarmed(self):
        assert AreaState.from_api("disarmed") == AreaState.DISARMED
        assert AreaState.from_api("Disarmed") == AreaState.DISARMED
        assert AreaState.from_api("DISARMED") == AreaState.DISARMED

    def test_from_api_armed(self):
        assert AreaState.from_api("armed") == AreaState.ARMED

    def test_from_api_stay_armed(self):
        assert AreaState.from_api("stay_armed") == AreaState.STAY_ARMED

    def test_from_api_arm_in_progress(self):
        assert AreaState.from_api("arm in progress") == AreaState.ARM_IN_PROGRESS

    def test_from_api_unknown_defaults_to_disarmed(self):
        assert AreaState.from_api("unknown") == AreaState.DISARMED
        assert AreaState.from_api("") == AreaState.DISARMED
        assert AreaState.from_api(None) == AreaState.DISARMED


# ---------------------------------------------------------------------------
# Zone  (state is boolean in the real API)
# ---------------------------------------------------------------------------

class TestZone:
    def test_from_api_basic(self):
        data = {"id": 1, "name": "Front Door", "state": False, "zone_type": 4}
        zone = Zone.from_api(data)

        assert zone.id == 1
        assert zone.name == "Front Door"
        assert zone.state is False
        assert zone.zone_type == 4
        assert zone.is_open is False

    def test_from_api_open_zone(self):
        data = {"id": 2, "name": "Window", "state": True}
        zone = Zone.from_api(data)
        assert zone.state is True
        assert zone.is_open is True

    def test_from_api_state_int(self):
        zone = Zone.from_api({"id": 3, "name": "T", "state": 1})
        assert zone.state is True
        zone2 = Zone.from_api({"id": 4, "name": "T", "state": 0})
        assert zone2.state is False

    def test_from_api_state_string(self):
        zone = Zone.from_api({"id": 5, "name": "T", "state": "true"})
        assert zone.state is True
        zone2 = Zone.from_api({"id": 6, "name": "T", "state": "false"})
        assert zone2.state is False

    def test_from_api_bypass_and_battery(self):
        data = {"id": 7, "name": "PIR", "bypass": True, "battery_low": True}
        zone = Zone.from_api(data)
        assert zone.bypass is True
        assert zone.battery_low is True
        assert zone.has_low_battery is True

    def test_is_open_via_active(self):
        zone = Zone(id=8, name="T", state=False, active=True)
        assert zone.is_open is True

    def test_raw_data_preserved(self):
        data = {"id": 9, "name": "X", "custom_field": "value"}
        zone = Zone.from_api(data)
        assert zone.raw_data["custom_field"] == "value"


# ---------------------------------------------------------------------------
# Area
# ---------------------------------------------------------------------------

class TestArea:
    def test_from_api_basic(self):
        data = {"id": 1, "name": "Home", "state": "disarmed"}
        area = Area.from_api(data)

        assert area.id == 1
        assert area.name == "Home"
        assert area.state == AreaState.DISARMED
        assert area.is_armed is False

    def test_from_api_armed(self):
        data = {"id": 2, "name": "Home", "state": "armed"}
        area = Area.from_api(data)
        assert area.state == AreaState.ARMED
        assert area.is_armed is True

    def test_is_arming(self):
        area = Area(id=3, name="T", state=AreaState.ARM_IN_PROGRESS)
        assert area.is_arming is True
        area2 = Area(id=4, name="T", state=AreaState.ARMED)
        assert area2.is_arming is False

    def test_stay_armed_is_armed(self):
        area = Area(id=5, name="T", state=AreaState.STAY_ARMED)
        assert area.is_armed is True

    def test_from_api_extended_fields(self):
        data = {
            "id": 6,
            "name": "Test",
            "state": "armed",
            "exit_delay": 30,
            "ready_to_arm": True,
            "zone_alarm": False,
        }
        area = Area.from_api(data)
        assert area.exit_delay == 30
        assert area.ready_to_arm is True
        assert area.zone_alarm is False


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

class TestOutput:
    def test_from_api_basic(self):
        data = {"id": 1, "name": "Siren", "state": True}
        output = Output.from_api(data)

        assert output.id == 1
        assert output.name == "Siren"
        assert output.state is True

    def test_state_from_int(self):
        assert Output.from_api({"id": 1, "name": "T", "state": 1}).state is True
        assert Output.from_api({"id": 2, "name": "T", "state": 0}).state is False

    def test_state_from_string(self):
        assert Output.from_api({"id": 1, "name": "T", "state": "on"}).state is True
        assert Output.from_api({"id": 2, "name": "T", "state": "active"}).state is True
        assert Output.from_api({"id": 3, "name": "T", "state": "false"}).state is False

    def test_default_state_false(self):
        output = Output.from_api({"id": 4, "name": "T"})
        assert output.state is False


# ---------------------------------------------------------------------------
# Measurement
# ---------------------------------------------------------------------------

class TestMeasurement:
    def test_from_api_temperature(self):
        data = {
            "device_id": 101,
            "device_type": "zone",
            "dect_interface": 32533,
            "temperature": 22500,   # raw millidegrees → 22.5 °C
        }
        m = Measurement.from_api(data)

        assert m.device_id == 101
        assert m.device_type == "zone"
        assert m.dect_interface == 32533
        assert m.temperature == pytest.approx(22.5)

    def test_from_api_humidity(self):
        data = {
            "device_id": 102,
            "device_type": "zone",
            "dect_interface": 32532,
            "humidity": 55000,   # raw → 55.0 %RH
        }
        m = Measurement.from_api(data)
        assert m.humidity == pytest.approx(55.0)

    def test_from_api_none_fields(self):
        data = {"device_id": 103, "device_type": "zone", "dect_interface": 0}
        m = Measurement.from_api(data)
        assert m.temperature is None
        assert m.humidity is None
        assert m.air_pressure is None


# ---------------------------------------------------------------------------
# Picture
# ---------------------------------------------------------------------------

class TestPicture:
    def test_from_api_basic(self):
        data = {
            "id": 1,
            "zone": 5,
            "zone_name": "Front Cam",
            "url": "https://example.com/img.jpg",
            "picture_type": 0,
        }
        pic = Picture.from_api(data)

        assert pic.id == 1
        assert pic.zone == 5
        assert pic.zone_name == "Front Cam"
        assert pic.url == "https://example.com/img.jpg"
        assert pic.picture_type == 0

    def test_defaults(self):
        pic = Picture.from_api({"id": 2, "zone": 1})
        assert pic.url == ""
        assert pic.key == ""
        assert pic.pic_total == 1
        assert pic.created is None


# ---------------------------------------------------------------------------
# Event
# ---------------------------------------------------------------------------

class TestEvent:
    def test_from_api_basic(self):
        data = {"id": 1, "cid": 130, "zone": 3, "area": 1, "account": "1234"}
        event = Event.from_api(data)

        assert event.id == 1
        assert event.cid == 130
        assert event.zone == 3
        assert event.area == 1
        assert event.account == "1234"

    def test_groups_default_empty(self):
        event = Event.from_api({"id": 2})
        assert event.groups == []

    def test_groups_populated(self):
        event = Event.from_api({"id": 3, "groups": ["g1", "g2"]})
        assert event.groups == ["g1", "g2"]


# ---------------------------------------------------------------------------
# Panel
# ---------------------------------------------------------------------------

class TestPanel:
    def test_from_api_basic(self):
        data = {
            "id": 42,
            "mac": "0013a1250a45",
            "name": "My Alarm",
            "remote_access_password": "secret",
        }
        panel = Panel.from_api(data)

        assert panel.id == 42
        assert panel.mac == "0013a1250a45"
        assert panel.name == "My Alarm"
        assert panel.remote_access_password == "secret"

    def test_from_api_firmware(self):
        data = {"id": 1, "mac": "aabbccddeeff", "name": "T", "version": "3.0.1"}
        panel = Panel.from_api(data)
        assert panel.firmware_version == "3.0.1"

    def test_require_client_raises(self):
        panel = Panel(mac="aabbccddeeff", id=1, name="T")
        with pytest.raises(RuntimeError, match="CrowClient"):
            panel._require_client()

    def test_raw_data_preserved(self):
        data = {"id": 5, "mac": "aabbccddeeff", "name": "T", "extra": "value"}
        panel = Panel.from_api(data)
        assert panel.raw_data["extra"] == "value"
