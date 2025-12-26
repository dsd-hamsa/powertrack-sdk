"""
Common utilities for examples.
Provides get_client(use_mock=False) which returns either a real PowerTrackClient
or a simple MockClient for local testing. Also includes JSON save/load helpers.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable, Iterable, Tuple

from powertrack_sdk import PowerTrackClient
from powertrack_sdk.models import Site, SiteList, SiteConfig, SiteData, HardwareDetails, ModelingData, AlertTrigger
from concurrent.futures import ThreadPoolExecutor, as_completed
from time import sleep
import math
import traceback

logger = logging.getLogger(__name__)


class MockClient:
    """A small mock client that mimics PowerTrackClient methods used by examples.

    This mock is intentionally minimal and deterministic so examples/tests can run
    without network or credentials. It returns small sample objects.
    """

    def __init__(self):
        # Create a couple of fake sites
        self._sites = SiteList([
            {"key": "S10001", "name": "Mock Site 1"},
            {"key": "S10002", "name": "Mock Site 2"},
        ])

    # Site listing
    def get_sites(self, site_list_file: Optional[str] = None) -> SiteList:
        if site_list_file:
            try:
                return SiteList.from_json_file(site_list_file)
            except Exception:
                # Fall back to built-in sample
                return self._sites
        return self._sites

    # Site config
    def get_site_config(self, site_id: str) -> SiteConfig:
        site_id = site_id if site_id.startswith("S") else f"S{site_id}"
        return SiteConfig(
            site_id=site_id,
            name=f"Mock Config for {site_id}",
            timezone="UTC",
            latitude=12.34,
            longitude=56.78,
            elevation=10,
            address="123 Mock St",
            city="Mockville",
            state="MK",
            zip_code="00000",
            country="Mockland",
            install_date="2020-01-01",
            ac_capacity_kw=100.0,
            dc_capacity_kw=120.0,
            module_count=400,
            raw_data={"mock": True},
        )

    # Hardware list / details
    def get_hardware_list(self, site_id: str):
        # Return mock Hardware list
        from powertrack_sdk.models import Hardware
        return [
            Hardware(
                key="H12345",
                name="Inverter 1",
                function_code=1,  # Inverter
                hid=12345,
                capacity_kw=50.0,
                enable_bool=True
            ),
            Hardware(
                key="H67890",
                name="Meter 1",
                function_code=2,  # Production Meter
                hid=67890,
                capacity_kw=None,
                enable_bool=True
            )
        ]

    def get_hardware_details(self, hardware_key: str) -> Optional[HardwareDetails]:
        from powertrack_sdk.models import HardwareDetails, Hardware
        summary = Hardware(
            key=hardware_key,
            name=f"Mock {hardware_key}",
            function_code=1,
            hid=int(hardware_key[1:]) if hardware_key.startswith('H') else 12345
        )
        return HardwareDetails(key=hardware_key, summary=summary, details={"mock": True, "config": "sample"})

    def get_hardware_diagnostics(self, hardware_id: str):
        # Return mock HardwareDiagnostics
        from powertrack_sdk.models import HardwareDiagnostics
        return HardwareDiagnostics(
            key=hardware_id,
            hardware_name=f"Mock {hardware_id}",
            last_attempt="2023-01-01T12:00:00Z",
            last_changed="2023-01-01T12:00:00Z",
            last_communication=1640995200,
            last_success="2023-01-01T12:00:00Z",
            out_of_service=False,
            out_of_service_note="",
            out_of_service_until=None,
            parent_key="S60308",
            read_only=False,
            time_zone="UTC",
            unit_id=1,
            register_sets=[{"name": "Basic", "registers": []}]
        )

    def get_site_hardware_production(self, site_id: str):
        # Return mock production data
        return [
            {
                "key": "H12345",
                "name": "Inverter 1",
                "today": 48.0,
                "thisMonth": 1440.0,
                "lastMonth": 1400.0,
                "lifetime": 50000.0
            },
            {
                "key": "H67890",
                "name": "Meter 1",
                "today": 50.0,
                "thisMonth": 1500.0,
                "lastMonth": 1450.0,
                "lifetime": 55000.0
            }
        ]

    # Alerts
    def get_alert_triggers(self, hardware_key: str, last_changed: Optional[str] = None) -> Optional[AlertTrigger]:
        # Return a sample alert trigger for one hardware key
        return AlertTrigger(key=hardware_key, triggers=[{"name": "MockTrigger", "isActive": True}])

    def get_alert_summary(self, customer_id: Optional[str] = None, site_id: Optional[str] = None):
        # Return a small dict-like response formatted like AlertSummaryResponse.hardware_summaries
        return type("_", (), {"hardware_summaries": {"H100": type("s", (), {"count": 1, "max_severity": 2})}})()

    def get_portfolio_overview(self, customer_id: str):
        # Return a mock PortfolioMetrics
        from powertrack_sdk.models import PortfolioMetrics, SiteOverview
        sites = [
            SiteOverview(
                key="S10001",
                name="Mock Site 1",
                availability=95.0,
                availabilityLoss=5.0,
                calculatedInverterAvailability=98.0,
                capacityDc=120.0,
                chargeDischarge=None,
                customColumnData=["data1", "data2"],
                downtimeLoss=2.0,
                energyAvailability=90.0,
                energyAvailabilityLoss=10.0,
                energyCapacity=None,
                energyLoss=5.0,
                energyRatio=0.95,
                gridOffline=0,
                ground=0,
                id=10001,
                insolation=5.0,
                inverterCount=2,
                inverterFaults=0,
                irradiance=800.0,
                kioskStatus=1,
                kiosks=1,
                kwPercent=50.0,
                kwhPercent=45.0,
                lastDataUTC="2023-01-01T12:00:00Z",
                lastMonth=1000,
                lastUpload="2023-01-01T12:00:00Z",
                lastYear=12000,
                lifetime=50000,
                message="OK",
                monitoredSiteType=1,
                parentKey=customer_id,
                paymentStatus=1,
                performanceIndex=85.0,
                performanceTestDelta=0.5,
                performanceTestStatus=1,
                performanceTestValue=100.0,
                power=50.0,
                power24=1200,
                power24Est=1150.0,
                powerAvg15=48.0,
                powerAvg15Exp=52.0,
                today=48.0,
                pvCapacityAc=100.0,
                pvCapacityDc=120.0,
                ratedPower=None,
                availableEnergy=None,
                reminderColor="green",
                revenueLoss=100.0,
                rolling24Kw=[1150, 1140, 1160],  # List[int]
                rolling24KwIdx=95,  # int
                ruleToolSummary={},  # Dict[str, Any]
                sizeDC=120.0,
                sizeKW=100.0,
                soilingLoss=2.0,
                stateOfCharge=None,
                status=1,
                alertSeverity=0,
                alertName="",
                systemSize=100.0,
                thisMonth=800,
                thisYear=9600,
                timeZone="UTC",
                todayEstimated=48.0,
                todayPercent=48.0,
                type=1,  # int
                todayAnd7DayAverageKw={}  # Dict[str, Any]
            )
        ]
        return PortfolioMetrics(
            customerId=customer_id,
            sites=sites,
            customColumnNames=["Col1", "Col2"],
            lastChanged="2023-01-01T00:00:00Z",
            merge=False,
            mergeHash=""
        )

    def get_site_overview(self, site_id: str):
        # Return a mock SiteOverview for the site
        from powertrack_sdk.models import SiteOverview
        return SiteOverview(
            key=site_id,
            name=f"Mock {site_id}",
            availability=95.0,
            availabilityLoss=5.0,
            calculatedInverterAvailability=98.0,
            capacityDc=120.0,
            chargeDischarge=None,
            customColumnData=["data1", "data2"],
            downtimeLoss=2.0,
            energyAvailability=90.0,
            energyAvailabilityLoss=10.0,
            energyCapacity=None,
            energyLoss=5.0,
            energyRatio=0.95,
            gridOffline=0,
            ground=0,
            id=int(site_id[1:]),
            insolation=5.0,
            inverterCount=2,
            inverterFaults=0,
            irradiance=800.0,
            kioskStatus=1,
            kiosks=1,
            kwPercent=50.0,
            kwhPercent=45.0,
            lastDataUTC="2023-01-01T12:00:00Z",
            lastMonth=1000,
            lastUpload="2023-01-01T12:00:00Z",
            lastYear=12000,
            lifetime=50000,
            message="OK",
            monitoredSiteType=1,
            parentKey="C8458",
            paymentStatus=1,
            performanceIndex=85.0,
            performanceTestDelta=0.5,
            performanceTestStatus=1,
            performanceTestValue=100.0,
            power=50.0,
            power24=1200,
            power24Est=1150.0,
            powerAvg15=48.0,
            powerAvg15Exp=52.0,
            pvCapacityAc=100.0,
            pvCapacityDc=120.0,
            ratedPower=None,
            availableEnergy=None,
            reminderColor="green",
            revenueLoss=100.0,
            rolling24Kw=[1150, 1140, 1160],
            rolling24KwIdx=95,
            ruleToolSummary={},
            sizeDC=120.0,
            sizeKW=100.0,
            soilingLoss=2.0,
            stateOfCharge=None,
            status=1,
            alertSeverity=0,
            alertName="",
            systemSize=100.0,
            thisMonth=800,
            thisYear=9600,
            timeZone="UTC",
            today=48.0,
            todayEstimated=48.0,
            todayPercent=48.0,
            type=1,
            todayAnd7DayAverageKw={},
            estimatedCommissioningDate=None,
            expirationDate=None
        )

    def get_site_detailed_info(self, site_id: str):
        # Return a mock SiteDetailedInfo
        from powertrack_sdk.models import SiteDetailedInfo
        return SiteDetailedInfo(
            key=site_id,
            name=f"Mock {site_id}",
            is_monitored=True,
            cell_modem_contract_end_date="2025-12-31",
            address={"street": "123 Mock St", "city": "Mock City", "state": "MC", "zip": "00000"},
            cell_modem_contract_start_date="2020-01-01",
            energy_capacity_unit=1,
            longitude=-74.0060,
            parent_key="C8458",
            weather_mode=1,
            monitoring_contract_is_manual=False,
            cell_modem_contract_custom_banner=False,
            monitoring_contract_warn_date=None,
            working_status="active",
            capacity_dc_unit=1,
            elevation=10,
            daily_production_estimate=48.0,
            last_changed="2023-01-01T00:00:00Z",
            monthly_production_estimate=1440.0,
            rated_power_unit=1,
            monitoring_contract_custom_banner=False,
            monitoring_contract_status=1,
            monitoring_contract_end_date="2025-12-31",
            estimated_commissioning_date="2020-01-01",
            cell_modem_contract_access_note="",
            cell_modem_contract_terminate_date=None,
            cell_modem_contract_is_manual=False,
            customer_logo="",
            capacity_ac=100,
            custom_query_key="",
            preferred_ws_for_estimated_insolation=1,
            requires_pub_ip=False,
            default_query=1,
            monitoring_contract_will_not_renew=False,
            capacity_ac_unit=1,
            status=1,
            latitude=40.7128,
            rated_power=100,
            advanced_site_configuration=False,
            monitoring_contract_terminate_date=None,
            actual_commissioning_date="2020-01-01",
            estimated_losses={},
            cell_modem_contract_warn_date=None,
            monitoring_contract_access_note="",
            valid_data_date="2023-01-01",
            payment_status=1,
            capacity_dc=120.0,
            monitoring_contract_start_date="2020-01-01",
            energy_capacity=100,
            overview_chart1="chart1",
            overview_chart2="chart2",
            cell_modem_contract_will_not_renew=False,
            site_type=1,
            site_photos=None
        )

    def get_chart_definitions(self):
        # Return mock chart definitions
        return [
            {
                "id": 1,
                "name": "Production Overview",
                "description": "Daily production chart",
                "type": "line"
            },
            {
                "id": 2,
                "name": "Inverter Performance",
                "description": "Inverter efficiency chart",
                "type": "bar"
            }
        ]

    def get_chart_data(self, chart_type, site_id, start_date=None, end_date=None):
        # Return mock ChartData
        from powertrack_sdk.models import ChartData, ChartSeries
        series = [
            ChartSeries(
                name="Production",
                key="prod",
                dataXy=[(1640995200, 50.0), (1641081600, 48.0)],  # Sample data
                color="#FF0000",
                custom_unit="kWh",
                data_max=50.0,
                data_min=48.0,
                diameter=2,
                fit_exponent=1,
                header="Production",
                line_color="#FF0000",
                line_type=0,
                line_width=2,
                right_axis=False,
                units=0,
                use_binned_data=False,
                visible=True,
                x_series_header="Time",
                x_series_key="time",
                x_series_name="Time",
                x_units="timestamp",
                y_axis_index=0,
                y_max=50.0,
                y_min=48.0,
                alert_message_map=None
            )
        ]
        return ChartData(
            allow_small_bin_size=True,
            bin_size=1440,
            current_now_bin_index=0,
            data_not_available=False,
            durations=[],
            end=end_date or "2024-01-31T23:59:59Z",
            error_string="",
            hardware_keys=["H12345"],
            has_alert_messages=False,
            has_overridden_query=False,
            is_category_chart=False,
            is_summary_chart=False,
            is_using_daylight_savings=False,
            key=f"chart_{chart_type}_{site_id}",
            last_changed="2023-01-01T00:00:00Z",
            last_data_datetime="2024-01-31T23:59:59Z",
            named_results={"energy": 98.0},
            render_type=0,
            series=series,
            start=start_date or "2024-01-01T00:00:00Z"
        )

    # Modeling
    def get_modeling_data(self, site_id: str) -> Optional[ModelingData]:
        return ModelingData(site_id=site_id, pv_config={}, inverters=[{"inverterKw": 50}], ts="ts", raw_data={})

    # Comprehensive site data
    def get_site_data(self, site_id: str, include_hardware: bool = True, include_alerts: bool = True, include_modeling: bool = True) -> SiteData:
        site = Site(key=site_id, name=f"Mock {site_id}")
        config = self.get_site_config(site_id)
        hardware = []
        alerts = []
        modeling = self.get_modeling_data(site_id) if include_modeling else None
        if include_alerts:
            at = self.get_alert_triggers("H100")
            alerts = [at] if at is not None else []
        return SiteData(site=site, config=config, hardware=hardware, alerts=alerts, modeling=modeling)


def get_client(use_mock: bool = False):
    """Return a client instance.

    If `use_mock` is True, returns a MockClient. Otherwise returns a real
    `PowerTrackClient()` instance which uses the SDK authentication behavior.
    """
    if use_mock:
        return MockClient()
    return PowerTrackClient()


def retry_call(fn: Callable, *args, retries: int = 2, backoff: float = 0.5, timeout: Optional[float] = None, **kwargs) -> Tuple[bool, Any]:
    """Call fn(*args, **kwargs) with retries and exponential backoff.

    Returns (success, result_or_exception).
    """
    attempt = 0
    while True:
        try:
            res = fn(*args, **kwargs)
            return True, res
        except Exception as e:
            attempt += 1
            if attempt > retries:
                return False, e
            sleep_seconds = backoff * (2 ** (attempt - 1))
            sleep(sleep_seconds)


def parallel_map(func: Callable[[Any], Any], items: Iterable[Any], workers: int = 5, retries: int = 2, backoff: float = 0.5, timeout: Optional[float] = None) -> List[Tuple[Any, bool, Any]]:
    """Apply func to items in parallel with retries. Returns list of (item, success, result_or_exception).
    """
    results: List[Tuple[Any, bool, Any]] = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        future_to_item = {}
        for item in items:
            future = ex.submit(retry_call, func, item, retries=retries, backoff=backoff, timeout=timeout)
            future_to_item[future] = item

        for fut in as_completed(future_to_item):
            item = future_to_item[fut]
            try:
                ok, res = fut.result()
            except Exception as e:
                ok = False
                res = e
            results.append((item, ok, res))
    return results


def save_json(obj: Any, path: str):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)


def load_site_list(path: str) -> SiteList:
    """Load a SiteList from a JSON file.

    Raises FileNotFoundError if the file doesn't exist.
    """
    return SiteList.from_json_file(path)


def ensure_dir(path: str):
    Path(path).mkdir(parents=True, exist_ok=True)
