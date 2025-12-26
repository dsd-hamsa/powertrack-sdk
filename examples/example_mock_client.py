#!/usr/bin/env python3
"""
Example: Run the PowerTrackClient in 'mock mode' to validate SDK behavior without network.

This script patches `PowerTrackClient.get_json`, `post_json`, and `put_json` to return
sample data so you can exercise methods like `get_site_config`, `get_hardware_list`,
`update_site_config`, and `get_chart_data` locally.

Usage:
    python examples/example_mock_client.py

No credentials or network required.
"""

from unittest.mock import patch
from powertrack_sdk import PowerTrackClient, AuthManager


# Sample fake responses used by mocked methods
SAMPLE_SITE_CONFIG = {
    "name": "Test Site",
    "timeZone": "UTC",
    "latitude": 12.34,
    "longitude": 56.78,
    "elevation": 100,
    "address": "123 Example Lane",
    "city": "Testville",
    "state": "TS",
    "zip": "00000",
    "country": "Neverland",
    "installDate": "2020-01-01",
    "acCapacityKw": 250.0,
    "dcCapacityKw": 300.0,
    "moduleCount": 1000
}

SAMPLE_HARDWARE_LIST = {"hardware": [
    {"key": "H100", "name": "Inverter A", "functionCode": 1, "hid": 100},
    {"key": "H101", "name": "Meter B", "functionCode": 2, "hid": 101},
]}

SAMPLE_PUT_ACK = {"success": True, "updated": True}

SAMPLE_CHART = {"series": [{"name": "Power", "key": "s1", "dataXy": [{"x": 1609459200, "y": 10.5}] }], "namedResults": {"energy": 50, "expEnergy": 100}}


def main():
    # Create client with explicit (fake) auth so AuthManager doesn't try to read files
    auth = AuthManager(cookie='fake-cookie', ae_s='fake-ae-s', ae_v='0000', base_url='https://example.com')
    client = PowerTrackClient(auth_manager=auth, base_url='https://example.com')

    # Patch client's network methods to return sample data
    with patch.object(client, 'get_json', return_value=SAMPLE_SITE_CONFIG) as mock_get_json:
        site_config = client.get_site_config('S99999')
        print('SiteConfig:', site_config)
        mock_get_json.assert_called()

    with patch.object(client, 'get_json', return_value=SAMPLE_HARDWARE_LIST):
        hw_list = client.get_hardware_list('S99999')
        print('Hardware list parsed:', [hw.key for hw in hw_list])

    # Demonstrate update_site_config flow: GET original -> PUT merged
    def fake_get_for_update(endpoint, **kwargs):
        # Return a minimal original config expected by update_site_config
        if endpoint.startswith('/api/edit/site/'):
            return {"name": "Original", "someField": 1}
        return None

    with patch.object(client, 'get_json', side_effect=fake_get_for_update):
        with patch.object(client, 'put_json', return_value=SAMPLE_PUT_ACK) as mock_put:
            result = client.update_site_config('S99999', {'someField': 2})
            print('UpdateResult.success:', result.success)
            mock_put.assert_called()

    # Demonstrate chart parsing using post_json
    with patch.object(client, 'post_json', return_value=SAMPLE_CHART):
        chart = client.get_chart_data(1, 'S99999')
        print('Chart series count:', len(chart.series) if chart else 'no chart')

    print('\n[✓] Mock example completed successfully. No network required.')


if __name__ == '__main__':
    main()
