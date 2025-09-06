#!/usr/bin/env python3

import requests
import json
import time

def test_optimized_travel_api():
    """Test the optimized travel API"""
    
    base_url = "http://localhost:8001"
    
    # Test query
    test_query = "Plan a romantic weekend trip from Bangalore to Goa for 2 adults"
    
    print("🚀 Testing Optimized Travel API")
    print(f"Query: {test_query}")
    print("=" * 50)
    
    # Measure request time
    start_time = time.time()
    
    try:
        response = requests.post(
            f"{base_url}/api/v1/travel/plan-simple",
            json={"query": test_query},
            timeout=60
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"⏱️  Response time: {duration:.2f} seconds")
        print(f"📊 Status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('success'):
                print("✅ SUCCESS: Travel plan created successfully!")
                
                # Print summary
                summary = data.get('summary', {})
                print(f"\n📋 TRIP SUMMARY:")
                print(f"   Route: {summary.get('origin')} → {summary.get('destination')}")
                print(f"   Date: {summary.get('departure_date')}")
                print(f"   Duration: {summary.get('duration_days')} days")
                print(f"   Travelers: {summary.get('travelers')}")
                print(f"   Type: {summary.get('travel_type')}")
                
                # Print flights
                flights = data.get('flights', {})
                outbound = flights.get('outbound', [])
                return_flights = flights.get('return', [])
                print(f"\n✈️  FLIGHTS:")
                print(f"   Outbound options: {len(outbound)}")
                print(f"   Return options: {len(return_flights)}")
                
                # Print hotels
                hotels = data.get('hotels', {})
                hotel_options = hotels.get('options', [])
                print(f"\n🏨 HOTELS:")
                print(f"   Options found: {len(hotel_options)}")
                
                # Print attractions
                attractions = data.get('attractions', {})
                must_visit = attractions.get('must_visit', [])
                dining = attractions.get('dining', [])
                print(f"\n🗺️  ATTRACTIONS & DINING:")
                print(f"   Must visit places: {len(must_visit)}")
                print(f"   Restaurant recommendations: {len(dining)}")
                
                # Print budget
                budget = data.get('budget', {})
                total_cost = budget.get('total', 0)
                print(f"\n💰 BUDGET:")
                print(f"   Total estimated cost: ₹{total_cost:,.0f}")
                print(f"   Per person: ₹{budget.get('per_person', 0):,.0f}")
                
                # Print itinerary
                itinerary = data.get('itinerary', [])
                print(f"\n📅 ITINERARY:")
                print(f"   Days planned: {len(itinerary)}")
                
                print("\n🎉 OPTIMIZATION SUCCESS!")
                print(f"   - Reduced API calls")
                print(f"   - Faster response time: {duration:.1f}s")
                print(f"   - Complete travel package generated")
                
            else:
                print(f"❌ ERROR: {data.get('error', 'Unknown error')}")
                
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.Timeout:
        print("⏰ Request timed out")
    except requests.exceptions.ConnectionError:
        print("🔌 Connection error - is the server running?")
    except Exception as e:
        print(f"💥 Error: {e}")

def test_health_endpoint():
    """Test the health endpoint"""
    try:
        response = requests.get("http://localhost:8001/api/v1/travel/health", timeout=10)
        if response.status_code == 200:
            print("✅ Health check passed")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

if __name__ == "__main__":
    print("🔍 Testing Travel Service Health...")
    if test_health_endpoint():
        print("\n" + "="*50)
        test_optimized_travel_api()
    else:
        print("❌ Cannot test - service is not healthy")