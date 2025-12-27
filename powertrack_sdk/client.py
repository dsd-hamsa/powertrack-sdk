"""
Main PowerTrack API client

Provides high-level interface for interacting with PowerTrack API endpoints.
"""

import logging
import dataclasses
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import re

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
        try:
            return response.json()
        except Exception:
            # Try to parse even if content-type is not json
            text = response.text.strip()
            if text:
                try:
                    import json
                    return json.loads(text)
                except Exception:
                    pass
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

                # Include response body in error for debugging
                body_preview = resp.text[:500] if resp.text else ""

                raise APIError(
                    f"HTTP {resp.status_code} error. "
                    f"Content-Type={resp.headers.get('Content-Type')}. "
                    f"URL={resp.url}. "
                    f"Body_snip={text_snip!r}. "
                    f"Body_preview={body_preview!r}",
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

    def get_site_config(self, siteId: str) -> Optional[SiteConfig]:
        """
        Get site configuration data.

        Args:
            siteId: Site ID (e.g., 'S60308')

        Returns:
            SiteConfig object or None if not found
        """
        siteId = parse_site_id(siteId)

        referer = f"{self.base_url}/powertrack/{siteId}/administration/config"
        data = self.get_json(f"/api/edit/site/{siteId}", referer=referer)

        if not data:
            return None

        return SiteConfig(
            siteId=siteId,
            name=safe_get(data, "name"),
            timezone=safe_get(data, "timeZone"),
            latitude=safe_get(data, "latitude"),
            longitude=safe_get(data, "longitude"),
            elevation=safe_get(data, "elevation"),
            address=safe_get(data, "address"),
            city=safe_get(data, "city"),
            state=safe_get(data, "state"),
            zipCode=safe_get(data, "zip"),
            country=safe_get(data, "country"),
            installDate=safe_get(data, "installDate"),
            acCapacityKw=safe_get(data, "acCapacityKw"),
            dcCapacityKw=safe_get(data, "dcCapacityKw"),
            moduleCount=safe_get(data, "moduleCount"),
            rawData=data,
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
        siteId: str,
        config_data: Dict[str, Any],
        return_full_response: bool = True
    ) -> UpdateResult:
        """
        Update site configuration.

        Args:
            siteId: Site ID
            config_data: Configuration data to update
            return_full_response: Whether to return original/updated data for backup

        Returns:
            UpdateResult with success status and optional response data
        """
        siteId = parse_site_id(siteId)
        referer = f"{self.base_url}/powertrack/{siteId}/administration/config"

        try:
            # GET current configuration
            originalData = self.get_json(f"/api/edit/site/{siteId}", referer=referer)
            if not originalData:
                return UpdateResult(
                    success=False,
                    errorMessage="Failed to fetch current site configuration"
                )

            # Merge updates into current config
            merged_data = deep_merge_dicts(originalData, config_data)

            # Add key to payload for PUT request
            put_payload = {**merged_data, "key": siteId}

            # PUT updated configuration
            putResponse = self.put_json("/api/edit/site", put_payload, referer=referer)

            if putResponse is None:
                return UpdateResult(
                    success=False,
                    originalData=originalData if return_full_response else None,
                    updatedData=merged_data if return_full_response else None,
                    errorMessage="PUT request failed"
                )

            return UpdateResult(
                success=True,
                originalData=originalData if return_full_response else None,
                updatedData=merged_data if return_full_response else None,
                putResponse=putResponse if return_full_response else None
            )

        except Exception as e:
            return UpdateResult(
                success=False,
                errorMessage=str(e)
            )

    # ===== HARDWARE METHODS =====

    def get_hardware_list(self, siteId: str) -> List[Hardware]:
        """
        Get hardware list for a site.

        Args:
            siteId: Site ID

        Returns:
            List of Hardware objects
        """
        siteId = parse_site_id(siteId)

        # Try operational API first
        try:
            data = self.get_json(f"/api/view/sitehardwareproduction/{siteId}")
            if data and "hardware" in data:
                return self._parse_hardware_list(data["hardware"])
        except APIError:
            pass

        # Fall back to /api/node
        try:
            payload = {
                "key": siteId,
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
            data = self.get_json(f"/api/edit/bulkhardware/{siteId}")
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
        siteId: str,
        hardware_data: List[Dict[str, Any]],
        return_full_response: bool = True
    ) -> UpdateResult:
        """
        Update site hardware configurations.

        Args:
            siteId: Site ID
            hardware_data: List of hardware configuration objects to update
            return_full_response: Whether to return original/updated data for backup

        Returns:
            UpdateResult with success status and optional response data
        """
        siteId = parse_site_id(siteId)
        referer = f"{self.base_url}/powertrack/{siteId}/administration/hardware/list"

        try:
            # GET current site hardware configuration
            originalData = self.get_json(f"/api/edit/sitehardware/{siteId}", referer=referer)
            if not originalData:
                return UpdateResult(
                    success=False,
                    errorMessage="Failed to fetch current site hardware configuration"
                )

            # The originalData should contain a "hardware" array
            current_hardware = originalData.get("hardware", [])

            # Create updates dict with hardware array
            updates = {"hardware": hardware_data}

            # Merge updates into current config
            merged_data = deep_merge_dicts(originalData, updates)

            # Prepare PUT payload
            put_payload = {**merged_data, "key": siteId}

            # PUT updated site hardware
            putResponse = self.put_json("/api/edit/sitehardware", put_payload, referer=referer)

            if putResponse is None:
                return UpdateResult(
                    success=False,
                    originalData=originalData if return_full_response else None,
                    updatedData=merged_data if return_full_response else None,
                    errorMessage="PUT request failed"
                )

            return UpdateResult(
                success=True,
                originalData=originalData if return_full_response else None,
                updatedData=merged_data if return_full_response else None,
                putResponse=putResponse if return_full_response else None
            )

        except Exception as e:
            return UpdateResult(
                success=False,
                errorMessage=str(e)
            )

    def _parse_hardware_list(self, hardware_data: List[Dict[str, Any]]) -> List[Hardware]:
        """Parse hardware list data into Hardware objects."""
        hardware_list = []
        for item in hardware_data:
            try:
                hardware = Hardware(
                    key=item.get("key", ""),
                    name=item.get("name", ""),
                    functionCode=item.get("functionCode"),
                    hid=item.get("hid"),
                    shortName=item.get("shortName"),
                    serialNum=item.get("serialNum"),
                    mfrModel=item.get("mfrModel"),
                    deviceId=item.get("deviceId"),
                    installDate=item.get("installDate"),
                    deviceAddress=item.get("deviceAddress"),
                    port=item.get("port"),
                    unitId=item.get("unitID"),
                    baud=item.get("baud"),
                    gatewayId=item.get("gatewayID"),
                    enableBool=item.get("enableBool", True),
                    hardwareStatus=item.get("hardwareStatus"),
                    capacityKw=item.get("capacityKW"),
                    inverterKw=item.get("inverterKw"),
                    driverName=item.get("driverName"),
                    outOfService=item.get("outOfService", False),
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
            functionCode=data.get("functionCode"),
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
            originalData = self.get_json(f"/api/edit/hardware/{hardware_id}", referer=referer)
            if not originalData:
                return UpdateResult(
                    success=False,
                    errorMessage="Failed to fetch current hardware configuration"
                )

            # Merge updates into current config
            merged_data = deep_merge_dicts(originalData, config_data)

            # Add hardwareId to payload for PUT request
            put_payload = {**merged_data, "hardwareId": hardware_id}

            # PUT updated configuration
            putResponse = self.put_json("/api/edit/hardware", put_payload, referer=referer)

            if putResponse is None:
                return UpdateResult(
                    success=False,
                    originalData=originalData if return_full_response else None,
                    updatedData=merged_data if return_full_response else None,
                    errorMessage="PUT request failed"
                )

            return UpdateResult(
                success=True,
                originalData=originalData if return_full_response else None,
                updatedData=merged_data if return_full_response else None,
                putResponse=putResponse if return_full_response else None
            )

        except Exception as e:
            return UpdateResult(
                success=False,
                errorMessage=str(e)
            )

    def bulk_update_hardware(self, siteId: str, hardware_data: List[Dict[str, Any]]) -> bool:
        """
        Bulk update hardware configurations for a site.

        Args:
            siteId: Site ID
            hardware_data: List of hardware configuration data

        Returns:
            True if bulk update successful, False otherwise
        """
        siteId = parse_site_id(siteId)

        payload = {"siteId": siteId, "hardware": hardware_data}

        result = self.put_json(f"/api/edit/bulkhardware/{siteId}", payload)

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
        self, hardware_key: str, lastChanged: Optional[str] = None
    ) -> Optional[AlertTrigger]:
        """
        Get alert triggers for hardware.

        Args:
            hardware_key: Hardware key
            lastChanged: Last changed timestamp (optional)

        Returns:
            AlertTrigger object or None
        """
        hardware_key = parse_hardware_id(hardware_key)

        endpoint = f"/api/alerttrigger/{hardware_key}"
        if lastChanged:
            endpoint += f"?lastChanged={lastChanged}"

        referer = f"{self.base_url}/powertrack/{hardware_key}/administration/alertsettings"
        data = self.get_json(endpoint, referer=referer)

        if not data:
            return None

        return AlertTrigger(
            key=hardware_key,
            parentKey=data.get("parentKey"),
            assetCode=data.get("assetCode"),
            calculatedCapacity=data.get("calculatedCapacity"),
            capacity=data.get("capacity"),
            lastChanged=data.get("lastChanged"),
            triggers=data.get("triggers", []),
            defaultTriggers=data.get("defaultTriggers", []),
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
            putResponse = self.put_json("/api/alerttrigger", put_payload, referer=referer)

            if putResponse is None:
                return UpdateResult(
                    success=False,
                    updatedData=put_payload if return_full_response else None,
                    errorMessage="PUT request failed"
                )

            return UpdateResult(
                success=True,
                updatedData=put_payload if return_full_response else None,
                putResponse=putResponse if return_full_response else None
            )

        except Exception as e:
            return UpdateResult(
                success=False,
                errorMessage=str(e)
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

    def get_modeling_data(self, siteId: str) -> Optional[ModelingData]:
        """
        Get modeling data for site.

        Args:
            siteId: Site ID

        Returns:
            ModelingData object or None
        """
        siteId = parse_site_id(siteId)

        referer = f"{self.base_url}/powertrack/{siteId}/administration/modeling"
        data = self.get_json(f"/api/edit/modeling/{siteId}", referer=referer)

        if not data:
            return None

        return ModelingData(
            siteId=siteId,
            pvConfig=data.get("pvConfig", {}),
            inverters=data.get("pvConfig", {}).get("inverters", []),
            ts=data.get("ts"),
            rawData=data,
        )

    def update_modeling_data(self, siteId: str, modeling_data: Dict[str, Any]) -> bool:
        """
        Update modeling data for site.

        Args:
            siteId: Site ID
            modeling_data: Modeling configuration data

        Returns:
            True if update successful, False otherwise
        """
        siteId = parse_site_id(siteId)

        referer = f"{self.base_url}/powertrack/{siteId}/administration/modeling"
        result = self.put_json(f"/api/edit/modeling/{siteId}", modeling_data, referer=referer)

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
        siteId: str,
        include_hardware: bool = True,
        include_alerts: bool = True,
        include_modeling: bool = True,
    ) -> Optional[SiteData]:
        """
        Get comprehensive site data.

        Args:
            siteId: Site ID
            include_hardware: Whether to fetch hardware data
            include_alerts: Whether to fetch alert data
            include_modeling: Whether to fetch modeling data

        Returns:
            SiteData object or None
        """
        siteId = parse_site_id(siteId)

        # Get basic site info
        site = Site(key=siteId)

        # Get config
        config = self.get_site_config(siteId)

        # Get hardware
        hardware_details = []
        if include_hardware:
            hardware_list = self.get_hardware_list(siteId)
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
            modeling = self.get_modeling_data(siteId)

        return SiteData(
            site=site,
            config=config,
            hardware=hardware_details,
            alerts=alerts,
            modeling=modeling,
            fetchedAt=datetime.now(),
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
                site_data_copy = site_data.copy()
                # Collect custom column data into list
                custom_data = []
                for i in range(6):
                    key = f"customColumnData{i}"
                    if key in site_data_copy:
                        custom_data.append(site_data_copy.pop(key))
                if custom_data:
                    site_data_copy["customColumnData"] = custom_data
                site = SiteOverview(**site_data_copy)
                sites.append(site)
            except Exception as e:
                logger.warning(f"Failed to parse site data: {e}")
                continue

        return PortfolioMetrics(
            customerId=customer_id,
            sites=sites,
            customColumnNames=data.get("customColumnNames", []),
            lastChanged=data.get("lastChanged", ""),
            merge=data.get("merge", False),
            mergeHash=data.get("mergeHash", ""),
        )

    def get_site_overview(self, siteId: str) -> Optional[SiteOverview]:
        """
        Get real-time site performance metrics.

        Args:
            siteId: Site ID

        Returns:
            SiteOverview object or None if not found
        """
        portfolio = self.get_portfolio_overview_from_site(siteId)
        if portfolio:
            for site in portfolio.sites:
                if site.key == siteId:
                    return site
        return None

    def get_portfolio_overview_from_site(self, siteId: str) -> Optional[PortfolioMetrics]:
        """
        Get portfolio data by inferring customer ID from site.

        Args:
            siteId: Site ID to get customer from

        Returns:
            PortfolioMetrics or None
        """
        # First get site details to find customer ID
        site_info = self.get_site_detailed_info(siteId)
        if not site_info or not site_info.parentKey:
            return None

        customer_id = site_info.parentKey
        return self.get_portfolio_overview(customer_id)

    def get_site_detailed_info(self, siteId: str) -> Optional[SiteDetailedInfo]:
        """
        Get detailed site information including contracts and configuration.

        Args:
            siteId: Site ID

        Returns:
            SiteDetailedInfo object or None if not found
        """
        siteId = parse_site_id(siteId)
        endpoint = f"/api/view/site/{siteId}"
        params = {"lastChanged": "1900-01-01T00:00:00.000Z"}

        data = self.get_json(endpoint, params=params)
        if not data:
            return None

        # Map API camelCase to dataclass camelCase fields
        return SiteDetailedInfo(
            key=data.get('key', ''),
            name=data.get('name', ''),
            isMonitored=data.get('isMonitored', False),
            cellModemContractEndDate=data.get('cellModemContractEndDate'),
            address=data.get('address', {}),
            cellModemContractStartDate=data.get('cellModemContractStartDate'),
            energyCapacityUnit=data.get('energyCapacityUnit', 0),
            longitude=data.get('longitude', 0.0),
            parentKey=data.get('parentKey', ''),
            weatherMode=data.get('weatherMode', 0),
            monitoringContractIsManual=data.get('monitoringContractIsManual', False),
            cellModemContractCustomBanner=data.get('cellModemContractCustomBanner', False),
            monitoringContractWarnDate=data.get('monitoringContractWarnDate'),
            workingStatus=data.get('workingStatus', ''),
            capacityDcUnit=data.get('capacityDcUnit', 0),
            elevation=data.get('elevation', 0),
            dailyProductionEstimate=data.get('dailyProductionEstimate', 0.0),
            lastChanged=data.get('lastChanged', ''),
            monthlyProductionEstimate=data.get('monthlyProductionEstimate', 0.0),
            ratedPowerUnit=data.get('ratedPowerUnit', 0),
            monitoringContractCustomBanner=data.get('monitoringContractCustomBanner', False),
            monitoringContractStatus=data.get('monitoringContractStatus', 0),
            monitoringContractEndDate=data.get('monitoringContractEndDate'),
            estimatedCommissioningDate=data.get('estimatedCommissioningDate'),
            cellModemContractAccessNote=data.get('cellModemContractAccessNote', ''),
            cellModemContractTerminateDate=data.get('cellModemContractTerminateDate'),
            cellModemContractIsManual=data.get('cellModemContractIsManual', False),
            customerLogo=data.get('customerLogo', ''),
            capacityAc=data.get('capacityAc', 0),
            customQueryKey=data.get('customQueryKey', ''),
            preferredWsForEstimatedInsolation=data.get('preferredWsForEstimatedInsolation', 0),
            requiresPubIp=data.get('requiresPubIp', False),
            defaultQuery=data.get('defaultQuery', 0),
            monitoringContractWillNotRenew=data.get('monitoringContractWillNotRenew', False),
            capacityAcUnit=data.get('capacityAcUnit', 0),
            status=data.get('status', 0),
            latitude=data.get('latitude', 0.0),
            ratedPower=data.get('ratedPower', 0),
            advancedSiteConfiguration=data.get('advancedSiteConfiguration', False),
            monitoringContractTerminateDate=data.get('monitoringContractTerminateDate'),
            actualCommissioningDate=data.get('actualCommissioningDate'),
            estimatedLosses=data.get('estimatedLosses', {}),
            cellModemContractWarnDate=data.get('cellModemContractWarnDate'),
            monitoringContractAccessNote=data.get('monitoringContractAccessNote', ''),
            validDataDate=data.get('validDataDate', ''),
            paymentStatus=data.get('paymentStatus', 0),
            capacityDc=data.get('capacityDc', 0.0),
            monitoringContractStartDate=data.get('monitoringContractStartDate'),
            energyCapacity=data.get('energyCapacity', 0),
            overviewChart1=data.get('overviewChart1', ''),
            overviewChart2=data.get('overviewChart2', ''),
            cellModemContractWillNotRenew=data.get('cellModemContractWillNotRenew', False),
            siteType=data.get('siteType', 0),
            sitePhotos=data.get('sitePhotos')
        )

    def get_chart_data(
        self,
        chart_type: int,
        siteId: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        bin_size: Optional[int] = None,
    ) -> Optional[ChartData]:
        """
        Get chart data for visualization.

        Args:
            chart_type: Chart type ID (from /api/view/chart/builtin)
            siteId: Site ID
            start_date: Start date (ISO format)
            end_date: End date (ISO format)
            bin_size: Bin size in minutes (optional, let API choose if None)

        Returns:
            ChartData object or None if failed
        """
        site_key = parse_site_id(siteId)

        # Build POST payload based on actual API structure from fetch logs
        from datetime import datetime, timedelta
        end_date = end_date or datetime.utcnow().strftime('%Y-%m-%d')
        start_date = start_date or (datetime.utcnow() - timedelta(days=7)).strftime('%Y-%m-%d')

        payload = {
            "chartType": chart_type,
            "context": "site",
            "source": [site_key],
            "binSize": bin_size,
            "sectionCode": -1,
            "query": None,
            "start": start_date,
            "end": end_date,
        }

        # Chart API requires specific referer
        referer = f"https://apps.alsoenergy.com/powertrack/{siteId}/overview/dashboard"
        data = self.post_json("/api/view/chart", payload, referer=referer)
        if not data:
            logger.warning(f"No data returned from chart API for site {siteId}, chart_type {chart_type}")
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
                dataXy=parsed_xy,
                color=series_data.get("color"),
                customUnit=series_data.get("customUnit"),
                dataMax=series_data.get("dataMax"),
                dataMin=series_data.get("dataMin"),
                diameter=series_data.get("diameter"),
                fitExponent=series_data.get("fitExponent"),
                header=series_data.get("header"),
                lineColor=series_data.get("lineColor"),
                lineType=series_data.get("lineType"),
                lineWidth=series_data.get("lineWidth"),
                rightAxis=series_data.get("rightAxis"),
                units=series_data.get("units"),
                useBinnedData=series_data.get("useBinnedData"),
                visible=series_data.get("visible"),
                xSeriesHeader=series_data.get("xSeriesHeader"),
                xSeriesKey=series_data.get("xSeriesKey"),
                xSeriesName=series_data.get("xSeriesName"),
                xUnits=series_data.get("xUnits"),
                yAxisIndex=series_data.get("yAxisIndex"),
                yMax=series_data.get("yMax"),
                yMin=series_data.get("yMin"),
                alertMessageMap=series_data.get("alertMessageMap"),
            )
            series.append(series_obj)

        return ChartData(
            allowSmallBinSize=data.get("allowSmallBinSize", False),
            binSize=data.get("binSize", 0),
            currentNowBinIndex=data.get("currentNowBinIndex", 0),
            dataNotAvailable=data.get("dataNotAvailable", False),
            durations=data.get("durations", []),
            end=data.get("end", ""),
            errorString=data.get("errorString", ""),
            hardwareKeys=data.get("hardwareKeys", []),
            hasAlertMessages=data.get("hasAlertMessages", False),
            hasOverriddenQuery=data.get("hasOverriddenQuery", False),
            isCategoryChart=data.get("isCategoryChart", False),
            isSummaryChart=data.get("isSummaryChart", False),
            isUsingDaylightSavings=data.get("isUsingDaylightSavings", False),
            key=data.get("key", ""),
            lastChanged=data.get("lastChanged", ""),
            lastDataDatetime=data.get("lastDataDatetime", ""),
            namedResults=data.get("namedResults", {}),
            renderType=data.get("renderType", 0),
            series=series,
            summaryTable=data.get("summaryTable", []),
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
            logger.warning("No chart definitions returned from API (endpoint may not be available)")
            return []

        # The API might return charts in different formats
        if isinstance(data, list):
            return data

        # Extract predefined charts from sections
        charts = []
        for section in data.get("chartMenuSections", []):
            for chart in section.get("predefinedCharts", []):
                charts.append(chart)

        # If no charts found in sections, return whatever we got
        if not charts and data:
            return [data] if isinstance(data, dict) else []

        return charts

    def get_alert_summary(
        self, customer_id: Optional[str] = None, siteId: Optional[str] = None
    ) -> Optional[AlertSummaryResponse]:
        """
        Get alert summary for customer or site.

        The API can return several shapes. Common shapes include:
        - { "hardwareSummary": { "H123": {"count":1, "maxSeverity":4}, ... }, ... }
        - { "H123": {"count":1, "maxSeverity":4}, ... }
        This method normalizes either shape into an AlertSummaryResponse.
        """
        if customer_id:
            endpoint = f"/api/view/activealerts/activesummary/{customer_id}"
        elif siteId:
            siteId = parse_site_id(siteId)
            endpoint = f"/api/view/activealerts/activesummary/{siteId}"
        else:
            raise ValueError("Either customer_id or siteId must be provided")

        data = self.get_json(endpoint)
        if not data:
            return None

        hardware_summaries: Dict[str, AlertSummary] = {}

        # Collect candidate maps that contain hardware-id keys (Hnnn)
        candidates: List[Dict[str, Any]] = []

        if isinstance(data, dict):
            # Prefer explicit 'hardwareSummary' key when present
            if "hardwareSummary" in data and isinstance(data["hardwareSummary"], dict):
                candidates.append(data["hardwareSummary"])

            # Top-level keys that look like hardware keys
            top_level_hw = {k: v for k, v in data.items() if isinstance(k, str) and re.match(r"^H\d+$", k) and isinstance(v, dict)}
            if top_level_hw:
                candidates.append(top_level_hw)

            # Also inspect nested dicts for a hardware map
            for v in data.values():
                if isinstance(v, dict):
                    nested_hw = {k: v2 for k, v2 in v.items() if isinstance(k, str) and re.match(r"^H\d+$", k) and isinstance(v2, dict)}
                    if nested_hw:
                        candidates.append(nested_hw)

        # Normalize entries from candidates
        for hw_map in candidates:
            for hw_key, summary_data in hw_map.items():
                if not isinstance(summary_data, dict):
                    continue
                max_sev = summary_data.get("maxSeverity", summary_data.get("max_severity", 0))
                count = summary_data.get("count", summary_data.get("cnt", 0))
                hardware_summaries[hw_key] = AlertSummary(
                    hardwareKey=hw_key,
                    maxSeverity=max_sev,
                    count=count,
                )

        return AlertSummaryResponse(hardwareSummaries=hardware_summaries)

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
            canEditAutoReport=data.get("canEditAutoReport", False),
            canAddEmailReport=data.get("canAddEmailReport", False),
            canAddSummaryReport=data.get("canAddSummaryReport", False),
            canAddAutoReport=data.get("canAddAutoReport", False),
            canAddUserReport=data.get("canAddUserReport", False),
            views=data.get("views", []),
        )

    def get_site_hardware_production(self, siteId: str) -> List[Dict[str, Any]]:
        """
        Get hardware production data for a site.

        Args:
            siteId: Site ID

        Returns:
            List of hardware production data
        """
        siteId = parse_site_id(siteId)
        endpoint = f"/api/view/sitehardwareproduction/{siteId}"

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

    def get_site_links(self, siteId: str) -> List[Dict[str, Any]]:
        """
        Get site links and sharing information.

        Args:
            siteId: Site ID

        Returns:
            List of site links
        """
        siteId = parse_site_id(siteId)
        endpoint = f"/api/view/sitelinks/{siteId}"

        data = self.get_json(endpoint)
        if not data:
            return []

        return data.get("links", [])

    def get_site_shares(self, siteId: str) -> List[Dict[str, Any]]:
        """
        Get site sharing configurations.

        Args:
            siteId: Site ID

        Returns:
            List of site shares
        """
        siteId = parse_site_id(siteId)
        endpoint = f"/api/view/siteshares/{siteId}"

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

        # API returns list directly, not wrapped in object
        if isinstance(data, list):
            return data
        return data.get("curves", [])

    def get_pvsyst_modules(
        self, hardware_id: Optional[str] = None, siteId: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get PVSyst module configurations.

        Args:
            hardware_id: Specific hardware ID
            siteId: Site ID (alternative to hardware_id)

        Returns:
            List of PVSyst modules
        """
        if hardware_id:
            hardware_id = parse_hardware_id(hardware_id)
            endpoint = f"/api/view/pvsystmodules/{hardware_id}"
        elif siteId:
            siteId = parse_site_id(siteId)
            endpoint = f"/api/view/pvsystmodules/{siteId}"
        else:
            raise ValueError("Either hardware_id or siteId must be provided")

        data = self.get_json(endpoint)
        if not data:
            return []

        # API returns list directly, not wrapped in object
        if isinstance(data, list):
            return data
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

        # API returns list directly, not wrapped in object
        if isinstance(data, list):
            return data
        return data.get("settings", [])

    def get_driver_list(self, code: int = 2) -> List[Dict[str, Any]]:
        """
        Get list of available drivers by function code.

        Args:
            code: Function code for hardware type (default: 2 = Production Meter)

        Returns:
            List of driver configurations
        """
        endpoint = f"/api/lookuplist/drivers/{code}"

        data = self.get_json(endpoint)
        if not data:
            return []

        # API returns list directly
        if isinstance(data, list):
            return data
        return []

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
