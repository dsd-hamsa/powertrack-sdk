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
    function_code: Optional[int] = None
    hid: Optional[int] = None
    short_name: Optional[str] = None
    serial_num: Optional[str] = None
    mfr_model: Optional[str] = None
    device_id: Optional[str] = None
    install_date: Optional[str] = None
    device_address: Optional[str] = None
    port: Optional[str] = None
    unit_id: Optional[str] = None
    baud: Optional[str] = None
    gateway_id: Optional[str] = None
    enable_bool: bool = True
    hardware_status: Optional[str] = None
    capacity_kw: Optional[float] = None
    inverter_kw: Optional[float] = None
    driver_name: Optional[str] = None
    out_of_service: bool = False

    @property
    def type_name(self) -> str:
        """Get human-readable hardware type name."""
        # Import here to avoid circular imports
        hardware_types = {
            1: "Inverter (PV)",
            2: "Production Meter (PM)",
            3: "Type 3",
            4: "Grid Meter (GM)",
            5: "Weather Station (WS)",
            6: "DC Combiner",
            9: "Kiosk",
            10: "Gateway (GW)",
            11: "Cell Modem (CE)",
            14: "Camera",
            20: "Extra Meter",
            21: "DNP3 Server",
            24: "Tracker",
            25: "BESS Controller",
            28: "Data Logger",
            31: "Data Capture",
            34: "Relay",
            37: "BESS Meter",
        }

        if self.function_code is None:
            return "Unknown"
        return hardware_types.get(self.function_code, f"Type {self.function_code}")


@dataclass
class AlertTrigger:
    """Represents an alert trigger configuration."""
    key: str
    parent_key: Optional[str] = None
    asset_code: Optional[str] = None
    calculated_capacity: Optional[float] = None
    capacity: Optional[float] = None
    last_changed: Optional[str] = None
    is_active: bool = False
    check_no_snow: bool = False
    sun_min_elevation: Optional[float] = None
    delay_hours_trigger: Optional[float] = None
    delay_hours_resolve: Optional[float] = None
    check_sun: bool = False
    has_impact: bool = False
    impact: int = 0
    triggers: List[Dict[str, Any]] = field(default_factory=list)
    default_triggers: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def active_triggers(self) -> List[Dict[str, Any]]:
        """Get list of active triggers."""
        return [t for t in self.triggers if t.get('isActive', False)]


@dataclass
class SiteConfig:
    """Represents site configuration data."""
    site_id: str
    name: Optional[str] = None
    timezone: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    elevation: Optional[float] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None
    install_date: Optional[str] = None
    ac_capacity_kw: Optional[float] = None
    dc_capacity_kw: Optional[float] = None
    module_count: Optional[int] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelingData:
    """Represents site modeling data."""
    site_id: str
    pv_config: Dict[str, Any] = field(default_factory=dict)
    inverters: List[Dict[str, Any]] = field(default_factory=list)
    ts: Optional[str] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)

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
    fetched_at: Optional[datetime] = None

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
    custom_unit: str
    data_max: float
    data_min: float
    diameter: int
    fit_exponent: int
    header: str
    line_color: str
    line_type: int
    line_width: int
    right_axis: bool
    units: int
    use_binned_data: bool
    visible: bool
    x_series_header: str
    x_series_key: str
    x_series_name: str
    x_units: str
    y_axis_index: int
    y_max: Optional[float]
    y_min: Optional[float]
    alert_message_map: Optional[Dict] = None

    @property
    def data_points(self) -> List[Tuple[int, float]]:
        """Get data points as (timestamp, value) tuples."""
        return self.dataXy


@dataclass
class ChartData:
    """Complete chart data response."""
    allow_small_bin_size: bool
    bin_size: int
    current_now_bin_index: int
    data_not_available: bool
    durations: List[Dict[str, Any]]
    end: str
    error_string: str
    hardware_keys: List[str]
    has_alert_messages: bool
    has_overridden_query: bool
    is_category_chart: bool
    is_summary_chart: bool
    is_using_daylight_savings: bool
    key: str
    last_changed: str
    last_data_datetime: str
    named_results: Dict[str, Any]
    render_type: int
    series: List[ChartSeries]
    start: Optional[str] = None

    @property
    def energy_production(self) -> Optional[float]:
        """Get total energy production from named results."""
        return self.named_results.get('energy')

    @property
    def expected_energy(self) -> Optional[float]:
        """Get expected energy from named results."""
        return self.named_results.get('expEnergy')

    @property
    def performance_ratio(self) -> Optional[float]:
        """Calculate performance ratio if data available."""
        energy = self.named_results.get('energy')
        expected = self.named_results.get('expEnergy')
        if energy and expected and expected > 0:
            return energy / expected
        return None

    @property
    def losses(self) -> Dict[str, float]:
        """Get loss breakdown from named results."""
        loss_keys = ['ageAC', 'clipping', 'downtime', 'inverter', 'inverterLimit',
                    'snow', 'soiling']
        return {key: self.named_results.get(key, 0) for key in loss_keys}


@dataclass
class AlertSummary:
    """Alert summary for hardware device."""
    hardware_key: str
    max_severity: int
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
        return severity_map.get(self.max_severity, "unknown")

    @property
    def has_critical_alerts(self) -> bool:
        """Check if hardware has critical or higher alerts."""
        return self.max_severity >= 4


