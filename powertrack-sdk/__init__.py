"""
PowerTrack SDK - Python SDK for AlsoEnergy PowerTrack API

A comprehensive SDK for interacting with the AlsoEnergy PowerTrack platform,
providing easy access to site data, hardware configurations, alerts, and modeling.

Example:
    from powertrack_sdk import PowerTrackClient

    client = PowerTrackClient()
    sites = client.get_sites()
"""

__version__ = "1.0.0"
__author__ = "PowerTrack SDK Team"

from .client import PowerTrackClient
from .auth import AuthManager
from .models import (
    Site, Hardware, AlertTrigger, SiteConfig, ModelingData,
    HardwareDetails, SiteData, SiteList, SiteOverview,
    PortfolioMetrics, ChartData, ChartSeries, AlertSummary,
    AlertSummaryResponse, HardwareDiagnostics, SiteDetailedInfo,
    ReportingCapabilities, UpdateResult
)
from .exceptions import (
    PowerTrackError,
    AuthenticationError,
    APIError,
    ValidationError,
    ConfigurationError
)

__all__ = [
    "PowerTrackClient",
    "AuthManager",
    "PowerTrackError",
    "AuthenticationError",
    "APIError",
    "ValidationError",
    "ConfigurationError",
    "Site",
    "Hardware",
    "AlertTrigger",
    "SiteConfig",
    "ModelingData",
    "HardwareDetails",
    "SiteData",
    "SiteList",
    "SiteOverview",
    "PortfolioMetrics",
    "ChartData",
    "ChartSeries",
    "AlertSummary",
    "AlertSummaryResponse",
    "HardwareDiagnostics",
    "SiteDetailedInfo",
    "ReportingCapabilities",
    "UpdateResult",
]