"""
Integration test for PowerTrack SDK expanded functionality.
Tests model instantiation and client method signatures without API calls.
"""
import inspect

# Import without initializing to avoid auth issues
from powertrack_sdk.client import PowerTrackClient
from powertrack_sdk.models import (
    AlertSummary,
    Hardware,
    ReportingCapabilities,
    Site,
    SiteList,
)


def test_basic_models():
    """Test that basic models work correctly."""

    # Test basic models that don't require many parameters
    site = Site(key="S123", name="Test Site")
    assert site.key == "S123"
    assert site.name == "Test Site"

    hardware = Hardware(
        key="H456",
        name="Test Inverter",
        functionCode=5,
        hid=456,
        enableBool=True
    )
    assert hardware.key == "H456"
    assert hardware.name == "Test Inverter"
    assert hardware.functionCode == 5
    assert hardware.hid == 456
    assert hardware.enableBool

    # Test SiteList with Site objects
    sites = [Site(key="S123", name="Test Site")]
    site_list = SiteList(sites)
    assert len(site_list.sites) == 1
    assert site_list.sites[0].key == "S123"

    # Test AlertSummary
    alert_summary = AlertSummary(
        hardwareKey="H123",
        maxSeverity=2,
        count=5
    )
    assert alert_summary.hardwareKey == "H123"
    assert alert_summary.maxSeverity == 2

    # Test ReportingCapabilities
    reporting = ReportingCapabilities(
        canEditAutoReport=True,
        canAddEmailReport=False,
        canAddSummaryReport=True,
        canAddAutoReport=False,
        canAddUserReport=True,
        views=[]
    )
    assert reporting.canEditAutoReport


def test_client_method_signatures():
    """Test that all client methods have correct signatures."""
    expected_signatures = {
        'get_portfolio_overview': [
            'self',
            'customer_id'
            ],
        'get_site_overview': [
            'self',
            'siteId'
            ],
        'get_site_detailed_info': [
            'self',
            'siteId'
            ],
        'get_chart_data': [
            'self',
            'chart_type',
            'siteId',
            'start_date',
            'end_date',
            'bin_size'
            ],
        'get_alert_summary': [
            'self',
            'customer_id',
            'siteId'
            ],
        'get_hardware_diagnostics': [
            'self',
            'hardware_id'
            ],
        'get_reporting_capabilities': ['self'],
        'get_pv_model_curves': [
            'self',
            'model_type'
            ],
        'get_pvsyst_modules': [
            'self',
            'hardware_id',
            'siteId'
            ],
        'get_driver_settings': [
            'self',
            'hardware_id'
            ],
        'get_site_links': [
            'self',
            'siteId'
            ],
        'get_site_shares': [
            'self',
            'siteId'
            ]
    }

    for method_name, expected_params in expected_signatures.items():
        assert hasattr(PowerTrackClient, method_name), f"Missing method: {method_name}"

        sig = inspect.signature(getattr(PowerTrackClient, method_name))
        actual_params = list(sig.parameters.keys())

        assert actual_params == expected_params, (
            f"{method_name} signature mismatch: expected {expected_params}, "
            f"got {actual_params}"
        )
