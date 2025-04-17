#!/usr/bin/env python3
import requests
import sys
import time
import json
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"
API_TOKEN = "datura"
ENDPOINTS = [
    "/health",
    "/api/v1/tao_dividends?netuid=18"
]

def print_header(message):
    """Print a formatted header."""
    print("\n" + "=" * 80)
    print(f" {message}")
    print("=" * 80)

def check_auth():
    """Test authentication methods."""
    print_header("TESTING AUTHENTICATION")
    
    # Test valid token
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    response = requests.get(f"{BASE_URL}/api/v1/tao_dividends?netuid=18", headers=headers)
    if response.status_code == 200:
        print("✅ Legacy token authentication working")
    else:
        print(f"❌ Legacy token authentication failed: {response.status_code}")
        print(response.text)
    
    # Test invalid token
    headers = {"Authorization": f"Bearer invalid_token"}
    response = requests.get(f"{BASE_URL}/api/v1/tao_dividends?netuid=18", headers=headers)
    if response.status_code == 403:
        print("✅ Authentication correctly rejects invalid tokens")
    else:
        print(f"❌ Invalid token check failed: {response.status_code}")
        print(response.text)
    
    # Try JWT token endpoint if implemented
    try:
        headers = {"Authorization": f"Bearer {API_TOKEN}"}
        response = requests.post(f"{BASE_URL}/token", headers=headers)
        if response.status_code == 200:
            jwt_token = response.json().get("access_token")
            print("✅ JWT token generation working")
            
            # Test using the JWT token
            headers = {"Authorization": f"Bearer {jwt_token}"}
            response = requests.get(f"{BASE_URL}/api/v1/tao_dividends?netuid=18", headers=headers)
            if response.status_code == 200:
                print("✅ JWT token authentication working")
            else:
                print(f"❌ JWT token authentication failed: {response.status_code}")
        else:
            print(f"⚠️ JWT token endpoint returned {response.status_code} - may not be implemented yet")
    except requests.exceptions.RequestException:
        print("⚠️ JWT token endpoint not accessible - may not be implemented yet")

def check_caching():
    """Test that Redis caching is working."""
    print_header("TESTING CACHING")
    
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    
    # First request
    start_time = time.time()
    response1 = requests.get(f"{BASE_URL}/api/v1/tao_dividends?netuid=18", headers=headers)
    time1 = time.time() - start_time
    
    # Second request should be faster (cached)
    start_time = time.time()
    response2 = requests.get(f"{BASE_URL}/api/v1/tao_dividends?netuid=18", headers=headers)
    time2 = time.time() - start_time
    
    print(f"First request: {time1:.4f} seconds")
    print(f"Second request: {time2:.4f} seconds")
    
    if time2 < time1:
        print("✅ Caching appears to be working (second request was faster)")
    else:
        print("⚠️ Caching may not be working (second request wasn't faster)")

def check_endpoints():
    """Check if all endpoints are accessible."""
    print_header("CHECKING ENDPOINTS")
    
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    
    for endpoint in ENDPOINTS:
        try:
            response = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
            if response.status_code == 200:
                print(f"✅ {endpoint} - Status: {response.status_code}")
            else:
                print(f"❌ {endpoint} - Status: {response.status_code}")
                print(response.text)
        except requests.exceptions.RequestException as e:
            print(f"❌ {endpoint} - Error: {e}")

def check_health():
    """Check the health endpoint for service status."""
    print_header("CHECKING SERVICE HEALTH")
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            health_data = response.json()
            status = health_data.get("status", "unknown")
            client_status = health_data.get("bittensor_client", "unknown")
            
            print(f"Service status: {status}")
            print(f"Bittensor client: {client_status}")
            
            if status == "healthy" and client_status == "initialized":
                print("✅ Service is fully operational")
            elif status == "healthy":
                print("⚠️ Service is healthy but some components may not be fully initialized")
            else:
                print("❌ Service is in degraded state")
        else:
            print(f"❌ Health check failed: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Health check failed: {e}")

def main():
    print(f"Running status check on {BASE_URL} at {datetime.now()}")
    
    try:
        check_health()
        check_endpoints()
        check_auth()
        check_caching()
        
        print_header("STATUS CHECK COMPLETE")
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to {BASE_URL} - is the service running?")
        sys.exit(1)

if __name__ == "__main__":
    main()
