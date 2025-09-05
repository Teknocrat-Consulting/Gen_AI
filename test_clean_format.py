#!/usr/bin/env python3
import requests
import json

url = "http://localhost:8000/api/chat"
data = {
    "message": "Show me flights from San Francisco to New York on October 20th",
    "session_id": "test_clean_format"
}

print("Testing Clean Text Format Output")
print("=" * 60)
print(f"Query: {data['message']}")
print("=" * 60)

try:
    response = requests.post(url, json=data, timeout=60)
    
    if response.status_code == 200:
        result = response.json()
        
        print("\n📋 CLEAN TEXT RESPONSE:")
        print("-" * 60)
        response_text = result.get('response', 'No response')
        print(response_text)
        print("-" * 60)
        
        # Check for markdown symbols
        markdown_symbols = ['**', '##', '###', '*', '_']
        found_symbols = []
        
        for symbol in markdown_symbols:
            if symbol in response_text:
                found_symbols.append(symbol)
        
        if found_symbols:
            print(f"\n❌ MARKDOWN SYMBOLS FOUND: {found_symbols}")
        else:
            print("\n✅ NO MARKDOWN SYMBOLS DETECTED - CLEAN TEXT FORMAT")
        
        # Check for emoji headers
        emoji_headers = ['🎯', '✈️', '💡', '📊', '🎁']
        found_emojis = []
        
        for emoji in emoji_headers:
            if emoji in response_text:
                found_emojis.append(emoji)
        
        if found_emojis:
            print(f"✅ EMOJI HEADERS FOUND: {found_emojis}")
        else:
            print("❌ NO EMOJI HEADERS DETECTED")
        
        if result.get('flight_data'):
            print(f"\n✅ Flight data available: {len(result['flight_data'])} flights")
        
    else:
        print(f"\nError: {response.status_code}")
        print(response.text)
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()