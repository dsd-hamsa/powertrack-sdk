"""
Main PowerTrack API client

Provides high-level interface for interacting with PowerTrack API endpoints.
"""

import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .auth import AuthManager
from .models import (
    Site,
    Hardware,
    AlertTrigger,
    SiteConfig,
    ModelingData,
    HardwareDetails,
    SiteData,
    SiteList,
    SiteOverview,
    PortfolioMetrics,
    ChartData,
    ChartSeries,
    AlertSummary,
    AlertSummaryResponse,
    HardwareDiagnostics,
    SiteDetailedInfo,
    ReportingCapabilities,
    UpdateResult,
)
from .utils import parse_site_id, parse_hardware_id, get_current_datetime_iso, safe_get, deep_merge_dicts
from .exceptions import APIError, AuthenticationError, ValidationError

logger = logging.getLogger(__name__)


class PowerTrackClient:
    """
    Main client for PowerTrack API interactions.

    Provides methods for fetching site data, hardware configurations,
    alerts, and modeling data.
    """

    def __init__(
        self,
        auth_manager: Optional[AuthManager] = None,
        base_url: Optional[str] = None,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        timeout: int = 30,
    ):
        """
        Initialize PowerTrack client.

        Args:
            auth_manager: Authentication manager (auto-created if None)
            base_url: API base URL (uses auth manager default if None)
            max_retries: Maximum retry attempts for failed requests
            backoff_factor: Backoff factor for retries
            timeout: Request timeout in seconds
        """
        self.auth_manager = auth_manager or AuthManager()
        self.base_url = base_url or self.auth_manager.get_base_url()
        self.timeout = timeout

        # Create session with retries
        self.session = requests.Session()

        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Set default headers
        self.session.headers.update(
            {
                "Accept": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            }
        )

        logger.info(f"Initialized PowerTrack client for {self.base_url}")

    def _safe_json(self, response: requests.Response):
        """Safely parse JSON from a response."""
        content_type = (response.headers.get("Content-Type") or "").lower()
        if "json" in content_type:
            try:
                return response.json()
            except Exception:
                return None
        return None

    def _safe_text(self, response: requests.Response, limit: int = 500) -> str:
        """Safely get response text snippet."""
        try:
            return (response.text or "")[:limit]
        except Exception:
            return ""

    def _make_request(
        self,
        method: str,
        endpoint: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
        referer: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> requests.Response:
        """
        Make authenticated API request.

        Args:
            method: HTTP method
            endpoint: API endpoint
            headers: Additional headers
            params: Query parameters
            json_data: JSON payload
            data: Form data payload
            referer: Referer URL
            timeout: Request timeout

        Returns:
            Response object

        Raises:
            APIError: On API errors
            AuthenticationError: On auth failures
        """
        url = (
            f"{self.base_url}{endpoint}"
            if endpoint.startswith("/")
            else f"{self.base_url}/{endpoint}"
        )

        # Get auth headers
        request_headers = self.auth_manager.get_auth_headers(referer=referer)
        if headers:
            request_headers.update(headers)

        logger.debug(f"{method} {url}")

        try:
            response = self.session.request(
                method=method,
                url=url,
                headers=request_headers,
                params=params,
                json=json_data,
                data=data,
                timeout=timeout or self.timeout,
            )
            response.raise_for_status()
            return response

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise AuthenticationError("Authentication failed (401 Unauthorized)")
            elif e.response.status_code == 403:
                raise APIError("Access forbidden (403)", e.response.status_code)
            elif e.response.status_code == 404:
                raise APIError("Resource not found (404)", e.response.status_code)
            else:
                resp = e.response
                payload = self._safe_json(resp)
                text_snip = self._safe_text(resp)

                raise APIError(
                    f"HTTP {resp.status_code} error. "
                    f"Content-Type={resp.headers.get('Content-Type')}. "
                    f"URL={resp.url}. "
                    f"Body_snip={text_snip!r}",
                    resp.status_code,
                    payload,
                )

        except requests.exceptions.RequestException as e:
            raise APIError(f"Request failed: {e}")

    def get_json(self, endpoint: str, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Make GET request and return JSON response.

        Args:
            endpoint: API endpoint
            **kwargs: Additional arguments for _make_request

        Returns:
            JSON response or None on error
        """
        try:
            response = self._make_request("GET", endpoint, **kwargs)
            return response.json()
        except APIError as e:
            raise e

    def post_json(
        self, endpoint: str, payload: Dict[str, Any], **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        Make POST request with JSON payload.

        Args:
            endpoint: API endpoint
            payload: JSON payload
            **kwargs: Additional arguments

        Returns:
            JSON response or None on error
        """
        try:
            response = self._make_request("POST", endpoint, json_data=payload, **kwargs)
            return response.json()
        except APIError as e:
            raise e

    def put_json(
        self, endpoint: str, payload: Dict[str, Any], **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        Make PUT request with JSON payload.

        Args:
            endpoint: API endpoint
            payload: JSON payload
            **kwargs: Additional arguments

        Returns:
            JSON response or None on error
        """
        try:
            response = self._make_request("PUT", endpoint, json_data=payload, **kwargs)
            return response.json()
        except APIError as e:
            raise e

    # ===== SITE METHODS =====

    def get_site_config(self, site_id: str) -> Optional[SiteConfig]:
        """
        Get site configuration data.

        Args:
            site_id: Site ID (e.g., 'S60308')

        Returns:
            SiteConfig object or None if not found
        """
        site_id = parse_site_id(site_id)

        referer = f"{self.base_url}/powertrack/{site_id}/administration/config"
        data = self.get_json(f"/api/edit/site/{site_id}", referer=referer)

        if not data:
            return None

        return SiteConfig(
            site_id=site_id,
            name=safe_get(data, "name"),
            timezone=safe_get(data, "timeZone"),
            latitude=safe_get(data, "latitude"),
            longitude=safe_get(data, "longitude"),
            elevation=safe_get(data, "elevation"),
            address=safe_get(data, "address"),
            city=safe_get(data, "city"),
            state=safe_get(data, "state"),
            zip_code=safe_get(data, "zip"),
            country=safe_get(data, "country"),
            install_date=safe_get(data, "installDate"),
            ac_capacity_kw=safe_get(data, "acCapacityKw"),
            dc_capacity_kw=safe_get(data, "dcCapacityKw"),
            module_count=safe_get(data, "moduleCount"),
            raw_data=data,
        )

    def get_sites(self, site_list_file: Optional[str] = None) -> SiteList:
        """
        Get list of available sites.

        Args:
            site_list_file: Path to JSON file with site list (optional)

        Returns:
            SiteList object

        Raises:
            FileNotFoundError: If site_list_file is specified but not found
        """
        if site_list_file:
            return SiteList.from_json_file(site_list_file)
        else:
            # Try to load from default locations
            import os

            candidates = ["portfolio/SiteList.json", "../portfolio/SiteList.json"]

            for candidate in candidates:
                if os.path.exists(candidate):
                    return SiteList.from_json_file(candidate)

            # Return empty list if no file found
            return SiteList([])

    def update_site_config(
        self,
        site_id: str,
        config_data: Dict[str, Any],
        return_full_response: bool = True
    ) -> UpdateResult:
        """
        Update site configuration.

        Args:
            site_id: Site ID
            config_data: Configuration data to update
            return_full_response: Whether to return original/updated data for backup

        Returns:
            UpdateResult with success status and optional response data
        """
        site_id = parse_site_id(site_id)
        referer = f"{self.base_url}/powertrack/{site_id}/administration/config"

        try:
            # GET current configuration
            original_data = self.get_json(f"/api/edit/site/{site_id}", referer=referer)
            if not original_data:
                return UpdateResult(
                    success=False,
                    error_message="Failed to fetch current site configuration"
                )

            # Merge updates into current config
            merged_data = deep_merge_dicts(original_data, config_data)

            # Add key to payload for PUT request
            put_payload = {**merged_data, "key": site_id}

            # PUT updated configuration
            put_response = self.put_json("/api/edit/site", put_payload, referer=referer)

            if put_response is None:
                return UpdateResult(
                    success=False,
                    original_data=original_data if return_full_response else None,
                    updated_data=merged_data if return_full_response else None,
                    error_message="PUT request failed"
                )

            return UpdateResult(
                success=True,
                original_data=original_data if return_full_response else None,
                updated_data=merged_data if return_full_response else None,
                put_response=put_response if return_full_response else None
            )

        except Exception as e:
            return UpdateResult(
                success=False,
                error_message=str(e)
            )

    # ===== HARDWARE METHODS =====

    def get_hardware_list(self, site_id: str) -> List[Hardware]:
        """
        Get hardware list for a site.

        Args:
            site_id: Site ID

        Returns:
            List of Hardware objects
        """
        site_id = parse_site_id(site_id)

        # Try operational API first
        try:
            data = self.get_json(f"/api/view/sitehardwareproduction/{site_id}")
            if data and "hardware" in data:
                return self._parse_hardware_list(data["hardware"])
        except APIError:
            pass

        # Fall back to /api/node
        try:
            payload = {
                "key": site_id,
                "context": "query",
                "kinds": ["customer", "site", "hardware"],
                "subKinds": [],
                "nodes": [],
                "filter": "",
                "filterBy": "Name",
            }

            data = self.post_json("/api/node", payload)
            if data and "nodes" in data:
                hardware_items = []
                for node in data["nodes"]:
                    if node.get("kind") == "hardware":
                        hardware_items.append(
                            {
                                "key": node["key"],
                                "name": node["name"],
                                "functionCode": node.get("subKind"),
                                "hid": int(node["key"][1:]),
                                "enableBool": True,
                            }
                        )
                return self._parse_hardware_list(hardware_items)
        except APIError:
            pass

        # Final fallback to bulk hardware API
        try:
            data = self.get_json(f"/api/edit/bulkhardware/{site_id}")
            if data and "list" in data:
                hardware_items = []
                for group in data["list"]:
                    for row in group.get("rows", []):
                        hardware_items.append(
                            {
                                "key": f"H{row['hid']}",
                                "name": row["name"],
                                "functionCode": group["functionCode"],
                                "hid": row["hid"],
                                "enableBool": row.get("enableBool", True),
                            }
                        )
                return self._parse_hardware_list(hardware_items)
        except APIError:
            pass

        return []

    def update_site_hardware(
        self,
        site_id: str,
        hardware_data: List[Dict[str, Any]],
        return_full_response: bool = True
    ) -> UpdateResult:
        """
        Update site hardware configurations.

        Args:
            site_id: Site ID
            hardware_data: List of hardware configuration objects to update
            return_full_response: Whether to return original/updated data for backup

        Returns:
            UpdateResult with success status and optional response data
        """
        site_id = parse_site_id(site_id)
        referer = f"{self.base_url}/powertrack/{site_id}/administration/hardware/list"

        try:
            # GET current site hardware configuration
            original_data = self.get_json(f"/api/edit/sitehardware/{site_id}", referer=referer)
            if not original_data:
                return UpdateResult(
                    success=False,
                    error_message="Failed to fetch current site hardware configuration"
                )

            # The original_data should contain a "hardware" array
            current_hardware = original_data.get("hardware", [])

            # Create updates dict with hardware array
            updates = {"hardware": hardware_data}

            # Merge updates into current config
            merged_data = deep_merge_dicts(original_data, updates)

            # Prepare PUT payload
            put_payload = {**merged_data, "key": site_id}

            # PUT updated site hardware
            put_response = self.put_json("/api/edit/sitehardware", put_payload, referer=referer)

            if put_response is None:
                return UpdateResult(
                    success=False,
                    original_data=original_data if return_full_response else None,
                    updated_data=merged_data if return_full_response else None,
                    error_message="PUT request failed"
                )

            return UpdateResult(
                success=True,
                original_data=original_data if return_full_response else None,
                updated_data=merged_data if return_full_response else None,
                put_response=put_response if return_full_response else None
            )

        except Exception as e:
            return UpdateResult(
                success=False,
                error_message=str(e)
            )

    def _parse_hardware_list(self, hardware_data: List[Dict[str, Any]]) -> List[Hardware]:
        """Parse hardware list data into Hardware objects."""
        hardware_list = []
        for item in hardware_data:
            try:
                hardware = Hardware(
                    key=item.get("key", ""),
                    name=item.get("name", ""),
                    function_code=item.get("functionCode"),
                    hid=item.get("hid"),
                    short_name=item.get("shortName"),
                    serial_num=item.get("serialNum"),
                    mfr_model=item.get("mfrModel"),
                    device_id=item.get("deviceID"),
                    install_date=item.get("installDate"),
                    device_address=item.get("deviceAddress"),
                    port=item.get("port"),
                    unit_id=item.get("unitID"),
                    baud=item.get("baud"),
                    gateway_id=item.get("gatewayID"),
                    enable_bool=item.get("enableBool", True),
                    hardware_status=item.get("hardwareStatus"),
                    capacity_kw=item.get("capacityKW"),
                    inverter_kw=item.get("inverterKw"),
                    driver_name=item.get("driverName"),
                    out_of_service=item.get("outOfService", False),
                )
                hardware_list.append(hardware)
            except Exception as e:
                logger.warning(f"Failed to parse hardware item: {e}")
                continue

        return hardware_list

    def get_hardware_details(self, hardware_key: str) -> Optional[HardwareDetails]:
        """
        Get detailed hardware configuration.

        Args:
            hardware_key: Hardware key (e.g., 'H123456')

        Returns:
            HardwareDetails object or None
        """
        hardware_key = parse_hardware_id(hardware_key)

        referer = f"{self.base_url}/powertrack/{hardware_key}/administration/config"
        data = self.get_json(f"/api/edit/hardware/{hardware_key}", referer=referer)
        if not data:
            return None

        # Get summary (minimal info for Hardware object)
        summary = Hardware(
            key=hardware_key,
            name=data.get("name", ""),
            function_code=data.get("functionCode"),
            hid=data.get("hid"),
        )

        return HardwareDetails(key=hardware_key, summary=summary, details=data)

    def update_hardware_config(
        self,
        hardware_id: str,
        config_data: Dict[str, Any],
        return_full_response: bool = True
    ) -> UpdateResult:
        """
        Update hardware configuration.

        Args:
            hardware_id: Hardware ID
            config_data: Configuration data to update
            return_full_response: Whether to return original/updated data for backup

        Returns:
            UpdateResult with success status and optional response data
        """
        hardware_id = parse_hardware_id(hardware_id)
        referer = f"{self.base_url}/powertrack/{hardware_id}/administration/config"

        try:
            # GET current configuration
            original_data = self.get_json(f"/api/edit/hardware/{hardware_id}", referer=referer)
            if not original_data:
                return UpdateResult(
                    success=False,
                    error_message="Failed to fetch current hardware configuration"
                )

            # Merge updates into current config
            merged_data = deep_merge_dicts(original_data, config_data)

            # Add hardwareId to payload for PUT request
            put_payload = {**merged_data, "hardwareId": hardware_id}

            # PUT updated configuration
            put_response = self.put_json("/api/edit/hardware", put_payload, referer=referer)

            if put_response is None:
                return UpdateResult(
                    success=False,
                    original_data=original_data if return_full_response else None,
                    updated_data=merged_data if return_full_response else None,
                    error_message="PUT request failed"
                )

            return UpdateResult(
                success=True,
                original_data=original_data if return_full_response else None,
                updated_data=merged_data if return_full_response else None,
                put_response=put_response if return_full_response else None
            )

        except Exception as e:
            return UpdateResult(
                success=False,
                error_message=str(e)
            )

    def bulk_update_hardware(self, site_id: str, hardware_data: List[Dict[str, Any]]) -> bool:
        """
        Bulk update hardware configurations for a site.

        Args:
            site_id: Site ID
            hardware_data: List of hardware configuration data

        Returns:
            True if bulk update successful, False otherwise
        """
        site_id = parse_site_id(site_id)

        payload = {"siteId": site_id, "hardware": hardware_data}

        result = self.put_json(f"/api/edit/bulkhardware/{site_id}", payload)

        return result is not None

    def update_hardware_driver(self, hardware_id: str, driver_data: Dict[str, Any]) -> bool:
        """
        Update hardware driver configuration.

        Args:
            hardware_id: Hardware ID
            driver_data: Driver configuration data

        Returns:
            True if update successful, False otherwise
        """
        hardware_id = parse_hardware_id(hardware_id)

        result = self.put_json(f"/api/edit/hardware/driver/{hardware_id}", driver_data)

        return result is not None

    # ===== ALERT METHODS =====

    def get_alert_triggers(
        self, hardware_key: str, last_changed: Optional[str] = None
    ) -> Optional[AlertTrigger]:
        """
        Get alert triggers for hardware.

        Args:
            hardware_key: Hardware key
            last_changed: Last changed timestamp (optional)

        Returns:
            AlertTrigger object or None
        """
        hardware_key = parse_hardware_id(hardware_key)

        endpoint = f"/api/alerttrigger/{hardware_key}"
        if last_changed:
            endpoint += f"?lastChanged={last_changed}"

        referer = f"{self.base_url}/powertrack/{hardware_key}/administration/alertsettings"
        data = self.get_json(endpoint, referer=referer)

        if not data:
            return None

        return AlertTrigger(
            key=hardware_key,
            parent_key=data.get("parentKey"),
            asset_code=data.get("assetCode"),
            calculated_capacity=data.get("calculatedCapacity"),
            capacity=data.get("capacity"),
            last_changed=data.get("lastChanged"),
            triggers=data.get("triggers", []),
            default_triggers=data.get("defaultTriggers", []),
        )

    def update_alert_triggers(
        self,
        hardware_key: str,
        trigger_data: Dict[str, Any],
        return_full_response: bool = True
    ) -> UpdateResult:
        """
        Update alert triggers for hardware.

        Args:
            hardware_key: Hardware key
            trigger_data: Alert trigger configuration data
            return_full_response: Whether to return original/updated data for backup

        Returns:
            UpdateResult with success status and optional response data
        """
        hardware_key = parse_hardware_id(hardware_key)
        referer = f"{self.base_url}/powertrack/{hardware_key}/administration/alertsettings"

        try:
            # For alerts, we don't have a simple GET equivalent for current state
            # So we assume trigger_data contains the full trigger object to update
            put_payload = {**trigger_data, "parentKey": hardware_key}

            # PUT updated trigger
            put_response = self.put_json("/api/alerttrigger", put_payload, referer=referer)

            if put_response is None:
                return UpdateResult(
                    success=False,
                    updated_data=put_payload if return_full_response else None,
                    error_message="PUT request failed"
                )

            return UpdateResult(
                success=True,
                updated_data=put_payload if return_full_response else None,
                put_response=put_response if return_full_response else None
            )

        except Exception as e:
            return UpdateResult(
                success=False,
                error_message=str(e)
            )

    def add_alert_trigger(self, hardware_key: str, trigger_data: Dict[str, Any]) -> bool:
        """
        Add new alert trigger for hardware.

        Args:
            hardware_key: Hardware key
            trigger_data: New alert trigger data

        Returns:
            True if addition successful, False otherwise
        """
        hardware_key = parse_hardware_id(hardware_key)

        result = self.post_json(f"/api/alerttrigger/{hardware_key}", trigger_data)

        return result is not None

    def delete_alert_trigger(self, hardware_key: str) -> bool:
        """
        Delete alert triggers for hardware.

        Args:
            hardware_key: Hardware key

        Returns:
            True if deletion successful, False otherwise
        """
        hardware_key = parse_hardware_id(hardware_key)

        try:
            response = self._make_request("DELETE", f"/api/alerttrigger/{hardware_key}")
            return response.status_code == 200
        except APIError:
            return False

    # ===== MODELING METHODS =====

    def get_modeling_data(self, site_id: str) -> Optional[ModelingData]:
        """
        Get modeling data for site.

        Args:
            site_id: Site ID

        Returns:
            ModelingData object or None
        """
        site_id = parse_site_id(site_id)

        referer = f"{self.base_url}/powertrack/{site_id}/administration/modeling"
        data = self.get_json(f"/api/edit/modeling/{site_id}", referer=referer)

        if not data:
            return None

        return ModelingData(
            site_id=site_id,
            pv_config=data.get("pvConfig", {}),
            inverters=data.get("pvConfig", {}).get("inverters", []),
            ts=data.get("ts"),
            raw_data=data,
        )

    def update_modeling_data(self, site_id: str, modeling_data: Dict[str, Any]) -> bool:
        """
        Update modeling data for site.

        Args:
            site_id: Site ID
            modeling_data: Modeling configuration data

        Returns:
            True if update successful, False otherwise
        """
        site_id = parse_site_id(site_id)

        referer = f"{self.base_url}/powertrack/{site_id}/administration/modeling"
        result = self.put_json(f"/api/edit/modeling/{site_id}", modeling_data, referer=referer)

        return result is not None

    def update_inverter_model(self, hardware_id: str, model_data: Dict[str, Any]) -> bool:
        """
        Update inverter model configuration.

        Args:
            hardware_id: Hardware ID
            model_data: Inverter model data

        Returns:
            True if update successful, False otherwise
        """
        hardware_id = parse_hardware_id(hardware_id)

        result = self.put_json(f"/api/edit/hardware/inverter/{hardware_id}", model_data)

        return result is not None

    def update_bifacial_settings(self, hardware_id: str, bifacial_data: Dict[str, Any]) -> bool:
        """
        Update bifacial settings for hardware.

        Args:
            hardware_id: Hardware ID
            bifacial_data: Bifacial configuration data

        Returns:
            True if update successful, False otherwise
        """
        hardware_id = parse_hardware_id(hardware_id)

        result = self.put_json(f"/api/edit/hardware/bifacial/{hardware_id}", bifacial_data)

        return result is not None

    # ===== COMPREHENSIVE DATA METHODS =====

    def get_site_data(
        self,
        site_id: str,
        include_hardware: bool = True,
        include_alerts: bool = True,
        include_modeling: bool = True,
    ) -> Optional[SiteData]:
        """
        Get comprehensive site data.

        Args:
            site_id: Site ID
            include_hardware: Whether to fetch hardware data
            include_alerts: Whether to fetch alert data
            include_modeling: Whether to fetch modeling data

        Returns:
            SiteData object or None
        """
        site_id = parse_site_id(site_id)

        # Get basic site info
        site = Site(key=site_id)

        # Get config
        config = self.get_site_config(site_id)

        # Get hardware
        hardware_details = []
        if include_hardware:
            hardware_list = self.get_hardware_list(site_id)
            for hw in hardware_list:
                details = self.get_hardware_details(hw.key)
                if details:
                    hardware_details.append(details)

        # Get alerts
        alerts = []
        if include_alerts:
            for hw_details in hardware_details:
                alert_trigger = self.get_alert_triggers(hw_details.key)
                if alert_trigger:
                    alerts.append(alert_trigger)

        # Get modeling
        modeling = None
        if include_modeling:
            modeling = self.get_modeling_data(site_id)

        return SiteData(
            site=site,
            config=config,
            hardware=hardware_details,
            alerts=alerts,
            modeling=modeling,
            fetched_at=datetime.now(),
        )

    # ===== NEW EXPANDED API METHODS =====

    def get_portfolio_overview(self, customer_id: str) -> Optional[PortfolioMetrics]:
        """
        Get comprehensive portfolio overview for a customer.

        Args:
            customer_id: Customer ID (e.g., 'C8458')

        Returns:
            PortfolioMetrics object with all site data or None if failed
        """
        endpoint = f"/api/view/portfolio/{customer_id}"
        params = {"lastChanged": "1900-01-01T00:00:00.000Z"}

        data = self.get_json(endpoint, params=params)
        if not data:
            return None

        # Parse site overviews
        sites = []
        for site_data in data.get("sites", []):
            try:
                site = SiteOverview(**site_data)
                sites.append(site)
            except Exception as e:
                logger.warning(f"Failed to parse site data: {e}")
                continue

        return PortfolioMetrics(
            customer_id=customer_id,
            sites=sites,
            custom_column_names=data.get("customColumnNames", []),
            last_changed=data.get("lastChanged", ""),
            merge=data.get("merge", False),
            merge_hash=data.get("mergeHash", ""),
        )

    def get_site_overview(self, site_id: str) -> Optional[SiteOverview]:
        """
        Get real-time site performance metrics.

        Args:
            site_id: Site ID

        Returns:
            SiteOverview object or None if not found
        """
        portfolio = self.get_portfolio_overview_from_site(site_id)
        if portfolio:
            for site in portfolio.sites:
                if site.site_id == site_id:
                    return site
        return None

    def get_portfolio_overview_from_site(self, site_id: str) -> Optional[PortfolioMetrics]:
        """
        Get portfolio data by inferring customer ID from site.

        Args:
            site_id: Site ID to get customer from

        Returns:
            PortfolioMetrics or None
        """
        # First get site details to find customer ID
        site_info = self.get_site_detailed_info(site_id)
        if not site_info or not site_info.parent_key:
            return None

        customer_id = site_info.parent_key
        return self.get_portfolio_overview(customer_id)

    def get_site_detailed_info(self, site_id: str) -> Optional[SiteDetailedInfo]:
        """
        Get detailed site information including contracts and configuration.

        Args:
            site_id: Site ID

        Returns:
            SiteDetailedInfo object or None if not found
        """
        site_id = parse_site_id(site_id)
        endpoint = f"/api/view/site/{site_id}"
        params = {"lastChanged": "1900-01-01T00:00:00.000Z"}

        data = self.get_json(endpoint, params=params)
        if not data:
            return None

        return SiteDetailedInfo(**data)

    def get_chart_data(
        self,
        chart_type: int,
        site_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Optional[ChartData]:
        """
        Get chart data for visualization.

        Args:
            chart_type: Chart type ID (from /api/view/chart/builtin)
            site_id: Site ID
            start_date: Start date (ISO format)
            end_date: End date (ISO format)

        Returns:
            ChartData object or None if failed
        """
        site_id = parse_site_id(site_id)

        # Build query payload
        payload = {
            "context": "site",
            "hardwareByType": [5, 2],  # Weather and production meters
            "siteKeys": [site_id],
        }

        if start_date and end_date:
            payload.update({"spanFrom": start_date, "spanTo": end_date})

        data = self.post_json("/api/view/chart", payload)
        if not data:
            return None

        # Parse series data
        series = []
        for series_data in data.get("series", []):
            # Parse dataXy into tuples
            data_xy = series_data.get("dataXy", [])
            parsed_xy = []
            for point in data_xy:
                if isinstance(point, dict) and "x" in point and "y" in point:
                    parsed_xy.append((point["x"], point["y"]))

            series_obj = ChartSeries(
                name=series_data.get("name", ""),
                key=series_data.get("key", ""),
                data_xy=parsed_xy,
                color=series_data.get("color", ""),
                custom_unit=series_data.get("customUnit", ""),
                data_max=series_data.get("dataMax", 0.0),
                data_min=series_data.get("dataMin", 0.0),
                diameter=series_data.get("diameter", 0),
                fit_exponent=series_data.get("fitExponent", 0),
                header=series_data.get("header", ""),
                line_color=series_data.get("lineColor", ""),
                line_type=series_data.get("lineType", 0),
                line_width=series_data.get("lineWidth", 2),
                right_axis=series_data.get("rightAxis", False),
                units=series_data.get("units", 0),
                use_binned_data=series_data.get("useBinnedData", False),
                visible=series_data.get("visible", True),
                x_series_header=series_data.get("xSeriesHeader", ""),
                x_series_key=series_data.get("xSeriesKey", ""),
                x_series_name=series_data.get("xSeriesName", ""),
                x_units=series_data.get("xUnits", ""),
                y_axis_index=series_data.get("yAxisIndex", 0),
                y_max=series_data.get("yMax"),
                y_min=series_data.get("yMin"),
                alert_message_map=series_data.get("alertMessageMap"),
            )
            series.append(series_obj)

        return ChartData(
            allow_small_bin_size=data.get("allowSmallBinSize", True),
            bin_size=data.get("binSize", 1440),
            current_now_bin_index=data.get("currentNowBinIndex", 0),
            data_not_available=data.get("dataNotAvailable", False),
            durations=data.get("durations", []),
            end=data.get("end", ""),
            error_string=data.get("errorString", ""),
            hardware_keys=data.get("hardwareKeys", []),
            has_alert_messages=data.get("hasAlertMessages", False),
            has_overridden_query=data.get("hasOverriddenQuery", False),
            is_category_chart=data.get("isCategoryChart", False),
            is_summary_chart=data.get("isSummaryChart", False),
            is_using_daylight_savings=data.get("isUsingDaylightSavings", False),
            key=data.get("key", ""),
            last_changed=data.get("lastChanged", ""),
            last_data_datetime=data.get("lastDataDatetime", ""),
            named_results=data.get("namedResults", {}),
            render_type=data.get("renderType", 0),
            series=series,
            start=data.get("start"),
        )

    def get_chart_definitions(self) -> List[Dict[str, Any]]:
        """
        Get available chart type definitions.

        Returns:
            List of chart definitions
        """
        data = self.get_json("/api/view/chart/builtin")
        if not data:
            return []

        # Extract predefined charts from sections
        charts = []
        for section in data.get("chartMenuSections", []):
            for chart in section.get("predefinedCharts", []):
                charts.append(chart)

        return charts

    def get_alert_summary(
        self, customer_id: Optional[str] = None, site_id: Optional[str] = None
    ) -> Optional[AlertSummaryResponse]:
        """
        Get alert summary for customer or site.

        Args:
            customer_id: Customer ID (preferred)
            site_id: Site ID (alternative)

        Returns:
            AlertSummaryResponse or None if failed
        """
        if customer_id:
            endpoint = f"/api/view/activealerts/activesummary/{customer_id}"
        elif site_id:
            site_id = parse_site_id(site_id)
            endpoint = f"/api/view/activealerts/activesummary/{site_id}"
        else:
            raise ValueError("Either customer_id or site_id must be provided")

        data = self.get_json(endpoint)
        if not data:
            return None

        hardware_summaries = {}
        for hw_key, summary_data in data.items():
            if isinstance(summary_data, dict):
                hardware_summaries[hw_key] = AlertSummary(
                    hardware_key=hw_key,
                    max_severity=summary_data.get("maxSeverity", 0),
                    count=summary_data.get("count", 0),
                )

        return AlertSummaryResponse(hardware_summaries=hardware_summaries)

    def get_hardware_diagnostics(self, hardware_id: str) -> Optional[HardwareDiagnostics]:
        """
        Get detailed hardware diagnostic information.

        Args:
            hardware_id: Hardware ID

        Returns:
            HardwareDiagnostics object or None if failed
        """
        hardware_id = parse_hardware_id(hardware_id)
        endpoint = f"/api/view/hardwarestatus/{hardware_id}"
        params = {"lastChanged": "1900-01-01T00:00:00.000Z"}

        data = self.get_json(endpoint, params=params)
        if not data:
            return None

        return HardwareDiagnostics(**data)

    def get_reporting_capabilities(self) -> Optional[ReportingCapabilities]:
        """
        Get user's reporting permissions and capabilities.

        Returns:
            ReportingCapabilities object or None if failed
        """
        data = self.get_json("/api/reporting")
        if not data:
            return None

        return ReportingCapabilities(
            can_edit_auto_report=data.get("canEditAutoReport", False),
            can_add_email_report=data.get("canAddEmailReport", False),
            can_add_summary_report=data.get("canAddSummaryReport", False),
            can_add_auto_report=data.get("canAddAutoReport", False),
            can_add_user_report=data.get("canAddUserReport", False),
            views=data.get("views", []),
        )

    def get_site_hardware_production(self, site_id: str) -> List[Dict[str, Any]]:
        """
        Get hardware production data for a site.

        Args:
            site_id: Site ID

        Returns:
            List of hardware production data
        """
        site_id = parse_site_id(site_id)
        endpoint = f"/api/view/sitehardwareproduction/{site_id}"

        data = self.get_json(endpoint)
        if not data:
            return []

        return data.get("hardware", [])

    def get_user_preferences(self) -> Optional[Dict[str, Any]]:
        """
        Get current user preferences.

        Returns:
            User preferences dict or None if failed
        """
        return self.get_json("/api/userpreferences")

    def get_audit_log(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Get audit log entries.

        Args:
            filters: Optional filters for audit log

        Returns:
            List of audit log entries
        """
        params = {}
        if filters:
            params.update(filters)

        data = self.get_json("/api/auditlog", params=params)
        if not data:
            return []

        return data.get("entries", [])

    def get_site_links(self, site_id: str) -> List[Dict[str, Any]]:
        """
        Get site links and sharing information.

        Args:
            site_id: Site ID

        Returns:
            List of site links
        """
        site_id = parse_site_id(site_id)
        endpoint = f"/api/view/sitelinks/{site_id}"

        data = self.get_json(endpoint)
        if not data:
            return []

        return data.get("links", [])

    def get_site_shares(self, site_id: str) -> List[Dict[str, Any]]:
        """
        Get site sharing configurations.

        Args:
            site_id: Site ID

        Returns:
            List of site shares
        """
        site_id = parse_site_id(site_id)
        endpoint = f"/api/view/siteshares/{site_id}"

        data = self.get_json(endpoint)
        if not data:
            return []

        return data.get("shares", [])

    def get_pv_model_curves(
        self, model_type: str = "efficiencycurvemodels"
    ) -> List[Dict[str, Any]]:
        """
        Get PV model curves (efficiency or incidence angle).

        Args:
            model_type: 'efficiencycurvemodels' or 'incidenceanglemodels'

        Returns:
            List of model curves
        """
        endpoint = f"/api/view/pvcurvemodels/{model_type}"

        data = self.get_json(endpoint)
        if not data:
            return []

        return data.get("curves", [])

    def get_pvsyst_modules(
        self, hardware_id: Optional[str] = None, site_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get PVSyst module configurations.

        Args:
            hardware_id: Specific hardware ID
            site_id: Site ID (alternative to hardware_id)

        Returns:
            List of PVSyst modules
        """
        if hardware_id:
            hardware_id = parse_hardware_id(hardware_id)
            endpoint = f"/api/view/pvsystmodules/{hardware_id}"
        elif site_id:
            site_id = parse_site_id(site_id)
            endpoint = f"/api/view/pvsystmodules/{site_id}"
        else:
            raise ValueError("Either hardware_id or site_id must be provided")

        data = self.get_json(endpoint)
        if not data:
            return []

        return data.get("modules", [])

    def get_driver_settings(self, hardware_id: str) -> Optional[Dict[str, Any]]:
        """
        Get hardware driver settings.

        Args:
            hardware_id: Hardware ID

        Returns:
            Driver settings or None if failed
        """
        hardware_id = parse_hardware_id(hardware_id)
        endpoint = f"/api/view/driversettings/{hardware_id}"

        return self.get_json(endpoint)

    def get_driver_settings_list(self, list_id: str) -> List[Dict[str, Any]]:
        """
        Get driver settings list.

        Args:
            list_id: List ID

        Returns:
            List of driver settings
        """
        endpoint = f"/api/view/driversettings/list/{list_id}"

        data = self.get_json(endpoint)
        if not data:
            return []

        return data.get("settings", [])

    def get_register_offsets(self, hardware_id: str) -> Dict[str, Any]:
        """
        Get register offsets for hardware.

        Args:
            hardware_id: Hardware ID

        Returns:
            Register offsets data
        """
        hardware_id = parse_hardware_id(hardware_id)
        endpoint = f"/api/view/registeroffsets/{hardware_id}"

        return self.get_json(endpoint) or {}

    def get_report_configs(self) -> List[Dict[str, Any]]:
        """
        Get available report configurations.

        Returns:
            List of report configurations
        """
        data = self.get_json("/api/view/reportconfigs")
        if not data:
            return []

        return data.get("configs", [])

    # ===== WRITE/UPDATE METHODS =====

    def create_report_config(self, report_config: Dict[str, Any]) -> bool:
        """
        Create a new report configuration.

        Args:
            report_config: Report configuration data

        Returns:
            True if creation successful, False otherwise
        """
        result = self.post_json("/api/report/config", report_config)
        return result is not None

    def start_report(self, report_id: str, parameters: Optional[Dict[str, Any]] = None) -> bool:
        """
        Start report generation.

        Args:
            report_id: Report ID to start
            parameters: Optional report parameters

        Returns:
            True if report started successfully, False otherwise
        """
        payload = {"reportId": report_id}
        if parameters:
            payload.update(parameters)

        result = self.post_json("/api/report/start", payload)
        return result is not None

    def upload_pan_data(self, pan_data: Dict[str, Any]) -> bool:
        """
        Upload PAN (Performance Analytics Network) data.

        Args:
            pan_data: PAN data to upload

        Returns:
            True if upload successful, False otherwise
        """
        result = self.post_json("/api/pan/upload", pan_data)
        return result is not None

    def close(self):
        """Close the client session."""
        self.session.close()
        logger.info("PowerTrack client session closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
