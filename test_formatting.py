#!/usr/bin/env python3
import requests
import json

url = "http://localhost:8000/api/chat"
data = {
    "message": "Find me flights from Delhi to Mumbai on October 15th",
    "session_id": "test_format_session"
}

print("Testing improved formatting...")
print("=" * 60)
print("Query:", data["message"])
print("=" * 60)

try:
    response = requests.post(url, json=data, timeout=60)
    
    if response.status_code == 200:
        result = response.json()
        
        print("\n📋 LLM RESPONSE WITH NEW FORMATTING:")
        print("=" * 60)
        print(result.get('response', 'No response'))
        print("=" * 60)
        
        if result.get('flight_data'):
            print(f"\n✅ Found {len(result['flight_data'])} flights")
            print("\nSample flight data (first 2):")
            for i, flight in enumerate(result['flight_data'][:2], 1):
                print(f"\n  Flight {i}:")
                print(f"    • Airline: {flight['Airline Name']}")
                print(f"    • Price: ₹{flight['Total Price']} {flight['Currency']}")
                print(f"    • Time: {flight['Departure']} → {flight['Arrival']}")
                print(f"    • Stops: {flight['Number of Stops']}")
        
    else:
        print(f"\nError: {response.status_code}")
        print(response.text)
except Exception as e:
    print(f"Error: {e}")