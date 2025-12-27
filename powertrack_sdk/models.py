"""
Data models for PowerTrack SDK

Defines classes representing PowerTrack API data structures.
"""

from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Site:
    """Represents a PowerTrack site."""
    key: str
    name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.name:
            self.name = self.key


@dataclass
class Hardware:
    """Represents a hardware device."""
    key: str
    name: str
    functionCode: Optional[int] = None
    hid: Optional[int] = None
    shortName: Optional[str] = None
    serialNum: Optional[str] = None
    mfrModel: Optional[str] = None
    deviceId: Optional[str] = None
    installDate: Optional[str] = None
    deviceAddress: Optional[str] = None
    port: Optional[str] = None
    unitId: Optional[str] = None
    baud: Optional[str] = None
    gatewayId: Optional[str] = None
    enableBool: bool = True
    hardwareStatus: Optional[str] = None
    capacityKw: Optional[float] = None
    inverterKw: Optional[float] = None
    driverName: Optional[str] = None
    outOfService: bool = False

    @property
    def type_name(self) -> str:
        """Get human-readable hardware type name."""
        # Import here to avoid circular imports
        hardware_types = {
            1: "Inverter (PV)",
            2: "Production Meter (PM)",
            3: "Type 3",
        }
        if self.functionCode is None:
            return "Unknown"
        return hardware_types.get(self.functionCode, f"Type {self.functionCode}")


@dataclass
class AlertTrigger:
    """Represents an alert trigger configuration."""
    key: str
    parentKey: Optional[str] = None
    assetCode: Optional[str] = None
    calculatedCapacity: Optional[float] = None
    capacity: Optional[float] = None
    lastChanged: Optional[str] = None
    isActive: bool = False
    checkNoSnow: bool = False
    sunMinElevation: Optional[float] = None
    delayHoursTrigger: Optional[float] = None
    delayHoursResolve: Optional[float] = None
    checkSun: bool = False
    hasImpact: bool = False
    impact: int = 0
    triggers: List[Dict[str, Any]] = field(default_factory=list)
    defaultTriggers: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def active_triggers(self) -> List[Dict[str, Any]]:
        """Get list of active triggers."""
        return [t for t in self.triggers if t.get('isActive', False)]


@dataclass
class SiteConfig:
    """Represents site configuration data."""
    siteId: str
    name: Optional[str] = None
    timezone: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    elevation: Optional[float] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zipCode: Optional[str] = None
    country: Optional[str] = None
    installDate: Optional[str] = None
    acCapacityKw: Optional[float] = None
    dcCapacityKw: Optional[float] = None
    moduleCount: Optional[int] = None
    rawData: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelingData:
    """Represents site modeling data."""
    siteId: str
    pvConfig: Dict[str, Any] = field(default_factory=dict)
    inverters: List[Dict[str, Any]] = field(default_factory=list)
    ts: Optional[str] = None
    rawData: Dict[str, Any] = field(default_factory=dict)

    @property
    def total_capacity_kw(self) -> float:
        """Get total modeled capacity."""
        return sum(inv.get('inverterKw', 0) for inv in self.inverters)


@dataclass
class HardwareDetails:
    """Represents detailed hardware configuration."""
    key: str
    summary: Hardware
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SiteData:
    """Represents comprehensive site data."""
    site: Site
    config: Optional[SiteConfig] = None
    hardware: List[HardwareDetails] = field(default_factory=list)
    alerts: List[AlertTrigger] = field(default_factory=list)
    modeling: Optional[ModelingData] = None
    fetchedAt: Optional[datetime] = None

    @property
    def hardware_count(self) -> int:
        """Get total hardware count."""
        return len(self.hardware)

    @property
    def active_alerts_count(self) -> int:
        """Get count of active alerts."""
        return sum(len(alert.active_triggers) for alert in self.alerts)


