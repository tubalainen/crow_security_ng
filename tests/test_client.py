"""Tests for CrowClient using mocked HTTP responses."""
import json

import pytest
from aioresponses import aioresponses

from crow_security_ng.client import CrowClient
from crow_security_ng.constants import BASE_URL
from crow_security_ng.exceptions import (
    AuthenticationError,
    PanelNotFoundError,
    RateLimitError,
    ResponseError,
)
from crow_security_ng.models import Area, AreaState, Output, Panel, Picture, Zone


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

TOKEN_RESPONSE = {
    "access_token": "test-access-token",
    "token_type": "Bearer",
    "refresh_token": "test-refresh-token",
    "expires_in": 36000,
}

PANEL_DATA = {
    "id": 42,
    "mac": "0013a1250a45",
    "name": "My Alarm",
    "remote_access_password": "rem-pass",
    "user_code": None,
    "state": "disarmed",
    "version": "3.1.0",
}

AREA_DATA = [
    {"id": 1, "name": "Home", "state": "disarmed", "exit_delay": 30},
    {"id": 2, "name": "Garage", "state": "armed", "exit_delay": 0},
]

ZONE_DATA = [
    {"id": 1, "name": "Front Door", "state": False, "bypass": False, "zone_type": 4},
    {"id": 2, "name": "Motion", "state": True, "bypass": False, "zone_type": 1},
]

OUTPUT_DATA = [
    {"id": 1, "name": "Siren", "state": False},
    {"id": 2, "name": "Light", "state": True},
]


def _token_url() -> str:
    return f"{BASE_URL}/o/token/"


def _panels_url() -> str:
    return f"{BASE_URL}/panels/"


def _panel_url(mac: str) -> str:
    return f"{BASE_URL}/panels/{mac}/"


def _areas_url(panel_id: int) -> str:
    return f"{BASE_URL}/panels/{panel_id}/areas/"


def _area_url(panel_id: int, area_id: int) -> str:
    return f"{BASE_URL}/panels/{panel_id}/areas/{area_id}/"


def _zones_url(panel_id: int) -> str:
    return f"{BASE_URL}/panels/{panel_id}/zones/"


def _outputs_url(panel_id: int) -> str:
    return f"{BASE_URL}/panels/{panel_id}/outputs/"


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

class TestLogin:
    @pytest.mark.asyncio
    async def test_login_success(self):
        async with CrowClient("user@example.com", "pass") as client:
            with aioresponses() as m:
                m.post(_token_url(), payload=TOKEN_RESPONSE)
                await client.login()
                assert client._access_token == "test-access-token"
                assert client._refresh_token == "test-refresh-token"
                assert client._token_type == "Bearer"

    @pytest.mark.asyncio
    async def test_login_bad_credentials(self):
        async with CrowClient("bad@example.com", "wrong") as client:
            with aioresponses() as m:
                m.post(_token_url(), status=400, payload={"error": "invalid_grant"})
                with pytest.raises(AuthenticationError):
                    await client.login()

    @pytest.mark.asyncio
    async def test_login_server_error(self):
        async with CrowClient("user@example.com", "pass") as client:
            with aioresponses() as m:
                m.post(_token_url(), status=500, body="Internal Server Error")
                with pytest.raises(ResponseError):
                    await client.login()


# ---------------------------------------------------------------------------
# get_panels / get_panel
# ---------------------------------------------------------------------------

class TestGetPanels:
    @pytest.mark.asyncio
    async def test_get_panels(self):
        async with CrowClient("user@example.com", "pass") as client:
            with aioresponses() as m:
                m.post(_token_url(), payload=TOKEN_RESPONSE)
                m.get(_panels_url(), payload=[PANEL_DATA])
                panels = await client.get_panels()

        assert len(panels) == 1
        assert isinstance(panels[0], Panel)
        assert panels[0].id == 42
        assert panels[0].mac == "0013a1250a45"

    @pytest.mark.asyncio
    async def test_get_panel_by_mac(self):
        async with CrowClient("user@example.com", "pass") as client:
            with aioresponses() as m:
                m.post(_token_url(), payload=TOKEN_RESPONSE)
                m.get(_panel_url("0013a1250a45"), payload=PANEL_DATA)
                panel = await client.get_panel("0013a1250a45")

        assert isinstance(panel, Panel)
        assert panel.id == 42
        assert panel.name == "My Alarm"
        assert panel.remote_access_password == "rem-pass"

    @pytest.mark.asyncio
    async def test_get_panel_normalises_mac(self):
        """MAC address with colons should be normalised before request."""
        async with CrowClient("user@example.com", "pass") as client:
            with aioresponses() as m:
                m.post(_token_url(), payload=TOKEN_RESPONSE)
                # The actual request should use the normalised (no-separator) form
                m.get(_panel_url("0013a1250a45"), payload=PANEL_DATA)
                panel = await client.get_panel("00:13:a1:25:0a:45")

        assert panel.mac == "0013a1250a45"

    @pytest.mark.asyncio
    async def test_get_panel_not_found(self):
        async with CrowClient("user@example.com", "pass") as client:
            with aioresponses() as m:
                m.post(_token_url(), payload=TOKEN_RESPONSE)
                m.get(_panel_url("aabbccddeeff"), status=404, body="Not found")
                with pytest.raises((PanelNotFoundError, ResponseError)):
                    await client.get_panel("aabbccddeeff")


# ---------------------------------------------------------------------------
# Areas
# ---------------------------------------------------------------------------

