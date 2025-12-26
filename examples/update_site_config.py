#!/usr/bin/env python3
"""
Read an update payload (JSON) and optionally apply it to a site config via the SDK.
Defaults to dry-run. Backups are saved before applying when --apply is used.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from examples._util import get_client, ensure_dir, save_json, retry_call
except Exception:
    from _util import get_client, ensure_dir, save_json, retry_call

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def load_update_file(path: str) -> Dict[str, Any]:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def compute_diff(original: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, List[str]]:
    added = []
    changed = []
    for k, v in updates.items():
        if k not in original:
            added.append(k)
        else:
            if original.get(k) != v:
                changed.append(k)
    return {"added": added, "changed": changed}


def main(argv: Optional[List[str]] = None):
    parser = argparse.ArgumentParser(description="Update site configuration (dry-run by default)")
    parser.add_argument("--site-id", required=True, help="Site ID to update (e.g., S12345)")
    parser.add_argument("--update-file", required=True, help="JSON file with update payload")
    parser.add_argument("--backup-dir", default="portfolio/config_backups/", help="Directory to save backups")
    parser.add_argument("--apply", action="store_true", help="Apply the update (writes to API)")
    parser.add_argument("--mock", action="store_true", help="Use mock client for testing")
    parser.add_argument("--retries", type=int, default=2, help="Retries on API call failure")
    parser.add_argument("--backoff", type=float, default=0.5, help="Initial backoff seconds for retries")
    parser.add_argument("--timeout", type=float, default=None, help="Per-request timeout (unused) - reserved")

    args = parser.parse_args(argv)

    client = get_client(use_mock=args.mock)

    # Load update payload
    try:
        updates = load_update_file(args.update_file)
    except Exception as e:
        logger.error(f"Failed to load update file: {e}")
        sys.exit(2)

    # Fetch current config with retries
    ok, current = retry_call(client.get_site_config, args.site_id, retries=args.retries, backoff=args.backoff, timeout=args.timeout)
    if not ok:
        logger.error(f"Failed to fetch current config for {args.site_id}: {current}")
        sys.exit(2)
    try:
        current_dict = current.__dict__
    except Exception:
        current_dict = current or {}

    diff = compute_diff(current_dict, updates)

    logger.info(f"Update summary for {args.site_id}: {diff}")

    if not args.apply:
        logger.info("Dry-run: no changes will be made. Use --apply to apply the update.")
        return {
            "site_id": args.site_id,
            "diff": diff,
            "backup": None,
            "applied": False,
        }

    # Applying: save backup and call client.update_site_config
    ensure_dir(args.backup_dir)
    ts = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    backup_path = Path(args.backup_dir) / f"{args.site_id}_{ts}.json"
    try:
        save_json(current_dict, str(backup_path))
    except Exception as e:
        logger.error(f"Failed to save backup: {e}")
        sys.exit(2)

    ok, result = retry_call(client.update_site_config, args.site_id, updates, return_full_response=True, retries=args.retries, backoff=args.backoff, timeout=args.timeout)
    if not ok:
        logger.exception(f"Failed to apply update: {result}")
        sys.exit(2)
    success = getattr(result, 'success', False)
    logger.info(f"Update applied: success={success}")
    # Save server response
    resp_path = Path(args.backup_dir) / f"{args.site_id}_{ts}_response.json"
    try:
        save_json(result.__dict__ if hasattr(result, '__dict__') else result, str(resp_path))
    except Exception:
        pass

    return {
        "site_id": args.site_id,
        "diff": diff,
        "backup": str(backup_path),
        "applied": success,
    }


if __name__ == '__main__':
    main()
