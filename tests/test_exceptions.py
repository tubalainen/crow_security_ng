"""Tests for exceptions."""
import pytest

from crow_security_ng.exceptions import (
    AuthenticationError,
    ConnectionError,
    CrowError,
    InvalidMacError,
    PanelNotFoundError,
    RateLimitError,
    ResponseError,
    TimeoutError,
)


class TestCrowError:
    """Tests for base CrowError."""
    
    def test_default_message(self):
        """Test default error message."""
        err = CrowError()
        assert "error occurred" in str(err).lower()
    
    def test_custom_message(self):
        """Test custom error message."""
        err = CrowError("Custom error message")
        assert str(err) == "Custom error message"


class TestAuthenticationError:
    """Tests for AuthenticationError."""
    
    def test_default_message(self):
        """Test default error message."""
        err = AuthenticationError()
        assert "authentication" in str(err).lower()
    
    def test_is_crow_error(self):
        """Test that it inherits from CrowError."""
        err = AuthenticationError()
        assert isinstance(err, CrowError)


class TestResponseError:
    """Tests for ResponseError."""
    
    def test_with_status_code(self):
        """Test with status code only."""
        err = ResponseError(404)
        assert err.status_code == 404
        assert "404" in str(err)
    
    def test_with_message(self):
        """Test with custom message."""
        err = ResponseError(500, "Server error")
        assert "Server error" in str(err)
    
    def test_with_response_text(self):
        """Test with response text."""
        err = ResponseError(400, "Bad request", "Invalid JSON")
        assert err.response_text == "Invalid JSON"
        assert "Invalid JSON" in str(err)
    
    def test_long_response_text_truncated(self):
        """Test that long response text is truncated."""
        long_text = "x" * 500
        err = ResponseError(400, "Bad request", long_text)
        assert len(str(err)) < 500  # Should be truncated


class TestPanelNotFoundError:
    """Tests for PanelNotFoundError."""
    
    def test_with_mac(self):
        """Test with MAC address."""
        err = PanelNotFoundError("AABBCCDDEEFF")
        assert err.mac == "AABBCCDDEEFF"
        assert "AABBCCDDEEFF" in str(err)


class TestRateLimitError:
    """Tests for RateLimitError."""
    
    def test_without_retry_after(self):
        """Test without retry-after value."""
        err = RateLimitError()
        assert err.retry_after is None
        assert "rate limit" in str(err).lower()
    
    def test_with_retry_after(self):
        """Test with retry-after value."""
        err = RateLimitError(retry_after=60)
        assert err.retry_after == 60
        assert "60" in str(err)


class TestInvalidMacError:
    """Tests for InvalidMacError."""
    
    def test_with_mac(self):
        """Test with invalid MAC."""
        err = InvalidMacError("invalid-mac")
        assert err.mac == "invalid-mac"
        assert "invalid-mac" in str(err)
        assert "12" in str(err)  # Should mention expected length
