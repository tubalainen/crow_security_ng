"""Tests for utility functions."""
import pytest

from crow_security_ng.utils import (
    format_mac,
    is_valid_mac,
    normalize_mac,
)
from crow_security_ng.exceptions import InvalidMacError


class TestNormalizeMac:
    """Tests for normalize_mac function."""
    
    def test_already_normalized(self):
        """Test with already normalized MAC."""
        assert normalize_mac("aabbccddeeff") == "aabbccddeeff"
    
    def test_uppercase(self):
        """Test with uppercase MAC."""
        assert normalize_mac("AABBCCDDEEFF") == "aabbccddeeff"
    
    def test_with_colons(self):
        """Test with colon separators."""
        assert normalize_mac("AA:BB:CC:DD:EE:FF") == "aabbccddeeff"
    
    def test_with_dashes(self):
        """Test with dash separators."""
        assert normalize_mac("AA-BB-CC-DD-EE-FF") == "aabbccddeeff"
    
    def test_with_spaces(self):
        """Test with space separators."""
        assert normalize_mac("AA BB CC DD EE FF") == "aabbccddeeff"
    
    def test_with_dots(self):
        """Test with dot separators."""
        assert normalize_mac("AABB.CCDD.EEFF") == "aabbccddeeff"
    
    def test_mixed_case(self):
        """Test with mixed case."""
        assert normalize_mac("aAbBcCdDeEfF") == "aabbccddeeff"
    
    def test_invalid_length(self):
        """Test with invalid length."""
        with pytest.raises(InvalidMacError):
            normalize_mac("AABBCCDD")
    
    def test_invalid_characters(self):
        """Test with invalid characters."""
        with pytest.raises(InvalidMacError):
            normalize_mac("AABBCCDDEEGG")
    
    def test_empty_string(self):
        """Test with empty string."""
        with pytest.raises(InvalidMacError):
            normalize_mac("")


class TestFormatMac:
    """Tests for format_mac function."""
    
    def test_default_separator(self):
        """Test with default colon separator."""
        assert format_mac("aabbccddeeff") == "AA:BB:CC:DD:EE:FF"
    
    def test_dash_separator(self):
        """Test with dash separator."""
        assert format_mac("aabbccddeeff", "-") == "AA-BB-CC-DD-EE-FF"
    
    def test_already_formatted(self):
        """Test with already formatted MAC."""
        assert format_mac("AA:BB:CC:DD:EE:FF") == "AA:BB:CC:DD:EE:FF"


class TestIsValidMac:
    """Tests for is_valid_mac function."""
    
    def test_valid_mac(self):
        """Test with valid MAC."""
        assert is_valid_mac("AABBCCDDEEFF") is True
        assert is_valid_mac("aa:bb:cc:dd:ee:ff") is True
    
    def test_invalid_mac(self):
        """Test with invalid MAC."""
        assert is_valid_mac("invalid") is False
        assert is_valid_mac("AABBCCDDEE") is False
        assert is_valid_mac("") is False
