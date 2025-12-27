#!/usr/bin/env python3
"""
Example script for PowerTrackClient.get_chart_data()
Usage: python3 examples/get_chart_data.py --chart-type 255 --site-id S70726 [--start-date 2024-01-01T00:00:00Z --end-date 2024-01-31T23:59:59Z] [--mock]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from typing import Any, Optional
import os

try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    import pandas as pd
    HAS_PLOTTING = True
except ImportError:
    HAS_PLOTTING = False
"""
The below allows for importing a mock client for testing purposes from the examples directory.
In production, you would import your client from the actual SDK package.
"""
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
  python3 examples/get_chart_data.py --site-id S60134
  python3 examples/get_chart_data.py --chart-type 255 --site-id S60134 --start-date 2024-01-01T00:00:00Z --end-date 2024-01-31T23:59:59Z --output chart.json
  python3 examples/get_chart_data.py --site-id S60134 --bin-size 60 --render --render-file my_chart.png
        """
    )
    parser.add_argument("--chart-type", type=int, default=255, help="Chart type ID (default: 255)")
    parser.add_argument("--site-id", required=True, help="Site ID (e.g., S60308)")
    parser.add_argument("--start-date", help="Start date (ISO format, optional)")
    parser.add_argument("--end-date", help="End date (ISO format, optional)")
    parser.add_argument("--bin-size", type=int, help="Bin size in minutes (optional, let API choose if not specified)")
    parser.add_argument("--mock", action="store_true", help="Use mock client for testing")
    parser.add_argument("--output", help="Output file (default: stdout)")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--render", action="store_true", help="Render chart to image file")
    parser.add_argument("--render-file", default="chart.png", help="Output file for rendered chart (default: chart.png)")

    args = parser.parse_args(argv)

    client = get_client(use_mock=args.mock)

    if args.verbose:
        print(f"Calling get_chart_data(chart_type={args.chart_type}, site_id='{args.site_id}', start_date={args.start_date}, end_date={args.end_date}, bin_size={args.bin_size})", file=sys.stderr)

    try:
        result = client.get_chart_data(args.chart_type, args.site_id, args.start_date, args.end_date, args.bin_size)
        if result is None:
            print(f"No chart data available for chart_type={args.chart_type}, site_id={args.site_id}", file=sys.stderr)
            sys.exit(1)
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
            "end_date": args.end_date,
            "bin_size": args.bin_size
        },
        "result": to_safe(result),
        "timestamp": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    }

    # Render chart if requested
    if args.render:
        if not HAS_PLOTTING:
            print("Warning: matplotlib and pandas required for chart rendering. Install with: pip install matplotlib pandas", file=sys.stderr)
        elif result and result.series:
            try:
                render_chart(result, args.render_file)
                if args.verbose:
                    print(f"Chart rendered to {args.render_file}", file=sys.stderr)
            except Exception as e:
                print(f"Warning: Failed to render chart: {e}", file=sys.stderr)
        else:
            print("Warning: No chart data available to render", file=sys.stderr)

    json_output = json.dumps(output, indent=2, ensure_ascii=False, default=str)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(json_output)
        if args.verbose:
            print(f"Output written to {args.output}", file=sys.stderr)
    else:
        print(json_output)


def render_chart(chart_data, output_file):
    """Render chart data to an image file using matplotlib."""
    if not HAS_PLOTTING:
        raise ImportError("matplotlib and pandas required for chart rendering")

    fig, axes = plt.subplots(len(chart_data.series), 1, figsize=(12, 6 * len(chart_data.series)), squeeze=False)
    fig.suptitle(f"Chart Data: {chart_data.key}", fontsize=14)

    for i, series in enumerate(chart_data.series):
        ax = axes[i, 0]

        if series.dataXy:
            # Convert timestamps to datetime
            timestamps = [datetime.fromtimestamp(point[0] / 1000) for point in series.dataXy]
            values = [point[1] for point in series.dataXy]

            ax.plot(timestamps, values, color=series.color or '#000000',
                   linewidth=series.line_width or 1, label=series.name)
            ax.scatter(timestamps, values, color=series.color or '#000000', s=10)

        ax.set_title(f"{series.name} ({series.custom_unit or 'units'})")
        ax.set_xlabel("Time")
        ax.set_ylabel(series.custom_unit or "Value")
        ax.grid(True, alpha=0.3)
        ax.legend()

        # Format x-axis dates
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()


if __name__ == "__main__":
    main()