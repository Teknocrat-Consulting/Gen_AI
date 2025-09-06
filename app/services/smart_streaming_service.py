"""
Smart Streaming Travel Service with Intent Detection
Responds based on what the user is actually asking for
"""

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
from app.services.intent_detection_service import IntentDetectionService, QueryIntent
from app.services.response_hierarchy_service import ResponseFormatter, SmartResponseOrchestrator

load_dotenv()


class SmartStreamingService:
    """Smart travel service with intent detection and selective streaming"""
    
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
        
        logger.info("Initializing SmartStreamingService (singleton)")
        self.openai_client = OpenAI(api_key=api_key)
        self.flight_service = FlightService()
        self.hotel_service = HotelService()
        self.intent_service = IntentDetectionService()
        self.response_formatter = ResponseFormatter()
        self.response_orchestrator = SmartResponseOrchestrator()
        SmartStreamingService._initialized = True
    
    async def stream_travel_plan(self, query: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream travel plan components based on detected intent"""
        
        try:
            # Step 1: Detect intent
            logger.info(f"Detecting intent for: {query}")
            intent_result = self.intent_service.detect_intent(query)
            components = intent_result['components']
            
            yield {
                "type": "intent", 
                "data": intent_result,
                "message": self.intent_service.get_response_message(intent_result['intent']),
                "progress": 5
            }
            
            # Step 2: Parse travel query
            yield {"type": "status", "message": "Understanding your requirements...", "progress": 10}
            parsed_travel = await self._parse_travel_query_async(query)
            
            if not parsed_travel:
                yield {"type": "error", "message": "Could not understand your travel request. Please be more specific."}
                return
            
            # Check if origin is missing
            if not parsed_travel.get("origin") or parsed_travel.get("origin") == "Not specified" or parsed_travel.get("origin") == "":
                yield {
                    "type": "error",
                    "message": "📍 Please specify your departure city to search for flights.\n\nExample: 'I want to go from Mumbai to Rajasthan' or 'Flights from Delhi to Jaipur'",
                    "needs_origin": True
                }
                return
            
            # Step 3: Stream summary (always shown)
            yield {"type": "status", "message": "Preparing travel summary...", "progress": 15}
            yield {
                "type": "summary",
                "data": {
                    "origin": parsed_travel.get("origin", "Not specified"),
                    "destination": parsed_travel.get("destination", "Not specified"),
                    "departure_date": parsed_travel.get("departure_date"),
                    "return_date": parsed_travel.get("return_date"),
                    "duration_days": self._calculate_days(
                        parsed_travel.get("departure_date"),
                        parsed_travel.get("return_date")
                    ),
                    "travelers": parsed_travel.get("adults", 1),
                    "travel_type": parsed_travel.get("travel_type", "Leisure"),
                    "intent": intent_result['intent'],
                    "components_requested": components
                },
                "progress": 20
            }
            
            current_progress = 20
            total_components = sum(1 for v in components.values() if v and v != 'summary')
            progress_per_component = 70 / max(total_components, 1)
            
            # Step 4: Search flights if requested
            if components.get('flights'):
                yield {"type": "status", "message": "Searching for best flight options...", "progress": current_progress + 5}
                
                try:
                    flight_results = await self._search_flights_async(parsed_travel)
                    
                    # Format flights with hierarchy
                    formatted_flights = {
                        "outbound": [],
                        "return": []
                    }
                    
                    for flight in flight_results.get("outbound", [])[:5]:
                        formatted_flights["outbound"].append(self.response_formatter.format_flight_response(flight))
                    
                    for flight in flight_results.get("return", [])[:5]:
                        formatted_flights["return"].append(self.response_formatter.format_flight_response(flight))
                    
                    current_progress += progress_per_component
                    
                    yield {
                        "type": "flights",
                        "data": {
                            "total_options": len(flight_results.get("outbound", [])) + len(flight_results.get("return", [])),
                            "outbound": flight_results.get("outbound", [])[:5],
                            "return": flight_results.get("return", [])[:5],
                            "formatted": formatted_flights
                        },
                        "progress": current_progress
                    }
                except Exception as e:
                    logger.error(f"Error in flight search: {e}")
                    yield {
                        "type": "warning",
                        "message": "Flight search encountered issues. Continuing with other services...",
                        "details": str(e),
                        "progress": current_progress
                    }
                    current_progress += progress_per_component
            
            # Step 5: Search hotels if requested
            if components.get('hotels'):
                yield {"type": "status", "message": "Finding perfect accommodations...", "progress": current_progress + 5}
                
                hotel_results = await self._search_hotels_async(parsed_travel)
                current_progress += progress_per_component
                
                yield {
                    "type": "hotels",
                    "data": {
                        "total_options": len(hotel_results),
                        "options": hotel_results[:6]
                    },
                    "progress": current_progress
                }
            
            # Step 6: Get attractions if requested
            if components.get('attractions'):
                yield {"type": "status", "message": "Discovering amazing places to visit...", "progress": current_progress + 5}
                
                attractions = await self._get_attractions_async(parsed_travel)
                current_progress += progress_per_component
                
                yield {
                    "type": "attractions",
                    "data": attractions,
                    "progress": current_progress
                }
            
            # Step 7: Create itinerary if requested
            if components.get('itinerary'):
                yield {"type": "status", "message": "Creating your personalized itinerary...", "progress": current_progress + 5}
                
                itinerary = await self._create_itinerary_async(parsed_travel)
                current_progress += progress_per_component
                
                yield {
                    "type": "itinerary",
                    "data": itinerary,
                    "progress": current_progress
                }
            
            # Step 8: Calculate budget if requested
            if components.get('budget'):
                yield {"type": "status", "message": "Calculating travel budget...", "progress": current_progress + 5}
                
                budget = await self._calculate_budget_async(
                    parsed_travel,
                    flight_results if components.get('flights') else None,
                    hotel_results if components.get('hotels') else None
                )
                current_progress += progress_per_component
                
                yield {
                    "type": "budget",
                    "data": budget,
                    "progress": current_progress
                }
            
            # Step 9: Get travel tips if requested
            if components.get('tips'):
                yield {"type": "status", "message": "Gathering helpful travel tips...", "progress": 90}
                
                tips = await self._get_travel_tips_async(parsed_travel)
                
                yield {
                    "type": "tips",
                    "data": tips,
                    "progress": 95
                }
            
            # Step 10: Complete
            yield {
                "type": "complete",
                "message": f"Your {intent_result['intent'].replace('_', ' ')} request is ready!",
                "progress": 100
            }
            
        except Exception as e:
            logger.error(f"Error in streaming travel plan: {str(e)}")
            yield {
                "type": "error",
                "message": f"An error occurred: {str(e)}",
                "progress": 0
            }
    
    async def _parse_travel_query_async(self, query: str) -> Optional[Dict]:
        """Parse travel query using OpenAI"""
        try:
            current_date = datetime.now()
            tomorrow = (current_date + timedelta(days=1)).strftime("%Y-%m-%d")
            next_week = (current_date + timedelta(days=7)).strftime("%Y-%m-%d")
            
            prompt = f"""Parse this travel query and extract details. Today is {current_date.strftime('%Y-%m-%d')}.
            IMPORTANT: All dates MUST be in {current_date.year} or later. Never use past years like 2022, 2023, etc.
            
            Query: {query}
            
            Extract and return as JSON:
            - origin: departure city (if not mentioned, set as "Not specified")
            - destination: arrival city
            - departure_date: date in YYYY-MM-DD format (use {tomorrow} if not specified, for "next monday" calculate from today)
            - return_date: date in YYYY-MM-DD format (use 3 days after departure if not specified)
            - adults: number of travelers (default 1)
            - travel_type: business/leisure/adventure/romantic (infer from context)
            - budget_level: budget/standard/luxury (infer from context, default standard)
            
            Example: If today is 2025-09-06 and query mentions "next monday", use 2025-09-09 or later.
            If origin city is not mentioned in the query, set origin as "Not specified".
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a travel assistant. Extract travel details from queries."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Validate and fix dates
            current_date = datetime.now()
            tomorrow = current_date + timedelta(days=1)
            
            # Parse and validate departure date
            if result.get("departure_date"):
                try:
                    dep_date = datetime.strptime(result["departure_date"], "%Y-%m-%d")
                    # If date is in the past, use tomorrow instead
                    if dep_date < current_date:
                        logger.warning(f"Departure date {result['departure_date']} is in the past, using tomorrow")
                        result["departure_date"] = tomorrow.strftime("%Y-%m-%d")
                        dep_date = tomorrow
                except:
                    result["departure_date"] = tomorrow.strftime("%Y-%m-%d")
                    dep_date = tomorrow
            else:
                result["departure_date"] = tomorrow.strftime("%Y-%m-%d")
                dep_date = tomorrow
            
            # Parse and validate return date
            if not result.get("return_date"):
                result["return_date"] = (dep_date + timedelta(days=3)).strftime("%Y-%m-%d")
            else:
                try:
                    ret_date = datetime.strptime(result["return_date"], "%Y-%m-%d")
                    # Ensure return date is after departure
                    if ret_date <= dep_date:
                        result["return_date"] = (dep_date + timedelta(days=3)).strftime("%Y-%m-%d")
                except:
                    result["return_date"] = (dep_date + timedelta(days=3)).strftime("%Y-%m-%d")
                
            return result
            
        except Exception as e:
            logger.error(f"Error parsing travel query: {e}")
            return None
    
    async def _search_flights_async(self, parsed_travel: Dict) -> Dict:
        """Search for flights"""
        try:
            # Simulate async flight search
            await asyncio.sleep(0.5)
            
            # Create a query string for the flight service
            query = f"flight from {parsed_travel.get('origin')} to {parsed_travel.get('destination')} on {parsed_travel.get('departure_date')}"
            if parsed_travel.get('return_date'):
                query += f" returning {parsed_travel.get('return_date')}"
            query += f" for {parsed_travel.get('adults', 1)} adults"
            
            flight_df, origin, destination = self.flight_service.process_flight_search(query)
            
            # Organize flights by direction
            outbound = []
            return_flights = []
            
            if flight_df is not None and not flight_df.empty:
                # Convert DataFrame to list of dicts
                flights_list = flight_df.to_dict('records')
                
                # Separate outbound and return flights based on direction
                for flight in flights_list:
                    if flight.get('Source') == origin:
                        outbound.append(flight)
                    else:
                        return_flights.append(flight)
                
                # If no separation by direction, assume first half are outbound
                if not outbound and not return_flights:
                    mid = len(flights_list) // 2
                    outbound = flights_list[:mid] if flights_list else []
                    return_flights = flights_list[mid:] if len(flights_list) > mid else []
            
            return {"outbound": outbound, "return": return_flights}
            
        except Exception as e:
            logger.error(f"Error searching flights: {e}")
            return {"outbound": [], "return": []}
    
    async def _search_hotels_async(self, parsed_travel: Dict) -> List[Dict]:
        """Search for hotels"""
        try:
            # Simulate async hotel search
            await asyncio.sleep(0.5)
            
            # Create a query string for the hotel service
            query = f"hotels in {parsed_travel.get('destination')} from {parsed_travel.get('departure_date')} to {parsed_travel.get('return_date')} for {parsed_travel.get('adults', 1)} adults"
            
            hotel_df, location, dates = self.hotel_service.process_hotel_search(query)
            
            if hotel_df is not None and not hotel_df.empty:
                # Convert DataFrame to list of dicts
                hotels_list = hotel_df.to_dict('records')
                return hotels_list
            
            return []
            
        except Exception as e:
            logger.error(f"Error searching hotels: {e}")
            return []
    
    async def _get_attractions_async(self, parsed_travel: Dict) -> Dict:
        """Get attractions and dining recommendations"""
        try:
            await asyncio.sleep(0.3)
            
            prompt = f"""Suggest attractions and dining for {parsed_travel.get('destination')}.
            Travel type: {parsed_travel.get('travel_type', 'leisure')}
            Duration: {self._calculate_days(parsed_travel.get('departure_date'), parsed_travel.get('return_date'))} days
            
            Provide as JSON with:
            - must_visit: array of 4-6 places with name, category, description
            - dining: array of 3-4 restaurants with name, cuisine_type, description, price_range
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a travel guide. Suggest attractions and dining."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.7
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            logger.error(f"Error getting attractions: {e}")
            return {"must_visit": [], "dining": []}
    
    async def _create_itinerary_async(self, parsed_travel: Dict) -> List[Dict]:
        """Create day-by-day itinerary"""
        try:
            await asyncio.sleep(0.3)
            
            days = self._calculate_days(parsed_travel.get('departure_date'), parsed_travel.get('return_date'))
            
            prompt = f"""Create a {days}-day itinerary for {parsed_travel.get('destination')}.
            Travel type: {parsed_travel.get('travel_type', 'leisure')}
            
            Provide as JSON array, each day with:
            - day_number: int
            - theme: string (e.g., "Arrival & City Exploration")
            - activities: array of objects with time and name
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a travel planner. Create detailed itineraries."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.7
            )
            
            result = json.loads(response.choices[0].message.content)
            return result.get("itinerary", result.get("days", []))
            
        except Exception as e:
            logger.error(f"Error creating itinerary: {e}")
            return []
    
    async def _calculate_budget_async(self, parsed_travel: Dict, flights: Dict = None, hotels: List = None) -> Dict:
        """Calculate estimated budget"""
        try:
            await asyncio.sleep(0.2)
            
            days = self._calculate_days(parsed_travel.get('departure_date'), parsed_travel.get('return_date'))
            travelers = parsed_travel.get('adults', 1)
            
            # Calculate flight costs
            flight_cost = 0
            if flights:
                outbound = flights.get('outbound', [])
                inbound = flights.get('return', [])
                if outbound:
                    flight_cost += float(outbound[0].get('Total Price', 15000))
                if inbound:
                    flight_cost += float(inbound[0].get('Total Price', 15000))
            else:
                flight_cost = 30000  # Default estimate
            
            # Calculate hotel costs
            hotel_cost = 0
            if hotels and len(hotels) > 0:
                avg_hotel_price = sum(float(h.get('Total Price', 3000)) for h in hotels[:3]) / min(3, len(hotels))
                hotel_cost = avg_hotel_price * (days - 1)  # nights = days - 1
            else:
                hotel_cost = 3000 * (days - 1)  # Default estimate
            
            # Estimate other costs
            food_per_day = 1500 if parsed_travel.get('budget_level') != 'budget' else 800
            activities_per_day = 2000 if parsed_travel.get('budget_level') != 'budget' else 1000
            local_transport = 500 * days
            
            activities_food = (food_per_day + activities_per_day) * days * travelers
            
            total = (flight_cost * travelers) + (hotel_cost) + activities_food + local_transport
            
            return {
                "flights": flight_cost * travelers,
                "accommodation": hotel_cost,
                "activities_food": activities_food,
                "local_transport": local_transport,
                "total": total,
                "per_person": total / travelers
            }
            
        except Exception as e:
            logger.error(f"Error calculating budget: {e}")
            return {
                "flights": 30000,
                "accommodation": 9000,
                "activities_food": 15000,
                "local_transport": 2000,
                "total": 56000,
                "per_person": 56000
            }
    
    async def _get_travel_tips_async(self, parsed_travel: Dict) -> Dict:
        """Get travel tips"""
        try:
            await asyncio.sleep(0.2)
            
            prompt = f"""Provide travel tips for {parsed_travel.get('destination')}.
            
            Provide as JSON with:
            - best_time_to_visit: string
            - what_to_pack: array of 5 essential items
            - safety_tips: string
            - money_tips: string
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a travel advisor. Provide helpful tips."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.7
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            logger.error(f"Error getting travel tips: {e}")
            return {
                "best_time_to_visit": "October to March for pleasant weather",
                "what_to_pack": ["Comfortable walking shoes", "Sunscreen", "Light clothing", "Power adapter", "First aid kit"],
                "safety_tips": "Keep copies of important documents. Stay aware of your surroundings.",
                "money_tips": "Carry both cash and cards. Inform your bank about travel dates."
            }
    
    def _calculate_days(self, departure_date: str, return_date: str) -> int:
        """Calculate number of days between dates"""
        try:
            if not departure_date or not return_date:
                return 3
            
            dep = datetime.strptime(departure_date, "%Y-%m-%d")
            ret = datetime.strptime(return_date, "%Y-%m-%d")
            return (ret - dep).days + 1
        except:
            return 3