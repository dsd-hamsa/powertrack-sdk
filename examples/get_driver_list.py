#!/usr/bin/env python3
"""
Example script for PowerTrackClient.get_driver_list()
Usage: python3 examples/get_driver_list.py [--category 1] [--mock]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from typing import Optional

try:
    from examples._util import get_client
except ImportError:
    from _util import get_client


def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description="Example: Get list of available drivers by functionCode",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 examples/get_driver_list.py --mock
  python3 examples/get_driver_list.py --category 1 --output drivers.json
        """
    )
    parser.add_argument(
        "--code", 
        type=int, 
        default=1, 
        help="Device functionCode (default: 1 for inverters)")
    parser.add_argument(
        "--mock", 
        action="store_true", 
        help="Use mock client for testing")
    parser.add_argument(
        "--output", 
        help="Output file (default: stdout)")
    parser.add_argument(
        "--verbose", 
        action="store_true", 
        help="Verbose output")

    args = parser.parse_args(argv)

    client = get_client(use_mock=args.mock)

    if args.verbose:
        print(f"Calling get_driver_list(code={args.code})", file=sys.stderr)

    try:
        result = client.get_driver_list(args.code)
    except (ValueError, ConnectionError, TimeoutError, OSError) as e:
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
        return str(o)

    output = {
        "method": "get_driver_list",
        "args": {
            "functionCode": args.code
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