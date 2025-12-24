"""
Custom exceptions for PowerTrack SDK
"""

from typing import Optional, Dict, Any


class PowerTrackError(Exception):
    """Base exception for PowerTrack SDK errors."""
    pass


class AuthenticationError(PowerTrackError):
    """Raised when authentication fails."""
    pass


class APIError(PowerTrackError):
    """Raised when API requests fail."""

    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data or {}


class ValidationError(PowerTrackError):
    """Raised when input validation fails."""
    pass


class ConfigurationError(PowerTrackError):
    """Raised when SDK configuration is invalid."""
    pass