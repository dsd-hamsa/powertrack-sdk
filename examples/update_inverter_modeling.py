#!/usr/bin/env python3
"""
Example script for updating inverter modeling configuration via PowerTrack SDK.

This script demonstrates the recommended workflow for modifying inverter modeling data:
1. GET current hardware configuration (including modeling data)
2. Modify the JSON locally (manually or via your preferred interface)
3. PUT the updated configuration back to the API

The script uses the SDK's update_hardware_config() method which:
- Fetches current hardware config via GET /api/edit/hardware/{hardware_id}
- Merges your partial updates into the full configuration
- PUTs the complete merged payload to /api/edit/hardware

Usage Examples:
  # Dry-run: fetch current config and show what would change
  python3 examples/update_inverter_modeling.py --site-id S60308 --inverter-id H511568 --mock

  # Apply updates from a JSON file
  python3 examples/update_inverter_modeling.py --site-id S60308 --inverter-id H511568 --update-file inverter_updates.json --apply

  # Interactive mode: edit config in your preferred editor
  python3 examples/update_inverter_modeling.py --site-id S60308 --inverter-id H511568 --edit --apply

Common Modeling Parameters to Modify:
- azimuth: Panel azimuth angle (degrees, 0-360)
- tilt: Panel tilt angle (degrees, 0-90)
- derate: System derate factor (0.0-1.0)
- pvSystModuleId: PVSyst module ID for modeling
- pvSystOutOfSync: Whether PVSyst data is synchronized
- mppWatts: Maximum power point watts (inverter capacity)

Finding Inverter Hardware IDs:
Use get_hardware_list() to find inverters at your site:
  python3 examples/get_hardware_list.py --site-id S60308 --mock

Look for hardware with functionCode: 1 (Inverter PV).
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import tempfile
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from examples._util import get_client, ensure_dir, save_json, retry_call
except Exception:
    from _util import get_client, ensure_dir, save_json, retry_call

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def load_update_file(path: str) -> Dict[str, Any]:
    """Load update payload from JSON file."""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def compute_config_diff(original: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, List[str]]:
    """Compute diff between original and updated configuration."""
    added = []
    changed = []
    removed = []

    # Check for added/changed keys
    for key, value in updates.items():
        if key not in original:
            added.append(key)
        elif original[key] != value:
            changed.append(key)

    return {"added": added, "changed": changed, "removed": removed}


def edit_config_interactively(config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Allow user to edit config using their preferred editor."""
    # Create temporary file with current config
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
        temp_path = f.name

    try:
        # Try to get editor from environment or use sensible defaults
        editor = (
            os.environ.get('EDITOR') or
            os.environ.get('VISUAL') or
            'nano'  # fallback editor
        )

        print(f"Opening {temp_path} in {editor}...")
        print("Modify the modeling parameters you want to change, then save and exit.")
        print("Common fields to modify: azimuth, tilt, derate, pvSystModuleId, etc.")

        result = subprocess.run([editor, temp_path])
        if result.returncode != 0:
            logger.error(f"Editor exited with code {result.returncode}")
            return None

        # Read back the edited config
        with open(temp_path, 'r', encoding='utf-8') as f:
            edited_config = json.load(f)

        # Show diff
        diff = compute_config_diff(config, edited_config)
        if any(diff.values()):
            print("Changes detected:")
            if diff['added']:
                print(f"  Added: {', '.join(diff['added'])}")
            if diff['changed']:
                print(f"  Changed: {', '.join(diff['changed'])}")
            if diff['removed']:
                print(f"  Removed: {', '.join(diff['removed'])}")
        else:
            print("No changes detected.")

        return edited_config

    except Exception as e:
        logger.error(f"Failed to edit config: {e}")
        return None
    finally:
        # Clean up temp file
        try:
            Path(temp_path).unlink()
        except Exception:
            pass


def validate_hardware(client, hardware_id: str, site_id: Optional[str] = None) -> bool:
    """Validate that the hardware exists and optionally check site association."""
    try:
        details = client.get_hardware_details(hardware_id)
        if not details:
            logger.error(f"Hardware {hardware_id} not found")
            return False

        # If site_id provided, validate hardware belongs to site
        if site_id:
            hardware_list = client.get_hardware_list(site_id)
            hardware_ids = [hw.key for hw in hardware_list]
            if hardware_id not in hardware_ids:
                logger.warning(f"Hardware {hardware_id} not found at site {site_id}")
                logger.warning("Continuing anyway - hardware may exist but site association unclear")

        if details.summary.functionCode != 1:
            logger.warning(f"Hardware {hardware_id} is not an inverter (functionCode: {details.summary.functionCode})")
            logger.warning("This script is designed for inverter modeling updates.")
            logger.warning("Use functionCode=1 for inverters (PV).")
        else:
            logger.info(f"Validated inverter hardware {hardware_id}")

        return True
    except Exception as e:
        logger.error(f"Failed to validate hardware {hardware_id}: {e}")
        return False


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description="Update hardware modeling configuration (primarily for inverters)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry-run: show current config and what would change
  python3 examples/update_inverter_modeling.py --hardware-id H511568 --mock

  # Apply updates from JSON file
  python3 examples/update_inverter_modeling.py --hardware-id H511568 --update-file updates.json --apply

  # Interactive editing mode
  python3 examples/update_inverter_modeling.py --hardware-id H511568 --edit --apply

  # Find hardware IDs first
  python3 examples/get_hardware_list.py --site-id S60308 --mock

