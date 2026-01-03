"""
Validation utilities for callsigns and modes.
"""
import re
from typing import List, Set

# Valid callsign pattern (simplified - allows most common formats)
CALLSIGN_PATTERN = re.compile(r'^[A-Z0-9]{1,3}[0-9][A-Z0-9]{0,3}[A-Z]$', re.IGNORECASE)

# PSKReporter supported digital modes
PSKREPORTER_MODES: Set[str] = {
    'FT8', 'FT4', 'PSK31', 'PSK63', 'PSK125', 'CW', 'RTTY',
    'JT65', 'JT9', 'WSPR', 'APRS', 'FSK441', 'JTMS', 'ISCAT',
    'MSK144', 'QRA64', 'T10', 'WSPR-15'
}

# Future: Voice modes for other sources
VOICE_MODES: Set[str] = {
    'SSB', 'AM', 'FM', 'USB', 'LSB'
}


def validate_callsign(callsign: str) -> bool:
    """
    Validate a callsign or prefix format.
    Supports both full callsigns (e.g., "N4OG") and prefixes (e.g., "N4", "W1").
    
    Args:
        callsign: Callsign or prefix to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not callsign:
        return False
    
    # Normalize to uppercase
    callsign = callsign.upper().strip()
    
    # Check length (prefixes can be as short as 1 character, full callsigns up to 15)
    if len(callsign) < 1 or len(callsign) > 15:
        return False
    
    # Allow simple prefix patterns (1-3 letters/numbers, optionally followed by a digit)
    # Examples: "N4", "W1", "K", "VE", "G", "F", etc.
    PREFIX_PATTERN = re.compile(r'^[A-Z0-9]{1,4}$', re.IGNORECASE)
    
    # Check if it's a valid prefix (shorter, simpler pattern)
    if len(callsign) <= 4:
        if PREFIX_PATTERN.match(callsign):
            return True
    
    # Check if it's a full callsign (longer, more complex pattern)
    if len(callsign) >= 3:
        if CALLSIGN_PATTERN.match(callsign):
            return True
    
    return False


def validate_modes(modes: List[str], data_source: str) -> tuple[bool, str]:
    """
    Validate mode names for a specific data source.
    Empty list is allowed (matches all modes).
    
    Args:
        modes: List of mode names to validate (empty list = match all modes)
        data_source: Data source name (e.g., 'pskreporter')
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Empty modes list is valid (matches all modes)
    if not modes:
        return True, ""
    
    modes_upper = [m.upper().strip() for m in modes if m.strip()]
    
    if not modes_upper:
        return False, "No valid modes provided"
    
    # Validate based on data source
    if data_source == 'pskreporter':
        valid_modes = PSKREPORTER_MODES
        invalid = [m for m in modes_upper if m not in valid_modes]
        if invalid:
            return False, f"Invalid modes for PSKReporter (digital only): {', '.join(invalid)}. Valid modes: {', '.join(sorted(valid_modes))}"
    else:
        # Future: Add validation for other sources
        # For now, allow any mode for future sources
        pass
    
    return True, ""


def parse_modes_string(modes_str: str) -> List[str]:
    """
    Parse a comma-separated modes string into a list.
    
    Args:
        modes_str: Comma-separated string of modes
        
    Returns:
        List of normalized mode names
    """
    if not modes_str:
        return []
    
    modes = [m.strip().upper() for m in modes_str.split(',') if m.strip()]
    return modes


def get_default_modes(data_source: str) -> List[str]:
    """
    Get default modes for a data source.
    
    Args:
        data_source: Data source name
        
    Returns:
        List of default mode names
    """
    if data_source == 'pskreporter':
        return ['FT8', 'FT4', 'PSK31', 'CW', 'RTTY']
    # Future: Add defaults for other sources
    return []