class SiteList:
    """Represents a list of sites with metadata."""

    def __init__(self, sites: List[Union[Site, Dict[str, Any]]], metadata: Optional[Dict[str, Any]] = None):
        """
        Initialize site list.

        Args:
            sites: List of Site objects or site dictionaries
            metadata: Additional metadata
        """
        self.sites = []
        self.metadata = metadata or {}

        for site_data in sites:
            if isinstance(site_data, Site):
                self.sites.append(site_data)
            elif isinstance(site_data, dict):
                # Extract valid Site fields, put extras in metadata
                site_kwargs = {}
                metadata = {}

                for key, value in site_data.items():
                    if key in ['key', 'name']:
                        site_kwargs[key] = value
                    else:
                        metadata[key] = value

                if metadata:
                    site_kwargs['metadata'] = metadata

                self.sites.append(Site(**site_kwargs))
            else:
                raise ValueError("Site must be Site object or dict")

    def __len__(self) -> int:
        return len(self.sites)

    def __getitem__(self, index: int) -> Site:
        return self.sites[index]

    def __iter__(self):
        return iter(self.sites)

    def get_by_key(self, key: str) -> Optional[Site]:
        """Get site by key."""
        return next((site for site in self.sites if site.key == key), None)

    def filter_by_keys(self, keys: List[str]) -> 'SiteList':
        """Filter sites by key list."""
        filtered_sites = [site for site in self.sites if site.key in keys]
        return SiteList(filtered_sites, self.metadata)

    @classmethod
    def from_json_file(cls, filepath: str) -> 'SiteList':
        """Load site list from JSON file."""
        import json
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        metadata = data.get('metadata', {})
        sites_data = data.get('sites', [])
        return cls(sites_data, metadata)

    @classmethod
    def from_directory(cls, directory: str) -> 'SiteList':
        """Load site list from directory of site folders."""
        from pathlib import Path

        dir_path = Path(directory)
        sites = []

        for item in dir_path.iterdir():
            if item.is_dir() and item.name.startswith('S') and len(item.name) == 6:
                try:
                    int(item.name[1:])  # Validate S##### format
                    sites.append(Site(key=item.name))
                except ValueError:
                    continue

        return cls(sites)


# ===== NEW MODELS FOR EXPANDED API CAPABILITIES =====

@dataclass
class SiteOverview:
    """Real-time site performance metrics from portfolio API."""
    key: str
    name: str
    availability: float
    availabilityLoss: float
    calculatedInverterAvailability: float
    capacityDc: float
    chargeDischarge: Optional[float]
    customColumnData: List[str]
    downtimeLoss: float
    energyAvailability: float
    energyAvailabilityLoss: float
    energyCapacity: Optional[float]
    energyLoss: float
    energyRatio: float
    gridOffline: int
    ground: int
    id: int
    insolation: float
    inverterCount: int
    inverterFaults: int
    irradiance: float
    kioskStatus: int
    kiosks: int
    kwPercent: float
    kwhPercent: float
    lastDataUTC: str
    lastMonth: int
    lastUpload: str
    lastYear: int
    lifetime: int
    message: str
    monitoredSiteType: int
    parentKey: str
    paymentStatus: int
    performanceIndex: float
    performanceTestDelta: float
    performanceTestStatus: int
    performanceTestValue: float
    power: float
    power24: int
    power24Est: float
    powerAvg15: float
    powerAvg15Exp: float
    pvCapacityAc: float
    pvCapacityDc: float
    ratedPower: Optional[float]
    availableEnergy: Optional[float]
    reminderColor: str
    revenueLoss: float
    rolling24Kw: List[int]
    rolling24KwIdx: int
    ruleToolSummary: Dict[str, Any]
    sizeDC: float
    sizeKW: float
    soilingLoss: float
    stateOfCharge: Optional[float]
    status: int
    alertSeverity: Optional[float]
    alertName: str
    systemSize: float
    thisMonth: int
    thisYear: int
    timeZone: str
    today: float
    todayEstimated: float
    todayPercent: float
    type: int
    todayAnd7DayAverageKw: Dict[str, Any]
    estimatedCommissioningDate: Optional[str] = None
    expirationDate: Optional[str] = None

    @property
    def is_online(self) -> bool:
        """Check if site is currently online."""
        return self.status == 8  # Active status

    @property
    def has_alerts(self) -> bool:
        """Check if site has active alerts."""
        return self.inverterFaults > 0

    @property
    def performance_status(self) -> str:
        """Get performance status based on energy ratio."""
        if self.energyRatio >= 0.95:
            return "excellent"
        elif self.energyRatio >= 0.85:
            return "good"
        elif self.energyRatio >= 0.75:
            return "fair"
        else:
            return "poor"


@dataclass
class PortfolioMetrics:
    """Portfolio-level aggregated metrics."""
    customerId: str
    sites: List[SiteOverview]
    customColumnNames: List[str]
    lastChanged: str
    merge: bool
    mergeHash: str

    @property
    def total_sites(self) -> int:
        """Total number of sites in portfolio."""
        return len(self.sites)

    @property
    def total_capacity_ac(self) -> float:
        """Total AC capacity across all sites."""
        return sum(site.pvCapacityAc for site in self.sites)

    @property
    def total_capacity_dc(self) -> float:
        """Total DC capacity across all sites."""
        return sum(site.pvCapacityDc for site in self.sites)

    @property
    def average_availability(self) -> float:
        """Average availability across all sites."""
        if not self.sites:
            return 0.0
        return sum(site.availability for site in self.sites) / len(self.sites)

    @property
    def total_energy_today(self) -> float:
        """Total energy produced today across all sites."""
        return sum(site.today for site in self.sites)

    @property
    def sites_with_alerts(self) -> List[SiteOverview]:
        """Sites that have active alerts."""
        return [site for site in self.sites if site.has_alerts]

    @property
    def online_sites(self) -> List[SiteOverview]:
        """Sites that are currently online."""
        return [site for site in self.sites if site.is_online]


