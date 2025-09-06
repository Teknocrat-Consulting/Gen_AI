#!/usr/bin/env python3
"""
Test script to diagnose hotel search issues
"""
import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

from app.services.hotel_service import HotelService
from app.core.logging import logger

def test_hotel_search():
    """Test hotel search with different scenarios"""
    
    print("=" * 60)
    print("HOTEL API TEST DIAGNOSTIC")
    print("=" * 60)
    
    service = HotelService()
    
    # Test 1: Search for Goa hotels with different date ranges
    print("\n1. Testing Goa hotel search with different date ranges:")
    print("-" * 50)
    
    test_cases = [
        {
            "name": "Immediate dates (likely to fail)",
            "city": "Goa",
            "check_in": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
            "check_out": (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
        },
        {
            "name": "This weekend",
            "city": "Goa", 
            "check_in": "2025-09-13",
            "check_out": "2025-09-16"
        },
        {
            "name": "Further out dates (2 weeks)",
            "city": "Goa",
            "check_in": (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d"),
            "check_out": (datetime.now() + timedelta(days=17)).strftime("%Y-%m-%d")
        },
        {
            "name": "Further out dates (1 month)",
            "city": "Goa",
            "check_in": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
            "check_out": (datetime.now() + timedelta(days=33)).strftime("%Y-%m-%d")
        }
    ]
    
    for test in test_cases:
        print(f"\nTest: {test['name']}")
        print(f"City: {test['city']}, Check-in: {test['check_in']}, Check-out: {test['check_out']}")
        
        # Get city code
        city_code = service.get_city_code(test['city'])
        print(f"City code: {city_code}")
        
        if city_code:
            # Search hotels
            hotels = service.search_hotels_by_city(
                city_code=city_code,
                check_in=test['check_in'],
                check_out=test['check_out'],
                adults=2,
                rooms=1
            )
            
            print(f"Results: Found {len(hotels)} hotel offers")
            
            if hotels and len(hotels) > 0:
                # Show first hotel details
                first_hotel = hotels[0]
                hotel_info = first_hotel.get('hotel', {})
                print(f"Sample Hotel: {hotel_info.get('name', 'Unknown')}")
                
                if first_hotel.get('offers'):
                    first_offer = first_hotel['offers'][0]
                    price = first_offer.get('price', {})
                    print(f"Price: {price.get('total', 'N/A')} {price.get('currency', '')}")
    
    # Test 2: Try with coordinate-based search for Goa
    print("\n" + "=" * 60)
    print("2. Testing coordinate-based search for Goa:")
    print("-" * 50)
    
    # Goa coordinates
    goa_lat, goa_lon = 15.2993, 74.1240
    
    hotels_by_coords = service.search_hotels_by_location(
        latitude=goa_lat,
        longitude=goa_lon,
        radius=20,  # 20km radius
        check_in=(datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d"),
        check_out=(datetime.now() + timedelta(days=17)).strftime("%Y-%m-%d"),
        adults=2,
        rooms=1
    )
    
    print(f"Found {len(hotels_by_coords)} hotels by coordinates")
    
    # Test 3: Check the actual query interpretation
    print("\n" + "=" * 60)
    print("3. Testing query interpretation:")
    print("-" * 50)
    
    test_queries = [
        "Hotels in Goa for this weekend",
        "Hotels in delhi to Goa for this weekend",  # This is confusing - is it Delhi or Goa?
        "Hotels in Goa from September 13 to 16",
        "Find hotels in Mumbai for tomorrow"
    ]
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        result = service.extract_hotel_info_from_query(query)
        if result:
            print(f"Extracted location: {result.get('location')}")
            print(f"Check-in: {result.get('check_in_date')}")
            print(f"Check-out: {result.get('check_out_date')}")
        else:
            print("Failed to extract hotel info")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    test_hotel_search()