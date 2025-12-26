#!/usr/bin/env python3
"""
Apply alert trigger updates from a JSON file. Dry-run by default; use --apply to perform writes.
Expected update file format: list of {"hardware_key": "H123", "action": "update"|"add"|"delete", "payload": {...}}
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from examples._util import get_client, ensure_dir, save_json, retry_call, parallel_map
except Exception:
    from _util import get_client, ensure_dir, save_json, retry_call, parallel_map

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def load_updates(path: str) -> List[Dict[str, Any]]:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def main(argv: Optional[List[str]] = None):
    parser = argparse.ArgumentParser(description="Apply alert updates (dry-run by default)")
    parser.add_argument("--updates-file", required=True, help="JSON file with updates")
    parser.add_argument("--apply", action="store_true", help="Perform updates")
    parser.add_argument("--backup-dir", default="portfolio/alert_backups/", help="Directory to save applied payloads/responses")
    parser.add_argument("--mock", action="store_true", help="Use mock client for testing")
    parser.add_argument("--parallel", action="store_true", help="Apply updates in parallel")
    parser.add_argument("--workers", type=int, default=5, help="Worker count when using --parallel")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of updates to process (0 = no limit)")
    parser.add_argument("--retries", type=int, default=2, help="Retries per update on failure")
    parser.add_argument("--backoff", type=float, default=0.5, help="Initial backoff seconds for retries")
    parser.add_argument("--timeout", type=float, default=None, help="Per-request timeout (unused) - reserved")

    args = parser.parse_args(argv)

    try:
        updates = load_updates(args.updates_file)
    except Exception as e:
        logger.error(f"Failed to load updates file: {e}")
        sys.exit(2)

    client = get_client(use_mock=args.mock)

    # Apply limit if requested
    if args.limit and args.limit > 0:
        updates = updates[:args.limit]

    summary = []

    if not args.apply:
        logger.info("Dry-run: will not apply changes. Listing planned actions:")
        for u in updates:
            logger.info(json.dumps(u, indent=2))
        return {"planned": updates}

    ensure_dir(args.backup_dir)
    ts = __import__('datetime').datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')

    def apply_update(u):
        hw = u.get('hardware_key')
        action = u.get('action', 'update')
        payload = u.get('payload', {})
        record = {"hardware_key": hw, "action": action, "success": False}
        try:
            if action == 'update':
                result = client.update_alert_triggers(hw, payload, return_full_response=True)
                record['success'] = getattr(result, 'success', bool(result))
                record['response'] = result.__dict__ if hasattr(result, '__dict__') else result
            elif action == 'add':
                ok = client.add_alert_trigger(hw, payload)
                record['success'] = bool(ok)
            elif action == 'delete':
                ok = client.delete_alert_trigger(hw)
                record['success'] = bool(ok)
            else:
                record['error'] = f"Unknown action: {action}"
        except Exception as e:
            logger.exception(f"Failed to process update for {hw}: {e}")
            record['error'] = str(e)
        return record

    if args.parallel:
        logger.info(f"Applying updates in parallel for {len(updates)} updates (workers={args.workers})")
        results = parallel_map(apply_update, updates, workers=args.workers, retries=args.retries, backoff=args.backoff, timeout=args.timeout)
        for item, ok, res in results:
            if ok:
                summary.append(res)
            else:
                logger.error(f"Failed to process update {item}: {res}")
                summary.append({"hardware_key": item.get('hardware_key'), "action": item.get('action'), "success": False, "error": str(res)})
    else:
        logger.info(f"Applying updates sequentially for {len(updates)} updates")
        for u in updates:
            ok, res = retry_call(apply_update, u, retries=args.retries, backoff=args.backoff, timeout=args.timeout)
            if ok:
                summary.append(res)
            else:
                logger.error(f"Failed to process update {u.get('hardware_key')}: {res}")
                summary.append({"hardware_key": u.get('hardware_key'), "action": u.get('action'), "success": False, "error": str(res)})

    # Save summary and responses
    out_path = Path(args.backup_dir) / f"applied_alerts_{ts}.json"
    save_json(summary, str(out_path))
    logger.info(f"Applied alerts saved to {out_path}")
    return {'applied': summary}


if __name__ == '__main__':
    main()
