# Examples for PowerTrack SDK

## Table of Contents
- [Environment Variables](#environment-variables)
- [Usage Examples](#usage-examples)
- [Mocking](#mocking)
- [Backups](#backups)
- [SDK Output Examples](#sdk-output-examples)

## Environment Variables
- Environment variables (for real API): `COOKIE`, `AE_S`, `AE_V`, `BASE_URL`

## Usage Examples
- Fetch data for all sites in a SiteList:
  - `python examples/fetch_all_site_data.py --site-list portfolio/SiteList.json --output-dir portfolio/site_data/`

- Fetch site configs:
  - `python examples/fetch_site_configs.py --site-id S12345 --output-dir portfolio/configs/`

- Dry-run config update:
  - `python examples/update_site_config.py --site-id S12345 --update-file edits.json`

- Apply config update:
  - `python examples/update_site_config.py --site-id S12345 --update-file edits.json --apply`

- Fetch alert summaries (mock):
  - `python examples/fetch_all_site_alerts.py --customer-id C12345 --mock`

- All examples are importable and accept an optional `argv` list via `main(argv)` for testing.

## Mocking
- Use `--mock` on scripts to run without network. The mock client is a deterministic local implementation.

## Backups
- Update scripts save backups to `portfolio/config_backups/` by default when `--apply` is used.

## Individual Method Examples

This directory contains individual CLI scripts for each SDK method, allowing you to test and explore every API endpoint supported by the SDK. All scripts support `--mock` for testing without API credentials.

### Portfolio & Overview
- `python3 examples/get_portfolio_overview.py --customer-id C8458 --mock`
- `python3 examples/get_site_overview.py --site-id S60308 --mock`
- `python3 examples/get_site_detailed_info.py --site-id S60308 --mock`

### Chart & Visualization
- `python3 examples/get_chart_data.py --chart-type 1 --site-id S60308 --mock`
- `python3 examples/get_chart_definitions.py --mock`

### Hardware Methods
- `python3 examples/get_hardware_list.py --site-id S60308 --mock`
- `python3 examples/get_hardware_details.py --hardware-id H12345 --mock`
- `python3 examples/get_hardware_diagnostics.py --hardware-id H12345 --mock`
- `python3 examples/get_site_hardware_production.py --site-id S60308 --mock`
- `python3 examples/get_register_offsets.py --hardware-id H12345 --mock`

### Alert Methods
- `python3 examples/get_alert_triggers.py --hardware-id H12345 --mock`
- `python3 examples/get_alert_summary.py --customer-id C8458 --mock`

### Modeling & Configuration
- `python3 examples/get_modeling_data.py --site-id S60308 --mock`
- `python3 examples/get_pv_model_curves.py --mock`
- `python3 examples/get_pvsyst_modules.py --hardware-id H12345 --mock`
- `python3 examples/get_driver_settings.py --hardware-id H12345 --mock`
- `python3 examples/get_driver_settings_list.py --list-id LIST123 --mock`

### Site Management
- `python3 examples/get_site_config.py --site-id S60308 --mock`
- `python3 examples/get_sites.py --mock`
- `python3 examples/get_site_links.py --site-id S60308 --mock`
- `python3 examples/get_site_shares.py --site-id S60308 --mock`

### Reporting & User
- `python3 examples/get_reporting_capabilities.py --mock`
- `python3 examples/get_user_preferences.py --mock`
- `python3 examples/get_audit_log.py --mock`
- `python3 examples/get_report_configs.py --mock`

### Comprehensive
- `python3 examples/get_site_data.py --site-id S60308 --mock`

## SDK Output Examples

### Alert Summary
`client.get_alert_summary(customer_id)` returns an `AlertSummaryResponse` with hardware-level summaries:

```json
{
  "hardware_summaries": {
    "H12345": {
      "hardware_key": "H12345",
      "count": 2,
      "max_severity": 4
    },
    "H67890": {
      "hardware_key": "H67890",
      "count": 1,
      "max_severity": 5
    }
  }
}
```

### Site Config
`client.get_site_config(site_id)` returns a `SiteConfig` object:

```json
{
  "site_id": "S12345",
  "name": "Example Site",
  "timezone": "UTC",
  "latitude": 40.7128,
  "longitude": -74.0060,
  "elevation": 10,
  "address": "123 Main St",
  "city": "New York",
  "state": "NY",
  "zip_code": "10001",
  "country": "USA",
  "install_date": "2020-01-01",
  "ac_capacity_kw": 100.0,
  "dc_capacity_kw": 120.0,
  "module_count": 400,
  "raw_data": { ... }
}
```

### Alert Triggers
`client.get_alert_triggers(hardware_key)` returns an `AlertTrigger` object:

```json
{
  "key": "H12345",
  "parent_key": "S12345",
  "asset_code": "H12345",
  "calculated_capacity": 100.0,
  "capacity": 100.0,
  "last_changed": "2023-01-01T00:00:00Z",
  "triggers": [
    {
      "id": 1,
      "name": "Overvoltage Alert",
      "isActive": true,
      "threshold": 500,
      "severity": 4
    }
  ],
  "default_triggers": [ ... ]
}
```

### Site Data
`client.get_site_data(site_id, include_hardware=True, include_alerts=True, include_modeling=True)` returns a `SiteData` object:

```json
{
  "site": {
    "key": "S12345",
    "name": "Example Site"
  },
  "config": { ... },
  "hardware": [
    {
      "key": "H12345",
      "name": "Inverter 1",
      "function_code": "INVERTER",
      "hid": 12345,
      "capacity_kw": 50.0
    }
  ],
  "alerts": [ ... ],
  "modeling": {
    "site_id": "S12345",
    "pv_config": { "inverters": [ ... ] },
    "inverters": [ ... ],
    "ts": "timestamp",
    "raw_data": { ... }
  },
  "fetched_at": "2023-01-01T12:00:00Z"
}
```
