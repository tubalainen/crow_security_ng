"""Custom exceptions for the Crow Security NG library."""
from __future__ import annotations


class CrowError(Exception):
    """Base exception for all Crow Security errors."""
    
    def __init__(self, message: str = "An error occurred with the Crow API") -> None:
        self.message = message
        super().__init__(self.message)


class AuthenticationError(CrowError):
    """Raised when authentication fails."""
    
    def __init__(self, message: str = "Authentication failed. Check your credentials.") -> None:
        super().__init__(message)


class ConnectionError(CrowError):
    """Raised when connection to the API fails."""
    
    def __init__(self, message: str = "Failed to connect to Crow Cloud.") -> None:
        super().__init__(message)


class ResponseError(CrowError):
    """Raised when the API returns an error response."""
    
    def __init__(
        self, 
        status_code: int, 
        message: str = "API returned an error response",
        response_text: str | None = None
    ) -> None:
        self.status_code = status_code
        self.response_text = response_text
        full_message = f"{message} (status: {status_code})"
        if response_text:
            full_message += f": {response_text[:200]}"  # Limit response text length
        super().__init__(full_message)


class PanelNotFoundError(CrowError):
    """Raised when the requested panel is not found."""
    
    def __init__(self, mac: str) -> None:
        self.mac = mac
        super().__init__(f"Panel with MAC address '{mac}' not found.")


class RateLimitError(CrowError):
    """Raised when rate limit is exceeded."""
    
    def __init__(
        self, 
        retry_after: int | None = None,
        message: str = "Rate limit exceeded"
    ) -> None:
        self.retry_after = retry_after
        if retry_after:
            message = f"{message}. Retry after {retry_after} seconds."
        super().__init__(message)


class TimeoutError(CrowError):
    """Raised when a request times out."""
    
    def __init__(self, message: str = "Request timed out") -> None:
        super().__init__(message)


class WebSocketError(CrowError):
    """Raised when WebSocket connection fails."""
    
    def __init__(self, message: str = "WebSocket connection error") -> None:
        super().__init__(message)


class InvalidMacError(CrowError):
    """Raised when an invalid MAC address is provided."""
    
    def __init__(self, mac: str) -> None:
        self.mac = mac
        super().__init__(
            f"Invalid MAC address format: '{mac}'. "
            "Expected 12 hexadecimal characters."
        )
