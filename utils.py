"""
Utility functions for the Edge IoT system.

This module provides helper functions used by both bridge.py and app.py:
- Data validation and sanitization
- Statistical calculations
- Time formatting and conversions
- Error handling utilities
"""

import json
from datetime import datetime, timezone
from typing import Any, Optional


def is_valid_json(text: str) -> bool:
    """
    Check if a string is valid JSON.
    
    This is used to validate payloads before processing.
    Returns True if the string can be parsed as JSON, False otherwise.
    
    Args:
        text: String to validate
        
    Returns:
        True if valid JSON, False otherwise
    """
    if not isinstance(text, str):
        return False
    try:
        json.loads(text)
        return True
    except (json.JSONDecodeError, ValueError):
        return False


def sanitize_device_id(device_id: str) -> str:
    """
    Sanitize a device ID to ensure it's safe to use.
    
    Device IDs come from MQTT topics and might contain unsafe characters.
    We ensure the ID only contains alphanumeric characters, hyphens, and underscores.
    
    Args:
        device_id: Raw device ID from MQTT topic
        
    Returns:
        Sanitized device ID (alphanumeric, hyphens, underscores only)
    """
    if not isinstance(device_id, str):
        return "unknown"
    
    # Remove any character that's not alphanumeric, hyphen, or underscore
    sanitized = ''.join(c if c.isalnum() or c in '-_' else '' for c in device_id)
    
    # Ensure we have at least something
    return sanitized if sanitized else "unknown"


def calculate_mean(values: list[float]) -> Optional[float]:
    """
    Calculate the mean (average) of a list of numbers.
    
    Returns None if list is empty (avoid division by zero).
    This is safer than just using sum()/len() which would crash on empty list.
    
    Args:
        values: List of numeric values
        
    Returns:
        Mean value, or None if list is empty
    """
    if not values or len(values) == 0:
        return None
    return sum(values) / len(values)


def calculate_std_dev(values: list[float]) -> Optional[float]:
    """
    Calculate the standard deviation of a list of numbers.
    
    Standard deviation measures how spread out the data is.
    - Low std dev: data is clustered closely around mean
    - High std dev: data is widely scattered
    
    Returns None if there's insufficient data for calculation.
    
    Args:
        values: List of numeric values
        
    Returns:
        Standard deviation, or None if insufficient data
    """
    if not values or len(values) < 2:
        return None
    
    mean = calculate_mean(values)
    if mean is None:
        return None
    
    # Calculate variance (average of squared differences from mean)
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    
    # Standard deviation is square root of variance
    return variance ** 0.5


def format_timestamp(iso_string: Optional[str]) -> str:
    """
    Format an ISO timestamp string to human-readable format.
    
    Converts from: 2024-01-15T14:30:45.123456+00:00
    To:            2024-01-15 14:30:45
    
    Args:
        iso_string: ISO format timestamp string or None
        
    Returns:
        Formatted timestamp (YYYY-MM-DD HH:MM:SS) or empty string if invalid
    """
    if not iso_string:
        return ""
    
    try:
        dt = datetime.fromisoformat(iso_string)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return iso_string or ""


def get_utc_timestamp() -> str:
    """
    Get current time as ISO format UTC timestamp.
    
    Returns a string like: 2024-01-15T14:30:45.123456+00:00
    This is useful for tagging events with exact timestamps.
    
    Returns:
        Current UTC timestamp in ISO format
    """
    return datetime.now(timezone.utc).isoformat()


def clamp(value: float, min_val: float, max_val: float) -> float:
    """
    Clamp a value to a specified range.
    
    If value < min, return min.
    If value > max, return max.
    Otherwise return value.
    
    This is useful for keeping values within valid ranges.
    
    Args:
        value: The value to clamp
        min_val: Minimum allowed value
        max_val: Maximum allowed value
        
    Returns:
        Value clamped to [min_val, max_val]
    """
    return max(min_val, min(value, max_val))


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    Safely divide two numbers, returning a default if denominator is zero.
    
    Prevents division by zero errors.
    
    Args:
        numerator: The dividend
        denominator: The divisor
        default: Value to return if denominator is 0
        
    Returns:
        numerator / denominator, or default if denominator is 0
    """
    if denominator == 0:
        return default
    return numerator / denominator
