#!/usr/bin/env python3
"""
Fetch site configuration(s) and save per-site JSON files.
"""

# The below allows for importing a mock client for testing purposes from the examples directory.
# In production, you would import your client from the actual SDK package.

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import List, Optional

try:
    from examples._util import get_client, ensure_dir, retry_call, parallel_map
except Exception:
    from _util import get_client, ensure_dir, retry_call, parallel_map
from powertrack_sdk.models import SiteList

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def main(argv: Optional[List[str]] = None):
    parser = argparse.ArgumentParser(description="Fetch site configuration(s) using the PowerTrack SDK")
    parser.add_argument("--site-id", help="Single site ID to fetch (e.g., S12345)")
    parser.add_argument("--site-list", default="portfolio/SiteList.json", help="Path to SiteList.json to iterate")
    parser.add_argument("--output-dir", default="portfolio/configs/", help="Directory to write config JSON files")
    parser.add_argument("--mock", action="store_true", help="Use mock client for testing")
    parser.add_argument("--parallel", action="store_true", help="Fetch configs in parallel")
    parser.add_argument("--workers", type=int, default=5, help="Worker count when using --parallel")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of sites to process (0 = no limit)")
    parser.add_argument("--retries", type=int, default=2, help="Retries per site fetch on failure")
    parser.add_argument("--backoff", type=float, default=0.5, help="Initial backoff seconds for retries")
    parser.add_argument("--timeout", type=float, default=None, help="Per-request timeout (unused) - reserved")

    args = parser.parse_args(argv)

    client = get_client(use_mock=args.mock)

    site_ids: List[str] = []
    if args.site_id:
        site_ids = [args.site_id]
    else:
        try:
            sites = client.get_sites(args.site_list)
            if isinstance(sites, SiteList):
                site_ids = [s.key for s in sites]
            else:
                # Try to construct site list
                site_ids = [s["key"] for s in sites]
        except Exception as e:
            logger.error(f"Failed to load site list: {e}")
            sys.exit(2)

    # Apply limit if requested
    if args.limit and args.limit > 0:
        site_ids = site_ids[:args.limit]

    ensure_dir(args.output_dir)

    def fetch_config(sid):
        try:
            cfg = client.get_site_config(sid)
            out_path = Path(args.output_dir) / f"{sid}.json"
            with out_path.open("w", encoding="utf-8") as f:
                # cfg may be dataclass-like
                try:
                    obj = cfg.__dict__
                except Exception:
                    obj = cfg
                json.dump(obj, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved config for {sid} -> {out_path}")
            return True
        except Exception as e:
            logger.exception(f"Failed to fetch config for {sid}: {e}")
            return False

    if args.parallel:
        logger.info(f"Fetching configs in parallel for {len(site_ids)} sites (workers={args.workers})")
        results = parallel_map(fetch_config, site_ids, workers=args.workers, retries=args.retries, backoff=args.backoff, timeout=args.timeout)
        # parallel_map returns (item, success, result), but since fetch_config returns bool, we can just log failures
        for item, ok, res in results:
            if not ok:
                logger.error(f"Overall failure for {item}")
    else:
        logger.info(f"Fetching configs sequentially for {len(site_ids)} sites")
        for sid in site_ids:
            ok, res = retry_call(fetch_config, sid, retries=args.retries, backoff=args.backoff, timeout=args.timeout)
            if not ok:
                logger.error(f"Failed to process {sid}")


if __name__ == "__main__":
    main()
