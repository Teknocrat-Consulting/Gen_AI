#!/usr/bin/env python3
import requests
import json

url = "http://localhost:8000/api/chat"
data = {
    "message": "I need 2 tickets from San Francisco to Tokyo next Monday",
    "session_id": "test_session_1"
}

print("Sending request to:", url)
print("Data:", json.dumps(data, indent=2))

try:
    response = requests.post(url, json=data, timeout=30)
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    print(f"Response Text: {response.text}")
    
    if response.status_code == 200:
        result = response.json()
        print("\nParsed Response:")
        print(json.dumps(result, indent=2))
    else:
        print(f"\nError: {response.status_code}")
        print(response.text)
except requests.exceptions.Timeout:
    print("Request timed out after 30 seconds")
except requests.exceptions.ConnectionError as e:
    print(f"Connection error: {e}")
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")