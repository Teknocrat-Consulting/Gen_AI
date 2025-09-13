#!/usr/bin/env python3
"""
Direct test of Amadeus Hotel API to understand what works and what doesn't.
Testing 5 different locations with various API approaches.
"""

import os
import sys
sys.path.append('/home/vineet/Desktop/projects/booking_agent/Gen_AI')

from amadeus import Client, ResponseError
from datetime import datetime, timedelta
import json
from app.core.config import settings

# Initialize Amadeus client
amadeus = Client(
    client_id=settings.API_Key,
    client_secret=settings.API_Secret
)

def test_location(city_name, city_code, lat, lon):
    """Test different API approaches for a single location"""
    print(f"\n{'='*60}")
    print(f"TESTING: {city_name} ({city_code})")
    print(f"Coordinates: {lat}, {lon}")
    print(f"{'='*60}")

    # Test dates (7 days from now for 2 nights)
    check_in = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
    check_out = (datetime.now() + timedelta(days=9)).strftime('%Y-%m-%d')

    results = {
        'city': city_name,
        'city_code': city_code,
        'coordinates': (lat, lon),
        'dates': (check_in, check_out),
        'tests': {}
    }

    # TEST 1: Hotel List by City Code
    print(f"\n1. Testing Hotel List by City Code: {city_code}")
    try:
        response = amadeus.reference_data.locations.hotels.by_city.get(cityCode=city_code)
        if response.data:
            hotel_count = len(response.data)
            print(f"   ✅ SUCCESS: Found {hotel_count} hotels")
            results['tests']['by_city'] = {
                'status': 'success',
                'count': hotel_count,
                'sample_hotels': [h.get('hotelId') for h in response.data[:3]]
            }
        else:
            print(f"   ❌ FAILED: No hotels found")
            results['tests']['by_city'] = {'status': 'no_data'}
    except ResponseError as e:
        print(f"   ❌ ERROR: {e}")
        results['tests']['by_city'] = {'status': 'error', 'message': str(e)}

    # TEST 2: Hotel List by Geocode
    print(f"\n2. Testing Hotel List by Geocode: {lat}, {lon}")
    try:
        response = amadeus.reference_data.locations.hotels.by_geocode.get(
            latitude=lat, longitude=lon, radius=20, radiusUnit='KM'
        )
        if response.data:
            hotel_count = len(response.data)
            print(f"   ✅ SUCCESS: Found {hotel_count} hotels")
            results['tests']['by_geocode'] = {
                'status': 'success',
                'count': hotel_count,
                'sample_hotels': [h.get('hotelId') for h in response.data[:3]]
            }
        else:
            print(f"   ❌ FAILED: No hotels found")
            results['tests']['by_geocode'] = {'status': 'no_data'}
    except ResponseError as e:
        print(f"   ❌ ERROR: {e}")
        results['tests']['by_geocode'] = {'status': 'error', 'message': str(e)}

    # TEST 3: Direct Hotel Offers Search with Coordinates
    print(f"\n3. Testing Hotel Offers Search with Coordinates")
    try:
        response = amadeus.shopping.hotel_offers_search.get(
            latitude=lat,
            longitude=lon,
            radius=20,
            radiusUnit='KM',
            checkInDate=check_in,
            checkOutDate=check_out,
            adults=1,
            roomQuantity=1,
            currency='INR'
        )
        if response.data:
            offer_count = len(response.data)
            print(f"   ✅ SUCCESS: Found {offer_count} hotel offers")
            # Get sample pricing
            sample_prices = []
            for offer in response.data[:3]:
                hotel_name = offer.get('hotel', {}).get('name', 'Unknown')
                price = offer.get('offers', [{}])[0].get('price', {}).get('total', 'N/A')
                sample_prices.append(f"{hotel_name}: {price}")

            results['tests']['offers_search_coords'] = {
                'status': 'success',
                'count': offer_count,
                'sample_prices': sample_prices
            }
        else:
            print(f"   ❌ FAILED: No offers found")
            results['tests']['offers_search_coords'] = {'status': 'no_data'}
    except ResponseError as e:
        print(f"   ❌ ERROR: {e}")
        results['tests']['offers_search_coords'] = {'status': 'error', 'message': str(e)}

    # TEST 4: Hotel Offers Search by City Code (if supported)
    print(f"\n4. Testing Hotel Offers Search by City Code")
    try:
        response = amadeus.shopping.hotel_offers_search.get(
            cityCode=city_code,
            checkInDate=check_in,
            checkOutDate=check_out,
            adults=1,
            roomQuantity=1,
            currency='INR'
        )
        if response.data:
            offer_count = len(response.data)
            print(f"   ✅ SUCCESS: Found {offer_count} hotel offers")
            results['tests']['offers_search_city'] = {
                'status': 'success',
                'count': offer_count
            }
        else:
            print(f"   ❌ FAILED: No offers found")
            results['tests']['offers_search_city'] = {'status': 'no_data'}
    except ResponseError as e:
        print(f"   ❌ ERROR: {e}")
        results['tests']['offers_search_city'] = {'status': 'error', 'message': str(e)}

    # TEST 5: Two-step approach (get hotels, then offers)
    print(f"\n5. Testing Two-step approach (Hotel List → Hotel Offers)")
    try:
        # Step 1: Get hotels
        hotel_response = amadeus.reference_data.locations.hotels.by_geocode.get(
            latitude=lat, longitude=lon, radius=20, radiusUnit='KM'
        )

        if hotel_response.data and len(hotel_response.data) > 0:
            # Get first 3 hotel IDs
            hotel_ids = [h.get('hotelId') for h in hotel_response.data[:3]]
            print(f"   Step 1: Got {len(hotel_ids)} hotel IDs")

            # Step 2: Get offers for these hotels
            offers_response = amadeus.shopping.hotel_offers_search.get(
                hotelIds=hotel_ids,
                checkInDate=check_in,
                checkOutDate=check_out,
                adults=1,
                roomQuantity=1,
                currency='INR'
            )

            if offers_response.data:
                offer_count = len(offers_response.data)
                print(f"   Step 2: ✅ SUCCESS: Found {offer_count} offers")
                results['tests']['two_step'] = {
                    'status': 'success',
                    'hotels_found': len(hotel_response.data),
                    'offers_found': offer_count
                }
            else:
                print(f"   Step 2: ❌ No offers found for hotels")
                results['tests']['two_step'] = {'status': 'no_offers'}
        else:
            print(f"   Step 1: ❌ No hotels found")
            results['tests']['two_step'] = {'status': 'no_hotels'}

    except ResponseError as e:
        print(f"   ❌ ERROR: {e}")
        results['tests']['two_step'] = {'status': 'error', 'message': str(e)}

    return results

