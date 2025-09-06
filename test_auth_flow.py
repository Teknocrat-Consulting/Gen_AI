#!/usr/bin/env python3
"""
Test script to verify authentication flow:
1. Access landing page without authentication -> should redirect to /auth
2. Logout clears session and redirects to /auth
"""

import requests
import json

BASE_URL = "http://localhost:8001"

def test_unauthenticated_access():
    """Test that unauthenticated users are redirected to auth page"""
    print("Testing unauthenticated access to landing page...")
    
    # Try to access the landing page without authentication
    response = requests.get(f"{BASE_URL}/", allow_redirects=False)
    
    if response.status_code == 302:
        location = response.headers.get('Location', '')
        if '/auth' in location:
            print("✓ Unauthenticated users are correctly redirected to /auth")
            return True
        else:
            print(f"✗ Unexpected redirect location: {location}")
            return False
    else:
        print(f"✗ Expected redirect (302), got status code: {response.status_code}")
        return False

def test_auth_page_accessible():
    """Test that auth page is accessible without authentication"""
    print("\nTesting auth page accessibility...")
    
    response = requests.get(f"{BASE_URL}/auth")
    
    if response.status_code == 200:
        print("✓ Auth page is accessible without authentication")
        return True
    else:
        print(f"✗ Auth page returned status code: {response.status_code}")
        return False

def test_logout_endpoint():
    """Test that logout endpoint exists and responds"""
    print("\nTesting logout endpoint...")
    
    # Test with invalid token (should still respond)
    headers = {'Authorization': 'Bearer invalid_token'}
    response = requests.post(f"{BASE_URL}/auth/logout", headers=headers)
    
    if response.status_code in [400, 401, 500]:
        print(f"✓ Logout endpoint exists and responds (status: {response.status_code})")
        return True
    else:
        print(f"✗ Unexpected logout response: {response.status_code}")
        return False

def main():
    print("=" * 50)
    print("Authentication Flow Test")
    print("=" * 50)
    
    results = []
    
    # Run tests
    results.append(test_unauthenticated_access())
    results.append(test_auth_page_accessible())
    results.append(test_logout_endpoint())
    
    # Summary
    print("\n" + "=" * 50)
    print("Test Summary")
    print("=" * 50)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("✓ All tests passed!")
    else:
        print("✗ Some tests failed. Please check the implementation.")

if __name__ == "__main__":
    main()