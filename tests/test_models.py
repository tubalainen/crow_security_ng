"""Tests for data models."""
import pytest

from crow_security_ng.models import (
    Area,
    AreaState,
    Measurement,
    Output,
    Zone,
)


class TestAreaState:
    """Tests for AreaState enum."""
    
    def test_from_api_disarmed(self):
        """Test parsing disarmed state."""
        assert AreaState.from_api("disarmed") == AreaState.DISARMED
        assert AreaState.from_api("Disarmed") == AreaState.DISARMED
        assert AreaState.from_api("DISARMED") == AreaState.DISARMED
    
    def test_from_api_armed(self):
        """Test parsing armed state."""
        assert AreaState.from_api("armed") == AreaState.ARMED
    
    def test_from_api_stay_armed(self):
        """Test parsing stay armed state."""
        assert AreaState.from_api("stay_armed") == AreaState.STAY_ARMED
    
    def test_from_api_unknown(self):
        """Test parsing unknown state defaults to disarmed."""
        assert AreaState.from_api("unknown") == AreaState.DISARMED
        assert AreaState.from_api("") == AreaState.DISARMED
        assert AreaState.from_api(None) == AreaState.DISARMED


class TestZone:
    """Tests for Zone model."""
    
    def test_from_api_basic(self):
        """Test creating zone from basic API data."""
        data = {
            "id": "1",
            "name": "Front Door",
            "state": "ok",
            "type": "door",
        }
        zone = Zone.from_api(data)
        
        assert zone.id == "1"
        assert zone.name == "Front Door"
        assert zone.state == "ok"
        assert zone.zone_type == "door"
        assert zone.is_open is False
    
    def test_from_api_with_device_id(self):
        """Test creating zone with nested _id."""
        data = {
            "_id": {"device_id": "123"},
            "name": "Motion Sensor",
            "status": "open",
        }
        zone = Zone.from_api(data)
        
        assert zone.id == "123"
        assert zone.is_open is True
    
    def test_is_open_various_states(self):
        """Test is_open property with various states."""
        states_open = ["open", "alarm", "triggered", "violated", "1", "active"]
        states_closed = ["ok", "closed", "0", "inactive", "normal"]
        
        for state in states_open:
            zone = Zone(id="1", name="Test", state=state)
            assert zone.is_open is True, f"State '{state}' should be open"
        
        for state in states_closed:
            zone = Zone(id="1", name="Test", state=state)
            assert zone.is_open is False, f"State '{state}' should be closed"
    
    def test_has_low_battery(self):
        """Test has_low_battery property."""
        zone_low = Zone(id="1", name="Test", battery=15)
        zone_ok = Zone(id="2", name="Test", battery=80)
        zone_none = Zone(id="3", name="Test", battery=None)
        
        assert zone_low.has_low_battery is True
        assert zone_ok.has_low_battery is False
        assert zone_none.has_low_battery is False


class TestArea:
    """Tests for Area model."""
    
    def test_from_api_basic(self):
        """Test creating area from basic API data."""
        data = {
            "id": "area1",
            "name": "Home",
            "state": "disarmed",
        }
        area = Area.from_api(data)
        
        assert area.id == "area1"
        assert area.name == "Home"
        assert area.state == AreaState.DISARMED
        assert area.is_armed is False
    
    def test_is_armed(self):
        """Test is_armed property."""
        area_armed = Area(id="1", name="Test", state=AreaState.ARMED)
        area_stay = Area(id="2", name="Test", state=AreaState.STAY_ARMED)
        area_disarmed = Area(id="3", name="Test", state=AreaState.DISARMED)
        
        assert area_armed.is_armed is True
        assert area_stay.is_armed is True
        assert area_disarmed.is_armed is False
    
    def test_is_arming(self):
        """Test is_arming property."""
        area_arming = Area(id="1", name="Test", state=AreaState.ARM_IN_PROGRESS)
        area_armed = Area(id="2", name="Test", state=AreaState.ARMED)
        
        assert area_arming.is_arming is True
        assert area_armed.is_arming is False


class TestOutput:
    """Tests for Output model."""
    
    def test_from_api_basic(self):
        """Test creating output from basic API data."""
        data = {
            "id": "out1",
            "name": "Siren",
            "state": True,
            "type": "alarm",
        }
        output = Output.from_api(data)
        
        assert output.id == "out1"
        assert output.name == "Siren"
        assert output.state is True
        assert output.output_type == "alarm"
    
    def test_state_parsing(self):
        """Test parsing various state formats."""
        # Boolean
        assert Output.from_api({"id": "1", "name": "Test", "state": True}).state is True
        assert Output.from_api({"id": "1", "name": "Test", "state": False}).state is False
        
        # Integer
        assert Output.from_api({"id": "1", "name": "Test", "state": 1}).state is True
        assert Output.from_api({"id": "1", "name": "Test", "state": 0}).state is False
        
        # String
        assert Output.from_api({"id": "1", "name": "Test", "state": "on"}).state is True
        assert Output.from_api({"id": "1", "name": "Test", "state": "off"}).state is False
        assert Output.from_api({"id": "1", "name": "Test", "state": "active"}).state is True


class TestMeasurement:
    """Tests for Measurement model."""
    
    def test_from_api_basic(self):
        """Test creating measurement from basic API data."""
        data = {
            "id": "temp1",
            "name": "Living Room Temperature",
            "value": 22.5,
            "unit": "°C",
            "type": "temperature",
        }
        measurement = Measurement.from_api(data)
        
        assert measurement.id == "temp1"
        assert measurement.name == "Living Room Temperature"
        assert measurement.value == 22.5
        assert measurement.unit == "°C"
        assert measurement.measurement_type == "temperature"
    
    def test_value_conversion(self):
        """Test value conversion to number."""
        # Numeric string
        m1 = Measurement.from_api({"id": "1", "name": "Test", "value": "25.5"})
        assert m1.value == 25.5
        
        # Integer
        m2 = Measurement.from_api({"id": "2", "name": "Test", "value": 100})
        assert m2.value == 100.0
        
        # Non-numeric string
        m3 = Measurement.from_api({"id": "3", "name": "Test", "value": "unknown"})
        assert m3.value == "unknown"
        
        # None
        m4 = Measurement.from_api({"id": "4", "name": "Test"})
        assert m4.value is None
