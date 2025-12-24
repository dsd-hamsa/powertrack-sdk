#!/usr/bin/env python3
"""
Quick authentication verification script.
Run this after updating mostRecentFetch.js to verify auth works.
"""

import requests
from powertrack_sdk import PowerTrackClient

def verify_auth():
    """Verify authentication is working."""
    print("🔐 Verifying PowerTrack Authentication...")
    print("-" * 40)

    try:
        client = PowerTrackClient()

        # Test basic endpoint
        url = f"{client.base_url}/api/view/portfolio/C8458?lastChanged=1900-01-01T00%3A00%3A00.000Z"
        headers = client.auth_manager.get_auth_headers()

        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            if response.text.strip():
                if response.text.strip().startswith('{') or response.text.strip().startswith('['):
                    print("✅ SUCCESS: Authentication working!")
                    print(f"   Response: {len(response.text)} characters of JSON data")
                    return True
                else:
                    print("⚠️  WARNING: Got 200 but unexpected response format")
                    print(f"   Response: {response.text[:100]}...")
                    return False
            else:
                print("❌ FAILED: Got 200 but empty response")
                return False

        elif response.status_code == 419:
            print("❌ FAILED: Authentication expired (419 AuthExpired)")
            print("   Get fresh fetch data from Chrome DevTools!")
            return False

        elif response.status_code == 401:
            print("❌ FAILED: Authentication invalid (401 Unauthorized)")
            print("   Check your mostRecentFetch.js data")
            return False

        else:
            print(f"❌ FAILED: Unexpected status {response.status_code}")
            print(f"   Response: {response.text[:100] if response.text else 'Empty'}")
            return False

    except Exception as e:
        print(f"❌ FAILED: Request error - {e}")
        return False

if __name__ == "__main__":
    success = verify_auth()
    if success:
        print("\n🎉 Ready to use PowerTrack SDK!")
        print("   You can now run your tests and API calls.")
    else:
        print("\n💡 Need fresh authentication data from Chrome DevTools")

    exit(0 if success else 1)