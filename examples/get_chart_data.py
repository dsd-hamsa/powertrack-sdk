#!/usr/bin/env python3
"""
Example script for PowerTrackClient.get_chart_data()
Usage: python3 examples/get_chart_data.py --chart-type 1 --site-id S60308 [--start-date 2024-01-01T00:00:00Z --end-date 2024-01-31T23:59:59Z] [--mock]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from typing import Any, Optional

try:
    from examples._util import get_client
except Exception:
    from _util import get_client


def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description="Example: Get chart data for visualization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 examples/get_chart_data.py --chart-type 1 --site-id S60308 --mock
  python3 examples/get_chart_data.py --chart-type 1 --site-id S60308 --start-date 2024-01-01T00:00:00Z --end-date 2024-01-31T23:59:59Z --output chart.json
        """
    )
    parser.add_argument("--chart-type", type=int, required=True, help="Chart type ID (e.g., 1)")
    parser.add_argument("--site-id", required=True, help="Site ID (e.g., S60308)")
    parser.add_argument("--start-date", help="Start date (ISO format, optional)")
    parser.add_argument("--end-date", help="End date (ISO format, optional)")
    parser.add_argument("--mock", action="store_true", help="Use mock client for testing")
    parser.add_argument("--output", help="Output file (default: stdout)")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args(argv)

    client = get_client(use_mock=args.mock)

    if args.verbose:
        print(f"Calling get_chart_data(chart_type={args.chart_type}, site_id='{args.site_id}', start_date={args.start_date}, end_date={args.end_date})", file=sys.stderr)

    try:
        result = client.get_chart_data(args.chart_type, args.site_id, args.start_date, args.end_date)
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
        "method": "get_chart_data",
        "args": {
            "chart_type": args.chart_type,
            "site_id": args.site_id,
            "start_date": args.start_date,
            "end_date": args.end_date
        },
        "result": to_safe(result),
        "timestamp": datetime.utcnow().isoformat() + "Z"
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