class TestAreas:
    @pytest.mark.asyncio
    async def test_get_areas(self):
        async with CrowClient("user@example.com", "pass") as client:
            with aioresponses() as m:
                m.post(_token_url(), payload=TOKEN_RESPONSE)
                m.get(_areas_url(42), payload=AREA_DATA)
                areas = await client.get_areas(42)

        assert len(areas) == 2
        assert all(isinstance(a, Area) for a in areas)
        assert areas[0].name == "Home"
        assert areas[0].state == AreaState.DISARMED
        assert areas[1].state == AreaState.ARMED

    @pytest.mark.asyncio
    async def test_set_area_state(self):
        patched_area = {**AREA_DATA[0], "state": "armed"}
        async with CrowClient("user@example.com", "pass") as client:
            with aioresponses() as m:
                m.post(_token_url(), payload=TOKEN_RESPONSE)
                m.patch(_area_url(42, 1), payload=patched_area)
                area = await client.set_area_state(
                    42, 1, "arm", remote_password="rem-pass"
                )

        assert area.state == AreaState.ARMED


# ---------------------------------------------------------------------------
# Zones
# ---------------------------------------------------------------------------

class TestZones:
    @pytest.mark.asyncio
    async def test_get_zones(self):
        async with CrowClient("user@example.com", "pass") as client:
            with aioresponses() as m:
                m.post(_token_url(), payload=TOKEN_RESPONSE)
                m.get(_zones_url(42), payload=ZONE_DATA)
                zones = await client.get_zones(42)

        assert len(zones) == 2
        assert all(isinstance(z, Zone) for z in zones)
        assert zones[0].state is False
        assert zones[0].is_open is False
        assert zones[1].state is True
        assert zones[1].is_open is True


# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------

class TestOutputs:
    @pytest.mark.asyncio
    async def test_get_outputs(self):
        async with CrowClient("user@example.com", "pass") as client:
            with aioresponses() as m:
                m.post(_token_url(), payload=TOKEN_RESPONSE)
                m.get(_outputs_url(42), payload=OUTPUT_DATA)
                outputs = await client.get_outputs(42)

        assert len(outputs) == 2
        assert all(isinstance(o, Output) for o in outputs)
        assert outputs[0].state is False
        assert outputs[1].state is True


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------

class TestRateLimiting:
    @pytest.mark.asyncio
    async def test_rate_limit_raises(self):
        async with CrowClient("user@example.com", "pass") as client:
            with aioresponses() as m:
                m.post(_token_url(), payload=TOKEN_RESPONSE)
                m.get(
                    _panels_url(),
                    status=429,
                    headers={"Retry-After": "30"},
                    body="Too Many Requests",
                )
                with pytest.raises(RateLimitError) as exc_info:
                    await client.get_panels()

        assert exc_info.value.retry_after == 30.0


# ---------------------------------------------------------------------------
# Token auto-refresh on 401
# ---------------------------------------------------------------------------

class TestTokenRefresh:
    @pytest.mark.asyncio
    async def test_auto_refresh_on_401(self):
        """Client should refresh token and retry on 401."""
        new_token_response = {**TOKEN_RESPONSE, "access_token": "new-access-token"}
        async with CrowClient("user@example.com", "pass") as client:
            with aioresponses() as m:
                # Initial login
                m.post(_token_url(), payload=TOKEN_RESPONSE)
                # First panels request returns 401
                m.get(_panels_url(), status=401, body="Unauthorized")
                # Refresh token call (or re-login)
                m.post(_token_url(), payload=new_token_response)
                # Retry panels request succeeds
                m.get(_panels_url(), payload=[PANEL_DATA])
                panels = await client.get_panels()

        assert len(panels) == 1


# ---------------------------------------------------------------------------
# Pictures / camera snapshots
# ---------------------------------------------------------------------------

class TestPictures:
    """Tests for picture/camera methods."""

    @pytest.mark.asyncio
    async def test_get_zone_pictures(self):
        pictures_payload = {
            "results": [
                {
                    "id": 1,
                    "zone": 7,
                    "zone_name": "cam hall ov",
                    "url": "https://s3.example.com/pic1.jpg",
                    "key": "abc",
                }
            ]
        }
        async with CrowClient("user@example.com", "pass") as client:
            with aioresponses() as m:
                m.post(f"{BASE_URL}/o/token/", payload=TOKEN_RESPONSE)
                m.get(f"{BASE_URL}/panels/42/zones/7/pictures/?page=1&page_size=10", payload=pictures_payload)
                pics = await client.get_zone_pictures(42, 7)

        assert len(pics) == 1
        assert pics[0].id == 1
        assert pics[0].url == "https://s3.example.com/pic1.jpg"

    @pytest.mark.asyncio
    async def test_capture_picture(self):
        async with CrowClient("user@example.com", "pass") as client:
            with aioresponses() as m:
                m.post(f"{BASE_URL}/o/token/", payload=TOKEN_RESPONSE)
                m.post(f"{BASE_URL}/panels/42/zones/7/pictures/", status=204)
                await client.capture_picture(42, 7, remote_password="secret")

    @pytest.mark.asyncio
    async def test_get_picture_bytes(self):
        pic = Picture(id=1, zone=7, url="https://s3.example.com/pic1.jpg")
        async with CrowClient("user@example.com", "pass") as client:
            with aioresponses() as m:
                m.get("https://s3.example.com/pic1.jpg", body=b"\xff\xd8\xff")
                data = await client.get_picture_bytes(pic)

        assert data == b"\xff\xd8\xff"

    @pytest.mark.asyncio
    async def test_download_picture(self, tmp_path):
        pic = Picture(id=2, zone=7, url="https://s3.example.com/pic2.jpg")
        out = tmp_path / "pic.jpg"
        async with CrowClient("user@example.com", "pass") as client:
            with aioresponses() as m:
                m.get("https://s3.example.com/pic2.jpg", body=b"\xff\xd8\xff\xe0")
                await client.download_picture(pic, str(out))

        assert out.read_bytes() == b"\xff\xd8\xff\xe0"
