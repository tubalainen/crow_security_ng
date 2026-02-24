"""Crow Security NG — async Python library for the Crow Cloud API."""

from .client import CrowClient
from .exceptions import (
    AuthenticationError,
    ConnectionError,
    CrowError,
    CrowSecurityAuthenticationError,
    CrowSecurityConnectionError,
    CrowSecurityError,
    InvalidMacError,
    PanelNotFoundError,
    RateLimitError,
    ResponseError,
    TimeoutError,
    WebSocketError,
)
from .models import (
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
from .session import Session
from .utils import format_mac, is_valid_mac, normalize_mac

# Backward-compatibility alias — old code that imported CrowSecurityClient still works
CrowSecurityClient = CrowClient

__all__ = [
    # Main entry points
    "CrowClient",
    "Session",
    # Models
    "Panel",
    "Area",
    "Zone",
    "Output",
    "Measurement",
    "Picture",
    "Event",
    # Enums
    "AreaState",
    "AreaCommand",
    "ZoneState",
    # Exceptions
    "CrowError",
    "AuthenticationError",
    "ConnectionError",
    "ResponseError",
    "PanelNotFoundError",
    "RateLimitError",
    "TimeoutError",
    "InvalidMacError",
    "WebSocketError",
    # Utilities
    "normalize_mac",
    "format_mac",
    "is_valid_mac",
    # Backward-compat aliases
    "CrowSecurityClient",
    "CrowSecurityError",
    "CrowSecurityAuthenticationError",
    "CrowSecurityConnectionError",
]
