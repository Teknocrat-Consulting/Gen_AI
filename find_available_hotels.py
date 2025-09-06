#!/usr/bin/env python3
"""
Script to find hotels with actual availability in Amadeus API
"""
import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from amadeus import Client, ResponseError
from app.core.config import settings

def find_available_hotels(city_code="GOI", max_attempts=50):
    """Find hotels that actually have availability"""
    
    amadeus = Client(
        client_id=settings.API_Key,
        client_secret=settings.API_Secret
    )
    
    print(f"\nSearching for available hotels in {city_code}...")
    print("=" * 60)
    
    # Get list of hotels
    try:
        response = amadeus.reference_data.locations.hotels.by_city.get(
            cityCode=city_code
        )
        if not response.data:
            print(f"No hotels found for {city_code}")
            return []
            
        hotel_ids = [h['hotelId'] for h in response.data]
        print(f"Found {len(hotel_ids)} hotels in {city_code}")
        
    except Exception as e:
        print(f"Error getting hotel list: {e}")
        return []
    
    # Test different date ranges
    date_ranges = [
        (30, 32, "1 month out"),
        (45, 47, "1.5 months out"),
        (60, 62, "2 months out"),
        (90, 92, "3 months out")
    ]
    
    available_hotels = []
    
    for days_start, days_end, desc in date_ranges:
        check_in = (datetime.now() + timedelta(days=days_start)).strftime("%Y-%m-%d")
        check_out = (datetime.now() + timedelta(days=days_end)).strftime("%Y-%m-%d")
        
        print(f"\nTrying dates {desc}: {check_in} to {check_out}")
        print("-" * 40)
        
        tested = 0
        batch_size = 1  # Test one at a time to identify working hotels
        
        for i in range(0, min(len(hotel_ids), max_attempts), batch_size):
            hotel_id = hotel_ids[i]
            tested += 1
            
            try:
                response = amadeus.shopping.hotel_offers_search.get(
                    hotelIds=[hotel_id],
                    checkInDate=check_in,
                    checkOutDate=check_out,
                    adults=1,
                    roomQuantity=1
                )
                
                if response.data and len(response.data) > 0:
                    hotel_data = response.data[0]
                    hotel_name = hotel_data.get('hotel', {}).get('name', 'Unknown')
                    
                    if hotel_data.get('offers'):
                        offer = hotel_data['offers'][0]
                        price = offer.get('price', {})
                        total = price.get('total', 'N/A')
                        currency = price.get('currency', '')
                        
                        print(f"✅ AVAILABLE: {hotel_id}")
                        print(f"   Name: {hotel_name}")
                        print(f"   Price: {total} {currency}")
                        
                        available_hotels.append({
                            'hotel_id': hotel_id,
                            'name': hotel_name,
                            'check_in': check_in,
                            'check_out': check_out,
                            'price': f"{total} {currency}"
                        })
                        
                        # Stop after finding 5 available hotels
                        if len(available_hotels) >= 5:
                            break
                
            except ResponseError as e:
                # Silently skip hotels with errors
                pass
            except Exception as e:
                print(f"Error testing {hotel_id}: {str(e)[:50]}")
        
        print(f"\nTested {tested} hotels, found {len(available_hotels)} with availability")
        
        if len(available_hotels) >= 5:
            break
    
    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY OF AVAILABLE HOTELS")
    print("=" * 60)
    
    if available_hotels:
        print(f"\nFound {len(available_hotels)} hotels with confirmed availability:\n")
        for i, hotel in enumerate(available_hotels, 1):
            print(f"{i}. {hotel['name']} ({hotel['hotel_id']})")
            print(f"   Dates: {hotel['check_in']} to {hotel['check_out']}")
            print(f"   Price: {hotel['price']}\n")
        
        # Save working hotel IDs
        working_ids = [h['hotel_id'] for h in available_hotels]
        print(f"Working Hotel IDs for {city_code}: {', '.join(working_ids)}")
        
        return available_hotels
    else:
        print("❌ No hotels with availability found")
        print("This might be due to:")
        print("• Test environment limitations")
        print("• Need to try dates further in the future")
        print("• Rate limiting")
        return []

if __name__ == "__main__":
    # Test different cities
    test_cities = ["GOI", "BOM", "DEL"]
    
    all_available = {}
    for city in test_cities:
        print(f"\n{'#' * 70}")
        print(f"# Testing {city}")
        print(f"{'#' * 70}")
        
        available = find_available_hotels(city, max_attempts=30)
        if available:
            all_available[city] = available
    
    # Final summary
    print("\n" + "=" * 70)
    print("FINAL RESULTS")
    print("=" * 70)
    
    if all_available:
        print("\nCities with available hotels:")
        for city, hotels in all_available.items():
            print(f"\n{city}: {len(hotels)} hotels found")
            print(f"  Sample: {hotels[0]['name'] if hotels else 'None'}")
    else:
        print("\n❌ No available hotels found in any test city")
        print("The Amadeus test environment may have limited availability data")