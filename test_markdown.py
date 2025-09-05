#!/usr/bin/env python3
import requests
import json

url = "http://localhost:8000/api/chat"
data = {
    "message": "Show me flights from Delhi to Mumbai on October 15th",
    "session_id": "test_markdown_session"
}

print("Testing Simplified Markdown Output")
print("=" * 60)
print(f"Query: {data['message']}")
print("=" * 60)

try:
    response = requests.post(url, json=data, timeout=30)
    
    if response.status_code == 200:
        result = response.json()
        
        print("\n📋 MARKDOWN RESPONSE:")
        print("-" * 60)
        print(result.get('response', 'No response'))
        print("-" * 60)
        
        if result.get('flight_data'):
            print(f"\n✅ Successfully retrieved {len(result['flight_data'])} flights")
            print("\nFirst flight data sample:")
            flight = result['flight_data'][0]
            print(f"  • {flight['Airline Name']} ({flight['Airline Code']})")
            print(f"  • Price: ₹{flight['Total Price']} {flight['Currency']}")
            print(f"  • {flight['Departure']} → {flight['Arrival']}")
            print(f"  • Stops: {flight['Number of Stops']}")
        
    else:
        print(f"\nError: {response.status_code}")
        print(response.text)
except Exception as e:
    print(f"Error: {e}")