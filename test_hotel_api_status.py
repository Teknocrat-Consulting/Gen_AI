#!/usr/bin/env python3
"""
Comprehensive test script to check Amadeus Hotel API status
"""
import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
import json

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

from amadeus import Client, ResponseError
from app.core.config import settings
from app.core.logging import logger

class HotelAPITester:
    def __init__(self):
        self.amadeus = Client(
            client_id=settings.API_Key,
            client_secret=settings.API_Secret
        )
        self.test_results = []
        
    def print_header(self, text):
        print("\n" + "=" * 70)
        print(f" {text}")
        print("=" * 70)
        
    def print_test(self, test_name):
        print(f"\n[TEST] {test_name}")
        print("-" * 50)
        
    def test_auth(self):
        """Test if authentication is working"""
        self.print_test("Authentication Test")
        try:
            # Try a simple API call to verify authentication
            response = self.amadeus.reference_data.locations.get(
                keyword="Mumbai",
                subType='CITY'
            )
            if response.data:
                print("✅ Authentication successful")
                print(f"   Client ID: {settings.API_Key[:10]}...")
                self.test_results.append(("Authentication", "PASS"))
                return True
            else:
                print("❌ Authentication failed - no response")
                self.test_results.append(("Authentication", "FAIL"))
                return False
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            self.test_results.append(("Authentication", "ERROR"))
            return False
    
    def test_city_codes(self):
        """Test city code lookup"""
        self.print_test("City Code Lookup Test")
        
        test_cities = ["Mumbai", "Delhi", "Goa", "Bangalore", "Dubai"]
        success_count = 0
        
        for city in test_cities:
            try:
                response = self.amadeus.reference_data.locations.get(
                    keyword=city,
                    subType='CITY'
                )
                if response.data:
                    code = response.data[0]['iataCode']
                    print(f"✅ {city}: {code}")
                    success_count += 1
                else:
                    print(f"❌ {city}: No code found")
            except Exception as e:
                print(f"❌ {city}: Error - {str(e)[:50]}")
        
        result = "PASS" if success_count == len(test_cities) else "PARTIAL"
        self.test_results.append(("City Code Lookup", f"{result} ({success_count}/{len(test_cities)})"))
        return success_count > 0
    
    def test_hotel_list_by_city(self):
        """Test getting hotel lists by city"""
        self.print_test("Hotel List by City Test")
        
        test_cities = [
            ("BOM", "Mumbai"),
            ("DEL", "Delhi"),
            ("GOI", "Goa"),
            ("DXB", "Dubai")
        ]
        
        success_count = 0
        
        for city_code, city_name in test_cities:
            try:
                response = self.amadeus.reference_data.locations.hotels.by_city.get(
                    cityCode=city_code
                )
                if response.data:
                    hotel_count = len(response.data)
                    print(f"✅ {city_name} ({city_code}): Found {hotel_count} hotels")
                    if hotel_count > 0:
                        # Show first 3 hotel IDs
                        sample_ids = [h['hotelId'] for h in response.data[:3]]
                        print(f"   Sample IDs: {', '.join(sample_ids)}")
                    success_count += 1
                else:
                    print(f"❌ {city_name} ({city_code}): No hotels found")
            except ResponseError as e:
                print(f"❌ {city_name} ({city_code}): API Error - {e.code if hasattr(e, 'code') else str(e)[:50]}")
            except Exception as e:
                print(f"❌ {city_name} ({city_code}): Error - {str(e)[:50]}")
        
        result = "PASS" if success_count == len(test_cities) else f"PARTIAL ({success_count}/{len(test_cities)})"
        self.test_results.append(("Hotel List by City", result))
        return success_count > 0
    
    def test_hotel_offers(self):
        """Test getting hotel offers with availability"""
        self.print_test("Hotel Offers Search Test")
        
        # Test with different date ranges
        date_ranges = [
            ("Tomorrow", 1, 3),
            ("Next Week", 7, 9),
            ("Two Weeks", 14, 16),
            ("One Month", 30, 32),
            ("Two Months", 60, 62)
        ]
        
        # First get some hotel IDs from Goa
        try:
            response = self.amadeus.reference_data.locations.hotels.by_city.get(
                cityCode="GOI"
            )
            if not response.data:
                print("❌ Cannot get hotel list for testing")
                self.test_results.append(("Hotel Offers Search", "FAIL - No hotels"))
                return False
                
            hotel_ids = [h['hotelId'] for h in response.data[:10]]
            print(f"Testing with {len(hotel_ids)} hotels from Goa")
            
        except Exception as e:
            print(f"❌ Error getting hotel list: {e}")
            self.test_results.append(("Hotel Offers Search", "ERROR"))
            return False
        
        success_count = 0
        
        for date_name, days_ahead_start, days_ahead_end in date_ranges:
            check_in = (datetime.now() + timedelta(days=days_ahead_start)).strftime("%Y-%m-%d")
            check_out = (datetime.now() + timedelta(days=days_ahead_end)).strftime("%Y-%m-%d")
            
            print(f"\n  Testing {date_name}: {check_in} to {check_out}")
            
            # Try with batches of 3 hotels
            found_offers = False
            for i in range(0, min(len(hotel_ids), 9), 3):
                batch = hotel_ids[i:i+3]
                try:
                    response = self.amadeus.shopping.hotel_offers_search.get(
                        hotelIds=batch,
                        checkInDate=check_in,
                        checkOutDate=check_out,
                        adults=1,
                        roomQuantity=1
                    )
                    
                    if response.data:
                        print(f"  ✅ Found {len(response.data)} offers for batch {i//3 + 1}")
                        # Show first offer details
                        if response.data[0].get('hotel'):
                            hotel_name = response.data[0]['hotel'].get('name', 'Unknown')
                            if response.data[0].get('offers'):
                                price = response.data[0]['offers'][0].get('price', {})
                                total = price.get('total', 'N/A')
                                currency = price.get('currency', '')
                                print(f"     Sample: {hotel_name} - {total} {currency}")
                        found_offers = True
                        success_count += 1
                        break
                    
                except ResponseError as e:
                    error_msg = str(e)[:100]
                    if "NO ROOMS AVAILABLE" in error_msg or "INVALID PROPERTY" in error_msg:
                        continue  # Try next batch
                    else:
                        print(f"  ⚠️  API Error for batch {i//3 + 1}: {error_msg}")
                except Exception as e:
                    print(f"  ❌ Error for batch {i//3 + 1}: {str(e)[:50]}")
            
            if not found_offers:
                print(f"  ❌ No offers found for {date_name}")
        
        result = f"PASS ({success_count}/{len(date_ranges)} date ranges)"
        self.test_results.append(("Hotel Offers Search", result))
        return success_count > 0
    
    def test_hotel_by_coordinates(self):
        """Test hotel search by coordinates"""
        self.print_test("Hotel Search by Coordinates Test")
        
        locations = [
            ("Mumbai", 19.0760, 72.8777),
            ("Goa", 15.2993, 74.1240),
            ("Delhi", 28.7041, 77.1025)
        ]
        
        success_count = 0
        
        for city_name, lat, lon in locations:
            try:
                response = self.amadeus.reference_data.locations.hotels.by_geocode.get(
                    latitude=lat,
                    longitude=lon,
                    radius=5,
                    radiusUnit='KM'
                )
                
                if response.data:
                    hotel_count = len(response.data)
                    print(f"✅ {city_name} ({lat}, {lon}): Found {hotel_count} hotels")
                    success_count += 1
                else:
                    print(f"❌ {city_name}: No hotels found")
                    
            except Exception as e:
                print(f"❌ {city_name}: Error - {str(e)[:50]}")
        
        result = f"PASS ({success_count}/{len(locations)})" if success_count > 0 else "FAIL"
        self.test_results.append(("Hotel by Coordinates", result))
        return success_count > 0
    
    def run_all_tests(self):
        """Run all tests and provide summary"""
        self.print_header("AMADEUS HOTEL API STATUS CHECK")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"API Endpoint: {self.amadeus.host}")
        
        # Run tests
        tests = [
            self.test_auth,
            self.test_city_codes,
            self.test_hotel_list_by_city,
            self.test_hotel_offers,
            self.test_hotel_by_coordinates
        ]
        
        for test in tests:
            try:
                test()
            except Exception as e:
                print(f"❌ Test crashed: {e}")
        
        # Print summary
        self.print_header("TEST SUMMARY")
        
        print("\nResults:")
        for test_name, result in self.test_results:
            status_icon = "✅" if "PASS" in result else "⚠️" if "PARTIAL" in result else "❌"
            print(f"{status_icon} {test_name}: {result}")
        
        # Overall status
        pass_count = sum(1 for _, r in self.test_results if "PASS" in r or "PARTIAL" in r)
        total_count = len(self.test_results)
        
        print(f"\nOverall: {pass_count}/{total_count} tests working")
        
        if pass_count == total_count:
            print("✅ All hotel APIs are working properly!")
        elif pass_count > 0:
            print("⚠️ Some hotel APIs are working, but there are issues")
        else:
            print("❌ Hotel APIs are not working properly")
        
        # Recommendations
        self.print_header("RECOMMENDATIONS")
        
        if pass_count < total_count:
            print("Issues detected:")
            for test_name, result in self.test_results:
                if "FAIL" in result or "ERROR" in result:
                    print(f"• Fix {test_name}: {result}")
        
        print("\nCommon issues and solutions:")
        print("• 'NO ROOMS AVAILABLE': Try dates further in the future (30+ days)")
        print("• 'INVALID PROPERTY': Some hotel IDs may be outdated")
        print("• Rate limits: Use smaller batches (3 hotels at a time)")
        print("• Authentication errors: Check API keys in .env file")

if __name__ == "__main__":
    tester = HotelAPITester()
    tester.run_all_tests()