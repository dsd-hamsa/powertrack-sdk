"""
Authentication handling for PowerTrack SDK

Handles authentication setup from various sources:
- Environment variables
- .env files
- Browser fetch parsing
- Cookie files
"""

import os
import re
from pathlib import Path
from typing import Dict, Optional, Any
from urllib.parse import urlparse

from .exceptions import AuthenticationError, ConfigurationError


class AuthManager:
    """
    Manages PowerTrack authentication from multiple sources.

    Priority order:
    1. Explicit parameters
    2. Environment variables
    3. .env file (if python-dotenv available)
    4. Browser fetch parsing (mostRecentFetch.js)
    5. Cookie file fallback
    """

    def __init__(
        self,
        cookie: Optional[str] = None,
        ae_s: Optional[str] = None,
        ae_v: Optional[str] = None,
        base_url: Optional[str] = None,
        cookie_file: Optional[str] = None,
        fetch_file: Optional[str] = None
    ):
        """
        Initialize authentication manager.

        Args:
            cookie: Explicit cookie string
            ae_s: Explicit AE_S security header
            ae_v: Explicit AE_V API version
            base_url: Explicit base URL
            cookie_file: Path to cookie file
            fetch_file: Path to browser fetch file
        """
        self.cookie = cookie
        self.ae_s = ae_s
        self.ae_v = ae_v  # Keep as is, default later
        self.base_url = base_url or "https://apps.alsoenergy.com"
        self.cookie_file = cookie_file or "cookie.txt"
        self.fetch_file = fetch_file

        # Load dotenv if available
        self._load_dotenv_if_available()

        # Load authentication data
        self.auth_data = self._setup_auth()

        # Validate
        self._validate_auth()

    def _load_dotenv_if_available(self) -> None:
        """Load environment variables from .env file if available."""
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass  # dotenv not required

    def _setup_auth(self) -> Dict[str, str]:
        """
        Set up authentication from various sources.

        Returns:
            Dict with auth data
        """
        auth_data = {
            'COOKIE': None,
            'AE_S': None,
            'AE_V': self.ae_v,  # None if not provided
            'BASE_URL': self.base_url
        }

        # 1. Explicit parameters
        if self.cookie:
            auth_data['COOKIE'] = self.cookie
        if self.ae_s:
            auth_data['AE_S'] = self.ae_s

        # 2. Parse browser fetch if available
        fetch_auth = self._parse_most_recent_fetch()
        for key, value in fetch_auth.items():
            if key in auth_data and not auth_data[key]:
                auth_data[key] = value

        # 3. Environment variables
        if not auth_data['COOKIE']:
            auth_data['COOKIE'] = os.getenv('COOKIE')
        if not auth_data['AE_S']:
            auth_data['AE_S'] = os.getenv('AE_S')
        if not auth_data['AE_V']:
            auth_data['AE_V'] = os.getenv('AE_V', '086665')
        if not auth_data['BASE_URL']:
            auth_data['BASE_URL'] = os.getenv('BASE_URL', 'https://apps.alsoenergy.com')

        # 4. Cookie file fallback
        if not auth_data['COOKIE']:
            auth_data['COOKIE'] = self._load_cookie_from_file()

        return auth_data

    def _parse_most_recent_fetch(self) -> Dict[str, str]:
        """
        Parse authentication details from mostRecentFetch.js file.

        Returns:
            Dict containing auth data
        """
        if self.fetch_file:
            fetch_path = Path(self.fetch_file)
        else:
            # Try common locations (prioritize root directory for user editing)
            candidates = [
                Path(__file__).parent.parent / "mostRecentFetch.js",  # SDK root first
                Path(__file__).parent / "mostRecentFetch.js",          # Package directory
                Path("mostRecentFetch.js"),                            # Current directory
                Path("auth/mostRecentFetch.js"),                       # Auth subdirectory
                Path("../auth/mostRecentFetch.js")                     # Parent auth directory
            ]
            fetch_path = None
            for candidate in candidates:
                if candidate.exists():
                    fetch_path = candidate
                    print(f"DEBUG: Found fetch file at: {fetch_path}")
                    break

        if not fetch_path or not fetch_path.exists():
            return {}

        try:
            with open(fetch_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Extract headers - look for the last occurrence of each header
            # (in case there are placeholder values earlier in the file)
            auth_data = {}

            # Cookie - find the last occurrence
            cookie_matches = re.findall(
                r'["\']cookie["\']\s*:\s*["\']([^"\']+)["\']',
                content,
                flags=re.IGNORECASE
)
            if cookie_matches:
                auth_data['COOKIE'] = cookie_matches[-1]  # Use last match

            # AE_S - find the last occurrence
            ae_s_matches = re.findall(
                r'["\']ae_s["\']\s*:\s*["\']([^"\']+)["\']',
                content,
                flags=re.IGNORECASE
            )
            if ae_s_matches:
                auth_data['AE_S'] = ae_s_matches[-1]  # Use last match

            # AE_V - find the last occurrence
            ae_v_matches = re.findall(
                r'["\']ae_v["\']\s*:\s*["\']([^"\']+)["\']',
                content,
                flags=re.IGNORECASE
            )
            if ae_v_matches:
                auth_data['AE_V'] = ae_v_matches[-1]  # Use last match

            return auth_data

        except Exception:
            return {}

    def _load_cookie_from_file(self) -> Optional[str]:
        """
        Load cookie from file.

        Returns:
            Cookie string or None
        """
        cookie_path = Path(self.cookie_file)
        if not cookie_path.exists():
            return None

        try:
            with open(cookie_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception:
            return None

    def _validate_auth(self) -> None:
        """Validate that required authentication is present."""
        if not self.auth_data.get('COOKIE'):
            raise AuthenticationError(
                "Cookie is required for authentication. "
                "Set COOKIE environment variable, provide cookie parameter, "
                "or ensure cookie.txt exists"
            )

        if not self.auth_data.get('AE_S'):
            raise AuthenticationError(
                "AE_S security header is required. "
                "Set AE_S environment variable or provide ae_s parameter"
            )

        # Validate base URL
        parsed = urlparse(self.auth_data['BASE_URL'])
        if not parsed.scheme or not parsed.netloc:
            raise ConfigurationError(f"Invalid base URL: {self.auth_data['BASE_URL']}")

    def get_auth_headers(self, referer: Optional[str] = None) -> Dict[str, str]:
        """
        Get authentication headers for API requests.

        Args:
            referer: Optional referer URL for the request

        Returns:
            Dict of headers
        """
        headers = {
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'ae_s': self.auth_data['AE_S'],
            'ae_v': self.auth_data['AE_V'],
            'cookie': self.auth_data['COOKIE']
        }

        if referer:
            headers['Referer'] = referer

        return headers

    def get_base_url(self) -> str:
        """Get the base API URL."""
        return self.auth_data['BASE_URL']

    def refresh_from_fetch(self, fetch_file: Optional[str] = None) -> bool:
        """
        Refresh authentication from a new fetch file.

        Args:
            fetch_file: Path to fetch file (optional)

        Returns:
            True if auth was updated
        """
        old_auth = self.auth_data.copy()

        if fetch_file:
            self.fetch_file = fetch_file

        self.auth_data = self._setup_auth()
        self._validate_auth()

        return self.auth_data != old_auth

    @classmethod
    def from_env(cls) -> 'AuthManager':
        """
        Create AuthManager using environment variables only.

        Returns:
            AuthManager instance
        """
        return cls()

    @classmethod
    def from_fetch_file(cls, fetch_file: str) -> 'AuthManager':
        """
        Create AuthManager from browser fetch file.

        Args:
            fetch_file: Path to fetch file

        Returns:
            AuthManager instance
        """
        return cls(fetch_file=fetch_file)