@dataclass
class ChartSeries:
    """Individual data series within a chart."""
    name: str
    key: str
    dataXy: List[Tuple[int, float]]
    color: str
    customUnit: str
    dataMax: float
    dataMin: float
    diameter: int
    fitExponent: int
    header: str
    lineColor: str
    lineType: int
    lineWidth: int
    rightAxis: bool
    units: int
    useBinnedData: bool
    visible: bool
    xSeriesHeader: str
    xSeriesKey: str
    xSeriesName: str
    xUnits: str
    yAxisIndex: int
    yMax: Optional[float]
    yMin: Optional[float]
    alertMessageMap: Optional[Dict] = None

    @property
    def data_points(self) -> List[Tuple[int, float]]:
        """Get data points as (timestamp, value) tuples."""
        return self.dataXy


@dataclass
class ChartData:
    """Complete chart data response."""
    allowSmallBinSize: bool
    binSize: int
    currentNowBinIndex: int
    dataNotAvailable: bool
    durations: List[Dict[str, Any]]
    end: str
    errorString: str
    hardwareKeys: List[str]
    hasAlertMessages: bool
    hasOverriddenQuery: bool
    isCategoryChart: bool
    isSummaryChart: bool
    isUsingDaylightSavings: bool
    key: str
    lastChanged: str
    lastDataDatetime: str
    namedResults: Dict[str, Any]
    renderType: int
    series: List[ChartSeries]
    summaryTable: List[Dict[str, Any]]
    start: Optional[str] = None

    @property
    def energy_production(self) -> Optional[float]:
        """Get total energy production from named results."""
        return self.namedResults.get('energy')

    @property
    def expected_energy(self) -> Optional[float]:
        """Get expected energy from named results."""
        return self.namedResults.get('expEnergy')

    @property
    def performance_ratio(self) -> Optional[float]:
        """Calculate performance ratio if data available."""
        energy = self.namedResults.get('energy')
        expected = self.namedResults.get('expEnergy')
        if energy and expected and expected > 0:
            return energy / expected
        return None

    @property
    def losses(self) -> Dict[str, float]:
        """Get loss breakdown from named results."""
        loss_keys = ['ageAC', 'clipping', 'downtime', 'inverter', 'inverterLimit',
                    'snow', 'soiling']
        return {key: self.namedResults.get(key, 0) for key in loss_keys}


@dataclass
class AlertSummary:
    """Alert summary for hardware device."""
    hardwareKey: str
    maxSeverity: int
    count: int

    @property
    def severity_level(self) -> str:
        """Get human-readable severity level."""
        severity_map = {
            0: "info",
            1: "low",
            2: "medium",
            3: "high",
            4: "critical",
            5: "emergency"
        }
        return severity_map.get(self.maxSeverity, "unknown")

    @property
    def has_critical_alerts(self) -> bool:
        """Check if hardware has critical or higher alerts."""
        return self.maxSeverity >= 4


@dataclass
class AlertSummaryResponse:
    """Response containing alert summaries by hardware."""
    hardwareSummaries: Dict[str, AlertSummary]

    @property
    def total_alerts(self) -> int:
        """Total number of alerts across all hardware."""
        return sum(summary.count for summary in self.hardwareSummaries.values())

    @property
    def hardware_with_alerts(self) -> List[str]:
        """Hardware keys that have active alerts."""
        return [key for key, summary in self.hardwareSummaries.items()
                if summary.count > 0]

    @property
    def critical_hardware(self) -> List[str]:
        """Hardware keys with critical alerts."""
        return [key for key, summary in self.hardwareSummaries.items()
                if summary.maxSeverity >= 4]


@dataclass
class RegisterData:
    """Hardware register information."""
    address: str
    name: str
    value: Any
    units: str
    canModify: bool
    isIgnored: bool
    isStored: bool
    localizedName: str
    pingCommand: str
    register: str
    scale: str
    standardAlertMessage: List[str]
    standardDataName: str
    writeFunction: str
    bustestCommand: str = ""
    hide: bool = False
    identifier: str = ""
    ipAddress: str = ""
    modpollCommand: str = ""

    @property
    def scaled_value(self) -> Any:
        """Get the scaled value if formula is available."""
        # Note: This would require a JavaScript engine to fully evaluate
        # the scale formulas. For now, return raw value.
        return self.value


