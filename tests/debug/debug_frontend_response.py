#!/usr/bin/env python3
"""
Debug script to test individual report endpoints and see what response we get.
This mimics what the frontend might be doing.
"""

import requests
import json
from uuid import uuid4

# Configuration
BASE_URL = "http://localhost:80"  # Adjust if your server runs on a different port
API_BASE = f"{BASE_URL}/api/v1.0"

def authenticate(username: str, password: str) -> str:
    """Authenticate to the backend and return the JWT access token."""
    url = f"{API_BASE}/user/login"
    data = {"username": username, "password": password}
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    response = requests.post(url, data=data, headers=headers)
    print(f"Auth Status Code: {response.status_code}")
    print(f"Auth Response: {response.text}")
    if response.status_code == 200:
        try:
            return response.json()["access_token"]
        except Exception as e:
            print(f"Failed to extract token: {e}")
            return None
    else:
        print("Authentication failed.")
        return None

def test_individual_test_performance(token: str = None):
    """Test the individual test performance endpoint."""
    test_id = "724d11ec-492e-4ade-a497-adf39aabc85e"  # Use the test ID from the error logs
    url = f"{API_BASE}/reports/performance/{test_id}"
    print(f"Testing URL: {url}")
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        response = requests.get(url, headers=headers)
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Content: {response.text}")
        if response.status_code == 200:
            try:
                json_data = response.json()
                print(f"JSON Response: {json.dumps(json_data, indent=2)}")
            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON: {e}")
        else:
            print(f"Error response: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")

def test_individual_test_trends(token: str = None):
    """Test the individual test trends endpoint."""
    test_id = "724d11ec-492e-4ade-a497-adf39aabc85e"  # Use the test ID from the error logs
    url = f"{API_BASE}/reports/trends/{test_id}"
    print(f"\nTesting URL: {url}")
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        response = requests.get(url, headers=headers)
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Content: {response.text}")
        if response.status_code == 200:
            try:
                json_data = response.json()
                print(f"JSON Response: {json.dumps(json_data, indent=2)}")
            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON: {e}")
        else:
            print(f"Error response: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")

def test_health_endpoint():
    """Test the health endpoint to see if it returns 'ok'."""
    url = f"{BASE_URL}/health"
    print(f"\nTesting Health URL: {url}")
    try:
        response = requests.get(url)
        print(f"Status Code: {response.status_code}")
        print(f"Response Content: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    print("=== Debugging Frontend Response Issue ===")
    # Test health endpoint first
    test_health_endpoint()
    # Uncomment and provide credentials to test authentication and endpoints
    username = "user"
    password = "pass!"
    token = authenticate(username, password)
    test_individual_test_performance(token)
    test_individual_test_trends(token)
    print("\n=== Debug Complete ===") 