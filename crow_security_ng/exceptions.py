"""Exception hierarchy for the Crow Security NG library."""


class CrowError(Exception):
    """Base exception for all Crow Security errors."""


class AuthenticationError(CrowError):
    """Raised when OAuth2 login fails or the token is rejected."""


class ConnectionError(CrowError):
    """Raised on network-level failures (no response from server)."""


class ResponseError(CrowError):
    """Raised when the API returns an unexpected HTTP error status."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_text: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text

    def __str__(self) -> str:
        base = super().__str__()
        if self.status_code is not None:
            return f"{base} (HTTP {self.status_code})"
        return base


class PanelNotFoundError(CrowError):
    """Raised when the requested panel MAC is not found on the account."""

    def __init__(self, mac: str) -> None:
        super().__init__(f"Panel not found: {mac}")
        self.mac = mac


class RateLimitError(CrowError):
    """Raised when the API returns HTTP 429 Too Many Requests."""

    def __init__(self, retry_after: int | float | None = None) -> None:
        super().__init__("Rate limit exceeded")
        self.retry_after = retry_after


class TimeoutError(CrowError):
    """Raised when a request exceeds the configured timeout."""


class InvalidMacError(CrowError):
    """Raised when a MAC address string is malformed."""

    def __init__(self, mac: str) -> None:
        super().__init__(f"Invalid MAC address: {mac!r}")
        self.mac = mac


class WebSocketError(CrowError):
    """Raised when the WebSocket authentication or subscription fails."""


# ---------------------------------------------------------------------------
# Backward-compatibility aliases
# The original broken crow_security_ng used these names. Keep them so any
# existing code that catches them continues to work.
# ---------------------------------------------------------------------------
CrowSecurityError = CrowError
CrowSecurityAuthenticationError = AuthenticationError
CrowSecurityConnectionError = ConnectionError
