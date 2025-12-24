#!/usr/bin/env python3
"""
PowerTrack SDK Authentication Helper

This script helps you update your authentication credentials.
Run this when your API calls start failing with authentication errors.
"""

import os
import sys

def show_auth_status():
    """Show current authentication status."""
    print("🔍 Checking current authentication...")

    try:
        from powertrack_sdk import PowerTrackClient
        client = PowerTrackClient()

        # Try a simple API call
        response = client._make_request('GET', '/api/view/portfolio/C8458?lastChanged=1900-01-01T00%3A00%3A00.000Z')
        if response.status_code == 200:
            print("✅ Authentication is working!")
            return True
        else:
            print(f"❌ Authentication failed (Status: {response.status_code})")
            print(f"Response: {response.text[:200]}")
            return False

    except Exception as e:
        print(f"❌ Authentication check failed: {e}")
        return False

def show_auth_instructions():
    """Show instructions for updating authentication."""
    print("\n📋 To update authentication:")
    print("1. Open Chrome and go to: https://apps.alsoenergy.com")
    print("2. Log in to your PowerTrack account")
    print("3. Open DevTools (F12) → Network tab")
    print("4. Navigate to any page or perform any action")
    print("5. Find any API request in the Network tab")
    print("6. Right-click it → 'Copy as fetch'")
    print("7. Replace the content in mostRecentFetch.js with your copied fetch call")
    print("8. Run this script again to verify")

    # Show the path to mostRecentFetch.js
    try:
        import powertrack_sdk
        fetch_path = os.path.join(os.path.dirname(powertrack_sdk.__file__), 'mostRecentFetch.js')
        print(f"\n📁 mostRecentFetch.js location: {fetch_path}")
    except:
        print("\n📁 mostRecentFetch.js location: [install powertrack-sdk first]")

if __name__ == "__main__":
    print("🔐 PowerTrack SDK Authentication Helper")
    print("=" * 50)

    auth_working = show_auth_status()

    if not auth_working:
        show_auth_instructions()
        print("\n💡 Need help? Check that:")
        print("   - You're logged into PowerTrack in Chrome")
        print("   - The fetch data is from a recent API call")
        print("   - Cookies haven't expired (try logging out/in)")
    else:
        print("\n🎉 Ready to use PowerTrack SDK!")

    sys.exit(0 if auth_working else 1)