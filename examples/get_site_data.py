#!/usr/bin/env python3
"""
Example script for PowerTrackClient.get_site_data()
Usage: python3 examples/get_site_data.py --site-id S60308 [--include-hardware --include-alerts --include-modeling] [--mock]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from typing import Any, Optional

# The below allows for importing a mock client for testing purposes from the examples directory.
# In production, you would import your client from the actual SDK package.

try:
    from examples._util import get_client
except Exception:
    from _util import get_client


def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description="Example: Get comprehensive site data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 examples/get_site_data.py --site-id S60308 --mock
  python3 examples/get_site_data.py --site-id S60308 --include-hardware --no-alerts --output site_data.json
        """
    )
    parser.add_argument("--site-id", required=True, help="Site ID (e.g., S60308)")
    parser.add_argument("--include-hardware", action="store_true", default=True, help="Include hardware details")
    parser.add_argument("--no-hardware", dest="include_hardware", action="store_false", help="Do not fetch hardware details")
    parser.add_argument("--include-alerts", action="store_true", default=True, help="Include alerts")
    parser.add_argument("--no-alerts", dest="include_alerts", action="store_false", help="Do not fetch alerts")
    parser.add_argument("--include-modeling", action="store_true", default=True, help="Include modeling data")
    parser.add_argument("--no-modeling", dest="include_modeling", action="store_false", help="Do not fetch modeling data")
    parser.add_argument("--mock", action="store_true", help="Use mock client for testing")
    parser.add_argument("--output", help="Output file (default: stdout)")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args(argv)

    client = get_client(use_mock=args.mock)

    if args.verbose:
        print(f"Calling get_site_data(site_id='{args.site_id}', include_hardware={args.include_hardware}, include_alerts={args.include_alerts}, include_modeling={args.include_modeling})", file=sys.stderr)

    try:
        result = client.get_site_data(args.site_id, args.include_hardware, args.include_alerts, args.include_modeling)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Convert result to serializable dict
    def to_safe(o):
        if o is None:
            return None
        if isinstance(o, (str, int, float, bool)):
            return o
        if isinstance(o, dict):
            return {str(k): to_safe(v) for k, v in o.items()}
        if isinstance(o, (list, tuple, set)):
            return [to_safe(v) for v in o]
        import types
        if isinstance(o, types.MappingProxyType):
            return to_safe(dict(o))
        if hasattr(o, '__dict__'):
            try:
                return to_safe(o.__dict__)
            except Exception:
                return str(o)
        return str(o)

    output = {
        "method": "get_site_data",
        "args": {
            "site_id": args.site_id,
            "include_hardware": args.include_hardware,
            "include_alerts": args.include_alerts,
            "include_modeling": args.include_modeling
        },
        "result": to_safe(result),
        "timestamp": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    }

    json_output = json.dumps(output, indent=2, ensure_ascii=False, default=str)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(json_output)
        if args.verbose:
            print(f"Output written to {args.output}", file=sys.stderr)
    else:
        print(json_output)


if __name__ == "__main__":
    main()