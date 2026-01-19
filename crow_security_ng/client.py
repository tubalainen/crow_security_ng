"""HTTP client for the Crow Cloud API."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable

import aiohttp

from .exceptions import (
    AuthenticationError,
    ConnectionError,
    PanelNotFoundError,
    RateLimitError,
    ResponseError,
    TimeoutError,
    WebSocketError,
)
from .models import Area, Measurement, Output, Panel, Zone
from .utils import normalize_mac

_LOGGER = logging.getLogger(__name__)

# API Configuration
DEFAULT_API_BASE = "https://api.crowcloud.xyz"
DEFAULT_TIMEOUT = 30
DEFAULT_RETRY_COUNT = 3
DEFAULT_RETRY_DELAY = 1.0


class CrowClient:
    """
    Async HTTP client for the Crow Cloud API.
    
    This client handles authentication, request retries, and
    provides methods for all Crow Cloud API operations.
    """
    
    def __init__(
        self,
        email: str,
        password: str,
        *,
        api_base: str = DEFAULT_API_BASE,
        timeout: int = DEFAULT_TIMEOUT,
        retry_count: int = DEFAULT_RETRY_COUNT,
        retry_delay: float = DEFAULT_RETRY_DELAY,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        """
        Initialize the Crow Cloud client.
        
        Args:
            email: Crow Cloud account email.
            password: Crow Cloud account password.
            api_base: Base URL for the API (default: https://api.crowcloud.com).
            timeout: Request timeout in seconds.
            retry_count: Number of retries for failed requests.
            retry_delay: Delay between retries in seconds.
            session: Optional aiohttp session to use.
        """
        self._email = email
        self._password = password
        self._api_base = api_base.rstrip("/")
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._retry_count = retry_count
        self._retry_delay = retry_delay
        self._session = session
        self._owns_session = session is None
        self._token: str | None = None
        self._token_expiry: float | None = None
        self._ws_connections: dict[str, asyncio.Task] = {}
    
    async def _ensure_session(self) -> aiohttp.ClientSession:
        """Ensure we have an active session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self._timeout)
            self._owns_session = True
        return self._session
    
    async def _authenticate(self) -> None:
        """Authenticate with the Crow Cloud API."""
        session = await self._ensure_session()
        
        try:
            async with session.post(
                f"{self._api_base}/api/auth/login",
                json={"email": self._email, "password": self._password},
            ) as response:
                if response.status == 401 or response.status == 403:
                    raise AuthenticationError()
                
                await self._validate_response(response)
                data = await response.json()
                
                self._token = data.get("token") or data.get("accessToken") or data.get("access_token")
                if not self._token:
                    raise AuthenticationError("No token received in authentication response")
                    
        except aiohttp.ClientError as err:
            raise ConnectionError(f"Failed to connect: {err}") from err
    
    async def _ensure_authenticated(self) -> None:
        """Ensure we have a valid authentication token."""
        if not self._token:
            await self._authenticate()
    
    def _get_headers(self) -> dict[str, str]:
        """Get headers for API requests."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers
    
    async def _validate_response(self, response: aiohttp.ClientResponse) -> None:
        """Validate an API response and raise appropriate exceptions."""
        if response.status == 200 or response.status == 201:
            return
        
        if response.status == 401 or response.status == 403:
            self._token = None  # Clear token to force re-auth
            raise AuthenticationError()
        
        if response.status == 404:
            text = await response.text()
            raise ResponseError(404, "Resource not found", text)
        
        if response.status == 408:
            # 408 is expected for some operations (arm state changes)
            _LOGGER.debug("Received 408 response (expected for some operations)")
            return
        
        if response.status == 429:
            retry_after = response.headers.get("Retry-After")
            raise RateLimitError(int(retry_after) if retry_after else None)
        
        text = await response.text()
        raise ResponseError(response.status, "API error", text)
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        authenticate: bool = True,
    ) -> dict[str, Any] | list[Any] | None:
        """
        Make an API request with retry logic.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE).
            endpoint: API endpoint (without base URL).
            json: JSON body data.
            params: Query parameters.
            authenticate: Whether to require authentication.
            
        Returns:
            Parsed JSON response or None.
        """
        if authenticate:
            await self._ensure_authenticated()
        
        session = await self._ensure_session()
        url = f"{self._api_base}/{endpoint.lstrip('/')}"
        
        last_error: Exception | None = None
        
        for attempt in range(self._retry_count):
            try:
                async with session.request(
                    method,
                    url,
                    headers=self._get_headers(),
                    json=json,
                    params=params,
                ) as response:
                    await self._validate_response(response)
                    
                    if response.status == 408:
                        return None
                    
                    # Try to parse JSON, return None if empty
                    try:
                        return await response.json()
                    except aiohttp.ContentTypeError:
                        return None
                        
            except AuthenticationError:
                # Re-authenticate and retry
                if attempt < self._retry_count - 1:
                    await self._authenticate()
                    continue
                raise
                
            except (aiohttp.ClientError, asyncio.TimeoutError) as err:
                last_error = err
                if attempt < self._retry_count - 1:
                    await asyncio.sleep(self._retry_delay * (attempt + 1))
                    continue
                    
        if last_error:
            if isinstance(last_error, asyncio.TimeoutError):
                raise TimeoutError() from last_error
            raise ConnectionError(str(last_error)) from last_error
            
        return None
    
    async def _get(
        self, 
        endpoint: str, 
        params: dict[str, Any] | None = None
    ) -> dict[str, Any] | list[Any] | None:
        """Make a GET request."""
        return await self._request("GET", endpoint, params=params)
    
    async def _post(
        self,
        endpoint: str,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[Any] | None:
        """Make a POST request."""
        return await self._request("POST", endpoint, json=json)
    
    async def _put(
        self,
        endpoint: str,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[Any] | None:
        """Make a PUT request."""
        return await self._request("PUT", endpoint, json=json)
    
    # Panel operations
    
    async def get_panel(self, mac: str) -> Panel:
        """
        Get a panel by MAC address.
        
        Args:
            mac: Panel MAC address (any format accepted).
            
        Returns:
            Panel object.
            
        Raises:
            PanelNotFoundError: If panel not found.
        """
        normalized_mac = normalize_mac(mac)
        
        try:
            data = await self._get(f"/api/panels/{normalized_mac}")
            if not data:
                raise PanelNotFoundError(mac)
            return Panel.from_api(data, normalized_mac, client=self)
        except ResponseError as err:
            if err.status_code == 404:
                raise PanelNotFoundError(mac) from err
            raise
    
    async def get_panels(self) -> list[Panel]:
        """
        Get all panels accessible to this account.
        
        Returns:
            List of Panel objects.
        """
        data = await self._get("/api/panels")
        if not data or not isinstance(data, list):
            return []
        return [
            Panel.from_api(
                p, 
                normalize_mac(p.get("mac", p.get("macAddress", ""))),
                client=self
            )
            for p in data
        ]
    
    # Area operations
    
    async def get_areas(self, mac: str) -> list[Area]:
        """
        Get all areas for a panel.
        
        Args:
            mac: Panel MAC address.
            
        Returns:
            List of Area objects.
        """
        normalized_mac = normalize_mac(mac)
        data = await self._get(f"/api/panels/{normalized_mac}/areas")
        if not data or not isinstance(data, list):
            return []
        return [Area.from_api(a) for a in data]
    
    async def get_area(self, mac: str, area_id: str) -> Area | None:
        """
        Get a specific area.
        
        Args:
            mac: Panel MAC address.
            area_id: Area ID.
            
        Returns:
            Area object or None if not found.
        """
        normalized_mac = normalize_mac(mac)
        try:
            data = await self._get(f"/api/panels/{normalized_mac}/areas/{area_id}")
            if not data:
                return None
            return Area.from_api(data)
        except ResponseError as err:
            if err.status_code == 404:
                return None
            raise
    
    async def set_area_state(
        self, 
        mac: str, 
        area_id: str, 
        command: str
    ) -> Area | None:
        """
        Set the arm state of an area.
        
        Args:
            mac: Panel MAC address.
            area_id: Area ID.
            command: Command ('arm', 'stay', 'disarm').
            
        Returns:
            Updated Area object or None.
        """
        normalized_mac = normalize_mac(mac)
        _LOGGER.info("Setting area %s state to %s", area_id, command)
        
        try:
            data = await self._post(
                f"/api/panels/{normalized_mac}/areas/{area_id}/state",
                json={"state": command}
            )
            if data:
                return Area.from_api(data)
            return None
        except ResponseError as err:
            if err.status_code == 408:
                _LOGGER.debug("Received expected 408 for arm state change")
                return None
            raise
    
    # Zone operations
    
    async def get_zones(self, mac: str) -> list[Zone]:
        """
        Get all zones for a panel.
        
        Args:
            mac: Panel MAC address.
            
        Returns:
            List of Zone objects.
        """
        normalized_mac = normalize_mac(mac)
        data = await self._get(f"/api/panels/{normalized_mac}/zones")
        if not data or not isinstance(data, list):
            return []
        return [Zone.from_api(z) for z in data]
    
    # Output operations
    
    async def get_outputs(self, mac: str) -> list[Output]:
        """
        Get all outputs for a panel.
        
        Args:
            mac: Panel MAC address.
            
        Returns:
            List of Output objects.
        """
        normalized_mac = normalize_mac(mac)
        data = await self._get(f"/api/panels/{normalized_mac}/outputs")
        if not data or not isinstance(data, list):
            return []
        return [Output.from_api(o) for o in data]
    
    async def set_output_state(
        self, 
        mac: str, 
        output_id: str, 
        state: bool
    ) -> bool:
        """
        Set the state of an output.
        
        Args:
            mac: Panel MAC address.
            output_id: Output ID.
            state: True for on, False for off.
            
        Returns:
            True if successful.
        """
        normalized_mac = normalize_mac(mac)
        _LOGGER.info("Setting output %s to %s", output_id, state)
        
        try:
            await self._post(
                f"/api/panels/{normalized_mac}/outputs/{output_id}",
                json={"state": state}
            )
            return True
        except ResponseError:
            return False
    
    # Measurement operations
    
    async def get_measurements(self, mac: str) -> list[Measurement]:
        """
        Get all measurements for a panel.
        
        Args:
            mac: Panel MAC address.
            
        Returns:
            List of Measurement objects.
        """
        normalized_mac = normalize_mac(mac)
        data = await self._get(f"/api/panels/{normalized_mac}/measurements")
        if not data or not isinstance(data, list):
            return []
        return [Measurement.from_api(m) for m in data]
    
    # Camera operations
    
    async def capture_cam_image(self, mac: str, zone_id: str) -> bytes | None:
        """
        Capture an image from a camera zone.
        
        Args:
            mac: Panel MAC address.
            zone_id: Camera zone ID.
            
        Returns:
            Image bytes or None.
        """
        normalized_mac = normalize_mac(mac)
        
        try:
            session = await self._ensure_session()
            await self._ensure_authenticated()
            
            async with session.post(
                f"{self._api_base}/api/panels/{normalized_mac}/cameras/{zone_id}/capture",
                headers=self._get_headers(),
            ) as response:
                if response.status == 200:
                    return await response.read()
                return None
        except Exception as err:
            _LOGGER.error("Failed to capture camera image: %s", err)
            return None
    
    # WebSocket operations
    
    async def ws_connect(
        self,
        mac: str,
        callback: Callable[[dict[str, Any]], None],
        *,
        auto_reconnect: bool = True,
        reconnect_delay: float = 5.0,
    ) -> None:
        """
        Connect to WebSocket for real-time updates.
        
        Args:
            mac: Panel MAC address.
            callback: Async callback function for messages.
            auto_reconnect: Whether to automatically reconnect on disconnect.
            reconnect_delay: Delay between reconnection attempts.
        """
        normalized_mac = normalize_mac(mac)
        await self._ensure_authenticated()
        
        ws_url = f"{self._api_base.replace('http', 'ws')}/ws/panels/{normalized_mac}"
        
        while True:
            try:
                session = await self._ensure_session()
                
                async with session.ws_connect(
                    ws_url,
                    headers=self._get_headers(),
                ) as ws:
                    _LOGGER.info("WebSocket connected for panel %s", normalized_mac)
                    
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            try:
                                data = msg.json()
                                await self._handle_ws_message(data, callback)
                            except Exception as err:
                                _LOGGER.error("Error handling WebSocket message: %s", err)
                                
                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            _LOGGER.error("WebSocket error: %s", ws.exception())
                            break
                            
                        elif msg.type == aiohttp.WSMsgType.CLOSED:
                            _LOGGER.info("WebSocket closed")
                            break
                            
            except Exception as err:
                _LOGGER.error("WebSocket connection error: %s", err)
            
            if not auto_reconnect:
                break
                
            _LOGGER.info("Reconnecting WebSocket in %s seconds...", reconnect_delay)
            await asyncio.sleep(reconnect_delay)
    
    async def _handle_ws_message(
        self,
        data: dict[str, Any],
        callback: Callable[[dict[str, Any]], None],
    ) -> None:
        """Handle an incoming WebSocket message."""
        # Skip certain info messages
        if (data.get("type") == "info" and 
            data.get("data", {}).get("_id", {}).get("dect_interface") == 32768):
            _LOGGER.debug("Skipping DECT info message")
            return
        
        _LOGGER.debug("WebSocket message: %s", data)
        
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(data)
            else:
                callback(data)
        except Exception as err:
            _LOGGER.error("Error in WebSocket callback: %s", err)
    
    # Cleanup
    
    async def close(self) -> None:
        """Close the client and clean up resources."""
        # Cancel WebSocket connections
        for task in self._ws_connections.values():
            task.cancel()
        self._ws_connections.clear()
        
        # Close session if we own it
        if self._owns_session and self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    async def __aenter__(self) -> "CrowClient":
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
