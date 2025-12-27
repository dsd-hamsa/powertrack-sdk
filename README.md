# PowerTrack SDK

A comprehensive Python SDK for interacting with the AlsoEnergy PowerTrack platform API (as documented [here](https://github.com/dsd-hamsa/PowerTrack-API)).

## Table of Contents

- [Disclaimer](#disclaimer)
- [Features](#features)
- [Installation](#installation)
- [Quick Authentication Setup](#quick-authentication-setup)
- [Quick Start](#quick-start)
- [API Reference](#api-reference)
- [Data Models](#data-models)
- [Configuration](#configuration)
- [Error Handling](#error-handling)
- [Advanced Features](#advanced-features)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)
- [Support](#support)

## Disclaimer
This SDK is user-created and is not endorsed or supported by AlsoEnergy or STEM. It is not intended for use by unqualified personnel. All write / edit actions taken by the user are at your own risk. While PowerTrack has some limited safeguards in place, this SDK mimics operations that can done in the browser with the goal of automating tedious data entry for site setup, standardization, or configuration. Thus, any typo in a script has the potential to affect every site in your portfolio. It is suggested to review the [examples](https://github.com/dsd-hamsa/powertrack-sdk/tree/main/examples), use the mock client, and use dry-run or limit flags for untested batch automations to confirm output. AlsoEnergy, STEM, and authors / contributors of this SDK are not liable for any damages caused by the user. **Use at your own risk, there may be dragons!**

## Features

- **Easy Authentication**: Multiple authentication methods (environment variables, browser fetch parsing, cookie files)
- **Full Read/Write Access**: Complete CRUD operations for configuration management
- **Portfolio Overview**: Real-time portfolio metrics and site performance data
- **Chart & Visualization**: Time-series data and chart definitions for analytics
- **Site Intelligence**: Detailed site information including contract dates and configurations
- **Hardware Diagnostics**: Register-level hardware diagnostics and status information
- **Alert Analytics**: Comprehensive alert summaries with severity tracking
- **Configuration Management**: Update site, hardware, modeling, and alert configurations
- **Bulk Operations**: Mass update hardware configurations via CSV/data
- **Reporting System**: Create, configure, and generate automated reports
- **PAN Data Upload**: Upload Performance Analytics Network data
- **Alert Management**: Full CRUD operations for alert triggers and settings
- **Modeling Updates**: Update PV configurations, inverter models, and bifacial settings
- **Reporting Capabilities**: User permissions and report configuration access
- **Site Management**: Fetch or edit site configurations, lists, and sharing information
- **Hardware Data**: Retrieve hardware lists, configurations, and details
- **Audit & Preferences**: User preferences, audit logs, and system access tracking
- **Robust Error Handling**: Automatic retries and comprehensive error reporting
- **Type Safety**: Full type hints and data models
- **Comprehensive API Coverage**: Support for all major PowerTrack webapp endpoints

## Installation
Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\Activate.ps1
```

Install the SDK:
```bash
# From PyPI
pip install powertrack-sdk

# Or from source (current development version)
git clone https://github.com/dsd-hamsa/powertrack-sdk.git
cd powertrack-sdk
pip install -e .
```

## Quick Authentication Setup

The SDK includes a placeholder `mostRecentFetch.js` file for easy authentication.    

1. **Find the file**: After installation, locate it in your Python environment:  
   ```python
   import powertrack_sdk
   import os
   fetch_file = os.path.join(os.path.dirname(powertrack_sdk.__file__), 'mostRecentFetch.js')
   print(fetch_file)  # Shows the path to edit
   ```

2. **Get fetch data**: In browser DevTools (`F12`) → Network tab → right-click any PowerTrack (*C#### / S##### / H######*) API call → "Copy as fetch (Node.js)"    
![Authentication Instructions](readme-auth.png)
3. **Replace content**: Paste your fetch call into the `mostRecentFetch.js` file and save   

4. **Done**: The SDK will automatically find and use it for authentication  

## Quick Start

### Basic Usage

```python
from powertrack_sdk import PowerTrackClient

# Initialize client (uses environment variables for auth)
client = PowerTrackClient()

# Get site configuration
site_config = client.get_site_config('S12345')
print(f"Site: {site_config.name}, Capacity: {site_config.ac_capacity_kw} kW")

# Get hardware list
hardware = client.get_hardware_list('S12345')
for hw in hardware:
    print(f"{hw.name}: {hw.type_name}")

# Get comprehensive site data
site_data = client.get_site_data('S12345')
print(f"Hardware count: {site_data.hardware_count}")
print(f"Active alerts: {site_data.active_alerts_count}")
```

### Advanced Analytics

```python
# Get real-time portfolio overview
portfolio = client.get_portfolio_overview('C1234')
for site in portfolio.sites:
    print(f"{site.name}: {site.availability}% availability, {site.power} kW")

# Get chart data for visualization
chart_data = client.get_chart_data(chart_type=1, site_id='S12345',
                                  start_date='2024-01-01T00:00:00Z',
                                  end_date='2024-01-31T23:59:59Z')
for series in chart_data.series:
    print(f"Series: {series.name}, Points: {len(series.data_xy)}")

# Get hardware diagnostics
diagnostics = client.get_hardware_diagnostics('H123456')
print(f"Temperature: {diagnostics.temperature}°C")
print(f"Status: {diagnostics.overall_status}")

# Get alert summary
alerts = client.get_alert_summary(customer_id='C1234')
for hw_key, summary in alerts.hardware_summaries.items():
    print(f"{hw_key}: {summary.count} alerts (max severity: {summary.max_severity})")
```

### Authentication Setup

The SDK supports multiple authentication methods. The easiest way is to use the included `mostRecentFetch.js` file:

1. **Environment Variables**:
   ```bash
   export COOKIE="your_cookie_string" # Usually cut off by most terminals. May need to import from text file.
   export AE_S="your_aes_value"
   export AE_V="086665"  # Optional, defaults to 086665
   export BASE_URL="https://apps.alsoenergy.com"  # Optional
   ```

2. **Browser Fetch Parsing** (recommended):
    - The SDK includes a placeholder `mostRecentFetch.js` file (if cloning the repo. If installing from pip, create a new file in your project directory or copy from the package contents)
    - Copy a fetch request from Chrome DevTools (see placeholder for instructions)
    - Replace the content in the SDK's `mostRecentFetch.js` file
    - The SDK will automatically find and parse authentication data

3. **Cookie File**:
   - Save cookie to `cookie.txt`
   - SDK will use it as fallback

### Advanced Usage

For most portfolio-wide operations, you'll need your Customer ID, which can be found in the URL of your homepage while logged into PowerTrack.  
![Customer ID](readme-customer-id.png)

```python
from powertrack_sdk import PowerTrackClient, SiteList

# First, create the site list (one time setup)
# python examples/fetch_site_list.py --customer-id YOUR_CUSTOMER_ID

# Load site list from file
sites = SiteList.from_json_file('portfolio/SiteList.json')

# Process multiple sites
for site in sites:
    try:
        data = client.get_site_data(site.key, include_alerts=False)
        print(f"Processed {site.key}: {data.hardware_count} devices")
    except Exception as e:
        print(f"Failed {site.key}: {e}")
```

## API Reference
This SDK was built using the API [documentation](https://github.com/dsd-hamsa/PowerTrack-API/) scraped directly from the PowerTrack web app. Use of an API key is not required for interacting with the SDK as it mimics browser / web app usage (with less overhead).  

## Data Models

Note: All models and exceptions can be imported directly from powertrack_sdk:

```python
from powertrack_sdk import SiteConfig, Hardware, AlertSummary, SiteList, etc.
```

### PowerTrackClient

#### Portfolio & Overview Methods
- `get_portfolio_overview(customer_id)` - Get real-time portfolio metrics
- `get_site_overview(site_id)` - Get individual site performance metrics
- `get_site_detailed_info(site_id)` - Get detailed site information and contracts

#### Chart & Visualization Methods
- `get_chart_data(chart_type, site_id, start_date=None, end_date=None)` - Get time-series chart data
- `get_chart_definitions()` - Get available chart type definitions

#### Hardware Methods
- `get_hardware_list(site_id)` - Get hardware list for site
- `get_hardware_details(hardware_key)` - Get detailed hardware config
- `get_hardware_diagnostics(hardware_id)` - Get hardware diagnostic information
- `get_site_hardware_production(site_id)` - Get hardware production data

#### Alert Methods
- `get_alert_triggers(hardware_key, last_changed=None)` - Get alert triggers
- `get_alert_summary(customer_id=None, site_id=None)` - Get alert summary by customer or site

#### Modeling & Configuration Methods
- `get_modeling_data(site_id)` - Get PV modeling data
- `get_pv_model_curves(model_type)` - Get PV model efficiency/angle curves
- `get_pvsyst_modules(hardware_id=None, site_id=None)` - Get PVSyst module configurations
- `get_driver_settings(hardware_id)` - Get hardware driver settings
- `get_driver_settings_list(list_id)` - Get driver settings list
- `get_register_offsets(hardware_id)` - Get register offset information

#### Site Management Methods
- `get_site_config(site_id)` - Get site configuration
- `get_sites(site_list_file=None)` - Get site list
- `get_site_links(site_id)` - Get site sharing links
- `get_site_shares(site_id)` - Get site sharing configurations

#### Reporting & User Methods
- `get_reporting_capabilities()` - Get user reporting permissions
- `get_user_preferences()` - Get current user preferences
- `get_audit_log(filters=None)` - Get audit log entries
- `get_report_configs()` - Get available report configurations

#### Comprehensive Methods
- `get_site_data(site_id, include_hardware=True, include_alerts=True, include_modeling=True)` - Get all site data

#### Write/Update Methods
- `update_site_config(site_id, config_data)` - Update site configuration
- `update_hardware_config(hardware_id, config_data)` - Update hardware configuration
- `bulk_update_hardware(site_id, hardware_data)` - Bulk update hardware configurations
- `update_hardware_driver(hardware_id, driver_data)` - Update hardware driver settings
- `update_alert_triggers(hardware_key, trigger_data)` - Update alert triggers
- `add_alert_trigger(hardware_key, trigger_data)` - Add new alert trigger
- `delete_alert_trigger(hardware_key)` - Delete alert triggers
- `update_modeling_data(site_id, modeling_data)` - Update modeling configuration
- `update_inverter_model(hardware_id, model_data)` - Update inverter model
- `update_bifacial_settings(hardware_id, bifacial_data)` - Update bifacial settings
- `create_report_config(report_config)` - Create report configuration
- `start_report(report_id, parameters)` - Start report generation
- `upload_pan_data(pan_data)` - Upload PAN data

### Data Models

#### Core Models
- **Site**: Basic site information
- **Hardware**: Hardware device information
- **AlertTrigger**: Alert configuration data
- **SiteConfig**: Complete site configuration
- **ModelingData**: PV modeling configuration
- **SiteData**: Comprehensive site data container
- **SiteList**: Collection of sites with metadata

#### Portfolio & Performance Models
- **SiteOverview**: Real-time site performance metrics
- **PortfolioMetrics**: Portfolio-wide site metrics and summaries

#### Chart & Visualization Models
- **ChartData**: Chart data with multiple series
- **ChartSeries**: Individual data series within charts

#### Alert & Diagnostic Models
- **AlertSummary**: Alert counts by severity
- **AlertSummaryResponse**: Complete alert summary response
- **HardwareDiagnostics**: Detailed hardware diagnostic information
- **RegisterData**: Hardware register information

#### Configuration & Metadata Models
- **SiteDetailedInfo**: Comprehensive site information including contracts
- **ReportingCapabilities**: User reporting permissions and capabilities

### Authentication

- **AuthManager**: Handles authentication setup from multiple sources

## Configuration

### Environment Variables

- `COOKIE`: Full cookie string from browser
- `AE_S`: Security header value
- `AE_V`: API version (default: 086665)
- `BASE_URL`: API base URL (default: https://apps.alsoenergy.com)

### Files

- `mostRecentFetch.js`: Browser fetch content for auth parsing (placeholder included in SDK)
- `cookie.txt`: Fallback cookie file
- `.env`: Environment variables file

## Error Handling

The SDK provides specific exceptions:

- `AuthenticationError`: Authentication failures
- `APIError`: API request failures
- `ValidationError`: Input validation errors
- `ConfigurationError`: Configuration issues

```python
from powertrack_sdk import PowerTrackClient, AuthenticationError, APIError

try:
    client = PowerTrackClient()
    data = client.get_site_config('S12345')
except AuthenticationError as e:
    print("Authentication failed:", e)
except APIError as e:
    print(f"API error {e.status_code}:", e)
```

## Advanced Features

### Custom Authentication

```python
from powertrack_sdk import AuthManager, PowerTrackClient

# Custom auth setup
auth = AuthManager(
    cookie="custom_cookie",
    ae_s="custom_aes",
    base_url="https://custom.alsoenergy.com"
)

client = PowerTrackClient(auth_manager=auth)
```

### Batch Processing

```python
# Process multiple sites with error handling
sites = ['S12345', 'S60309', 'S60310']
results = {}

for site_id in sites:
    try:
        data = client.get_site_data(site_id)
        results[site_id] = data
    except Exception as e:
        print(f"Failed {site_id}: {e}")
        results[site_id] = None
```

### Context Manager

```python
# Automatic session cleanup
with PowerTrackClient() as client:
    data = client.get_site_config('S12345')
    # Session automatically closed
```

### Configuration Management

The PowerTrack API requires that all PUT request payloads contain the full json object. The best approach for handling this is to pair a GET request with a PUT, so the GET response can be modified in memory before being submitted as the payload.   

The PowerTrack API has different endpoints for GET and PUT requests. All PUTs lack an identifier (Site / Hardware / Alert) in the endpoint and thus require a Referer header.
```python
# Update site configuration
site_config = {
    "latitude": 40.7128,
    "longitude": -74.0060,
    "acCapacityKw": 500.0,
    "dcCapacityKw": 550.0
}
success = client.update_site_config('S12345', site_config)

# Update hardware configuration
hardware_config = {
    "name": "Updated Inverter Name",
    "capacityKw": 250.0,
    "enableBool": True
}
success = client.update_hardware_config('H123456', hardware_config)

# Bulk update multiple hardware devices
bulk_hardware = [
    {"hid": 123, "name": "Inverter 1", "capacityKw": 250.0},
    {"hid": 124, "name": "Inverter 2", "capacityKw": 250.0}
]
success = client.bulk_update_hardware('S12345', bulk_hardware)
```

### Alert Management

```python
# Update alert triggers for hardware
alert_config = {
    "triggers": [
        {
            "name": "High Temperature",
            "severity": 2,
            "enabled": True,
            "threshold": 80.0
        }
    ]
}
success = client.update_alert_triggers('H123456', alert_config)

# Add new alert trigger
new_trigger = {
    "name": "Low Voltage",
    "severity": 3,
    "enabled": True,
    "threshold": 200.0
}
success = client.add_alert_trigger('H123456', new_trigger)

# Remove all alert triggers for hardware
success = client.delete_alert_trigger('H123456')
```

### Modeling Updates

```python
# Update modeling data
modeling_config = {
    "pvConfig": {
        "inverters": [
            {
                "id": "INV001",
                "power": 250000,
                "efficiency": 0.96
            }
        ]
    }
}
success = client.update_modeling_data('S12345', modeling_config)

# Update inverter model
inverter_model = {
    "model": "SMA Sunny Tripower",
    "powerRating": 25000,
    "efficiencyCurve": [0.85, 0.92, 0.95, 0.96, 0.95]
}
success = client.update_inverter_model('H123456', inverter_model)

# Update bifacial settings
bifacial_config = {
    "enabled": True,
    "groundReflectance": 0.25,
    "bifacialityFactor": 0.75
}
success = client.update_bifacial_settings('H123456', bifacial_config)
```

### Reporting Operations

```python
# Create new report configuration
report_config = {
    "name": "Monthly Performance Report",
    "type": "performance",
    "schedule": "monthly",
    "recipients": ["admin@company.com"],
    "sites": ["S12345", "S60309"]
}
success = client.create_report_config(report_config)

# Start report generation
success = client.start_report("REPORT123", {
    "dateRange": "lastMonth",
    "includeCharts": True
})

# Upload PAN data
pan_data = {
    "siteId": "S12345",
    "performanceData": {...},
    "timestamp": "2024-01-01T00:00:00Z"
}
success = client.upload_pan_data(pan_data)
```

### Portfolio Analytics

```python
# Analyze entire portfolio performance
portfolio = client.get_portfolio_overview('C1234')

# Find underperforming sites
underperforming = [site for site in portfolio.sites if site.availability < 95.0]
print(f"Underperforming sites: {len(underperforming)}")

# Calculate portfolio totals
total_capacity = sum(site.pv_capacity_ac for site in portfolio.sites if site.pv_capacity_ac)
total_production = sum(site.today for site in portfolio.sites if site.today)
print(f"Total capacity: {total_capacity} kW, Today's production: {total_production} kWh")
```

### Hardware Health Monitoring

```python
# Monitor hardware health across sites
sites = client.get_sites()
health_issues = []

for site in sites:
    hardware = client.get_hardware_list(site.key)
    for hw in hardware:
        diagnostics = client.get_hardware_diagnostics(hw.key)
        if diagnostics and diagnostics.has_critical_issues:
            health_issues.append({
                'site': site.key,
                'hardware': hw.key,
                'issues': diagnostics.critical_issues
            })

print(f"Found {len(health_issues)} hardware health issues")
```

### Alert Management & Analytics

```python
# Get comprehensive alert overview
alert_summary = client.get_alert_summary(customer_id='C1234')

# Analyze alert patterns
high_severity_sites = []
for hw_key, summary in alert_summary.hardware_summaries.items():
    if summary.max_severity >= 3:  # Critical or high severity
        site_id = hw_key.split('H')[0]  # Extract site from hardware key
        high_severity_sites.append(site_id)

print(f"Sites with high-severity alerts: {set(high_severity_sites)}")

# Get detailed alert triggers
for hw_key in list(alert_summary.hardware_summaries.keys())[:5]:  # Sample first 5
    triggers = client.get_alert_triggers(hw_key)
    if triggers:
        print(f"{hw_key} has {len(triggers.triggers)} alert triggers")
```

## Development

### Running Tests

```bash
pytest
```



### Code Quality

```bash
black .  # Format code
flake8 .  # Lint code
mypy .    # Type checking
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

For issues and questions:
- GitHub Issues: https://github.com/dsd-hamsa/powertrack-sdk/issues