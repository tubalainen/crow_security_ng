"""Tests for the exception hierarchy."""
import pytest

from crow_security_ng.exceptions import (
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


class TestCrowError:
    def test_custom_message(self):
        err = CrowError("Something went wrong")
        assert str(err) == "Something went wrong"

    def test_no_message(self):
        err = CrowError()
        assert isinstance(err, Exception)

    def test_is_exception(self):
        assert issubclass(CrowError, Exception)


class TestAuthenticationError:
    def test_is_crow_error(self):
        assert issubclass(AuthenticationError, CrowError)

    def test_with_message(self):
        err = AuthenticationError("Invalid credentials")
        assert "Invalid credentials" in str(err)
        assert isinstance(err, CrowError)


class TestConnectionError:
    def test_is_crow_error(self):
        assert issubclass(ConnectionError, CrowError)


class TestResponseError:
    def test_message_only(self):
        err = ResponseError("Not found")
        assert "Not found" in str(err)
        assert err.status_code is None
        assert err.response_text is None

    def test_with_status_code(self):
        err = ResponseError("Not found", status_code=404)
        assert "Not found" in str(err)
        assert "404" in str(err)
        assert err.status_code == 404

    def test_with_response_text(self):
        err = ResponseError("Bad request", status_code=400, response_text="Invalid JSON")
        assert err.response_text == "Invalid JSON"
        assert err.status_code == 400

    def test_is_crow_error(self):
        assert issubclass(ResponseError, CrowError)


class TestPanelNotFoundError:
    def test_with_mac(self):
        err = PanelNotFoundError("AABBCCDDEEFF")
        assert err.mac == "AABBCCDDEEFF"
        assert "AABBCCDDEEFF" in str(err)

    def test_is_crow_error(self):
        assert issubclass(PanelNotFoundError, CrowError)


class TestRateLimitError:
    def test_without_retry_after(self):
        err = RateLimitError()
        assert err.retry_after is None
        assert "rate limit" in str(err).lower()

    def test_with_retry_after(self):
        err = RateLimitError(retry_after=60)
        assert err.retry_after == 60

    def test_is_crow_error(self):
        assert issubclass(RateLimitError, CrowError)


class TestTimeoutError:
    def test_is_crow_error(self):
        assert issubclass(TimeoutError, CrowError)


class TestInvalidMacError:
    def test_with_mac(self):
        err = InvalidMacError("invalid-mac")
        assert err.mac == "invalid-mac"
        assert "invalid-mac" in str(err)

    def test_is_crow_error(self):
        assert issubclass(InvalidMacError, CrowError)


class TestWebSocketError:
    def test_is_crow_error(self):
        assert issubclass(WebSocketError, CrowError)

    def test_with_message(self):
        err = WebSocketError("WS auth failed")
        assert "WS auth failed" in str(err)


class TestBackwardCompatAliases:
    def test_crow_security_error_alias(self):
        assert CrowSecurityError is CrowError

    def test_authentication_alias(self):
        assert CrowSecurityAuthenticationError is AuthenticationError

    def test_connection_alias(self):
        assert CrowSecurityConnectionError is ConnectionError

    def test_catching_via_alias(self):
        with pytest.raises(CrowSecurityError):
            raise AuthenticationError("test")
