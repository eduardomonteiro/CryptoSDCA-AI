#!/usr/bin/env python3
"""
Test script to verify all routes are working correctly
"""

import requests
import json
from urllib.parse import urljoin

BASE_URL = "http://127.0.0.1:8000"

def test_route(url, expected_status=200):
    """Test a route and return the response"""
    try:
        response = requests.get(url, timeout=5)
        print(f"✅ {url} - Status: {response.status_code}")
        if response.status_code != expected_status:
            print(f"   ⚠️  Expected {expected_status}, got {response.status_code}")
        return response
    except requests.exceptions.RequestException as e:
        print(f"❌ {url} - Error: {e}")
        return None

def main():
    print("🔍 Testing CryptoSDCA-AI Routes...")
    print("=" * 50)
    
    # Test main pages
    routes_to_test = [
        ("/", "Home page"),
        ("/dashboard", "Dashboard page"),
        ("/admin/exchanges", "Admin exchanges page"),
        ("/admin/ai-agents", "Admin AI agents page"),
        ("/admin/settings", "Admin settings page"),
        ("/admin/history", "Admin history page"),
        ("/manager", "Manager page"),
    ]
    
    for route, description in routes_to_test:
        print(f"\n📄 Testing {description}:")
        test_route(urljoin(BASE_URL, route))
    
    # Test API endpoints
    print(f"\n🔌 Testing API Endpoints:")
    api_routes = [
        ("/admin/api/exchanges", "Get exchanges API"),
        ("/admin/api/ai-agents", "Get AI agents API"),
        ("/admin/api/settings", "Get settings API"),
        ("/admin/api/history", "Get history API"),
        ("/api/trading/status", "Trading status API"),
        ("/api/trading/statistics", "Trading statistics API"),
    ]
    
    for route, description in api_routes:
        print(f"\n📡 Testing {description}:")
        test_route(urljoin(BASE_URL, route))
    
    print("\n" + "=" * 50)
    print("🎉 Route testing completed!")
    print("\n📋 Summary:")
    print("- Frontend pages should return HTML (status 200)")
    print("- API endpoints should return JSON (status 200)")
    print("- If you see errors, check that the server is running on http://127.0.0.1:8000")

if __name__ == "__main__":
    main()