@dataclass
class AlertSummaryResponse:
    """Response containing alert summaries by hardware."""
    hardware_summaries: Dict[str, AlertSummary]

    @property
    def total_alerts(self) -> int:
        """Total number of alerts across all hardware."""
        return sum(summary.count for summary in self.hardware_summaries.values())

    @property
    def hardware_with_alerts(self) -> List[str]:
        """Hardware keys that have active alerts."""
        return [key for key, summary in self.hardware_summaries.items()
                if summary.count > 0]

    @property
    def critical_hardware(self) -> List[str]:
        """Hardware keys with critical alerts."""
        return [key for key, summary in self.hardware_summaries.items()
                if summary.has_critical_alerts]


@dataclass
class RegisterData:
    """Hardware register information."""
    address: str
    name: str
    value: Any
    units: str
    can_modify: bool
    is_ignored: bool
    is_stored: bool
    localized_name: str
    ping_command: str
    register: str
    scale: str
    standard_alert_message: List[str]
    standard_data_name: str
    write_function: str
    bustest_command: str = ""
    hide: bool = False
    identifier: str = ""
    ip_address: str = ""
    modpoll_command: str = ""

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
    hardware_name: str
    last_attempt: str
    last_changed: str
    last_communication: int
    last_success: str
    out_of_service: bool
    out_of_service_note: str
    out_of_service_until: Optional[str]
    parent_key: str
    read_only: bool
    time_zone: str
    unit_id: int
    register_sets: List[Dict[str, Any]]
    gateway_type: int = 0
    jwt: str = ""
    parity: str = ""
    stop_bits: str = ""
    tcp_port: Optional[int] = None
    baud_rate: str = ""
    device_path: str = ""
    ip_address: int = 0
    is_pmce: bool = False
    is_tcp: bool = False
    obvius_network_info: Optional[Any] = None
    easy_config_link: str = ""
    easy_config_base_url: str = ""
    base_url: str = ""
    control_url: str = ""
    dashboard_key: str = ""
    last_success_image_url: str = ""

    @property
    def is_online(self) -> bool:
        """Check if hardware is currently online."""
        if not self.last_communication:
            return False
        # Consider online if communication within last hour
        current_time = int(datetime.now().timestamp() * 1000)
        return (current_time - self.last_communication) < (60 * 60 * 1000)


@dataclass
class SiteDetailedInfo:
    """Detailed site information from /api/view/site/{site_id}."""
    key: str
    name: str
    is_monitored: bool
    cell_modem_contract_end_date: Optional[str]
    address: Dict[str, str]
    cell_modem_contract_start_date: Optional[str]
    energy_capacity_unit: int
    longitude: float
    parent_key: str
    weather_mode: int
    monitoring_contract_is_manual: bool
    cell_modem_contract_custom_banner: bool
    monitoring_contract_warn_date: Optional[str]
    working_status: str
    capacity_dc_unit: int
    elevation: int
    daily_production_estimate: float
    last_changed: str
    monthly_production_estimate: float
    rated_power_unit: int
    monitoring_contract_custom_banner: bool
    monitoring_contract_status: int
    monitoring_contract_end_date: Optional[str]
    estimated_commissioning_date: Optional[str]
    cell_modem_contract_access_note: str
    cell_modem_contract_terminate_date: Optional[str]
    cell_modem_contract_is_manual: bool
    customer_logo: str
    capacity_ac: int
    custom_query_key: str
    preferred_ws_for_estimated_insolation: int
    requires_pub_ip: bool
    default_query: int
    monitoring_contract_will_not_renew: bool
    capacity_ac_unit: int
    status: int
    latitude: float
    rated_power: int
    advanced_site_configuration: bool
    monitoring_contract_terminate_date: Optional[str]
    actual_commissioning_date: Optional[str]
    estimated_losses: Dict[str, str]
    cell_modem_contract_warn_date: Optional[str]
    monitoring_contract_access_note: str
    valid_data_date: str
    payment_status: int
    capacity_dc: float
    monitoring_contract_start_date: Optional[str]
    energy_capacity: int
    overview_chart1: str
    overview_chart2: str
    cell_modem_contract_will_not_renew: bool
    site_type: int
    site_photos: Optional[Any]

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
        if not self.monitoring_contract_end_date:
            return None

        try:
            end_date = datetime.fromisoformat(self.monitoring_contract_end_date.replace('Z', '+00:00'))
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
    can_edit_auto_report: bool
    can_add_email_report: bool
    can_add_summary_report: bool
    can_add_auto_report: bool
    can_add_user_report: bool
    views: List[Dict[str, Any]]

    @property
    def has_reporting_access(self) -> bool:
        """Check if user has any reporting capabilities."""
        return any([
            self.can_edit_auto_report,
            self.can_add_email_report,
            self.can_add_summary_report,
            self.can_add_auto_report,
            self.can_add_user_report
        ])


# ===== UPDATE OPERATION RESULTS =====

@dataclass
class UpdateResult:
    """Result of an update operation with full audit trail for backup/versioning."""
    success: bool
    original_data: Optional[Dict[str, Any]] = None
    updated_data: Optional[Dict[str, Any]] = None
    put_response: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None