import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv

from app.core.logging import logger
from app.core.config import settings
from app.services.flight_service import FlightService
from app.services.hotel_service import HotelService

load_dotenv()


class OptimizedTravelService:
    """Optimized travel service with reduced API calls and better error handling"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        api_key = settings.OPENAI_API_KEY
        if not api_key:
            logger.error("OPENAI_API_KEY is not set!")
            raise ValueError("OPENAI_API_KEY is required")
        
        logger.info("Initializing OptimizedTravelService (singleton)")
        self.openai_client = OpenAI(api_key=api_key)
        self.flight_service = FlightService()
        self.hotel_service = HotelService()
        OptimizedTravelService._initialized = True
    
    def parse_travel_query_simple(self, query: str) -> Optional[Dict[str, Any]]:
        """Simple travel query parsing with fewer API calls"""
        today = datetime.now()
        current_date_str = today.strftime('%Y-%m-%d')
        
        messages = [
            {
                "role": "system",
                "content": (
                    "Parse travel request and extract: origin_city, destination_city, departure_date (YYYY-MM-DD), "
                    f"travelers (number), travel_type, duration_days. Today is {current_date_str}. "
                    "Convert relative dates. Return JSON only: "
                    '{"origin_city": "string", "destination_city": "string", "departure_date": "YYYY-MM-DD", '
                    '"travelers": number, "travel_type": "string", "duration_days": number}'
                )
            },
            {
                "role": "user",
                "content": query
            }
        ]
        
        try:
            logger.info(f"Parsing travel query: {query}")
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=200,
                temperature=0.1
            )
            
            if response and response.choices:
                response_text = response.choices[0].message.content.strip()
                
                # Clean response
                if "```json" in response_text:
                    start = response_text.find("```json") + 7
                    end = response_text.find("```", start)
                    if end != -1:
                        response_text = response_text[start:end].strip()
                elif response_text.startswith("{") and response_text.endswith("}"):
                    pass  # Already clean JSON
                else:
                    # Extract JSON from text
                    start_idx = response_text.find("{")
                    end_idx = response_text.rfind("}")
                    if start_idx != -1 and end_idx != -1:
                        response_text = response_text[start_idx:end_idx+1]
                
                parsed_info = json.loads(response_text)
                
                # Set defaults
                parsed_info.setdefault('travelers', 1)
                parsed_info.setdefault('travel_type', 'leisure')
                parsed_info.setdefault('duration_days', 1)
                
                # Calculate return date if needed
                if parsed_info.get('duration_days', 0) > 1:
                    try:
                        departure = datetime.strptime(parsed_info['departure_date'], '%Y-%m-%d')
                        return_date = departure + timedelta(days=parsed_info['duration_days'])
                        parsed_info['return_date'] = return_date.strftime('%Y-%m-%d')
                    except:
                        parsed_info['return_date'] = None
                
                logger.info(f"Successfully parsed travel query: {parsed_info}")
                return parsed_info
                
        except Exception as e:
            logger.error(f"Error parsing travel query: {e}")
            return None
    
    def get_simple_attractions(self, city_name: str, travel_type: str = "leisure") -> List[Dict[str, Any]]:
        """Get attractions with single API call"""
        try:
            messages = [
                {
                    "role": "system",
                    "content": (
                        f"List 8 top attractions in {city_name} for {travel_type} travel. "
                        f"Return JSON array with: name, category, description (50 words max), "
                        f"estimated_time (hours), best_time (morning/afternoon/evening). "
                        f"Include mix of popular landmarks, cultural sites, and local experiences."
                    )
                },
                {
                    "role": "user",
                    "content": f"Top attractions in {city_name}"
                }
            ]
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=1500,
                temperature=0.3
            )
            
            if response and response.choices:
                response_text = response.choices[0].message.content.strip()
                
                # Clean response
                if "```json" in response_text:
                    start = response_text.find("```json") + 7
                    end = response_text.find("```", start)
                    if end != -1:
                        response_text = response_text[start:end].strip()
                elif response_text.startswith("[") and response_text.endswith("]"):
                    pass  # Already clean JSON array
                else:
                    # Extract JSON array from text
                    start_idx = response_text.find("[")
                    end_idx = response_text.rfind("]")
                    if start_idx != -1 and end_idx != -1:
                        response_text = response_text[start_idx:end_idx+1]
                
                attractions = json.loads(response_text)
                return attractions if isinstance(attractions, list) else []
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting attractions for {city_name}: {e}")
            return []
    
    def get_dining_recommendations(self, city_name: str) -> List[Dict[str, Any]]:
        """Get dining recommendations with single API call"""
        try:
            messages = [
                {
                    "role": "system",
                    "content": (
                        f"List 6 best restaurants in {city_name}. "
                        f"Return JSON array with: name, cuisine_type, description (40 words max), "
                        f"price_range (budget/moderate/expensive), location_area, meal_type. "
                        f"Include variety of cuisines and price ranges."
                    )
                },
                {
                    "role": "user",
                    "content": f"Best restaurants in {city_name}"
                }
            ]
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=1200,
                temperature=0.3
            )
            
            if response and response.choices:
                response_text = response.choices[0].message.content.strip()
                
                # Clean response
                if "```json" in response_text:
                    start = response_text.find("```json") + 7
                    end = response_text.find("```", start)
                    if end != -1:
                        response_text = response_text[start:end].strip()
                elif response_text.startswith("[") and response_text.endswith("]"):
                    pass
                else:
                    start_idx = response_text.find("[")
                    end_idx = response_text.rfind("]")
                    if start_idx != -1 and end_idx != -1:
                        response_text = response_text[start_idx:end_idx+1]
                
                restaurants = json.loads(response_text)
                return restaurants if isinstance(restaurants, list) else []
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting dining recommendations for {city_name}: {e}")
            return []
    
    def create_simple_itinerary(self, parsed_travel: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create simple day-by-day itinerary with single API call"""
        try:
            duration = parsed_travel['duration_days']
            destination = parsed_travel['destination_city']
            travel_type = parsed_travel.get('travel_type', 'leisure')
            travelers = parsed_travel['travelers']
            
            messages = [
                {
                    "role": "system",
                    "content": (
                        f"Create {duration}-day itinerary for {destination} ({travel_type} trip, {travelers} travelers). "
                        f"Return JSON array with: day_number, date (starting {parsed_travel['departure_date']}), "
                        f"theme, activities (array with time, name, description), "
                        f"meals (breakfast/lunch/dinner locations), budget_estimate (INR), tips. "
                        f"Keep activities realistic and well-timed."
                    )
                },
                {
                    "role": "user",
                    "content": f"Create {duration}-day {travel_type} itinerary for {destination}"
                }
            ]
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=2000,
                temperature=0.4
            )
            
            if response and response.choices:
                response_text = response.choices[0].message.content.strip()
                
                # Clean response
                if "```json" in response_text:
                    start = response_text.find("```json") + 7
                    end = response_text.find("```", start)
                    if end != -1:
                        response_text = response_text[start:end].strip()
                elif response_text.startswith("[") and response_text.endswith("]"):
                    pass
                else:
                    start_idx = response_text.find("[")
                    end_idx = response_text.rfind("]")
                    if start_idx != -1 and end_idx != -1:
                        response_text = response_text[start_idx:end_idx+1]
                
                itinerary = json.loads(response_text)
                return itinerary if isinstance(itinerary, list) else []
            
            return []
            
        except Exception as e:
            logger.error(f"Error creating itinerary: {e}")
            return []
    
    def calculate_simple_budget(self, flights_data: Dict, hotels_data: Dict, parsed_travel: Dict) -> Dict[str, Any]:
        """Calculate budget with fewer API calls"""
        try:
            travelers = parsed_travel['travelers']
            duration = parsed_travel['duration_days']
            
            # Flight costs
            flight_cost = 0
            outbound_flights = flights_data.get('outbound_flights', [])
            return_flights = flights_data.get('return_flights', [])
            
            if outbound_flights:
                cheapest_outbound = min([
                    float(str(f.get('Total Price', '0')).replace(',', '')) 
                    for f in outbound_flights 
                    if f.get('Total Price') and str(f['Total Price']) != 'N/A'
                ] or [0])
                flight_cost += cheapest_outbound * travelers
            
            if return_flights:
                cheapest_return = min([
                    float(str(f.get('Total Price', '0')).replace(',', '')) 
                    for f in return_flights 
                    if f.get('Total Price') and str(f['Total Price']) != 'N/A'
                ] or [0])
                flight_cost += cheapest_return * travelers
            
            # Hotel costs
            hotel_cost = 0
            hotels = hotels_data.get('hotels', [])
            if hotels:
                cheapest_hotel = min([
                    float(str(h.get('Total Price', '0')).replace(',', '')) 
                    for h in hotels 
                    if h.get('Total Price') and str(h['Total Price']) != 'N/A'
                ] or [0])
                hotel_cost = cheapest_hotel * duration
            
            # Estimated daily expenses
            daily_expenses = 3000 * travelers * duration  # 3000 INR per person per day
            transport_cost = 500 * travelers * duration   # 500 INR per person per day
            
            total_cost = flight_cost + hotel_cost + daily_expenses + transport_cost
            
            return {
                'flights': flight_cost,
                'accommodation': hotel_cost,
                'activities_food': daily_expenses,
                'local_transport': transport_cost,
                'total': total_cost,
                'per_person': total_cost / travelers if travelers > 0 else total_cost,
                'currency': 'INR'
            }
            
        except Exception as e:
            logger.error(f"Error calculating budget: {e}")
            return {'total': 0, 'currency': 'INR', 'error': 'Could not calculate budget'}
    
    def create_travel_plan(self, query: str) -> Dict[str, Any]:
        """Main method to create complete travel plan with optimized API calls"""
        logger.info(f"Creating optimized travel plan for query: {query}")
        
        try:
            # Step 1: Parse query
            parsed_travel = self.parse_travel_query_simple(query)
            if not parsed_travel:
                return {
                    'success': False,
                    'error': 'Could not parse travel query. Please provide origin, destination, and travel date.',
                    'data': None
                }
            
            # Step 2: Search flights
            logger.info("Searching flights...")
            flight_query = f"Flight from {parsed_travel['origin_city']} to {parsed_travel['destination_city']} on {parsed_travel['departure_date']} for {parsed_travel['travelers']} adults"
            outbound_df, _, _ = self.flight_service.process_flight_search(flight_query)
            
            outbound_flights = []
            if outbound_df is not None and not outbound_df.empty:
                outbound_flights = outbound_df.head(3).to_dict('records')
            
            # Return flights if duration > 1
            return_flights = []
            if parsed_travel.get('return_date'):
                return_query = f"Flight from {parsed_travel['destination_city']} to {parsed_travel['origin_city']} on {parsed_travel['return_date']} for {parsed_travel['travelers']} adults"
                return_df, _, _ = self.flight_service.process_flight_search(return_query)
                if return_df is not None and not return_df.empty:
                    return_flights = return_df.head(3).to_dict('records')
            
            flights_data = {
                'outbound_flights': outbound_flights,
                'return_flights': return_flights,
                'total_options': len(outbound_flights) + len(return_flights)
            }
            
            # Step 3: Search hotels (simplified)
            logger.info("Searching hotels...")
            try:
                hotel_query = f"Hotels in {parsed_travel['destination_city']} from {parsed_travel['departure_date']} to {parsed_travel.get('return_date', parsed_travel['departure_date'])} for {parsed_travel['travelers']} adults"
                hotels_df, _, _ = self.hotel_service.process_hotel_search(hotel_query)
                
                hotels = []
                if hotels_df is not None and not hotels_df.empty:
                    hotels = hotels_df.head(5).to_dict('records')
                
                hotels_data = {
                    'hotels': hotels,
                    'total_options': len(hotels)
                }
            except Exception as e:
                logger.warning(f"Hotel search failed: {e}, using empty hotel data")
                hotels_data = {'hotels': [], 'total_options': 0}
            
            # Step 4: Get attractions and dining (combined)
            logger.info("Getting attractions and dining...")
            attractions = self.get_simple_attractions(
                parsed_travel['destination_city'], 
                parsed_travel.get('travel_type', 'leisure')
            )
            dining = self.get_dining_recommendations(parsed_travel['destination_city'])
            
            attractions_data = {
                'must_visit': attractions[:5],
                'experiences': [],  # Simplified
                'dining': dining
            }
            
            # Step 5: Create itinerary
            logger.info("Creating itinerary...")
            itinerary = self.create_simple_itinerary(parsed_travel)
            
            # Step 6: Calculate budget
            budget = self.calculate_simple_budget(flights_data, hotels_data, parsed_travel)
            
            # Build response
            result = {
                'success': True,
                'error': None,
                'summary': {
                    'origin': parsed_travel['origin_city'],
                    'destination': parsed_travel['destination_city'],
                    'departure_date': parsed_travel['departure_date'],
                    'return_date': parsed_travel.get('return_date'),
                    'duration_days': parsed_travel['duration_days'],
                    'travelers': parsed_travel['travelers'],
                    'travel_type': parsed_travel['travel_type'],
                    'budget_preference': 'moderate'
                },
                'flights': flights_data,
                'hotels': hotels_data,
                'attractions': attractions_data,
                'itinerary': itinerary,
                'budget': budget,
                'tips': {
                    'best_time_to_visit': 'Check local weather conditions',
                    'what_to_pack': ['Comfortable clothes', 'Travel documents', 'Phone charger'],
                    'safety_tips': 'Keep valuables safe and stay aware of surroundings',
                    'money_tips': 'Carry some cash along with cards',
                    'local_customs': 'Be respectful of local traditions and customs'
                }
            }
            
            logger.info("Successfully created optimized travel plan")
            return result
            
        except Exception as e:
            logger.error(f"Error creating travel plan: {e}")
            return {
                'success': False,
                'error': f"Failed to create travel plan: {str(e)}",
                'data': None
            }