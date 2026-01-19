"""
Session class for backwards compatibility with crow_security library.

This provides the same interface as the original crow_security.Session class
but uses the improved CrowClient under the hood.
"""
from __future__ import annotations

import logging
from typing import Any, Callable

from .client import CrowClient
from .models import Panel
from .utils import normalize_mac

_LOGGER = logging.getLogger(__name__)


class Session:
    """
    Session class compatible with the original crow_security library.
    
    This class provides a simpler interface that matches the original
    crow_security.Session API while using the improved CrowClient.
    
    Example usage:
        session = Session(email, password)
        panel = await session.get_panel(mac_address)
        areas = await panel.get_areas()
    """
    
    def __init__(self, email: str, password: str) -> None:
        """
        Initialize a new session.
        
        Args:
            email: Crow Cloud account email.
            password: Crow Cloud account password.
        """
        self._email = email
        self._password = password
        self._client: CrowClient | None = None
        self._panels: dict[str, Panel] = {}
    
    def _get_client(self) -> CrowClient:
        """Get or create the underlying client."""
        if self._client is None:
            self._client = CrowClient(self._email, self._password)
        return self._client
    
    async def get_panel(self, mac: str) -> Panel:
        """
        Get a panel by MAC address.
        
        This is the main entry point compatible with crow_security.Session.
        
        Args:
            mac: Panel MAC address (any format - with or without separators).
            
        Returns:
            Panel object with methods to interact with the panel.
            
        Raises:
            PanelNotFoundError: If the panel is not found.
        """
        normalized_mac = normalize_mac(mac)
        
        # Check cache
        if normalized_mac in self._panels:
            return self._panels[normalized_mac]
        
        client = self._get_client()
        panel = await client.get_panel(normalized_mac)
        
        # Cache the panel
        self._panels[normalized_mac] = panel
        
        return panel
    
    async def get_panels(self) -> list[Panel]:
        """
        Get all panels accessible to this account.
        
        Returns:
            List of Panel objects.
        """
        client = self._get_client()
        panels = await client.get_panels()
        
        # Cache all panels
        for panel in panels:
            self._panels[panel.mac] = panel
        
        return panels
    
    async def get_panel_data(self, mac: str) -> dict[str, Any]:
        """
        Get raw panel data by MAC address.
        
        This method returns the raw API response data.
        
        Args:
            mac: Panel MAC address.
            
        Returns:
            Raw panel data dictionary.
        """
        panel = await self.get_panel(mac)
        return panel.raw_data
    
    async def ws_connect(
        self,
        mac: str,
        callback: Callable[[dict[str, Any]], None],
    ) -> None:
        """
        Connect to WebSocket for real-time updates.
        
        This provides the same interface as crow_security.Session.ws_connect.
        
        Args:
            mac: Panel MAC address.
            callback: Callback function for WebSocket messages.
        """
        client = self._get_client()
        await client.ws_connect(mac, callback)
    
    async def close(self) -> None:
        """Close the session and clean up resources."""
        if self._client:
            await self._client.close()
            self._client = None
        self._panels.clear()
    
    async def __aenter__(self) -> "Session":
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()


# Alias for backwards compatibility
create = Session
