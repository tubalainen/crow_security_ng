"""Utility functions for the Crow Security NG library."""
from __future__ import annotations

import re
from .exceptions import InvalidMacError


def normalize_mac(mac: str) -> str:
    """
    Normalize a MAC address to lowercase without separators.
    
    Accepts formats like:
    - AA:BB:CC:DD:EE:FF
    - AA-BB-CC-DD-EE-FF
    - AABBCCDDEEFF
    - aa:bb:cc:dd:ee:ff
    - AA BB CC DD EE FF
    
    Returns: aabbccddeeff (lowercase, no separators)
    
    Raises:
        InvalidMacError: If the MAC address is invalid.
    """
    # Remove all common separators and whitespace
    normalized = re.sub(r'[:\-\s.]', '', mac)
    # Convert to lowercase
    normalized = normalized.lower()
    
    # Validate
    if not re.match(r'^[0-9a-f]{12}$', normalized):
        raise InvalidMacError(mac)
    
    return normalized


def format_mac(mac: str, separator: str = ":") -> str:
    """
    Format a MAC address with separators.
    
    Args:
        mac: The MAC address to format (any format accepted).
        separator: The separator to use (default: ':').
        
    Returns:
        Formatted MAC address (e.g., 'AA:BB:CC:DD:EE:FF').
    """
    normalized = normalize_mac(mac)
    pairs = [normalized[i:i+2] for i in range(0, 12, 2)]
    return separator.join(pairs).upper()


def is_valid_mac(mac: str) -> bool:
    """
    Check if a MAC address is valid.
    
    Args:
        mac: The MAC address to validate.
        
    Returns:
        True if valid, False otherwise.
    """
    try:
        normalize_mac(mac)
        return True
    except InvalidMacError:
        return False
