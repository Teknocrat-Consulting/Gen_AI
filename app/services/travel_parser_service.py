import json
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from openai import OpenAI
from dotenv import load_dotenv
from app.core.logging import logger
from app.core.config import settings

load_dotenv()


class TravelQueryParser:
    def __init__(self):
        api_key = settings.OPENAI_API_KEY
        if not api_key:
            logger.error("OPENAI_API_KEY is not set!")
            raise ValueError("OPENAI_API_KEY is required")
        self.openai_client = OpenAI(api_key=api_key)
    
    def parse_travel_query(self, query: str) -> Optional[Dict[str, Any]]:
        """Parse a natural language travel query and extract structured information"""
        today = datetime.now()
        current_date_str = today.strftime('%Y-%m-%d')
        
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an advanced travel query parser. Extract comprehensive travel information from user queries. "
                    f"Today is {current_date_str}. Parse the following details: "
                    "\n"
                    "1. origin_city: Departure city (required) "
                    "2. destination_city: Destination city (required) "
                    "3. departure_date: Travel date (required, convert relative dates like 'next Monday' to absolute) "
                    "4. return_date: Return date (optional, calculate if duration mentioned) "
                    "5. duration_days: Trip duration in days (extract from phrases like '2 days', 'weekend', 'week') "
                    "6. travelers: Number of people traveling (default: 1) "
                    "7. travel_type: 'business', 'leisure', 'family', 'romantic', 'adventure', 'cultural' (infer from context) "
                    "8. budget_preference: 'budget', 'moderate', 'luxury' (infer from context or use 'moderate' as default) "
                    "9. accommodation_preference: Hotel star preference 1-5, or 'any' (default: 'any') "
                    "10. interests: List of interests/activities mentioned (sightseeing, food, shopping, nightlife, adventure, culture, etc.) "
                    "11. special_requirements: Any special needs (accessibility, dietary, etc.) "
                    "12. transportation_preference: Flight class preference if mentioned (economy, business, first) "
                    "\n"
                    "Examples of duration parsing: "
                    "- 'for 2 days' = 2 days "
                    "- 'weekend trip' = 2 days "
                    "- 'for a week' = 7 days "
                    "- 'staying 3 nights' = 3 days "
                    "\n"
                    "Return ONLY valid JSON format: "
                    "{"
                    "  \"origin_city\": \"string\","
                    "  \"destination_city\": \"string\","
                    "  \"departure_date\": \"YYYY-MM-DD\","
                    "  \"return_date\": \"YYYY-MM-DD or null\","
                    "  \"duration_days\": number,"
                    "  \"travelers\": number,"
                    "  \"travel_type\": \"string\","
                    "  \"budget_preference\": \"string\","
                    "  \"accommodation_preference\": \"string or number\","
                    "  \"interests\": [\"list\", \"of\", \"interests\"],"
                    "  \"special_requirements\": [\"list\", \"if\", \"any\"],"
                    "  \"transportation_preference\": \"string or null\""
                    "}"
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
                max_tokens=800,
                temperature=0.1
            )
            
            if not response or not response.choices or len(response.choices) == 0:
                logger.error("Empty or invalid response from OpenAI")
                return None
                
            response_text = response.choices[0].message.content
            if response_text is None:
                logger.error("Response content is None")
                return None
            
            response_text = response_text.strip()
            logger.info(f"OpenAI parsing response: {response_text}")
            
            # Handle potential markdown code blocks
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
            
            # Extract JSON part
            if response_text and not response_text.startswith("{"):
                start_idx = response_text.find("{")
                end_idx = response_text.rfind("}")
                if start_idx != -1 and end_idx != -1:
                    response_text = response_text[start_idx:end_idx+1]
            
            parsed_info = json.loads(response_text)
            
            # Validate required fields
            required_fields = ["origin_city", "destination_city", "departure_date"]
            if not all(field in parsed_info for field in required_fields):
                raise ValueError(f"Missing required fields: {[f for f in required_fields if f not in parsed_info]}")
            
            # Set defaults for optional fields
            parsed_info.setdefault('duration_days', 1)
            parsed_info.setdefault('travelers', 1)
            parsed_info.setdefault('travel_type', 'leisure')
            parsed_info.setdefault('budget_preference', 'moderate')
            parsed_info.setdefault('accommodation_preference', 'any')
            parsed_info.setdefault('interests', ['sightseeing'])
            parsed_info.setdefault('special_requirements', [])
            parsed_info.setdefault('transportation_preference', None)
            
            # Calculate return date if not provided but duration is given
            if not parsed_info.get('return_date') and parsed_info.get('duration_days', 0) > 1:
                try:
                    departure = datetime.strptime(parsed_info['departure_date'], '%Y-%m-%d')
                    return_date = departure + timedelta(days=parsed_info['duration_days'] - 1)
                    parsed_info['return_date'] = return_date.strftime('%Y-%m-%d')
                except Exception as e:
                    logger.warning(f"Could not calculate return date: {e}")
                    parsed_info['return_date'] = None
            
            return parsed_info
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            logger.error(f"Failed to parse response: {response_text if 'response_text' in locals() else 'No response text'}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error parsing travel query: {e}")
            return None
    
    def extract_flight_preferences(self, parsed_travel: Dict[str, Any]) -> Dict[str, Any]:
        """Extract flight-specific preferences from parsed travel data"""
        return {
            'origin': parsed_travel['origin_city'],
            'destination': parsed_travel['destination_city'],
            'departure_date': parsed_travel['departure_date'],
            'return_date': parsed_travel.get('return_date'),
            'adults': parsed_travel['travelers'],
            'class': parsed_travel.get('transportation_preference', 'economy'),
            'budget_preference': parsed_travel['budget_preference']
        }
    
    def extract_hotel_preferences(self, parsed_travel: Dict[str, Any]) -> Dict[str, Any]:
        """Extract hotel-specific preferences from parsed travel data"""
        # Calculate check-in and check-out dates
        check_in = parsed_travel['departure_date']
        check_out = parsed_travel.get('return_date')
        
        # If no return date, use departure date + duration
        if not check_out and parsed_travel.get('duration_days', 0) > 1:
            try:
                departure = datetime.strptime(check_in, '%Y-%m-%d')
                checkout_date = departure + timedelta(days=parsed_travel['duration_days'])
                check_out = checkout_date.strftime('%Y-%m-%d')
            except Exception as e:
                logger.warning(f"Could not calculate hotel check-out date: {e}")
                check_out = check_in
        
        # Determine number of rooms (simple logic: 1 room per 2 people, minimum 1)
        travelers = parsed_travel['travelers']
        rooms = max(1, (travelers + 1) // 2)
        
        hotel_rating = None
        accommodation_pref = parsed_travel.get('accommodation_preference', 'any')
        if isinstance(accommodation_pref, (int, str)) and str(accommodation_pref).isdigit():
            hotel_rating = int(accommodation_pref)
        
        return {
            'location': parsed_travel['destination_city'],
            'check_in_date': check_in,
            'check_out_date': check_out or check_in,
            'adults': travelers,
            'rooms': rooms,
            'price_range': parsed_travel['budget_preference'],
            'hotel_rating': hotel_rating,
            'amenities': self._infer_hotel_amenities(parsed_travel)
        }
    
    def extract_attractions_preferences(self, parsed_travel: Dict[str, Any]) -> Dict[str, Any]:
        """Extract attractions and activities preferences"""
        return {
            'destination': parsed_travel['destination_city'],
            'interests': parsed_travel.get('interests', ['sightseeing']),
            'travel_type': parsed_travel.get('travel_type', 'leisure'),
            'duration_days': parsed_travel.get('duration_days', 1),
            'travelers': parsed_travel['travelers'],
            'budget_preference': parsed_travel['budget_preference']
        }
    
    def _infer_hotel_amenities(self, parsed_travel: Dict[str, Any]) -> List[str]:
        """Infer preferred hotel amenities based on travel type and interests"""
        amenities = []
        
        travel_type = parsed_travel.get('travel_type', 'leisure')
        interests = parsed_travel.get('interests', [])
        travelers = parsed_travel.get('travelers', 1)
        
        # Basic amenities everyone needs
        amenities.extend(['wifi', 'air_conditioning'])
        
        # Business travel amenities
        if travel_type == 'business':
            amenities.extend(['business_center', 'meeting_rooms', 'gym'])
        
        # Family travel amenities
        if travel_type == 'family' or travelers > 2:
            amenities.extend(['family_friendly', 'connecting_rooms'])
        
        # Luxury/romantic travel amenities
        if travel_type == 'romantic' or parsed_travel.get('budget_preference') == 'luxury':
            amenities.extend(['spa', 'room_service', 'concierge'])
        
        # Activity-based amenities
        if 'swimming' in interests or 'relaxation' in interests:
            amenities.append('pool')
        
        if 'fitness' in interests or 'wellness' in interests:
            amenities.append('gym')
        
        return amenities