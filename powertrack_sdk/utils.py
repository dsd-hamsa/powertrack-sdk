"""
Utility functions for PowerTrack SDK
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import re

def camel_to_snake(name: str) -> str:
    """Convert camelCase string to snake_case."""
    if not name:
        return name
    result = [name[0].lower()]
    for i in range(1, len(name)):
        if name[i].isupper():
            if name[i-1].islower() or (i < len(name)-1 and name[i+1].islower()):
                result.append("_")
            result.append(name[i].lower())
        else:
            result.append(name[i])
    return "".join(result)

def convert_keys_to_snake_case(data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert all dictionary keys from camelCase to snake_case recursively."""
    if not isinstance(data, dict):
        return data
    
    result = {}
    for key, value in data.items():
        snake_key = camel_to_snake(key)
        if isinstance(value, dict):
            result[snake_key] = convert_keys_to_snake_case(value)
        elif isinstance(value, list):
            result[snake_key] = [convert_keys_to_snake_case(item) if isinstance(item, dict) else item for item in value]
        else:
            result[snake_key] = value
    return result



def get_current_datetime_iso() -> str:
    """Get current datetime in ISO format with Z suffix."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")[:-3] + "Z"


def load_json_file(filepath: Path) -> Dict[str, Any]:
    """
    Load JSON data from file.

    Args:
        filepath: Path to JSON file

    Returns:
        Parsed JSON data

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If JSON is invalid
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json_file(data: Any, filepath: Path, indent: int = 2) -> None:
    """
    Save data to JSON file.

    Args:
        data: Data to save
        filepath: Output file path
        indent: JSON indentation level
    """
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=indent)


def parse_site_id(site_identifier: str) -> str:
    """
    Parse and validate site ID format.

    Args:
        site_identifier: Site ID (e.g., 'S60308' or '60308')

    Returns:
        Normalized site ID with 'S' prefix

    Raises:
        ValueError: If format is invalid
    """
    if site_identifier.startswith('S'):
        site_id = site_identifier
    else:
        site_id = f'S{site_identifier}'

    if len(site_id) != 6 or not site_id[1:].isdigit():
        raise ValueError(f"Invalid site ID format: {site_identifier}. Expected format: S#####")

    return site_id


def parse_hardware_id(hardware_identifier: str) -> str:
    """
    Parse and validate hardware ID format.

    Args:
        hardware_identifier: Hardware ID (e.g., 'H123456' or '123456')

    Returns:
        Normalized hardware ID with 'H' prefix

    Raises:
        ValueError: If format is invalid
    """
    if hardware_identifier.startswith('H'):
        hw_id = hardware_identifier
    else:
        hw_id = f'H{hardware_identifier}'

    if not hw_id[1:].isdigit():
        raise ValueError(f"Invalid hardware ID format: {hardware_identifier}. Expected format: H#####")

    return hw_id


def get_hardware_type_name(function_code: Optional[int]) -> str:
    """Get human-readable hardware type name from function code."""
    hardware_types = {
        1: "Inverter (PV)",
        2: "Production Meter (PM)",
        3: "Type 3",
        4: "Grid Meter (GM)",
        5: "Weather Station (WS)",
        6: "DC Combiner",
        9: "Kiosk",
        10: "Gateway (GW)",
        11: "Cell Modem (CE)",
        14: "Camera",
        20: "Extra Meter",
        21: "DNP3 Server",
        24: "Tracker",
        25: "BESS Controller",
        28: "Data Logger",
        31: "Data Capture",
        34: "Relay",
        37: "BESS Meter",
    }

    if function_code is None:
        return "Unknown"
    return hardware_types.get(function_code, f"Type {function_code}")


