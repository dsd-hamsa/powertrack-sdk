#!/usr/bin/env python3
"""
PowerTrack Site List Fetcher (SDK Version)
Fetches all sites in a user's portfolio using the PowerTrack SDK
and creates SiteList.json for use with other SDK methods.

Usage:
    python3 fetch_site_list.py --customer-id C1234

Environment Variables:
    Same as PowerTrack SDK (COOKIE, AE_S, etc.)

Output:
    portfolio/SiteList.json - Complete site list with metadata
"""

import os
import argparse
import json
import sys
import logging
from pathlib import Path
from datetime import datetime, timezone

# Try to load environment variables from .env file (optional)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from powertrack_sdk import PowerTrackClient, Site, SiteList


# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def fetch_site_list_sdk(customer_id: str) -> SiteList:
    """Fetch site list using PowerTrack SDK."""
    print(f"[i] Fetching site list for customer: {customer_id}")

    try:
        client = PowerTrackClient()

        # Get portfolio overview which includes all sites
        portfolio = client.get_portfolio_overview(customer_id)
        if not portfolio:
            raise RuntimeError(f"Failed to fetch portfolio for customer {customer_id}")

        print(f"[i] Found {len(portfolio.sites)} sites in portfolio")

        # Convert portfolio sites to Site objects
        sites = []
        for site_overview in portfolio.sites:
            site = Site(
                key=site_overview.site_id,
                name=site_overview.name
            )
            sites.append(site)

        # Create metadata
        metadata = {
            "customer_id": customer_id,
            "total_sites": len(sites),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source": "PowerTrack SDK get_portfolio_overview"
        }

        site_list = SiteList(sites, metadata)
        return site_list

    except Exception as e:
        print(f"[x] Error fetching site list: {e}")
        raise


def save_site_list(site_list: SiteList, output_file: str):
    """Save SiteList to JSON file."""
    try:
        # Create output directory
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to dict format for JSON
        data = {
            "metadata": site_list.metadata,
            "sites": [
                {
                    "key": site.key,
                    "name": site.name,
                    "metadata": site.metadata
                }
                for site in site_list
            ]
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"[✓] Site list saved to: {output_file}")
        print(f"[i] Contains {len(site_list)} sites")

    except Exception as e:
        print(f"[x] Error saving site list: {e}")
        raise


def main():
    parser = argparse.ArgumentParser(
        description="Fetch all sites in a PowerTrack portfolio using the SDK",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment Variables (required):
    COOKIE        Full cookie string from Chrome DevTools
    AE_S          Security header value (ae_s)
    AE_V          API version header (default: 086665)
    BASE_URL      API base URL (default: https://apps.alsoenergy.com)

Examples:
    # Basic usage
    export COOKIE="your_cookie_string_here"
    export AE_S="*WPOMs1+UDquA3lmqjIlKm9mGjr7uixpBspy0HA=="
    python fetch_site_list.py --customer-id C1234

    # Custom output location
    python fetch_site_list.py --customer-id C1234 --output portfolio/my_sites.json

Note: Authentication setup is the same as the main SDK.
See README.md for authentication instructions.
        """
    )
    parser.add_argument(
        "--customer-id",
        required=True,
        help="Customer ID to fetch sites for (e.g., C1234)"
    )
    parser.add_argument(
        "--output",
        default="portfolio/SiteList.json",
        help="Output file path (default: portfolio/SiteList.json)"
    )

    args = parser.parse_args()

    print(f"[i] Customer ID: {args.customer_id}")
    print(f"[i] Output file: {args.output}")

    try:
        # Fetch site list using SDK
        site_list = fetch_site_list_sdk(args.customer_id)

        # Save to file
        save_site_list(site_list, args.output)

        print("\n[✓] Site list fetching complete!")
        print("[i] Use this file with SDK methods like:")
        print(f"    site_list = SiteList.from_json_file('{args.output}')")

    except Exception as e:
        print(f"[x] Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()