#!/usr/bin/env python3
"""
Fetch comprehensive site data for all sites in a SiteList using the SDK.

Outputs one JSON file per site under the output directory.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from examples._util import get_client, save_json, ensure_dir, retry_call, parallel_map
except Exception:
    from _util import get_client, save_json, ensure_dir, retry_call, parallel_map
from powertrack_sdk.models import SiteList, SiteData

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def serialize(obj: Any) -> Any:
    """Turn dataclasses and known SDK models into JSON-serializable structures."""
    try:
        if is_dataclass(obj):
            return asdict(obj)
        # datetime, etc. handled by default json dumps if str
        return obj
    except Exception:
        return str(obj)


def fetch_and_save(client, site_key: str, output_dir: str, include_hardware: bool, include_alerts: bool, include_modeling: bool) -> Dict[str, Any]:
    """Fetch data for single site and save to file. Returns summary dict."""
    summary = {"site": site_key, "success": False, "error": None, "path": None}
    try:
        site_data: Optional[SiteData] = client.get_site_data(site_key, include_hardware, include_alerts, include_modeling)
        if site_data is None:
            raise RuntimeError("No data returned")

        # Serialize site_data
        data = serialize(site_data)
        # Ensure fetched_at is JSON serializable
        if isinstance(data, dict) and data.get("fetched_at") is not None:
            try:
                data["fetched_at"] = data["fetched_at"].isoformat()
            except Exception:
                data["fetched_at"] = str(data["fetched_at"])

        out_path = Path(output_dir) / f"{site_key}.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        summary.update({"success": True, "path": str(out_path)})
        logger.info(f"Saved site data for {site_key} -> {out_path}")
    except Exception as e:
        logger.exception(f"Failed to fetch/save data for {site_key}: {e}")
        summary["error"] = str(e)
    return summary


def main(argv: Optional[List[str]] = None):
    parser = argparse.ArgumentParser(description="Fetch comprehensive site data for a SiteList using the PowerTrack SDK")
    parser.add_argument("--site-list", default="portfolio/SiteList.json", help="Path to SiteList.json")
    parser.add_argument("--output-dir", default="portfolio/site_data/", help="Directory to write per-site JSON files")
    parser.add_argument("--include-hardware", action="store_true", default=True, help="Include hardware details")
    parser.add_argument("--no-hardware", dest="include_hardware", action="store_false", help="Do not fetch hardware details")
    parser.add_argument("--include-alerts", action="store_true", default=True, help="Include alerts")
    parser.add_argument("--no-alerts", dest="include_alerts", action="store_false", help="Do not fetch alerts")
    parser.add_argument("--include-modeling", action="store_true", default=True, help="Include modeling data")
    parser.add_argument("--no-modeling", dest="include_modeling", action="store_false", help="Do not fetch modeling data")
    parser.add_argument("--parallel", action="store_true", help="Fetch sites in parallel using threads")
    parser.add_argument("--workers", type=int, default=5, help="Worker count when using --parallel")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of sites to process (0 = no limit)")
    parser.add_argument("--retries", type=int, default=2, help="Retries per site fetch on failure")
    parser.add_argument("--backoff", type=float, default=0.5, help="Initial backoff seconds for retries")
    parser.add_argument("--timeout", type=float, default=None, help="Per-request timeout (unused) - reserved")
    parser.add_argument("--mock", action="store_true", help="Use a local mock client instead of real API")

    args = parser.parse_args(argv)

    client = get_client(use_mock=args.mock)

    # Load site list
    try:
        sites = client.get_sites(args.site_list)
    except Exception as e:
        logger.error(f"Failed to load site list: {e}")
        sys.exit(2)

    if not isinstance(sites, SiteList):
        # If client returned a raw structure, try to construct SiteList
        try:
            sites = SiteList(sites)
        except Exception:
            logger.error("Invalid site list returned by client")
            sys.exit(2)

    site_keys = [s.key for s in sites]
    # Apply limit if requested
    if args.limit and args.limit > 0:
        site_keys = site_keys[:args.limit]
    logger.info(f"Processing {len(site_keys)} sites")
    ensure_dir(args.output_dir)

    summaries: List[Dict[str, Any]] = []

    if args.parallel:
        logger.info(f"Fetching in parallel with {args.workers} workers")
        # Use parallel_map with retry_call inside fetch_and_save
        results = parallel_map(lambda key: fetch_and_save(client, key, args.output_dir, args.include_hardware, args.include_alerts, args.include_modeling),
                               site_keys, workers=args.workers, retries=args.retries, backoff=args.backoff, timeout=args.timeout)
        for item, ok, res in results:
            if ok:
                summaries.append(res)
            else:
                logger.error(f"Failed to process {item}: {res}")
                summaries.append({"site": item, "success": False, "error": str(res), "path": None})
    else:
        for key in site_keys:
            ok, res = retry_call(fetch_and_save, client, key, args.output_dir, args.include_hardware, args.include_alerts, args.include_modeling,
                                 retries=args.retries, backoff=args.backoff, timeout=args.timeout)
            if ok:
                summaries.append(res)
            else:
                logger.error(f"Failed to process {key}: {res}")
                summaries.append({"site": key, "success": False, "error": str(res), "path": None})

    # Save summary
    summary_path = Path(args.output_dir) / "summary.json"
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summaries, f, indent=2, ensure_ascii=False)

    logger.info(f"Completed fetching site data. Summary -> {summary_path}")


if __name__ == "__main__":
    main()