def get_function_codes_help() -> str:
    """Get formatted help text for available function codes."""
    codes = {
        1: "Inverter (PV)",
        2: "Production Meter (PM)",
        3: "Type 3",
        4: "Grid Meter (GM)",
        5: "Weather Station (WS)",
        6: "DC Combiner",
        9: "Kiosk",
        10: "Gateway (GW)",
        11: "Cell Modem (CE)",
        14: "Camera",
        20: "Extra Meter",
        21: "DNP3 Server",
        24: "Tracker",
        25: "BESS Controller",
        28: "Data Logger",
        31: "Data Capture",
        34: "Relay",
        37: "BESS Meter",
    }

    lines = ["Available function codes:"]
    for code, name in sorted(codes.items()):
        lines.append(f"  {code}: {name}")
    return "\n".join(lines)


def flatten_dict(data: Dict[str, Any], prefix: str = '', separator: str = '_') -> Dict[str, Any]:
    """
    Flatten nested dictionary.

    Args:
        data: Dictionary to flatten
        prefix: Key prefix
        separator: Key separator

    Returns:
        Flattened dictionary
    """
    flattened = {}

    for key, value in data.items():
        new_key = f"{prefix}{separator}{key}" if prefix else key

        if isinstance(value, dict):
            flattened.update(flatten_dict(value, new_key, separator))
        elif isinstance(value, list):
            # Convert lists to comma-separated strings for CSV compatibility
            flattened[new_key] = ', '.join(str(item) for item in value)
        else:
            flattened[new_key] = value

    return flattened


def safe_get(data: Dict[str, Any], key_path: str, default: Any = None) -> Any:
    """
    Safely get nested dictionary value.

    Args:
        data: Dictionary to search
        key_path: Dot-separated key path (e.g., 'hardware.name')
        default: Default value if key not found

    Returns:
        Value at key path or default
    """
    keys = key_path.split('.')
    current = data

    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default

    return current


def validate_site_list(site_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Validate and normalize site list.

    Args:
        site_list: List of site dictionaries

    Returns:
        Validated and normalized site list

    Raises:
        ValueError: If validation fails
    """
    if not isinstance(site_list, list):
        raise ValueError("Site list must be a list")

    normalized_sites = []
    for site in site_list:
        if not isinstance(site, dict):
            raise ValueError("Each site must be a dictionary")

        if 'key' not in site:
            raise ValueError("Each site must have a 'key' field")

        # Normalize site ID
        normalized_site = site.copy()
        normalized_site['key'] = parse_site_id(site['key'])

        normalized_sites.append(normalized_site)

    return normalized_sites


def deep_merge_dicts(base: Dict[str, Any], updates: Dict[str, Any], key_field: str = 'hardwareKey') -> Dict[str, Any]:
    """
    Recursively merge update dictionary into base dictionary.

    Handles nested dictionaries and key-based array merging.

    Args:
        base: Base dictionary to merge into
        updates: Updates to apply
        key_field: Field name to use for matching array items (default: 'hardwareKey')

    Returns:
        Merged dictionary
    """
    result = base.copy()

    for key, value in updates.items():
        if key not in result:
            # New key, add it
            result[key] = value
        elif isinstance(value, dict) and isinstance(result[key], dict):
            # Both are dicts, recursive merge
            result[key] = deep_merge_dicts(result[key], value, key_field)
        elif isinstance(value, list) and isinstance(result[key], list):
            # Both are lists, merge by key field if items are dicts
            result[key] = _merge_arrays_by_key(result[key], value, key_field)
        else:
            # Direct replacement
            result[key] = value

    return result


def _merge_arrays_by_key(base_array: List[Any], update_array: List[Any], key_field: str) -> List[Any]:
    """
    Merge two arrays by matching items based on key field.

    Args:
        base_array: Base array
        update_array: Updates to merge
        key_field: Field to match items by

    Returns:
        Merged array
    """
    result = base_array.copy()

    for update_item in update_array:
        if not isinstance(update_item, dict):
            # Not a dict, append if not already present
            if update_item not in result:
                result.append(update_item)
            continue

        # Find matching item in base array
        matched = False
        for i, base_item in enumerate(result):
            if isinstance(base_item, dict) and base_item.get(key_field) == update_item.get(key_field):
                # Merge the dictionaries
                result[i] = deep_merge_dicts(base_item, update_item, key_field)
                matched = True
                break

        if not matched:
            # No match found, append new item
            result.append(update_item)

    return result