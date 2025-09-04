#!/usr/bin/env python3
import requests
import json

url = "http://localhost:8000/api/chat"
data = {
    "message": "I want to fly from San Francisco to New York on October 20",
    "session_id": "test_simple_session"
}

print("Testing with a simple query...")
print("Sending request to:", url)
print("Query:", data["message"])
print("-" * 50)

try:
    response = requests.post(url, json=data, timeout=60)
    print(f"\nStatus Code: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        
        # Check if flight data is present
        if result.get('flight_data'):
            print(f"\nFound {len(result['flight_data'])} flights")
            print("\nFirst 3 flights:")
            print("-" * 50)
            
            for i, flight in enumerate(result['flight_data'][:3], 1):
                print(f"\nFlight {i}:")
                print(f"  Airline: {flight['Airline Name']}")
                print(f"  Price: {flight['Total Price']} {flight['Currency']}")
                print(f"  Departure: {flight['Departure']}")
                print(f"  Arrival: {flight['Arrival']}")
                print(f"  Stops: {flight['Number of Stops']}")
        else:
            print("\nNo flights found")
        
        print("\n" + "="*50)
        print("Response:")
        print(result.get('response', 'No response'))
        
    else:
        print(f"\nError: {response.status_code}")
        print(response.text)
except Exception as e:
    print(f"Error: {e}")