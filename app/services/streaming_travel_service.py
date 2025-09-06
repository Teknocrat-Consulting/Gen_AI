import json
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, AsyncGenerator
from openai import OpenAI
from dotenv import load_dotenv

from app.core.logging import logger
from app.core.config import settings
from app.services.flight_service import FlightService
from app.services.hotel_service import HotelService

load_dotenv()


class StreamingTravelService:
    """Travel service with streaming support for real-time updates"""
    
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
        
        logger.info("Initializing StreamingTravelService (singleton)")
        self.openai_client = OpenAI(api_key=api_key)
        self.flight_service = FlightService()
        self.hotel_service = HotelService()
        StreamingTravelService._initialized = True
    
    async def stream_travel_plan(self, query: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream travel plan components as they become available"""
        
        try:
            # Step 1: Parse query and stream immediately
            logger.info(f"Starting streaming travel plan for: {query}")
            yield {"type": "status", "message": "Analyzing your travel request...", "progress": 5}
            
            parsed_travel = await self._parse_travel_query_async(query)
            if not parsed_travel:
                yield {"type": "error", "message": "Could not understand your travel request. Please provide origin, destination, and dates."}
                return
            
            # Check if origin city is missing
            if not parsed_travel.get('origin_city') or parsed_travel.get('origin_city') == 'NOT_SPECIFIED' or parsed_travel.get('origin_city') == '':
                yield {
                    "type": "error", 
                    "message": "Please specify your departure city. For example: 'I want to go from Mumbai to Rajasthan' or 'Flight from Delhi to Jaipur'.",
                    "needs_origin": True
                }
                return
            
            # Stream parsed summary
            yield {
                "type": "summary",
                "data": {
                    "origin": parsed_travel['origin_city'],
                    "destination": parsed_travel['destination_city'],
                    "departure_date": parsed_travel['departure_date'],
                    "return_date": parsed_travel.get('return_date'),
                    "duration_days": parsed_travel['duration_days'],
                    "travelers": parsed_travel['travelers'],
                    "travel_type": parsed_travel['travel_type']
                },
                "progress": 15
            }
            
            # Step 2: Search flights (async)
            yield {"type": "status", "message": "Searching for best flights...", "progress": 20}
            
            flight_task = asyncio.create_task(self._search_flights_async(parsed_travel))
            
            # Step 3: Search hotels (parallel with flights)
            yield {"type": "status", "message": "Finding accommodation options...", "progress": 30}
            
            hotel_task = asyncio.create_task(self._search_hotels_async(parsed_travel))
            
            # Step 4: Get attractions (parallel)
            yield {"type": "status", "message": "Discovering attractions and experiences...", "progress": 40}
            
            attractions_task = asyncio.create_task(self._get_attractions_async(parsed_travel))
            
            # Wait for and stream results as they complete
            flights_data = await flight_task
            yield {
                "type": "flights",
                "data": flights_data,
                "progress": 50
            }
            
            hotels_data = await hotel_task
            yield {
                "type": "hotels",
                "data": hotels_data,
                "progress": 60
            }
            
            attractions_data = await attractions_task
            yield {
                "type": "attractions",
                "data": attractions_data,
                "progress": 70
            }
            
            # Step 5: Generate itinerary
            yield {"type": "status", "message": "Creating your personalized itinerary...", "progress": 75}
            
            itinerary = await self._create_itinerary_async(parsed_travel, attractions_data)
            yield {
                "type": "itinerary",
                "data": itinerary,
                "progress": 85
            }
            
            # Step 6: Calculate budget
            yield {"type": "status", "message": "Calculating trip budget...", "progress": 90}
            
            budget = await self._calculate_budget_async(flights_data, hotels_data, parsed_travel)
            yield {
                "type": "budget",
                "data": budget,
                "progress": 95
            }
            
            # Step 7: Generate travel tips
            tips = await self._get_travel_tips_async(parsed_travel)
            yield {
                "type": "tips",
                "data": tips,
                "progress": 100
            }
            
            # Final completion message
            yield {"type": "complete", "message": "Your travel plan is ready!", "progress": 100}
            
        except Exception as e:
            logger.error(f"Error in streaming travel plan: {e}")
            yield {"type": "error", "message": f"An error occurred: {str(e)}"}
    
    async def _parse_travel_query_async(self, query: str) -> Optional[Dict[str, Any]]:
        """Parse travel query asynchronously"""
        today = datetime.now()
        current_date_str = today.strftime('%Y-%m-%d')
        
        messages = [
            {
                "role": "system",
                "content": (
                    "Parse travel request and extract: origin_city, destination_city, departure_date (YYYY-MM-DD), "
                    f"travelers (number), travel_type, duration_days. Today is {current_date_str}. "
                    "Return JSON only."
                )
            },
            {
                "role": "user",
                "content": query
            }
        ]
        
        try:
            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=200,
                temperature=0.1
            )
            
            if response and response.choices:
                response_text = response.choices[0].message.content.strip()
                
                # Extract JSON
                if "```json" in response_text:
                    start = response_text.find("```json") + 7
                    end = response_text.find("```", start)
                    if end != -1:
                        response_text = response_text[start:end].strip()
                elif not response_text.startswith("{"):
                    start_idx = response_text.find("{")
                    end_idx = response_text.rfind("}")
                    if start_idx != -1 and end_idx != -1:
                        response_text = response_text[start_idx:end_idx+1]
                
                parsed_info = json.loads(response_text)
                
                # Set defaults
                parsed_info.setdefault('travelers', 1)
                parsed_info.setdefault('travel_type', 'leisure')
                parsed_info.setdefault('duration_days', 1)
                
                # Handle missing origin
                if not parsed_info.get('origin_city') or parsed_info.get('origin_city') == '':
                    parsed_info['origin_city'] = 'NOT_SPECIFIED'
                
                # Calculate return date
                if parsed_info.get('duration_days', 0) > 1:
                    departure = datetime.strptime(parsed_info['departure_date'], '%Y-%m-%d')
                    return_date = departure + timedelta(days=parsed_info['duration_days'])
                    parsed_info['return_date'] = return_date.strftime('%Y-%m-%d')
                
                return parsed_info
                
        except Exception as e:
            logger.error(f"Error parsing travel query: {e}")
            return None
    
    async def _search_flights_async(self, parsed_travel: Dict[str, Any]) -> Dict[str, Any]:
        """Search for flights asynchronously"""
        try:
            # Check if we have valid origin and destination
            if not parsed_travel.get('origin_city') or parsed_travel['origin_city'] == 'NOT_SPECIFIED':
                logger.warning("Origin city not specified, skipping flight search")
                return {"outbound": [], "return": [], "error": "Origin city not specified"}
            
            outbound_query = f"Flight from {parsed_travel['origin_city']} to {parsed_travel['destination_city']} on {parsed_travel['departure_date']} for {parsed_travel['travelers']} adults"
            
            outbound_df, _, _ = await asyncio.to_thread(
                self.flight_service.process_flight_search,
                outbound_query
            )
            
            outbound_flights = []
            if outbound_df is not None and not outbound_df.empty:
                outbound_flights = outbound_df.head(3).to_dict('records')
            
            return_flights = []
            if parsed_travel.get('return_date'):
                return_query = f"Flight from {parsed_travel['destination_city']} to {parsed_travel['origin_city']} on {parsed_travel['return_date']} for {parsed_travel['travelers']} adults"
                
                return_df, _, _ = await asyncio.to_thread(
                    self.flight_service.process_flight_search,
                    return_query
                )
                
                if return_df is not None and not return_df.empty:
                    return_flights = return_df.head(3).to_dict('records')
            
            return {
                'outbound': outbound_flights,
                'return': return_flights,
                'total_options': len(outbound_flights) + len(return_flights)
            }
            
        except Exception as e:
            logger.error(f"Error searching flights: {e}")
            return {'outbound': [], 'return': [], 'total_options': 0}
    
    async def _search_hotels_async(self, parsed_travel: Dict[str, Any]) -> Dict[str, Any]:
        """Search for hotels asynchronously"""
        try:
            hotel_query = f"Hotels in {parsed_travel['destination_city']} from {parsed_travel['departure_date']} to {parsed_travel.get('return_date', parsed_travel['departure_date'])} for {parsed_travel['travelers']} adults"
            
            hotels_df, _, _ = await asyncio.to_thread(
                self.hotel_service.process_hotel_search,
                hotel_query
            )
            
            hotels = []
            if hotels_df is not None and not hotels_df.empty:
                hotels = hotels_df.head(5).to_dict('records')
            
            return {
                'options': hotels,
                'total_options': len(hotels)
            }
            
        except Exception as e:
            logger.warning(f"Hotel search failed: {e}")
            return {'options': [], 'total_options': 0}
    
    async def _get_attractions_async(self, parsed_travel: Dict[str, Any]) -> Dict[str, Any]:
        """Get attractions asynchronously"""
        try:
            destination = parsed_travel['destination_city']
            travel_type = parsed_travel.get('travel_type', 'leisure')
            
            # Parallel requests for attractions and dining
            attractions_task = asyncio.create_task(
                self._fetch_attractions(destination, travel_type)
            )
            dining_task = asyncio.create_task(
                self._fetch_dining(destination)
            )
            
            attractions = await attractions_task
            dining = await dining_task
            
            return {
                'must_visit': attractions[:5],
                'dining': dining[:4]
            }
            
        except Exception as e:
            logger.error(f"Error getting attractions: {e}")
            return {'must_visit': [], 'dining': []}
    
    async def _fetch_attractions(self, city_name: str, travel_type: str) -> List[Dict[str, Any]]:
        """Fetch attractions from OpenAI"""
        messages = [
            {
                "role": "system",
                "content": f"List 5 top attractions in {city_name} for {travel_type} travel. Return JSON array with: name, category, description (30 words max)."
            },
            {
                "role": "user",
                "content": f"Top attractions in {city_name}"
            }
        ]
        
        response = await asyncio.to_thread(
            self.openai_client.chat.completions.create,
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=800,
            temperature=0.3
        )
        
        if response and response.choices:
            response_text = response.choices[0].message.content.strip()
            
            # Extract JSON
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                if end != -1:
                    response_text = response_text[start:end].strip()
            elif not response_text.startswith("["):
                start_idx = response_text.find("[")
                end_idx = response_text.rfind("]")
                if start_idx != -1 and end_idx != -1:
                    response_text = response_text[start_idx:end_idx+1]
            
            attractions = json.loads(response_text)
            return attractions if isinstance(attractions, list) else []
        
        return []
    
    async def _fetch_dining(self, city_name: str) -> List[Dict[str, Any]]:
        """Fetch dining recommendations from OpenAI"""
        messages = [
            {
                "role": "system",
                "content": f"List 4 best restaurants in {city_name}. Return JSON array with: name, cuisine_type, description (20 words max), price_range."
            },
            {
                "role": "user",
                "content": f"Best restaurants in {city_name}"
            }
        ]
        
        response = await asyncio.to_thread(
            self.openai_client.chat.completions.create,
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=600,
            temperature=0.3
        )
        
        if response and response.choices:
            response_text = response.choices[0].message.content.strip()
            
            # Extract JSON
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                if end != -1:
                    response_text = response_text[start:end].strip()
            elif not response_text.startswith("["):
                start_idx = response_text.find("[")
                end_idx = response_text.rfind("]")
                if start_idx != -1 and end_idx != -1:
                    response_text = response_text[start_idx:end_idx+1]
            
            dining = json.loads(response_text)
            return dining if isinstance(dining, list) else []
        
        return []
    
    async def _create_itinerary_async(self, parsed_travel: Dict[str, Any], attractions_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create simple itinerary asynchronously"""
        duration = parsed_travel['duration_days']
        destination = parsed_travel['destination_city']
        
        messages = [
            {
                "role": "system",
                "content": f"Create {duration}-day itinerary for {destination}. Return JSON array with: day_number, theme, activities (3 max per day with time and name)."
            },
            {
                "role": "user",
                "content": f"Create {duration}-day itinerary"
            }
        ]
        
        response = await asyncio.to_thread(
            self.openai_client.chat.completions.create,
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=1000,
            temperature=0.4
        )
        
        if response and response.choices:
            response_text = response.choices[0].message.content.strip()
            
            # Extract JSON
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                if end != -1:
                    response_text = response_text[start:end].strip()
            elif not response_text.startswith("["):
                start_idx = response_text.find("[")
                end_idx = response_text.rfind("]")
                if start_idx != -1 and end_idx != -1:
                    response_text = response_text[start_idx:end_idx+1]
            
            itinerary = json.loads(response_text)
            return itinerary if isinstance(itinerary, list) else []
        
        return []
    
    async def _calculate_budget_async(self, flights_data: Dict, hotels_data: Dict, parsed_travel: Dict) -> Dict[str, Any]:
        """Calculate budget asynchronously"""
        travelers = parsed_travel['travelers']
        duration = parsed_travel['duration_days']
        
        flight_cost = 0
        outbound_flights = flights_data.get('outbound', [])
        if outbound_flights:
            cheapest = min([
                float(str(f.get('Total Price', '0')).replace(',', '')) 
                for f in outbound_flights 
                if f.get('Total Price')
            ] or [0])
            flight_cost = cheapest * travelers * 2  # Round trip
        
        hotel_cost = 0
        hotels = hotels_data.get('options', [])
        if hotels:
            cheapest = min([
                float(str(h.get('Total Price', '0')).replace(',', '')) 
                for h in hotels 
                if h.get('Total Price')
            ] or [0])
            hotel_cost = cheapest * duration
        
        daily_expenses = 3000 * travelers * duration
        transport_cost = 500 * travelers * duration
        
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
    
    async def _get_travel_tips_async(self, parsed_travel: Dict[str, Any]) -> Dict[str, Any]:
        """Get travel tips asynchronously"""
        destination = parsed_travel['destination_city']
        
        return {
            'best_time_to_visit': 'Check local weather conditions',
            'what_to_pack': ['Comfortable clothes', 'Travel documents', 'Phone charger', 'Medications'],
            'safety_tips': 'Keep valuables safe, stay aware of surroundings',
            'money_tips': 'Carry mix of cash and cards, inform bank of travel',
            'local_customs': f'Research local customs and etiquette in {destination}'
        }