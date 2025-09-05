#!/usr/bin/env python3
import requests
import json

url = "http://localhost:8000/api/chat"
data = {
    "message": "cheapest flights from mumbai to delhi next monday",
    "session_id": "test_mumbai_delhi"
}

print("Testing Mumbai to Delhi Route")
print("=" * 60)
print(f"Query: {data['message']}")
print("=" * 60)

try:
    response = requests.post(url, json=data, timeout=60)
    
    if response.status_code == 200:
        result = response.json()
        
        print("\n📋 RESPONSE:")
        print("-" * 60)
        response_text = result.get('response', 'No response')
        print(response_text)
        print("-" * 60)
        
        if result.get('flight_data'):
            print(f"\n✅ Flight data available: {len(result['flight_data'])} flights")
            print("Sample flight data:")
            flight = result['flight_data'][0]
            for key, value in flight.items():
                print(f"  {key}: {value}")
        
        print(f"\n📊 Show flight cards: {result.get('show_flight_cards')}")
        print(f"🗒️ Session ID: {result.get('session_id')}")
        
    else:
        print(f"\nError: {response.status_code}")
        print(response.text)
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()