#!/usr/bin/env python3
"""
Example script for PowerTrackClient.get_chart_definitions()
Usage: python3 examples/get_chart_definitions.py [--mock]
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
        description="Example: Get available chart type definitions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 examples/get_chart_definitions.py --mock
  python3 examples/get_chart_definitions.py --output charts.json
        """
    )
    parser.add_argument("--mock", action="store_true", help="Use mock client for testing")
    parser.add_argument("--output", help="Output file (default: stdout)")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args(argv)

    client = get_client(use_mock=args.mock)

    if args.verbose:
        print("Calling get_chart_definitions()", file=sys.stderr)

    try:
        result = client.get_chart_definitions()
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
        "method": "get_chart_definitions",
        "args": {},
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