@dataclass
class HardwareDiagnostics:
    """Detailed hardware diagnostic information."""
    key: str
    hardwareName: str
    lastAttempt: str
    lastChanged: str
    lastCommunication: int
    lastSuccess: str
    outOfService: bool
    outOfServiceNote: str
    outOfServiceUntil: Optional[str]
    parentKey: str
    readOnly: bool
    timeZone: str
    unitId: int
    registerSets: List[Dict[str, Any]]
    gatewayType: int = 0
    jwt: str = ""
    parity: str = ""
    stopBits: str = ""
    tcpPort: Optional[int] = None
    baudRate: str = ""
    devicePath: str = ""
    ipAddress: int = 0
    isPMCE: bool = False
    isTcp: bool = False
    obviusNetworkInfo: Optional[Any] = None
    easyConfigLink: str = ""
    easyConfigBaseUrl: str = ""
    baseUrl: str = ""
    controlUrl: str = ""
    dashboardKey: str = ""
    lastSuccessImageUrl: str = ""
    dataBits: str = ""

    @property
    def is_online(self) -> bool:
        """Check if hardware is currently online."""
        if not self.lastCommunication:
            return False
        # Consider online if communication within last hour
        current_time = int(datetime.now().timestamp() * 1000)
        return (current_time - self.lastCommunication) < (60 * 60 * 1000)


@dataclass
class SiteDetailedInfo:
    """Detailed site information from /api/view/site/{site_id}."""
    key: str
    name: str
    isMonitored: bool
    cellModemContractEndDate: Optional[str]
    address: Dict[str, str]
    cellModemContractStartDate: Optional[str]
    energyCapacityUnit: int
    longitude: float
    parentKey: str
    weatherMode: int
    monitoringContractIsManual: bool
    cellModemContractCustomBanner: bool
    monitoringContractWarnDate: Optional[str]
    workingStatus: str
    capacityDcUnit: int
    elevation: int
    dailyProductionEstimate: float
    lastChanged: str
    monthlyProductionEstimate: float
    ratedPowerUnit: int
    monitoringContractCustomBanner: bool
    monitoringContractStatus: int
    monitoringContractEndDate: Optional[str]
    estimatedCommissioningDate: Optional[str]
    cellModemContractAccessNote: str
    cellModemContractTerminateDate: Optional[str]
    cellModemContractIsManual: bool
    customerLogo: str
    capacityAc: int
    customQueryKey: str
    preferredWsForEstimatedInsolation: int
    requiresPubIp: bool
    defaultQuery: int
    monitoringContractWillNotRenew: bool
    capacityAcUnit: int
    status: int
    latitude: float
    ratedPower: int
    advancedSiteConfiguration: bool
    monitoringContractTerminateDate: Optional[str]
    actualCommissioningDate: Optional[str]
    estimatedLosses: Dict[str, str]
    cellModemContractWarnDate: Optional[str]
    monitoringContractAccessNote: str
    validDataDate: str
    paymentStatus: int
    capacityDc: float
    monitoringContractStartDate: Optional[str]
    energyCapacity: int
    overviewChart1: str
    overviewChart2: str
    cellModemContractWillNotRenew: bool
    siteType: int
    sitePhotos: Optional[Any]

    @property
    def full_address(self) -> str:
        """Get formatted full address."""
        addr = self.address
        parts = [
            addr.get('address1', ''),
            addr.get('address2', ''),
            addr.get('city', ''),
            addr.get('stateProvince', ''),
            addr.get('postalCode', ''),
            addr.get('country', '')
        ]
        return ', '.join(part for part in parts if part)

    @property
    def contract_days_remaining(self) -> Optional[int]:
        """Calculate days remaining on monitoring contract."""
        if not self.monitoringContractEndDate:
            return None

        try:
            end_date = datetime.fromisoformat(self.monitoringContractEndDate.replace('Z', '+00:00'))
            remaining = end_date - datetime.now(end_date.tzinfo)
            return max(0, remaining.days)
        except (ValueError, AttributeError):
            return None

    @property
    def is_contract_expiring_soon(self) -> bool:
        """Check if contract is expiring within 90 days."""
        days = self.contract_days_remaining
        return days is not None and days <= 90


@dataclass
class ReportingCapabilities:
    """User reporting permissions and capabilities."""
    canEditAutoReport: bool
    canAddEmailReport: bool
    canAddSummaryReport: bool
    canAddAutoReport: bool
    canAddUserReport: bool
    views: List[Dict[str, Any]]

    @property
    def has_reporting_access(self) -> bool:
        """Check if user has any reporting capabilities."""
        return any([
            self.canEditAutoReport,
            self.canAddEmailReport,
            self.canAddSummaryReport,
            self.canAddAutoReport,
            self.canAddUserReport
        ])


# ===== UPDATE OPERATION RESULTS =====

@dataclass
class UpdateResult:
    """Result of an update operation with full audit trail for backup/versioning."""
    success: bool
    originalData: Optional[Dict[str, Any]] = None
    updatedData: Optional[Dict[str, Any]] = None
    putResponse: Optional[Dict[str, Any]] = None
    errorMessage: Optional[str] = None