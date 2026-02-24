"""Crow Security NG — async HTTP + WebSocket client."""
from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

import aiohttp

from .constants import (
    BASE_URL,
    DEFAULT_PAGE_SIZE,
    DEFAULT_TIMEOUT,
    WS_URL,
    _CLIENT_ID,
    _CLIENT_SECRET,
)
from .exceptions import (
    AuthenticationError,
    PanelNotFoundError,
    RateLimitError,
    ResponseError,
    TimeoutError,
    WebSocketError,
)
from .models import Area, Measurement, Output, Panel, Picture, Zone
from .utils import normalize_mac

_LOGGER = logging.getLogger(__name__)


def _control_headers(
    remote_password: str | None,
    user_code: str | None,
) -> dict[str, str]:
    """Return X-Crow-CP-* headers for arming/control operations.

    These headers are required by the Crow Cloud API when performing
    privileged operations (arming, disarming, output control, zone bypass).
    Both values come from the Panel object returned by get_panel().
    """
    headers: dict[str, str] = {}
    if remote_password is not None:
        headers["X-Crow-CP-Remote"] = remote_password
    if user_code is not None:
        headers["X-Crow-CP-User"] = user_code
    return headers


class CrowClient:
    """Low-level async client for the Crow Cloud REST API and WebSocket.

    Authentication uses OAuth2 Resource Owner Password Credentials (ROPC)
    at POST /o/token/ with a shared CLIENT_ID/CLIENT_SECRET that is the
    same for all Crow Cloud users.

    After login the response provides:
      - access_token  — used as  Authorization: Bearer {access_token}
      - refresh_token — used to renew without re-entering credentials
      - token_type    — always "Bearer" on the production API

    Panel sub-resources (zones, areas, outputs, measurements) are accessed
    by the panel's numeric database ID, not the MAC address.  The MAC is
    only used for the initial panel lookup at GET /panels/{mac}/.

    Example::

        async with CrowClient("email@example.com", "password") as client:
            panels = await client.get_panels()
            panel  = await client.get_panel("AABBCCDDEEFF")
            areas  = await client.get_areas(panel.id)
    """

    def __init__(
        self,
        email: str,
        password: str,
        api_base: str = BASE_URL,
        ws_base: str = WS_URL,
        timeout: int = DEFAULT_TIMEOUT,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        self._email = email
        self._password = password
        self._api_base = api_base.rstrip("/")
        self._ws_base = ws_base.rstrip("/")
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._owned_session = session is None
        self._session: aiohttp.ClientSession | None = session
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._token_type: str = "Bearer"

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None:
            self._session = aiohttp.ClientSession(timeout=self._timeout)
        return self._session

    async def close(self) -> None:
        """Close the underlying aiohttp session."""
        if self._session and self._owned_session:
            await self._session.close()
            self._session = None

    async def __aenter__(self) -> "CrowClient":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    async def login(self) -> None:
        """Authenticate with OAuth2 Resource Owner Password Credentials.

        Sends form-encoded data (not JSON) to POST /o/token/.
        Stores the access_token, refresh_token, and token_type internally.
        """
        _LOGGER.debug("Logging in as %s", self._email)
        session = self._get_session()
        data = {
            "username": self._email,
            "password": self._password,
            "grant_type": "password",
            "client_id": _CLIENT_ID,
            "client_secret": _CLIENT_SECRET,
        }
        try:
            async with session.post(
                f"{self._api_base}/o/token/", data=data
            ) as resp:
                if resp.status in (400, 401):
                    text = await resp.text()
                    _LOGGER.error("Login failed (HTTP %s): %s", resp.status, text)
                    raise AuthenticationError(
                        f"Invalid credentials for {self._email}"
                    )
                resp.raise_for_status()
                result = await resp.json()
                self._access_token = result["access_token"]
                self._refresh_token = result.get("refresh_token")
                self._token_type = result.get("token_type", "Bearer")
                _LOGGER.debug("Login successful, token_type=%s", self._token_type)
        except aiohttp.ServerTimeoutError as exc:
            raise TimeoutError("Login request timed out") from exc
        except aiohttp.ClientError as exc:
            raise ResponseError(f"Login connection error: {exc}") from exc

    async def _refresh(self) -> None:
        """Attempt to renew the access token using the refresh token."""
        if not self._refresh_token:
            await self.login()
            return
        _LOGGER.debug("Refreshing access token")
        session = self._get_session()
        data = {
            "refresh_token": self._refresh_token,
            "grant_type": "refresh_token",
            "client_id": _CLIENT_ID,
            "client_secret": _CLIENT_SECRET,
        }
        try:
            async with session.post(
                f"{self._api_base}/o/token/", data=data
            ) as resp:
                if resp.status in (400, 401):
                    _LOGGER.debug("Refresh failed, falling back to full login")
                    await self.login()
                    return
                resp.raise_for_status()
                result = await resp.json()
                self._access_token = result["access_token"]
                self._refresh_token = result.get("refresh_token", self._refresh_token)
                self._token_type = result.get("token_type", self._token_type)
        except aiohttp.ClientError:
            await self.login()

    def _auth_headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json",
            "Authorization": f"{self._token_type} {self._access_token}",
        }

    # ------------------------------------------------------------------
    # Central request dispatcher
    # ------------------------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        *,
        retry: bool = True,
        extra_headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> Any:
        """Make an authenticated request with automatic token refresh."""
        if not self._access_token:
            await self.login()

        headers = self._auth_headers()
        if extra_headers:
            headers.update(extra_headers)

        url = f"{self._api_base}{path}"
        session = self._get_session()

        try:
            async with getattr(session, method)(
                url, headers=headers, **kwargs
            ) as resp:
                if resp.status in (400, 401) and retry:
                    _LOGGER.debug("Got %s, refreshing token and retrying", resp.status)
                    await self._refresh()
                    return await self._request(
                        method, path, retry=False,
                        extra_headers=extra_headers, **kwargs
                    )
                if resp.status == 429:
                    retry_after_raw = resp.headers.get("Retry-After")
                    retry_after = float(retry_after_raw) if retry_after_raw else None
                    raise RateLimitError(retry_after=retry_after)
                if resp.status == 404:
                    raise ResponseError("Not found", status_code=404)
                if resp.status >= 400:
                    text = await resp.text()
                    raise ResponseError(
                        f"API error: {text[:200]}",
                        status_code=resp.status,
                        response_text=text,
                    )
                if resp.status == 204 or resp.content_length == 0:
                    return None
                return await resp.json()

        except aiohttp.ServerTimeoutError as exc:
            raise TimeoutError(f"Request timed out: {method.upper()} {path}") from exc
        except aiohttp.ClientError as exc:
            raise ResponseError(f"Connection error: {exc}") from exc

    # ------------------------------------------------------------------
    # Panel endpoints  (use MAC in URL path)
    # ------------------------------------------------------------------

    async def get_panels(self) -> list[Panel]:
        """Return all panels visible to this account.

        GET /panels/
        """
        data = await self._request("get", "/panels/")
        items = data if isinstance(data, list) else data.get("results", [])
        return [Panel.from_api(item, client=self) for item in items]

    async def get_panel(self, mac: str) -> Panel:
        """Return a single panel by MAC address.

        GET /panels/{mac}/

        Raises PanelNotFoundError if the panel does not exist on the account.
        """
        normalized = normalize_mac(mac)
        try:
            data = await self._request("get", f"/panels/{normalized}/")
        except ResponseError as exc:
            if exc.status_code == 404:
                raise PanelNotFoundError(mac) from exc
            raise
        return Panel.from_api(data, client=self)

    # ------------------------------------------------------------------
    # Area endpoints  (use numeric panel ID in URL path)
    # ------------------------------------------------------------------

    async def get_areas(self, panel_id: int) -> list[Area]:
        """Return all areas for a panel.

        GET /panels/{panel_id}/areas/
        """
        data = await self._request("get", f"/panels/{panel_id}/areas/")
        items = data if isinstance(data, list) else data.get("results", [])
        return [Area.from_api(a) for a in items]

    async def get_area(self, panel_id: int, area_id: int) -> Area:
        """Return a single area.

        GET /panels/{panel_id}/areas/{area_id}/
        """
        data = await self._request("get", f"/panels/{panel_id}/areas/{area_id}/")
        return Area.from_api(data)

    async def set_area_state(
        self,
        panel_id: int,
        area_id: int,
        state: str,
        force: bool = False,
        remote_password: str | None = None,
        user_code: str | None = None,
    ) -> Area:
        """Arm, stay-arm, or disarm an area.

        PATCH /panels/{panel_id}/areas/{area_id}/
        Body: {"state": "arm"|"stay"|"disarm", "force": false}

        state values:  "arm"    → fully armed
                       "stay"   → stay/home arm
                       "disarm" → disarmed
        """
        data = await self._request(
            "patch",
            f"/panels/{panel_id}/areas/{area_id}/",
            json={"state": state, "force": force},
            extra_headers=_control_headers(remote_password, user_code),
        )
        return Area.from_api(data)

    # ------------------------------------------------------------------
    # Zone endpoints
    # ------------------------------------------------------------------

    async def get_zones(self, panel_id: int) -> list[Zone]:
        """Return all zones for a panel.

        GET /panels/{panel_id}/zones/
        """
        data = await self._request("get", f"/panels/{panel_id}/zones/")
        items = data if isinstance(data, list) else data.get("results", [])
        return [Zone.from_api(z) for z in items]

    async def get_zone(self, panel_id: int, zone_id: int) -> Zone:
        """Return a single zone.

        GET /panels/{panel_id}/zones/{zone_id}/
        """
        data = await self._request("get", f"/panels/{panel_id}/zones/{zone_id}/")
        return Zone.from_api(data)

    async def set_zone_bypass(
        self,
        panel_id: int,
        zone_id: int,
        bypass: bool,
        remote_password: str | None = None,
        user_code: str | None = None,
    ) -> Zone:
        """Bypass or un-bypass a zone.

        PATCH /panels/{panel_id}/zones/{zone_id}/
        Body: {"bypass": true|false}
        """
        data = await self._request(
            "patch",
            f"/panels/{panel_id}/zones/{zone_id}/",
            json={"bypass": bypass},
            extra_headers=_control_headers(remote_password, user_code),
        )
        return Zone.from_api(data)

    # ------------------------------------------------------------------
    # Output endpoints
    # ------------------------------------------------------------------

    async def get_outputs(self, panel_id: int) -> list[Output]:
        """Return all outputs (smart plugs, sirens, etc.) for a panel.

        GET /panels/{panel_id}/outputs/
        """
        data = await self._request("get", f"/panels/{panel_id}/outputs/")
        items = data if isinstance(data, list) else data.get("results", [])
        return [Output.from_api(o) for o in items]

    async def get_output(self, panel_id: int, output_id: int) -> Output:
        """Return a single output.

        GET /panels/{panel_id}/outputs/{output_id}/
        """
        data = await self._request("get", f"/panels/{panel_id}/outputs/{output_id}/")
        return Output.from_api(data)

    async def set_output_state(
        self,
        panel_id: int,
        output_id: int,
        state: bool,
        remote_password: str | None = None,
        user_code: str | None = None,
    ) -> Output:
        """Turn an output on or off.

        PATCH /panels/{panel_id}/outputs/{output_id}/
        Body: {"state": true|false}
        """
        data = await self._request(
            "patch",
            f"/panels/{panel_id}/outputs/{output_id}/",
            json={"state": state},
            extra_headers=_control_headers(remote_password, user_code),
        )
        return Output.from_api(data)

    # ------------------------------------------------------------------
    # Measurements endpoint
    # ------------------------------------------------------------------

    async def get_measurements(self, panel_id: int) -> list[Measurement]:
        """Return the latest sensor measurements for all DECT devices.

        GET /panels/{panel_id}/dect/measurements/latest/by_zone/

        The response is a dict keyed by zone; this method flattens it into
        a list of Measurement objects with pre-divided values.
        """
        data = await self._request(
            "get", f"/panels/{panel_id}/dect/measurements/latest/by_zone/"
        )
        measurements: list[Measurement] = []
        if isinstance(data, dict):
            for zone_key, zone_data in data.items():
                if isinstance(zone_data, dict) and "values" in zone_data:
                    for reading in zone_data["values"]:
                        measurements.append(Measurement.from_api(reading))
                elif isinstance(zone_data, list):
                    for reading in zone_data:
                        measurements.append(Measurement.from_api(reading))
        elif isinstance(data, list):
            for reading in data:
                measurements.append(Measurement.from_api(reading))
        return measurements

    # ------------------------------------------------------------------
    # Picture endpoints
    # ------------------------------------------------------------------

    async def get_zone_pictures(
        self,
        panel_id: int,
        zone_id: int,
        page_size: int = DEFAULT_PAGE_SIZE,
        page: int = 1,
    ) -> list[Picture]:
        """Return pictures captured by a zone's camera.

        GET /panels/{panel_id}/zones/{zone_id}/pictures/?page_size=N&page=N
        """
        data = await self._request(
            "get",
            f"/panels/{panel_id}/zones/{zone_id}/pictures/",
            params={"page_size": page_size, "page": page},
        )
        items: list[Any]
        if isinstance(data, dict):
            items = data.get("results", [])
        else:
            items = data or []
        return [Picture.from_api(p) for p in items]

    async def capture_picture(
        self,
        panel_id: int,
        zone_id: int,
        remote_password: str | None = None,
        user_code: str | None = None,
    ) -> None:
        """Trigger a new picture capture on a smartcam zone.

        POST /panels/{panel_id}/zones/{zone_id}/pictures/
        """
        await self._request(
            "post",
            f"/panels/{panel_id}/zones/{zone_id}/pictures/",
            extra_headers=_control_headers(remote_password, user_code),
        )

    async def download_picture(self, picture: Picture, path: str) -> None:
        """Download a picture to a local file.

        The picture URL is pre-signed and does not require the Authorization
        header — it is fetched directly.
        """
        session = self._get_session()
        async with session.get(picture.url) as resp:
            resp.raise_for_status()
            with open(path, "wb") as f:
                async for chunk in resp.content.iter_chunked(8192):
                    f.write(chunk)

    # ------------------------------------------------------------------
    # WebSocket  (real-time event stream)
    # ------------------------------------------------------------------

    async def ws_connect(
        self,
        mac: str,
        callback: Callable[[dict[str, Any]], Awaitable[None] | None],
    ) -> None:
        """Connect to the Crow Cloud WebSocket for real-time events.

        Handshake protocol:
          1. Send {"type": "authentication", "value": access_token}
          2. Receive {"status": "OK"}  (raises WebSocketError on failure)
          3. Send {"type": "subscribe", "value": panel_mac}
          4. Receive {"status": "OK"}  (raises WebSocketError on failure)
          5. Receive event messages until connection closes

        The callback receives each message as a parsed dict. It may be
        a coroutine or a plain callable.

        Reconnection is left to the caller (e.g. HA's async_track_time_interval
        or a retry loop).
        """
        if not self._access_token:
            await self.login()

        normalized = normalize_mac(mac)
        ws_url = f"{self._ws_base}/sockjs/websocket"
        session = self._get_session()

        _LOGGER.debug("Connecting to WebSocket %s for panel %s", ws_url, normalized)
        async with session.ws_connect(ws_url) as ws:
            # Step 1 — authenticate
            await ws.send_json({"type": "authentication", "value": self._access_token})
            auth_msg = await ws.receive_json()
            if auth_msg.get("status") != "OK":
                raise WebSocketError(
                    f"WebSocket authentication failed: {auth_msg.get('description', auth_msg)}"
                )

            # Step 2 — subscribe to panel events
            await ws.send_json({"type": "subscribe", "value": normalized})
            sub_msg = await ws.receive_json()
            if sub_msg.get("status") != "OK":
                raise WebSocketError(
                    f"WebSocket subscription failed: {sub_msg.get('description', sub_msg)}"
                )
            _LOGGER.debug("WebSocket subscribed to panel %s", normalized)

            # Step 3 — receive event loop
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                    except json.JSONDecodeError:
                        _LOGGER.warning("WebSocket received non-JSON message: %s", msg.data)
                        continue
                    result = callback(data)
                    if result is not None:
                        await result
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    _LOGGER.error("WebSocket error: %s", ws.exception())
                    break
                elif msg.type == aiohttp.WSMsgType.CLOSED:
                    _LOGGER.debug("WebSocket closed")
                    break
