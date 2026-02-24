"""Constants for the Crow Security NG library."""

BASE_URL = "https://api.crowcloud.xyz"
WS_URL = "wss://websocket.crowcloud.xyz"

# OAuth2 application credentials for the Crow Cloud platform.
# These are the same for all users — they identify the client application,
# not an individual user. The user's email+password are sent alongside these.
# Source: crow_security 0.3.0 PyPI package (confirmed production working).
_CLIENT_ID = "t4WDssse5zzTbRlm8Vi7Evpa8ADz7g4xLiRnYOmx"
_CLIENT_SECRET = (
    "qz8p9hcJNG6p3PJi7nZMva9M7IOOmTmhenPzMb8wV4aMQ4BIrmQpJVDIPyJK3mQ4"
    "LMYmhCwCoalQ4VRIaXXQBNvARrOpcrrO4PBxdyNiSmYOiurXULPk2C38oUVvBeAL"
)

DEFAULT_TIMEOUT = 30
DEFAULT_PAGE_SIZE = 10
