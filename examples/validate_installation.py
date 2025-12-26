#!/usr/bin/env python3
"""
Quick validation script to check that the SDK imports and core helpers work locally.

This script performs purely local checks (no network):
- Imports package and prints version
- Runs a handful of utils and models checks

Usage:
    python examples/validate_installation.py
"""

from powertrack_sdk import __version__, utils, models


def smoke_tests():
    print('PowerTrack SDK version:', __version__)

    # utils checks
    assert utils.camel_to_snake('TestValue') == 'test_value'
    assert utils.parse_site_id('60001') == 'S60001'

    # models checks
    hw = models.Hardware(key='H1', name='Device', function_code=1)
    assert 'Inverter' in hw.type_name

    md = models.ModelingData(site_id='S1', inverters=[{'inverterKw': 1.0}, {'inverterKw': 2.0}])
    assert md.total_capacity_kw == 3.0

    sl = models.SiteList([{'key': 'S10000', 'name': 'A'}])
    assert len(sl) == 1

    print('\n[✓] Local smoke tests passed. SDK appears to be importable and core helpers work.')


if __name__ == '__main__':
    smoke_tests()
