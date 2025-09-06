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
from app.services.attractions_service import AttractionsService
from app.services.travel_parser_service import TravelQueryParser

load_dotenv()


class TravelItineraryService:
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
        
        logger.info("Initializing TravelItineraryService (singleton)")
        self.openai_client = OpenAI(api_key=api_key)
        self.flight_service = None
        self.hotel_service = None
        self.attractions_service = None
        self.travel_parser = None
        TravelItineraryService._initialized = True
    
    def _ensure_services_initialized(self):
        """Lazy initialization of services to avoid circular imports"""
        if self.flight_service is None:
            self.flight_service = FlightService()
        if self.hotel_service is None:
            self.hotel_service = HotelService()
        if self.attractions_service is None:
            self.attractions_service = AttractionsService()
        if self.travel_parser is None:
            self.travel_parser = TravelQueryParser()
    
    def create_complete_itinerary(self, query: str) -> Dict[str, Any]:
        """Create a complete travel itinerary from natural language query"""
        logger.info(f"Creating complete itinerary for query: {query}")
        
        # Ensure all services are initialized
        self._ensure_services_initialized()
        
        # Step 1: Parse the travel query
        parsed_travel = self.travel_parser.parse_travel_query(query)
        if not parsed_travel:
            return {
                'success': False,
                'error': 'Could not parse travel query. Please provide origin, destination, and travel date.',
                'data': None
            }
        
        logger.info(f"Parsed travel data: {parsed_travel}")
        
        # Step 2: Search flights
        flight_preferences = self.travel_parser.extract_flight_preferences(parsed_travel)
        flights_data = self._search_flights(flight_preferences)
        
        # Step 3: Search hotels
        hotel_preferences = self.travel_parser.extract_hotel_preferences(parsed_travel)
        hotels_data = self._search_hotels(hotel_preferences)
        
        # Step 4: Get attractions and activities
        attractions_preferences = self.travel_parser.extract_attractions_preferences(parsed_travel)
        attractions_data = self._get_attractions(attractions_preferences)
        
        # Step 5: Generate day-by-day itinerary
        itinerary_schedule = self._generate_day_by_day_itinerary(
            parsed_travel, attractions_data
        )
        
        # Step 6: Calculate budget estimate
        budget_estimate = self._calculate_budget_estimate(
            flights_data, hotels_data, attractions_data, parsed_travel
        )
        
        # Step 7: Compile complete response
        result = {
            'success': True,
            'error': None,
            'data': {
                'trip_summary': {
                    'origin': parsed_travel['origin_city'],
                    'destination': parsed_travel['destination_city'],
                    'departure_date': parsed_travel['departure_date'],
                    'return_date': parsed_travel.get('return_date'),
                    'duration_days': parsed_travel['duration_days'],
                    'travelers': parsed_travel['travelers'],
                    'travel_type': parsed_travel['travel_type'],
                    'budget_preference': parsed_travel['budget_preference']
                },
                'flights': flights_data,
                'hotels': hotels_data,
                'attractions': attractions_data,
                'daily_itinerary': itinerary_schedule,
                'budget_estimate': budget_estimate,
                'recommendations': self._generate_travel_tips(parsed_travel)
            }
        }
        
        return result
    
    def _search_flights(self, flight_preferences: Dict[str, Any]) -> Dict[str, Any]:
        """Search for flights using flight service"""
        try:
            # Search outbound flights
            outbound_query = f"Flight from {flight_preferences['origin']} to {flight_preferences['destination']} on {flight_preferences['departure_date']} for {flight_preferences['adults']} adults"
            
            outbound_df, origin, destination = self.flight_service.process_flight_search(outbound_query)
            
            outbound_flights = []
            if outbound_df is not None and not outbound_df.empty:
                outbound_flights = outbound_df.head(5).to_dict('records')
            
            # Search return flights if return date is specified
            return_flights = []
            if flight_preferences.get('return_date'):
                return_query = f"Flight from {flight_preferences['destination']} to {flight_preferences['origin']} on {flight_preferences['return_date']} for {flight_preferences['adults']} adults"
                
                return_df, _, _ = self.flight_service.process_flight_search(return_query)
                
                if return_df is not None and not return_df.empty:
                    return_flights = return_df.head(5).to_dict('records')
            
            return {
                'outbound_flights': outbound_flights,
                'return_flights': return_flights,
                'total_options': len(outbound_flights) + len(return_flights)
            }
            
        except Exception as e:
            logger.error(f"Error searching flights: {e}")
            return {'outbound_flights': [], 'return_flights': [], 'total_options': 0}
    
    def _search_hotels(self, hotel_preferences: Dict[str, Any]) -> Dict[str, Any]:
        """Search for hotels using hotel service"""
        try:
            hotel_query = f"Hotels in {hotel_preferences['location']} from {hotel_preferences['check_in_date']} to {hotel_preferences['check_out_date']} for {hotel_preferences['adults']} adults, {hotel_preferences['rooms']} rooms"
            
            hotels_df, location, dates = self.hotel_service.process_hotel_search(hotel_query)
            
            hotels = []
            if hotels_df is not None and not hotels_df.empty:
                hotels = hotels_df.head(10).to_dict('records')
            
            return {
                'hotels': hotels,
                'total_options': len(hotels),
                'location': location,
                'dates': dates
            }
            
        except Exception as e:
            logger.error(f"Error searching hotels: {e}")
            return {'hotels': [], 'total_options': 0}
    
    def _get_attractions(self, attractions_preferences: Dict[str, Any]) -> Dict[str, Any]:
        """Get attractions and activities"""
        try:
            destination = attractions_preferences['destination']
            interests = attractions_preferences['interests']
            
            # Get main attractions
            attractions = self.attractions_service.get_attractions_for_city(destination)
            
            # Get local experiences
            experiences = self.attractions_service.get_local_experiences(destination, interests)
            
            # Get dining recommendations
            dining = self.attractions_service.get_dining_recommendations(destination)
            
            return {
                'attractions': attractions[:8],  # Top 8 attractions
                'experiences': experiences[:6],  # Top 6 experiences
                'dining': dining[:6],  # Top 6 dining options
                'total_options': len(attractions) + len(experiences) + len(dining)
            }
            
        except Exception as e:
            logger.error(f"Error getting attractions: {e}")
            return {'attractions': [], 'experiences': [], 'dining': [], 'total_options': 0}
    
    def _generate_day_by_day_itinerary(self, parsed_travel: Dict[str, Any], 
                                     attractions_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate a detailed day-by-day itinerary"""
        try:
            duration = parsed_travel['duration_days']
            destination = parsed_travel['destination_city']
            interests = parsed_travel.get('interests', ['sightseeing'])
            travel_type = parsed_travel.get('travel_type', 'leisure')
            travelers = parsed_travel['travelers']
            
            attractions = attractions_data.get('attractions', [])
            experiences = attractions_data.get('experiences', [])
            dining = attractions_data.get('dining', [])
            
            messages = [
                {
                    "role": "system",
                    "content": (
                        f"You are an expert travel planner creating a detailed {duration}-day itinerary for {destination}. "
                        f"Travel type: {travel_type}, Travelers: {travelers}, Interests: {', '.join(interests)}. "
                        f"Create a realistic day-by-day schedule with timings. For each day, provide: "
                        f"1. day_number: Day number (1, 2, 3...) "
                        f"2. date: Date in YYYY-MM-DD format "
                        f"3. theme: Daily theme/focus "
                        f"4. activities: List of activities with time, name, description, duration, and type "
                        f"5. meals: Recommended meals with restaurant suggestions "
                        f"6. transportation: How to get around "
                        f"7. budget_estimate: Estimated daily cost in INR "
                        f"8. tips: Practical tips for the day "
                        f"\n"
                        f"Available attractions: {[a.get('name', 'Unknown') for a in attractions[:10]]} "
                        f"Available experiences: {[e.get('name', 'Unknown') for e in experiences[:6]]} "
                        f"Available dining: {[d.get('name', 'Unknown') for d in dining[:6]]} "
                        f"\n"
                        f"Return as JSON array of day objects."
                    )
                },
                {
                    "role": "user",
                    "content": (
                        f"Create a {duration}-day itinerary for {destination} starting from {parsed_travel['departure_date']}. "
                        f"Focus on {', '.join(interests)} and {travel_type} travel style."
                    )
                }
            ]
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=3000,
                temperature=0.4
            )
            
            if response and response.choices:
                response_text = response.choices[0].message.content.strip()
                
                # Handle markdown code blocks
                if "```json" in response_text:
                    start = response_text.find("```json") + 7
                    end = response_text.find("```", start)
                    if end != -1:
                        response_text = response_text[start:end].strip()
                elif "```" in response_text:
                    start = response_text.find("```") + 3
                    end = response_text.find("```", start)
                    if end != -1:
                        response_text = response_text[start:end].strip()
                
                if response_text and not response_text.startswith("["):
                    start_idx = response_text.find("[")
                    end_idx = response_text.rfind("]")
                    if start_idx != -1 and end_idx != -1:
                        response_text = response_text[start_idx:end_idx+1]
                
                itinerary = json.loads(response_text)
                return itinerary if isinstance(itinerary, list) else []
            
            return []
            
        except Exception as e:
            logger.error(f"Error generating day-by-day itinerary: {e}")
            return []
    
    def _calculate_budget_estimate(self, flights_data: Dict[str, Any], 
                                 hotels_data: Dict[str, Any], 
                                 attractions_data: Dict[str, Any], 
                                 parsed_travel: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate estimated budget for the trip"""
        try:
            travelers = parsed_travel['travelers']
            duration = parsed_travel['duration_days']
            
            # Flight costs
            flight_cost = 0
            outbound_flights = flights_data.get('outbound_flights', [])
            return_flights = flights_data.get('return_flights', [])
            
            if outbound_flights:
                # Get cheapest flight and multiply by travelers
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
                # Get cheapest hotel per night
                cheapest_hotel = min([
                    float(str(h.get('Total Price', '0')).replace(',', '')) 
                    for h in hotels 
                    if h.get('Total Price') and str(h['Total Price']) != 'N/A'
                ] or [0])
                hotel_cost = cheapest_hotel * duration
            
            # Activities and food estimate
            budget_pref = parsed_travel.get('budget_preference', 'moderate')
            daily_expenses = {
                'budget': 2000,    # 2000 INR per person per day
                'moderate': 4000,  # 4000 INR per person per day
                'luxury': 8000     # 8000 INR per person per day
            }
            
            activity_food_cost = daily_expenses.get(budget_pref, 4000) * travelers * duration
            
            # Local transportation estimate
            transport_cost = 500 * travelers * duration  # 500 INR per person per day
            
            total_cost = flight_cost + hotel_cost + activity_food_cost + transport_cost
            
            return {
                'flights': flight_cost,
                'accommodation': hotel_cost,
                'activities_food': activity_food_cost,
                'local_transport': transport_cost,
                'total': total_cost,
                'per_person': total_cost / travelers,
                'currency': 'INR',
                'breakdown': {
                    'flights_percentage': (flight_cost / total_cost * 100) if total_cost > 0 else 0,
                    'accommodation_percentage': (hotel_cost / total_cost * 100) if total_cost > 0 else 0,
                    'activities_food_percentage': (activity_food_cost / total_cost * 100) if total_cost > 0 else 0,
                    'transport_percentage': (transport_cost / total_cost * 100) if total_cost > 0 else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error calculating budget estimate: {e}")
            return {'total': 0, 'currency': 'INR', 'error': 'Could not calculate budget'}
    
    def _generate_travel_tips(self, parsed_travel: Dict[str, Any]) -> Dict[str, Any]:
        """Generate travel tips and recommendations"""
        try:
            destination = parsed_travel['destination_city']
            travel_type = parsed_travel.get('travel_type', 'leisure')
            duration = parsed_travel['duration_days']
            
            messages = [
                {
                    "role": "system",
                    "content": (
                        f"You are a local travel expert for {destination}. Provide practical travel tips and recommendations "
                        f"for a {duration}-day {travel_type} trip. Include: "
                        f"1. best_time_to_visit: Weather and seasonal info "
                        f"2. what_to_pack: Essential items to pack "
                        f"3. local_customs: Cultural etiquette and customs "
                        f"4. transportation_tips: How to get around the city "
                        f"5. safety_tips: Safety and security advice "
                        f"6. money_tips: Currency, tipping, and payment methods "
                        f"7. language_tips: Common phrases and language info "
                        f"8. emergency_contacts: Important phone numbers "
                        f"Provide concise, practical advice in JSON format."
                    )
                },
                {
                    "role": "user",
                    "content": f"Give me travel tips for {destination}"
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
                
                # Handle markdown code blocks
                if "```json" in response_text:
                    start = response_text.find("```json") + 7
                    end = response_text.find("```", start)
                    if end != -1:
                        response_text = response_text[start:end].strip()
                elif "```" in response_text:
                    start = response_text.find("```") + 3
                    end = response_text.find("```", start)
                    if end != -1:
                        response_text = response_text[start:end].strip()
                
                if response_text and not response_text.startswith("{"):
                    start_idx = response_text.find("{")
                    end_idx = response_text.rfind("}")
                    if start_idx != -1 and end_idx != -1:
                        response_text = response_text[start_idx:end_idx+1]
                
                tips = json.loads(response_text)
                return tips if isinstance(tips, dict) else {}
            
            return {}
            
        except Exception as e:
            logger.error(f"Error generating travel tips: {e}")
            return {}