def main():
    """Test 5 different locations"""
    print("AMADEUS HOTEL API COMPREHENSIVE TEST")
    print("Testing 5 locations with multiple API approaches")

    # Test locations with their coordinates
    test_locations = [
        ("Delhi", "DEL", 28.7041, 77.1025),
        ("Mumbai", "BOM", 19.0760, 72.8777),
        ("Bangalore", "BLR", 12.9716, 77.5946),
        ("Goa", "GOI", 15.2993, 74.1240),
        ("London", "LON", 51.5074, -0.1278),
    ]

    all_results = []

    for city_name, city_code, lat, lon in test_locations:
        result = test_location(city_name, city_code, lat, lon)
        all_results.append(result)

    # SUMMARY
    print(f"\n\n{'='*80}")
    print("COMPREHENSIVE ANALYSIS")
    print(f"{'='*80}")

    for result in all_results:
        city = result['city']
        print(f"\n{city.upper()}:")

        for test_name, test_result in result['tests'].items():
            status = test_result.get('status')
            if status == 'success':
                count = test_result.get('count', 0)
                print(f"  ✅ {test_name}: {count} results")
            elif status == 'no_data':
                print(f"  ⚠️  {test_name}: No data")
            elif status == 'error':
                error_msg = test_result.get('message', 'Unknown error')
                print(f"  ❌ {test_name}: {error_msg}")
            else:
                print(f"  ❓ {test_name}: {status}")

    # RECOMMENDATIONS
    print(f"\n\n{'='*80}")
    print("RECOMMENDATIONS")
    print(f"{'='*80}")

    # Analyze which approach works best
    approach_success = {}
    for result in all_results:
        for test_name, test_result in result['tests'].items():
            if test_name not in approach_success:
                approach_success[test_name] = {'success': 0, 'total': 0}

            approach_success[test_name]['total'] += 1
            if test_result.get('status') == 'success':
                approach_success[test_name]['success'] += 1

    print("\nSuccess rates by approach:")
    for approach, stats in approach_success.items():
        success_rate = (stats['success'] / stats['total']) * 100
        print(f"  {approach}: {stats['success']}/{stats['total']} ({success_rate:.1f}%)")

    # Find best approach
    best_approach = max(approach_success.items(),
                       key=lambda x: x[1]['success'])
    print(f"\n🏆 BEST APPROACH: {best_approach[0]}")
    print(f"   Success rate: {best_approach[1]['success']}/{best_approach[1]['total']}")

if __name__ == "__main__":
    main()