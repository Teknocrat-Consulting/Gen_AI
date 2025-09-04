#!/usr/bin/env python3
import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

def test_flight_extraction():
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("ERROR: OPENAI_API_KEY not found in environment")
        return
    
    print(f"Using API key: {api_key[:10]}...")
    
    client = OpenAI(api_key=api_key)
    
    today = datetime.now()
    current_date_str = today.strftime('%Y-%m-%d')
    
    query = "I need 2 tickets from San Francisco to Tokyo next Monday"
    
    messages = [
        {
            "role": "system",
            "content": (
                f"You are an assistant that helps extract flight information from user queries. "
                f"Today is {current_date_str}. Extract the following details from the query: "
                "1. location_origin: The departure city or airport, ensure it corresponds to a valid airport code "
                "2. location_destination: The destination city or airport, ensure it corresponds to a valid airport code "
                "3. departure_date: The date of departure "
                "4. adults: The number of adult passengers. (If there is no information regarding this then consider only 1 Adult is there)"
                "If the query specifies a relative date (e.g., 'next Monday'), convert it to an absolute date. "
                "Provide the information in JSON format as follows: "
                '{"location_origin": "origin", "location_destination": "destination", "departure_date": "YYYY-MM-DD", "adults": number_of_adults}'
            )
        },
        {
            "role": "user",
            "content": query
        }
    ]
    
    print(f"\nSending query: {query}")
    print("\nCalling OpenAI API...")
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=300,
            temperature=0.1
        )
        
        print(f"\nResponse object type: {type(response)}")
        print(f"Response has choices: {hasattr(response, 'choices')}")
        if hasattr(response, 'choices'):
            print(f"Number of choices: {len(response.choices)}")
            if response.choices:
                print(f"First choice type: {type(response.choices[0])}")
                print(f"First choice has message: {hasattr(response.choices[0], 'message')}")
                if hasattr(response.choices[0], 'message'):
                    message = response.choices[0].message
                    print(f"Message type: {type(message)}")
                    print(f"Message has content: {hasattr(message, 'content')}")
                    if hasattr(message, 'content'):
                        content = message.content
                        print(f"\nContent type: {type(content)}")
                        print(f"Content value: '{content}'")
                        print(f"Content is None: {content is None}")
                        print(f"Content length: {len(content) if content else 0}")
    except Exception as e:
        print(f"\nERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_flight_extraction()