Common Modeling Parameters (examples - you can edit ANY field):
  azimuth: Panel azimuth angle (0-360 degrees)
  tilt: Panel tilt angle (0-90 degrees)
  derate: System derate factor (0.0-1.0)
  pvSystModuleId: PVSyst module ID
  mppWatts: Inverter capacity in watts
  pvSystOutOfSync: PVSyst synchronization flag

The interactive editor opens the COMPLETE hardware configuration JSON,
allowing you to modify any field, not just modeling parameters.

Note: While designed for inverters, this script works with any hardware type.
        """
    )
    parser.add_argument("--site-id", help="Site ID (optional, used for validation - e.g., S60308)")
    parser.add_argument("--hardware-id", required=True, help="Hardware ID to update (e.g., H511568)")
    parser.add_argument("--update-file", help="JSON file with update payload")
    parser.add_argument("--edit", action="store_true", help="Interactively edit current config")
    parser.add_argument("--output-dir", default="portfolio/hardware_backups/", help="Directory to save backups")
    parser.add_argument("--apply", action="store_true", help="Apply the update (writes to API)")
    parser.add_argument("--mock", action="store_true", help="Use mock client for testing")
    parser.add_argument("--retries", type=int, default=2, help="Retries on API call failure")
    parser.add_argument("--backoff", type=float, default=0.5, help="Initial backoff seconds for retries")
    parser.add_argument("--timeout", type=float, default=None, help="Per-request timeout")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args(argv)

    client = get_client(use_mock=args.mock)

    # Validate hardware
    if not validate_hardware(client, args.hardware_id, args.site_id):
        sys.exit(1)

    # Determine update payload
    updates = {}

    if args.update_file:
        # Load updates from file
        try:
            updates = load_update_file(args.update_file)
        except Exception as e:
            logger.error(f"Failed to load update file: {e}")
            sys.exit(1)
    elif args.edit:
        # Interactive editing mode
        try:
            # First fetch current config for editing
            ok, current_config = retry_call(
                client.get_hardware_details,
                args.hardware_id,
                retries=args.retries,
                backoff=args.backoff,
                timeout=args.timeout
            )
            if not ok:
                logger.error(f"Failed to fetch current config: {current_config}")
                sys.exit(1)

            if not current_config:
                logger.error("No current configuration data available")
                sys.exit(1)

            # Extract the details dict for editing
            current_config = current_config.details
            if not current_config:
                logger.error("No configuration details available")
                sys.exit(1)

            edited_config = edit_config_interactively(current_config)
            if edited_config is None:
                logger.error("Config editing cancelled or failed")
                sys.exit(1)

            # Compute what changed
            diff = compute_config_diff(current_config, edited_config)
            if not any(diff.values()):
                logger.info("No changes made, exiting.")
                return

            # Use only the changed fields as updates
            updates = {k: edited_config[k] for k in diff['added'] + diff['changed']}

        except Exception as e:
            logger.error(f"Interactive editing failed: {e}")
            sys.exit(1)
    else:
        # Just show current config (dry-run mode)
        logger.info("No --update-file or --edit specified, showing current configuration...")

    if args.verbose:
        logger.info(f"Update payload: {json.dumps(updates, indent=2)}")

    # Dry-run: show what would happen
    if not args.apply:
        logger.info("DRY-RUN MODE - No changes will be made")
        logger.info(f"Would update hardware {args.hardware_id} with: {updates}")
        return

    # Apply updates
    ensure_dir(args.output_dir)
    ts = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    backup_path = Path(args.output_dir) / f"{args.hardware_id}_{ts}.json"

    logger.info(f"Applying updates to {args.hardware_id}...")

    ok, result = retry_call(
        client.update_hardware_config,
        args.hardware_id,
        updates,
        return_full_response=True,
        retries=args.retries,
        backoff=args.backoff,
        timeout=args.timeout
    )

    if not ok:
        logger.error(f"Failed to apply update: {result}")
        sys.exit(1)

    success = getattr(result, 'success', False)
    logger.info(f"Update applied: success={success}")

    # Save backup of original config
    if hasattr(result, 'originalData') and result.originalData:
        try:
            save_json(result.originalData, str(backup_path))
            logger.info(f"Original config backed up to: {backup_path}")
        except Exception as e:
            logger.warning(f"Failed to save backup: {e}")

    # Save response data
    resp_path = Path(args.output_dir) / f"{args.hardware_id}_{ts}_response.json"
    try:
        save_json(result.__dict__ if hasattr(result, '__dict__') else result, str(resp_path))
    except Exception as e:
        pass

    if success:
        logger.info(f"Successfully updated hardware {args.hardware_id} configuration")
        if updates:
            logger.info(f"Applied changes: {list(updates.keys())}")
    else:
        error_msg = getattr(result, 'errorMessage', 'Unknown error')
        logger.error(f"Update failed: {error_msg}")
        sys.exit(1)


if __name__ == "__main__":
    main()