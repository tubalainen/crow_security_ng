class CrowSecurityError(Exception):
    """Base exception for Crow Security."""
    pass

class CrowSecurityAuthenticationError(CrowSecurityError):
    """Raised when authentication fails."""
    pass

class CrowSecurityConnectionError(CrowSecurityError):
    """Raised when connection issues occur."""
    pass