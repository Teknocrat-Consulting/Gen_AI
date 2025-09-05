import json
from datetime import datetime
from typing import Optional, Dict, Any, List
import pandas as pd
from amadeus import Client, ResponseError
from openai import OpenAI
from dotenv import load_dotenv
from app.core.logging import logger
from app.core.config import settings

load_dotenv()


class HotelService:
    def __init__(self):
        self.amadeus = Client(
            client_id=settings.API_Key,
            client_secret=settings.API_Secret
        )
        api_key = settings.OPENAI_API_KEY
        if not api_key:
            logger.error("OPENAI_API_KEY is not set!")
            raise ValueError("OPENAI_API_KEY is required")
        logger.info(f"Initializing OpenAI client with key: {api_key[:10]}...")
        self.openai_client = OpenAI(api_key=api_key)
        self.exchange_rate = self.get_exchange_rate()
    
    def get_exchange_rate(self) -> float:
        """Get current EUR to INR exchange rate"""
        try:
            # Using a reasonable approximate rate
            return 90.50
        except Exception as e:
            logger.warning(f"Could not fetch exchange rate: {e}, using default")
            return 90.50
    
    def get_city_code(self, location: str) -> Optional[str]:
        """Get city code for hotel search"""
        try:
            response = self.amadeus.reference_data.locations.get(
                keyword=location,
                subType='CITY'
            )
            if response.data:
                return response.data[0]['iataCode']
            else:
                logger.warning(f"No city code found for {location}")
                return None
        except ResponseError as error:
            logger.error(f"Error finding city code for {location}: {error}")
            return None
    
    def extract_hotel_info_from_query(self, query: str) -> Optional[Dict[str, Any]]:
        today = datetime.now()
        current_date_str = today.strftime('%Y-%m-%d')
        
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an assistant that helps extract hotel search information from user queries. "
                    f"Today is {current_date_str}. Extract the following details from the query: "
                    "1. location: The city or area where the user wants to find hotels "
                    "2. check_in_date: The check-in date "
                    "3. check_out_date: The check-out date "
                    "4. adults: The number of adult guests (default is 1 if not specified) "
                    "5. rooms: The number of rooms needed (default is 1 if not specified) "
                    "6. price_range: The price preference (cheap, moderate, expensive, luxury) - default is 'moderate' "
                    "7. amenities: List of required amenities (e.g., pool, wifi, parking, gym, spa) "
                    "8. hotel_rating: Preferred hotel star rating (1-5 stars) if mentioned "
                    "If the query specifies relative dates (e.g., 'next week'), convert them to absolute dates. "
                    "Provide the information in JSON format as follows: "
                    '{"location": "city", "check_in_date": "YYYY-MM-DD", "check_out_date": "YYYY-MM-DD", '
                    '"adults": number, "rooms": number, "price_range": "preference", '
                    '"amenities": ["amenity1", "amenity2"], "hotel_rating": rating}'
                )
            },
            {
                "role": "user",
                "content": query
            }
        ]
        
        try:
            logger.info(f"Calling OpenAI for hotel query extraction")
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=300,
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
            logger.info(f"OpenAI response: {response_text}")
            
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
            
            hotel_info = json.loads(response_text)
            
            # Set defaults if not provided
            hotel_info.setdefault('adults', 1)
            hotel_info.setdefault('rooms', 1)
            hotel_info.setdefault('price_range', 'moderate')
            hotel_info.setdefault('amenities', [])
            hotel_info.setdefault('hotel_rating', None)
            
            required_keys = ["location", "check_in_date", "check_out_date"]
            if not all(key in hotel_info for key in required_keys):
                raise ValueError("Incomplete response from LLM")
            
            return hotel_info
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error extracting hotel info: {e}")
            return None
    
    def search_hotels_by_city(self, city_code: str, check_in: str, check_out: str, 
                              adults: int = 1, rooms: int = 1) -> List[Dict[str, Any]]:
        """Search hotels by city using Amadeus API"""
        try:
            # First, get hotels in the city
            response = self.amadeus.reference_data.locations.hotels.by_city.get(
                cityCode=city_code
            )
            
            if not response.data:
                logger.warning(f"No hotels found for city code: {city_code}")
                return []
            
            # Get hotel IDs (limit to first 20 for performance)
            hotel_ids = [hotel['hotelId'] for hotel in response.data[:20]]
            
            # Now get hotel offers for these hotels
            if hotel_ids:
                offers_response = self.amadeus.shopping.hotel_offers_search.get(
                    hotelIds=hotel_ids[:10],  # Limit to 10 hotels for API limits
                    checkInDate=check_in,
                    checkOutDate=check_out,
                    adults=adults,
                    roomQuantity=rooms
                )
                
                return offers_response.data if offers_response.data else []
            
            return []
            
        except ResponseError as error:
            logger.error(f"Hotel search error: {error}")
            return []
    
    def search_hotels_by_location(self, latitude: float, longitude: float, 
                                  radius: int = 5, check_in: Optional[str] = None, 
                                  check_out: Optional[str] = None, adults: int = 1, 
                                  rooms: int = 1) -> List[Dict[str, Any]]:
        """Search hotels by geographic coordinates"""
        try:
            # Get hotels by geographic coordinates
            response = self.amadeus.reference_data.locations.hotels.by_geocode.get(
                latitude=latitude,
                longitude=longitude,
                radius=radius,
                radiusUnit='KM'
            )
            
            if not response.data:
                logger.warning(f"No hotels found at coordinates: {latitude}, {longitude}")
                return []
            
            # Get hotel IDs
            hotel_ids = [hotel['hotelId'] for hotel in response.data[:10]]
            
            # Get hotel offers if dates are provided
            if hotel_ids and check_in and check_out:
                offers_response = self.amadeus.shopping.hotel_offers_search.get(
                    hotelIds=hotel_ids,
                    checkInDate=check_in,
                    checkOutDate=check_out,
                    adults=adults,
                    roomQuantity=rooms
                )
                
                return offers_response.data if offers_response.data else []
            
            return response.data
            
        except ResponseError as error:
            logger.error(f"Hotel location search error: {error}")
            return []
    
    def get_hotel_details(self, hotel_id: str, check_in: str, check_out: str, 
                         adults: int = 1, rooms: int = 1) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific hotel"""
        try:
            response = self.amadeus.shopping.hotel_offer_search(hotel_id).get(
                checkInDate=check_in,
                checkOutDate=check_out,
                adults=adults,
                roomQuantity=rooms
            )
            
            return response.data if response.data else None
            
        except ResponseError as error:
            logger.error(f"Hotel details error: {error}")
            return None
    
    def create_hotel_dataframe(self, hotel_data: List[Dict[str, Any]]) -> pd.DataFrame:
        """Create a structured DataFrame from hotel search results"""
        hotel_details = []
        
        EUR_TO_INR = self.exchange_rate
        
        for hotel_offer in hotel_data:
            hotel = hotel_offer.get('hotel', {})
            
            # Extract hotel basic info
            hotel_name = hotel.get('name', 'Unknown Hotel')
            hotel_id = hotel.get('hotelId', '')
            rating = hotel.get('rating', 'N/A')
            
            # Extract address
            address = hotel.get('address', {})
            city_name = address.get('cityName', '')
            country_code = address.get('countryCode', '')
            
            # Extract coordinates
            latitude = hotel.get('latitude', None)
            longitude = hotel.get('longitude', None)
            
            # Extract amenities
            amenities = hotel.get('amenities', [])
            amenities_str = ', '.join(amenities[:5]) if amenities else 'Not specified'
            
            # Process offers
            offers = hotel_offer.get('offers', [])
            for offer in offers:
                price = offer.get('price', {})
                total_price = price.get('total', '')
                currency = price.get('currency', '')
                
                # Convert EUR to INR
                if currency == 'EUR' and total_price:
                    try:
                        price_eur = float(total_price)
                        price_inr = price_eur * EUR_TO_INR
                        total_price = f"{price_inr:.2f}"
                        currency = 'INR'
                    except (ValueError, TypeError):
                        logger.warning(f"Could not convert price: {total_price}")
                
                # Extract room info
                room = offer.get('room', {})
                room_type = room.get('typeEstimated', {}).get('category', 'Standard Room')
                beds = room.get('typeEstimated', {}).get('beds', 'N/A')
                bed_type = room.get('typeEstimated', {}).get('bedType', 'N/A')
                
                # Extract policies
                policies = offer.get('policies', {})
                cancellation = policies.get('cancellation', {}).get('description', {}).get('text', 'Check with hotel')
                check_in_time = policies.get('checkInOut', {}).get('checkIn', 'Standard')
                check_out_time = policies.get('checkInOut', {}).get('checkOut', 'Standard')
                
                hotel_details.append({
                    "Hotel Name": hotel_name,
                    "Hotel ID": hotel_id,
                    "Rating": rating,
                    "City": city_name,
                    "Country": country_code,
                    "Latitude": latitude,
                    "Longitude": longitude,
                    "Room Type": room_type,
                    "Beds": beds,
                    "Bed Type": bed_type,
                    "Total Price": total_price,
                    "Currency": currency,
                    "Amenities": amenities_str,
                    "Cancellation Policy": cancellation,
                    "Check-in Time": check_in_time,
                    "Check-out Time": check_out_time
                })
        
        df = pd.DataFrame(hotel_details)
        df.drop_duplicates(subset=['Hotel Name', 'Room Type'], inplace=True)
        return df
    
    def filter_hotels_by_preferences(self, hotels_df: pd.DataFrame, 
                                    price_range: str = 'moderate',
                                    amenities: Optional[List[str]] = None,
                                    rating: Optional[int] = None) -> pd.DataFrame:
        """Filter hotels based on user preferences"""
        filtered_df = hotels_df.copy()
        
        # Filter by rating if specified
        if rating and 'Rating' in filtered_df.columns:
            try:
                filtered_df = filtered_df[filtered_df['Rating'] != 'N/A']
                filtered_df['Rating'] = pd.to_numeric(filtered_df['Rating'], errors='coerce')
                filtered_df = filtered_df[filtered_df['Rating'] >= rating]
            except Exception as e:
                logger.warning(f"Could not filter by rating: {e}")
        
        # Sort by price based on preference
        try:
            filtered_df['Price_Numeric'] = filtered_df['Total Price'].apply(
                lambda x: float(str(x).replace(',', '')) if x and str(x) != 'N/A' else float('inf')
            )
            
            if price_range == 'cheap':
                filtered_df = filtered_df.nsmallest(min(10, len(filtered_df)), 'Price_Numeric')
            elif price_range == 'expensive' or price_range == 'luxury':
                filtered_df = filtered_df.nlargest(min(10, len(filtered_df)), 'Price_Numeric')
            else:  # moderate
                filtered_df = filtered_df.sort_values('Price_Numeric')
                mid_point = len(filtered_df) // 2
                start = max(0, mid_point - 5)
                end = min(len(filtered_df), mid_point + 5)
                filtered_df = filtered_df.iloc[start:end]
            
            filtered_df.drop('Price_Numeric', axis=1, inplace=True)
        except Exception as e:
            logger.warning(f"Could not sort by price: {e}")
        
        return filtered_df
    
    def process_hotel_search(self, query: str) -> tuple:
        """Main method to process hotel search queries"""
        logger.info(f"Processing hotel search query: {query}")
        
        result = self.extract_hotel_info_from_query(query)
        if not result:
            return None, None, None
        
        logger.info(f"Extracted hotel info: {result}")
        
        location = result['location']
        check_in = result['check_in_date']
        check_out = result['check_out_date']
        adults = result['adults']
        rooms = result['rooms']
        price_range = result['price_range']
        amenities = result['amenities']
        hotel_rating = result['hotel_rating']
        
        # Get city code for the location
        city_code = self.get_city_code(location)
        if not city_code:
            logger.error(f"Could not find city code for {location}")
            return None, None, None
        
        # Search for hotels
        hotel_info = self.search_hotels_by_city(city_code, check_in, check_out, adults, rooms)
        
        if isinstance(hotel_info, list) and hotel_info:
            hotel_df = self.create_hotel_dataframe(hotel_info)
            
            # Apply filters based on preferences
            filtered_df = self.filter_hotels_by_preferences(
                hotel_df, 
                price_range=price_range,
                amenities=amenities,
                rating=hotel_rating
            )
            
            logger.info(f"Created dataframe with {len(filtered_df)} hotels")
            return filtered_df, location, {'check_in': check_in, 'check_out': check_out}
        else:
            logger.error("No hotels found or error in forming dataframe")
            return None, None, None