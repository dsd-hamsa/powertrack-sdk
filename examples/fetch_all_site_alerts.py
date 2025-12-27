#!/usr/bin/env python3
"""
Fetch alert summaries and detailed triggers for a customer or site.

Saves aggregated JSON with summary and per-hardware details.
"""

# The below allows for importing a mock client for testing purposes from the examples directory.
# In production, you would import your client from the actual SDK package.

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
import re

try:
    from examples._util import get_client, save_json, ensure_dir, retry_call, parallel_map
except Exception:
    # Allow running the script directly (not as package)
    from _util import get_client, save_json, ensure_dir, retry_call, parallel_map

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def main(argv: Optional[List[str]] = None):
    parser = argparse.ArgumentParser(description="Fetch alert summaries and triggers using the PowerTrack SDK")
    parser.add_argument("--customer-id", help="Customer ID (preferred)")
    parser.add_argument("--site-id", help="Site ID (alternative)")
    parser.add_argument("--output", help="Output JSON file", default=None)
    parser.add_argument("--mock", action="store_true", help="Use mock client for testing")
    parser.add_argument("--parallel", action="store_true", help="Fetch triggers in parallel")
    parser.add_argument("--workers", type=int, default=5, help="Worker count when using --parallel")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of hardware triggers to fetch (0 = no limit)")
    parser.add_argument("--retries", type=int, default=2, help="Retries per hardware fetch on failure")
    parser.add_argument("--backoff", type=float, default=0.5, help="Initial backoff seconds for retries")
    parser.add_argument("--timeout", type=float, default=None, help="Per-request timeout (unused) - reserved")
    parser.add_argument("--no-filter", action="store_true", help="Do not filter keys to H#### pattern")

    args = parser.parse_args(argv)

    if not args.customer_id and not args.site_id:
        parser.error("Either --customer-id or --site-id must be provided")

    client = get_client(use_mock=args.mock)

    try:
        summary = client.get_alert_summary(customer_id=args.customer_id, siteId=args.site_id)
    except Exception as e:
        logger.error(f"Failed to fetch alert summary: {e}")
        sys.exit(2)

    # Build details for each hardware with alerts
    details = {}
    hw_keys = []
    # Determine hardware keys in a safe, type-aware way
    hw_keys = []
    if hasattr(summary, "hardware_summaries"):
        # Typed response (AlertSummaryResponse) exposes a dict attribute
        try:
            hw_map = getattr(summary, "hardware_summaries")
            if isinstance(hw_map, dict):
                hw_keys = list(hw_map.keys())
        except Exception:
            hw_keys = []
    elif isinstance(summary, dict):
        # Plain dict-like response
        hw_keys = list(summary.keys())

    # Filter keys to hardware-like keys (e.g., H12345) to avoid non-hardware items
    if not args.no_filter:
        hw_keys = [k for k in hw_keys if isinstance(k, str) and re.match(r"^H\d+$", k)]

    # Apply limit if requested
    if args.limit and args.limit > 0:
        hw_keys = hw_keys[: args.limit]

    if args.parallel:
        logger.info(f"Fetching triggers in parallel for {len(hw_keys)} hardware (workers={args.workers})")
        results = parallel_map(lambda hw: client.get_alert_triggers(hw), hw_keys, workers=args.workers, retries=args.retries, backoff=args.backoff, timeout=args.timeout)
        for item, ok, res in results:
            if ok:
                details[item] = res.__dict__ if res is not None and hasattr(res, "__dict__") else res
            else:
                logger.warning(f"Failed to fetch trigger for {item}: {res}")
                details[item] = {"error": str(res)}
    else:
        logger.info(f"Fetching triggers sequentially for {len(hw_keys)} hardware")
        for hw in hw_keys:
            ok, res = retry_call(client.get_alert_triggers, hw, retries=args.retries, backoff=args.backoff, timeout=args.timeout)
            if ok:
                details[hw] = res.__dict__ if res is not None and hasattr(res, "__dict__") else res
            else:
                logger.warning(f"Failed to fetch trigger for {hw}: {res}")
                details[hw] = {"error": str(res)}

    # Prepare a JSON-serializable summary
    summary_out = None
    aggregated_summary = {"total_alerts": 0, "by_severity": {}, "alert_names": set()}
    if hasattr(summary, "hardware_summaries"):
        hw_map = getattr(summary, "hardware_summaries") or {}
        summary_out = {"hardware_summaries": {}}
        if isinstance(hw_map, dict):
            for k, v in hw_map.items():
                if hasattr(v, "__dict__"):
                    # dataclass-like object
                    try:
                        v_dict = v.__dict__
                        summary_out["hardware_summaries"][k] = v_dict
                        # Aggregate
                        count = v_dict.get("count", 0)
                        severity = v_dict.get("max_severity", 0)
                        aggregated_summary["total_alerts"] += count
                        aggregated_summary["by_severity"][severity] = aggregated_summary["by_severity"].get(severity, 0) + count
                    except Exception:
                        summary_out["hardware_summaries"][k] = str(v)
                else:
                    summary_out["hardware_summaries"][k] = v
                    # Aggregate if dict
                    if isinstance(v, dict):
                        count = v.get("count", 0)
                        severity = v.get("maxSeverity", v.get("max_severity", 0))
                        aggregated_summary["total_alerts"] += count
                        aggregated_summary["by_severity"][severity] = aggregated_summary["by_severity"].get(severity, 0) + count

    # Collect alert names from details
    for hw_detail in details.values():
        if isinstance(hw_detail, dict) and "triggers" in hw_detail:
            for trigger in hw_detail["triggers"]:
                if isinstance(trigger, dict) and "name" in trigger:
                    aggregated_summary["alert_names"].add(trigger["name"])

    # Convert set to list for JSON
    aggregated_summary["alert_names"] = sorted(list(aggregated_summary["alert_names"]))

    if isinstance(summary, dict):
        summary_out = summary
    else:
        summary_out = str(summary)

    out = {
        "aggregated_summary": aggregated_summary,
        "summary": summary_out,
        "details": details,
    }

    output_path = args.output or f"portfolio/alert_summary_{args.customer_id or args.site_id}.json"
    ensure_dir(Path(output_path).parent.as_posix())
    # Ensure everything is JSON-serializable by converting common SDK model wrappers
    import types

    def to_safe(o):
        if o is None:
            return None
        if isinstance(o, (str, int, float, bool)):
            return o
        if isinstance(o, dict):
            return {str(k): to_safe(v) for k, v in o.items()}
        if isinstance(o, (list, tuple, set)):
            return [to_safe(v) for v in o]
        if isinstance(o, types.MappingProxyType):
            return to_safe(dict(o))
        # dataclass-like or objects with __dict__
        if hasattr(o, '__dict__'):
            try:
                return to_safe(o.__dict__)
            except Exception:
                return str(o)
        # fallback
        return str(o)

    out_safe = to_safe(out)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(out_safe, f, indent=2, ensure_ascii=False)

    logger.info(f"Alert summary and details saved to {output_path}")


if __name__ == "__main__":
    main()
