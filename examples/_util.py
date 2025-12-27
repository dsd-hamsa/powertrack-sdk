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
    def get_sites(self, site_list_file: Optional[str] = None, customer_id: Optional[str] = None,
                  limit: Optional[int] = None, filter_active: bool = False, filter_inactive: bool = False) -> SiteList:
        # Get base site list
        if customer_id:
            # For mock, just return sample sites
            site_list = self._sites
        elif site_list_file:
            try:
                site_list = SiteList.from_json_file(site_list_file)
            except Exception:
                # Fall back to built-in sample
                site_list = self._sites
        else:
            site_list = self._sites

        # Apply filters
        filtered_sites = []
        for site in site_list.sites:
            # Mock site status - alternate between active/inactive for demo
            is_active = hash(site.key) % 2 == 0

            if filter_active and not is_active:
                continue
            if filter_inactive and is_active:
                continue

            filtered_sites.append(site)

        # Apply limit
        if limit:
            filtered_sites = filtered_sites[:limit]

        return SiteList(sites=filtered_sites)
        return self._sites

    # Site config
    def get_site_config(self, site_id: str) -> SiteConfig:
        site_id = site_id if site_id.startswith("S") else f"S{site_id}"
        return SiteConfig(
            siteId=site_id,
            name=f"Mock Config for {site_id}",
            timezone="UTC",
            latitude=12.34,
            longitude=56.78,
            elevation=10,
            address="123 Mock St",
            city="Mockville",
            state="MK",
            zipCode="00000",
            country="Mockland",
            installDate="2020-01-01",
            acCapacityKw=100.0,
            dcCapacityKw=120.0,
            moduleCount=400,
            rawData={"mock": True},
        )

    # Hardware list / details
    def get_hardware_list(self, site_id: str):
        # Return mock Hardware list
        from powertrack_sdk.models import Hardware
        return [
            Hardware(
                key="H12345",
                name="Inverter 1",
                functionCode=1,  # Inverter
                hid=12345,
                capacityKw=50.0,
                enableBool=True
            ),
            Hardware(
                key="H67890",
                name="Meter 1",
                functionCode=2,  # Production Meter
                hid=67890,
                capacityKw=None,
                enableBool=True
            )
        ]

    def get_hardware_details(self, hardware_key: str) -> Optional[HardwareDetails]:
        from powertrack_sdk.models import HardwareDetails, Hardware
        summary = Hardware(

            key=hardware_key,

            name=f"Mock {hardware_key}",

            functionCode=1,

            hid=int(hardware_key[1:]) if hardware_key.startswith('H') else 12345

        )
        return HardwareDetails(key=hardware_key, summary=summary, details={"mock": True, "config": "sample"})

    def get_hardware_diagnostics(self, hardware_id: str):
        # Return mock HardwareDiagnostics
        from powertrack_sdk.models import HardwareDiagnostics
        return HardwareDiagnostics(
            key=hardware_id,
            hardwareName="Mock Hardware",
            lastAttempt="2023-01-01T00:00:00Z",
            lastChanged="2023-01-01T00:00:00Z",
            lastCommunication=1672531200000,  # 2023-01-01 in milliseconds
            lastSuccess="2023-01-01T00:00:00Z",
            outOfService=False,
            outOfServiceNote="",
            outOfServiceUntil=None,
            parentKey="S12345",
            readOnly=False,
            timeZone="UTC",
            unitId=1,
            registerSets=[],
            dataBits="",
            baudRate="",
            parity="",
            stopBits="",
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

    def get_alert_summary(self, customer_id: Optional[str] = None, siteId: Optional[str] = None):
        # Return a mock AlertSummaryResponse
        from powertrack_sdk.models import AlertSummary, AlertSummaryResponse
        return AlertSummaryResponse(hardwareSummaries={"H100": AlertSummary(hardwareKey="H100", maxSeverity=2, count=1)})

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
            isMonitored=True,
            cellModemContractEndDate="2025-12-31",
            address={"street": "123 Mock St", "city": "Mock City", "state": "MC", "zip": "00000"},
            cellModemContractStartDate="2020-01-01",
            energyCapacityUnit=1,
            longitude=-74.0060,
            parentKey="C8458",
            weatherMode=1,
            monitoringContractIsManual=False,
            cellModemContractCustomBanner=False,
            monitoringContractWarnDate=None,
            workingStatus="active",
            capacityDcUnit=1,
            elevation=10,
            dailyProductionEstimate=48.0,
            lastChanged="2023-01-01T00:00:00Z",
            monthlyProductionEstimate=1440.0,
            ratedPowerUnit=1,
            monitoringContractCustomBanner=False,
            monitoringContractStatus=1,
            monitoringContractEndDate="2025-12-31",
            estimatedCommissioningDate="2020-01-01",
            cellModemContractAccessNote="",
            cellModemContractTerminateDate=None,
            cellModemContractIsManual=False,
            customerLogo="",
            capacityAc=100,
            customQueryKey="",
            preferredWsForEstimatedInsolation=1,
            requiresPubIp=False,
            defaultQuery=1,
            monitoringContractWillNotRenew=False,
            capacityAcUnit=1,
            status=1,
            latitude=40.7128,
            ratedPower=100,
            advancedSiteConfiguration=False,
            monitoringContractTerminateDate=None,
            actualCommissioningDate="2020-01-01",
            estimatedLosses={},
            cellModemContractWarnDate=None,
            monitoringContractAccessNote="",
            validDataDate="2023-01-01",
            paymentStatus=1,
            capacityDc=120.0,
            monitoringContractStartDate="2020-01-01",
            energyCapacity=100,
            overviewChart1="chart1",
            overviewChart2="chart2",
            cellModemContractWillNotRenew=False,
            siteType=1,
            sitePhotos=None
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

    def get_chart_data(self, chart_type, site_id, start_date=None, end_date=None, bin_size=None):
        # Return mock ChartData
        from powertrack_sdk.models import ChartData, ChartSeries
        series = [
            ChartSeries(
                name="Production",
                key="prod",
                dataXy=[(1640995200, 50.0), (1641081600, 48.0)],  # Sample data
                color="#FF0000",
                customUnit="kWh",
                dataMax=50.0,
                dataMin=48.0,
                diameter=2,
                fitExponent=1,
                header="Production",
                lineColor="#FF0000",
                lineType=0,
                lineWidth=2,
                rightAxis=False,
                units=0,
                useBinnedData=False,
                visible=True,
                xSeriesHeader="Time",
                xSeriesKey="time",
                xSeriesName="Time",
                xUnits="timestamp",
                yAxisIndex=0,
                yMax=50.0,
                yMin=48.0,
                alertMessageMap=None
            )
        ]
        return ChartData(
            allowSmallBinSize=True,
            binSize=bin_size or 1440,
            currentNowBinIndex=0,
            dataNotAvailable=False,
            durations=[{"key": "day", "name": "Day", "value": 1}],
            end=end_date or "2024-01-31T23:59:59Z",
            errorString="",
            hardwareKeys=["H12345"],
            hasAlertMessages=False,
            hasOverriddenQuery=False,
            isCategoryChart=False,
            isSummaryChart=False,
            isUsingDaylightSavings=False,
            key=f"chart_{chart_type}_{site_id}",
            lastChanged="2023-01-01T00:00:00Z",
            lastDataDatetime="2024-01-31T23:59:59Z",
            namedResults={"energy": 98.0},
            renderType=0,
            series=series,
            summaryTable=[{"key": "total", "value": 100.0}],
            start=start_date or "2024-01-01T00:00:00Z"
        )

    # Modeling
    def get_modeling_data(self, site_id: str) -> Optional[ModelingData]:
        from powertrack_sdk.models import ModelingData
        return ModelingData(siteId=site_id, pvConfig={}, inverters=[{"inverterKw": 50}], ts="ts", rawData={})

    def get_register_offsets(self, hardware_id: str) -> Dict[str, Any]:
        # Return mock register offsets
        return {
            "key": hardware_id,
            "lastChanged": "2023-01-01T00:00:00Z",
            "registerOffsets": [
                {
                    "register": "40001",
                    "offset": 0,
                    "scale": 1.0,
                    "description": "Voltage Phase A"
                },
                {
                    "register": "40002",
                    "offset": 100,
                    "scale": 0.1,
                    "description": "Current Phase A"
                }
            ]
        }

    def get_pv_model_curves(self, model_type: str = "efficiencycurvemodels") -> List[Dict[str, Any]]:
        # Return mock PV model curves
        return [
            {"name": "Efficiency at 1000 W/m²", "value": 0.85},
            {"name": "Efficiency at 800 W/m²", "value": 0.82},
            {"name": "Efficiency at 600 W/m²", "value": 0.78},
            {"name": "Efficiency at 400 W/m²", "value": 0.75},
            {"name": "Efficiency at 200 W/m²", "value": 0.70}
        ]

    def get_pvsyst_modules(self, hardware_id: Optional[str] = None, site_id: Optional[str] = None) -> List[Dict[str, Any]]:
        # Return mock PVSyst modules (hardware/site-specific configurations)
        return [
            {"name": "Canadian Solar CS6P-250P", "value": "CS6P-250P"},
            {"name": "LG Electronics LG300N1C-A5", "value": "LG300N1C-A5"},
            {"name": "Sunrun SR-M250-BLK", "value": "SR-M250-BLK"},
            {"name": "Trina Solar TSM-250PA05", "value": "TSM-250PA05"},
            {"name": "Hanwha Q.CELLS Q.PEAK 250", "value": "Q.PEAK-250"}
        ]

    def get_driver_settings(self, hardware_id: str) -> Optional[Dict[str, Any]]:
        # Return mock driver settings
        return {
            "key": hardware_id,
            "lastChanged": "2023-01-01T00:00:00Z",
            "driverSettings": [
                {
                    "name": "dev:KWHoffset",
                    "value": "0",
                    "type": 2
                }
            ]
        }

    def get_driver_settings_list(self, list_id: str) -> List[Dict[str, Any]]:
        # Return mock driver settings list
        return [
            {
                "id": list_id,
                "name": f"Settings List {list_id}",
                "settings": [
                    {"name": "baud_rate", "value": 9600},
                    {"name": "parity", "value": "none"}
                ]
            }
        ]

    def get_driver_list(self, code: int = 2) -> List[Dict[str, Any]]:
        # Return mock driver list (subset from real data)
        # Return different mock data based on function code
        if code == 1:  # Inverters
            return [
                {"name": "ABB, PVS980-58-1818kVA-I", "value": 818, "isGolden": False, "isTest": False, "refGolden": None},
                {"name": "SMA Sunny Tripower", "value": 1234, "isGolden": True, "isTest": False, "refGolden": None}
            ]
        elif code == 4:  # Grid Meters
            return [
                {"name": "AccuEnergy Acuvim II(R-D-5A) Primary Mode(SS)Standard", "value": 19601, "isGolden": True, "isTest": False, "refGolden": None},
                {"name": "Schneider Electric PM5560", "value": 5678, "isGolden": False, "isTest": False, "refGolden": None}
            ]
        elif code == 5:  # Weather Stations
            return [
                {"name": "A8814 Acquisuite+ [Obvius DC = 73] Standard", "value": 881, "isGolden": True, "isTest": False, "refGolden": None},
                {"name": "Campbell Scientific CR1000", "value": 9012, "isGolden": False, "isTest": False, "refGolden": None}
            ]
        else:  # Default (Production Meters)
            return [
                {"name": "AccuEnergy Acuvim II(R-D-5A) Primary Mode(SS)Standard", "value": 19601, "isGolden": True, "isTest": False, "refGolden": None},
                {"name": "A8814 Acquisuite+ [Obvius DC = 73] Standard", "value": 881, "isGolden": True, "isTest": False, "refGolden": None},
                {"name": "ABB, PVS980-58-1818kVA-I", "value": 818, "isGolden": False, "isTest": False, "refGolden": None}
            ]

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
