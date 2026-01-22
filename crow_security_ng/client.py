import logging
import aiohttp
import asyncio
import json
import re

from .exceptions import (
    CrowSecurityError,
    CrowSecurityAuthenticationError,
    CrowSecurityConnectionError,
)

_LOGGER = logging.getLogger(__name__)

BASE_URL = "https://api.crowcloud.xyz"

class CrowSecurityClient:
    def __init__(self, username, password, mac_address, session=None):
        """Initialize the Crow Security Client."""
        self._username = username
        self._password = password
        self._mac = self._format_mac(mac_address)
        self._session = session
        self._token = None
        self._panel_id = None  # Sometimes returned by login, useful for subsequent calls

    def _format_mac(self, mac: str) -> str:
        """
        Strip colons, dashes, and spaces, and convert to uppercase.
        Example: '00:11:22:AA:BB:CC' -> '001122AABBCC'
        """
        if not mac:
            return ""
        clean_mac = re.sub(r"[^a-fA-F0-9]", "", mac)
        return clean_mac.upper()

    async def _get_session(self):
        """Get or create the aiohttp session."""
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self._session

    async def login(self):
        """
        Authenticate with the Crow Security API.
        
        Based on standard patterns for this API:
        POST /auth/login (or similar endpoint)
        Payload usually requires username, password, and the system ID (MAC).
        """
        session = await self._get_session()
        
        # Endpoint: Based on standard Crow API structure. 
        # If this 404s, the endpoint might be /v1/user/login or /api/auth/login
        url = f"{BASE_URL}/v1/login" 

        # Payload structure
        # We send the formatted MAC address. Some APIs call this 'central_id', 'mac', or 'panel_id'.
        # I am sending it as 'mac' and 'central_id' to cover bases, or strictly as 'mac' if documented.
        payload = {
            "username": self._username,
            "password": self._password,
            "mac": self._mac, 
            "type": "crow_security_ng" # Sometimes required to identify the client type
        }

        _LOGGER.debug(f"Attempting login to {url} with MAC: {self._mac}")

        try:
            async with session.post(url, json=payload) as response:
                _LOGGER.debug(f"Login Response Status: {response.status}")
                
                if response.status in (401, 403):
                    data = await response.json()
                    _LOGGER.error(f"Authentication failed: {data}")
                    raise CrowSecurityAuthenticationError("Invalid credentials or MAC address")
                
                response.raise_for_status()
                data = await response.json()
                
                # Parse Token
                # Adjust 'access_token' key based on actual API response
                if "token" in data:
                    self._token = data["token"]
                elif "access_token" in data:
                    self._token = data["access_token"]
                else:
                    _LOGGER.error(f"No token found in response: {data}")
                    raise CrowSecurityAuthenticationError("API did not return an access token")

                # Parse Panel ID if available
                self._panel_id = data.get("panel_id", data.get("id"))
                
                _LOGGER.info("Login successful.")
                return True

        except aiohttp.ClientError as e:
            raise CrowSecurityConnectionError(f"Connection error: {e}")
        except Exception as e:
            raise CrowSecurityError(f"Unexpected error during login: {e}")

    async def get_systems(self):
        """Get list of systems/panels associated with the account."""
        if not self._token:
            await self.login()

        url = f"{BASE_URL}/v1/systems" # or /v1/panels
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/json"
        }

        session = await self._get_session()
        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 401:
                    # Token might be expired, retry once
                    await self.login()
                    headers["Authorization"] = f"Bearer {self._token}"
                    async with session.get(url, headers=headers) as retry_response:
                        retry_response.raise_for_status()
                        return await retry_response.json()
                
                response.raise_for_status()
                return await response.json()
        except Exception as e:
            raise CrowSecurityError(f"Failed to fetch systems: {e}")

    async def close(self):
        """Close the session."""
        if self._session:
            await self._session.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()