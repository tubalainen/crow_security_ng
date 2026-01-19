"""
Crow Security NG - A modern Python library for the Crow Cloud API.

This library provides async access to Crow Cloud security systems,
including the Shepherd alarm panel series.
"""
from .client import CrowClient
from .models import Panel, Area, Zone, Output, Measurement
from .exceptions import (
    CrowError,
    AuthenticationError,
    ConnectionError,
    ResponseError,
    PanelNotFoundError,
    RateLimitError,
    TimeoutError,
)
from .session import Session

__version__ = "0.1.0"
__author__ = "Crow Security NG Contributors"
__license__ = "MIT"

__all__ = [
    # Main classes
    "CrowClient",
    "Session",
    "Panel",
    # Models
    "Area",
    "Zone", 
    "Output",
    "Measurement",
    # Exceptions
    "CrowError",
    "AuthenticationError",
    "ConnectionError",
    "ResponseError",
    "PanelNotFoundError",
    "RateLimitError",
    "TimeoutError",
]
