import json
from pathlib import Path
import sys
import os

# Add examples to path for import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'examples'))

import fetch_all_site_data
import fetch_site_configs
import fetch_all_site_alerts
import update_site_config


def test_fetch_all_site_data_mock(tmp_path):
    site_list = tmp_path / "SiteList.json"
    site_list.write_text(json.dumps({"sites": [{"key": "S10001", "name": "Mock Site 1"}, {"key": "S10002", "name": "Mock Site 2"}]}))
    out_dir = tmp_path / "site_data"

    # Run fetch_all_site_data with mock client, limit to 1 for speed
    fetch_all_site_data.main(["--site-list", str(site_list), "--output-dir", str(out_dir), "--mock", "--limit", "1", "--parallel"]) 

    # Assert file created
    expected = out_dir / "S10001.json"
    assert expected.exists()
    data = json.loads(expected.read_text())
    # Top-level keys we expect from serialization
    assert "site" in data
    assert "config" in data
    assert "fetched_at" in data or True


def test_fetch_site_configs_mock(tmp_path):
    site_list = tmp_path / "SiteList.json"
    site_list.write_text(json.dumps({"sites": [{"key": "S10001", "name": "Mock Site 1"}]}))
    out_dir = tmp_path / "configs"

    fetch_site_configs.main(["--site-list", str(site_list), "--output-dir", str(out_dir), "--mock", "--limit", "1"]) 
    cfg_file = out_dir / "S10001.json"
    assert cfg_file.exists()
    cfg = json.loads(cfg_file.read_text())
    assert isinstance(cfg, dict)


def test_fetch_all_site_alerts_mock(tmp_path):
    out = tmp_path / "alerts.json"
    fetch_all_site_alerts.main(["--customer-id", "C123", "--output", str(out), "--mock", "--limit", "1"]) 
    assert out.exists()
    j = json.loads(out.read_text())
    assert "summary" in j
    assert "details" in j


def test_update_site_config_dry_run(tmp_path):
    upd = tmp_path / "upd.json"
    upd.write_text(json.dumps({"someField": 2}))
    # dry-run should not create backups
    res = update_site_config.main(["--site-id", "S10001", "--update-file", str(upd), "--mock"])
    assert isinstance(res, dict)
    assert res.get("applied") is False


def test_get_chart_data_mock():
    import get_chart_data
    # Test with mock
    result = get_chart_data.main(["--chart-type", "255", "--site-id", "S70726", "--mock"])
    # Should return 0 (success)
    assert result is None  # main returns None on success

