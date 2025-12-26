# Examples package entrypoint for tests
from . import fetch_all_site_data, fetch_site_configs, fetch_all_site_alerts

# Optional modules that may not exist in older checkouts
try:
    from . import update_site_config, apply_alert_updates
except Exception:
    pass

__all__ = [
    'fetch_all_site_data',
    'fetch_site_configs',
    'fetch_all_site_alerts',
    'update_site_config',
    'apply_alert_updates',
]
