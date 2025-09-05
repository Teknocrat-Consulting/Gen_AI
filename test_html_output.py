#!/usr/bin/env python3
import requests
import json

url = "http://localhost:8000/api/chat"
data = {
    "message": "Show me flights from Delhi to Mumbai on October 20th",
    "session_id": "test_html_session"
}

print("Testing HTML formatted output...")
print("=" * 60)
print("Query:", data["message"])
print("=" * 60)

try:
    response = requests.post(url, json=data, timeout=60)
    
    if response.status_code == 200:
        result = response.json()
        
        # Save the HTML response to a file for viewing
        html_response = result.get('response', 'No response')
        
        with open('flight_response.html', 'w') as f:
            f.write('''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Flight Search Results</title>
    <style>
        body {
            margin: 0;
            padding: 0;
            background: #f5f5f5;
        }
    </style>
</head>
<body>
''')
            f.write(html_response)
            f.write('''
</body>
</html>''')
        
        print("\n✅ HTML Response saved to 'flight_response.html'")
        print("\nFirst 500 characters of response:")
        print(html_response[:500] + "...")
        
        if result.get('flight_data'):
            print(f"\n✅ Found {len(result['flight_data'])} flights in data")
        
    else:
        print(f"\nError: {response.status_code}")
        print(response.text)
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()