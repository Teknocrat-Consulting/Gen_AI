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
        # Common city mappings and typo corrections for Indian cities
        city_mappings = {
            # Mumbai variations
            'mumbai': 'BOM',
            'mumdai': 'BOM',  # Common typo
            'mumbay': 'BOM',  # Common typo
            'bombay': 'BOM',
            
            # Delhi variations
            'delhi': 'DEL',
            'new delhi': 'DEL',
            'newdelhi': 'DEL',
            
            # Bangalore variations
            'bangalore': 'BLR',
            'bengaluru': 'BLR',
            'banglore': 'BLR',  # Common typo
            
            # Other major Indian cities
            'chennai': 'MAA',
            'madras': 'MAA',
            'kolkata': 'CCU',
            'calcutta': 'CCU',
            'hyderabad': 'HYD',
            'pune': 'PNQ',
            'ahmedabad': 'AMD',
            'goa': 'GOI',
            'jaipur': 'JAI',
            'kochi': 'COK',
            'cochin': 'COK',
            'lucknow': 'LKO',
            'chandigarh': 'IXC',
            'guwahati': 'GAU',
            'bhubaneswar': 'BBI',
            'surat': 'STV',
            'nagpur': 'NAG',
            'indore': 'IDR',
            'coimbatore': 'CJB',
            'visakhapatnam': 'VTZ',
            'vizag': 'VTZ',
            'patna': 'PAT',
            'vadodara': 'BDQ',
            'baroda': 'BDQ',
            'amritsar': 'ATQ',
            'srinagar': 'SXR',
            'agra': 'AGR',
            'varanasi': 'VNS',
            'bhopal': 'BHO',
            'ranchi': 'IXR',
            'mysore': 'MYQ',
            'mysuru': 'MYQ',
            'udaipur': 'UDR',
            'jodhpur': 'JDH',
            'gwalior': 'GWL',
            'dehradun': 'DED',
            'shimla': 'SLV',
            'manali': 'KUU',
            'darjeeling': 'IXB',
            'gangtok': 'IXB',
            'port blair': 'IXZ',
            
            # International cities commonly searched from India
            'dubai': 'DXB',
            'singapore': 'SIN',
            'bangkok': 'BKK',
            'kuala lumpur': 'KUL',
            'maldives': 'MLE',
            'male': 'MLE',
            'london': 'LON',
            'new york': 'NYC',
            'paris': 'PAR',
            'tokyo': 'TYO',
            'sydney': 'SYD'
        }
        
        # Check if we have a direct mapping (case-insensitive)
        location_lower = location.lower().strip()
        if location_lower in city_mappings:
            logger.info(f"Using mapped city code {city_mappings[location_lower]} for {location}")
            return city_mappings[location_lower]
        
        # Try Amadeus API
        try:
            response = self.amadeus.reference_data.locations.get(
                keyword=location,
                subType='CITY'
            )
            if response.data:
                city_code = response.data[0]['iataCode']
                logger.info(f"Found city code {city_code} for {location} from Amadeus API")
                return city_code
            else:
                logger.warning(f"No city code found for {location}")
                # Try with corrected spelling if it might be a typo
                # Simple typo correction for common mistakes
                if 'mumda' in location_lower or 'mubai' in location_lower:
                    logger.info("Detected possible typo for Mumbai, using BOM")
                    return 'BOM'
                elif 'delh' in location_lower:
                    logger.info("Detected possible match for Delhi, using DEL")
                    return 'DEL'
                elif 'bangal' in location_lower or 'bengl' in location_lower:
                    logger.info("Detected possible match for Bangalore, using BLR")
                    return 'BLR'
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
                    "   IMPORTANT: "
                    "   - If query mentions 'from X to Y' or 'X to Y', the DESTINATION (Y) is where they want hotels "
                    "   - Example: 'Hotels in delhi to Goa' means hotels in GOA (not Delhi) "
                    "   - Correct common typos: 'mumdai'→'Mumbai', 'dehli'→'Delhi', 'banglore'→'Bangalore' "
                    "2. check_in_date: The check-in date "
                    "   IMPORTANT: For 'this weekend', use the NEXT weekend if today is Friday/Saturday/Sunday "
                    "   For immediate dates like 'tomorrow', add at least 3 days buffer for availability "
                    "3. check_out_date: The check-out date (typically 2-3 days after check-in if not specified) "
                    "4. adults: The number of adult guests (default is 1 if not specified) "
                    "5. rooms: The number of rooms needed (default is 1 if not specified) "
                    "6. price_range: The price preference (cheap, moderate, expensive, luxury) - default is 'moderate' "
                    "7. amenities: List of required amenities (e.g., pool, wifi, parking, gym, spa) "
                    "8. hotel_rating: Preferred hotel star rating (1-5 stars) if mentioned "
                    "If dates are too close (within 3 days), adjust to at least 7 days from today for better availability. "
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
            logger.info(f"Searching hotels for city code: {city_code}, check-in: {check_in}, check-out: {check_out}")
            
            # First, get hotels in the city
            response = self.amadeus.reference_data.locations.hotels.by_city.get(
                cityCode=city_code
            )
            
            if not response.data:
                logger.warning(f"No hotels found for city code: {city_code}")
                # Try alternative approach with coordinates for major cities
                if city_code in ['BOM', 'DEL', 'BLR', 'MAA', 'CCU', 'HYD']:
                    logger.info(f"Trying coordinate-based search for {city_code}")
                    # Coordinates for major Indian cities
                    city_coords = {
                        'BOM': (19.0760, 72.8777),  # Mumbai
                        'DEL': (28.7041, 77.1025),  # Delhi
                        'BLR': (12.9716, 77.5946),  # Bangalore
                        'MAA': (13.0827, 80.2707),  # Chennai
                        'CCU': (22.5726, 88.3639),  # Kolkata
                        'HYD': (17.3850, 78.4867),  # Hyderabad
                    }
                    if city_code in city_coords:
                        lat, lon = city_coords[city_code]
                        return self.search_hotels_by_location(lat, lon, radius=10, 
                                                             check_in=check_in, 
                                                             check_out=check_out,
                                                             adults=adults, 
                                                             rooms=rooms)
                return []
            
            logger.info(f"Found {len(response.data)} hotels in {city_code}")
            
            # Get hotel IDs (limit to first 20 for performance)
            all_hotel_ids = [hotel['hotelId'] for hotel in response.data]
            
            # Prioritize known working hotels for common cities
            known_working = {
                'GOI': ['HIGOIB6B', 'FGGOIAZO', 'ILGOI085'],  # Goa hotels that often have availability
                'BOM': ['RTBOMIIB', 'HSBOMADP', 'YXBOMVMT'],  # Mumbai hotels
                'DEL': ['FGDELSWA', 'TADEL115', 'TJDELGUR'],  # Delhi hotels
            }
            
            # If we have known working hotels for this city, prioritize them
            if city_code in known_working:
                priority_ids = [h for h in known_working[city_code] if h in all_hotel_ids]
                other_ids = [h for h in all_hotel_ids if h not in priority_ids]
                hotel_ids = priority_ids + other_ids[:20-len(priority_ids)]
                logger.info(f"Using {len(priority_ids)} known working hotels plus {len(hotel_ids)-len(priority_ids)} others")
            else:
                hotel_ids = all_hotel_ids[:20]
            
            logger.info(f"Selected {len(hotel_ids)} hotel IDs for offer search")
            
            # Now get hotel offers for these hotels
            # Try in smaller batches to avoid API errors
            all_offers = []
            batch_size = 3  # Smaller batch size to avoid errors
            
            for i in range(0, min(len(hotel_ids), 9), batch_size):
                batch = hotel_ids[i:i+batch_size]
                try:
                    logger.info(f"Searching offers for batch {i//batch_size + 1}: {batch}")
                    offers_response = self.amadeus.shopping.hotel_offers_search.get(
                        hotelIds=batch,
                        checkInDate=check_in,
                        checkOutDate=check_out,
                        adults=adults,
                        roomQuantity=rooms
                    )
                    
                    if offers_response.data:
                        all_offers.extend(offers_response.data)
                        logger.info(f"Found {len(offers_response.data)} offers in this batch")
                        
                        # If we have enough offers, stop searching
                        if len(all_offers) >= 5:
                            break
                except Exception as e:
                    logger.warning(f"Error searching batch {batch}: {e}")
                    continue
            
            if all_offers:
                logger.info(f"Found total {len(all_offers)} hotel offers")
                return all_offers
            else:
                logger.warning("No hotel offers available for selected hotels")
                # Try with further out dates
                logger.info("Attempting search with dates 2 weeks out for better availability")
                try:
                    from datetime import datetime, timedelta
                    future_check_in = (datetime.strptime(check_in, "%Y-%m-%d") + timedelta(days=14)).strftime("%Y-%m-%d")
                    future_check_out = (datetime.strptime(check_out, "%Y-%m-%d") + timedelta(days=14)).strftime("%Y-%m-%d")
                    
                    logger.info(f"Retrying with dates: {future_check_in} to {future_check_out}")
                    
                    for i in range(0, min(len(hotel_ids), 6), batch_size):
                        batch = hotel_ids[i:i+batch_size]
                        try:
                            offers_response = self.amadeus.shopping.hotel_offers_search.get(
                                hotelIds=batch,
                                checkInDate=future_check_in,
                                checkOutDate=future_check_out,
                                adults=adults,
                                roomQuantity=rooms
                            )
                            
                            if offers_response.data:
                                logger.info(f"Found {len(offers_response.data)} offers with future dates")
                                # Update the dates in the response to match what was found
                                for offer in offers_response.data:
                                    if 'offers' in offer:
                                        for o in offer['offers']:
                                            o['checkInDate'] = future_check_in
                                            o['checkOutDate'] = future_check_out
                                return offers_response.data
                        except Exception as e:
                            logger.warning(f"Error with future dates batch: {e}")
                            continue
                except Exception as e:
                    logger.error(f"Error adjusting dates: {e}")
                    
                return []
            
            return []
            
        except ResponseError as error:
            logger.error(f"Hotel search error: {error}")
            logger.error(f"Error details - Code: {error.code if hasattr(error, 'code') else 'N/A'}")
            logger.error(f"Error response: {error.response.body if hasattr(error, 'response') else 'N/A'}")
            
            # Try fallback search with coordinates for known cities
            if city_code in ['BOM', 'DEL', 'BLR', 'MAA', 'CCU', 'HYD']:
                logger.info(f"Attempting fallback coordinate search for {city_code}")
                city_coords = {
                    'BOM': (19.0760, 72.8777),  # Mumbai
                    'DEL': (28.7041, 77.1025),  # Delhi
                    'BLR': (12.9716, 77.5946),  # Bangalore
                    'MAA': (13.0827, 80.2707),  # Chennai
                    'CCU': (22.5726, 88.3639),  # Kolkata
                    'HYD': (17.3850, 78.4867),  # Hyderabad
                }
                if city_code in city_coords:
                    lat, lon = city_coords[city_code]
                    return self.search_hotels_by_location(lat, lon, radius=10,
                                                         check_in=check_in,
                                                         check_out=check_out,
                                                         adults=adults,
                                                         rooms=rooms)
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
        """Get detailed information about a specific hotel with offers"""
        try:
            # Using Hotel Search API - Get specific hotel offers with pricing
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
    
    def get_hotel_offer_pricing(self, offer_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed pricing for a specific hotel offer before booking"""
        try:
            # Get offer pricing details
            response = self.amadeus.shopping.hotel_offers.get(
                hotelOfferSearch=offer_id
            )
            
            if response.data:
                logger.info(f"Retrieved pricing for offer {offer_id}")
                return response.data[0]
            return None
            
        except ResponseError as error:
            logger.error(f"Hotel offer pricing error: {error}")
            return None
    
    def create_hotel_booking(self, offer_id: str, guest_data: Dict[str, Any], 
                           payment_data: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Create a hotel booking using the Amadeus Hotel Booking API
        
        Args:
            offer_id: The hotel offer ID to book
            guest_data: Guest information dictionary containing:
                - firstName: str
                - lastName: str
                - email: str
                - phone: str (optional)
                - title: str (MR, MS, MRS, etc.)
            payment_data: Optional payment information
        
        Returns:
            Booking confirmation data or None if failed
        """
        try:
            # First get the offer details to ensure it's still available
            offer_details = self.get_hotel_offer_pricing(offer_id)
            if not offer_details:
                logger.error(f"Could not retrieve offer details for {offer_id}")
                return None
            
            # Prepare booking data
            booking_data = {
                "data": {
                    "offerId": offer_id,
                    "guests": [
                        {
                            "id": 1,
                            "name": {
                                "title": guest_data.get("title", "MR"),
                                "firstName": guest_data["firstName"],
                                "lastName": guest_data["lastName"]
                            },
                            "contact": {
                                "email": guest_data["email"]
                            }
                        }
                    ]
                }
            }
            
            # Add phone if provided
            if guest_data.get("phone"):
                booking_data["data"]["guests"][0]["contact"]["phone"] = guest_data["phone"]
            
            # Add payment if provided
            if payment_data:
                booking_data["data"]["payments"] = [payment_data]
            
            # Create the booking
            logger.info(f"Creating hotel booking for offer {offer_id}")
            response = self.amadeus.booking.hotel_bookings.post(
                body=booking_data
            )
            
            if response.data:
                logger.info(f"Hotel booking created successfully: {response.data[0].get('id')}")
                return response.data[0]
            
            return None
            
        except ResponseError as error:
            logger.error(f"Hotel booking error: {error}")
            logger.error(f"Error details: {error.response.body if hasattr(error, 'response') else 'N/A'}")
            return None
    
    def get_booking_by_id(self, booking_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve booking details by booking ID"""
        try:
            response = self.amadeus.booking.hotel_booking(booking_id).get()
            return response.data if response.data else None
        except ResponseError as error:
            logger.error(f"Error retrieving booking {booking_id}: {error}")
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
        """Main method to process hotel search queries using Hotel List and Search APIs"""
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
        
        # Step 1: Hotel List API - Get city code and find hotels in the city
        city_code = self.get_city_code(location)
        if not city_code:
            logger.error(f"Could not find city code for {location}")
            return None, None, None
        
        # Step 2: Hotel Search API - Get hotel offers with pricing and room details
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
            
            # Add offer IDs to the dataframe for potential booking
            if not filtered_df.empty:
                offer_ids = []
                for idx, hotel_data in enumerate(hotel_info[:len(filtered_df)]):
                    offers = hotel_data.get('offers', [])
                    if offers:
                        offer_ids.append(offers[0].get('id', ''))
                    else:
                        offer_ids.append('')
                
                if len(offer_ids) == len(filtered_df):
                    filtered_df['Offer ID'] = offer_ids
            
            logger.info(f"Created dataframe with {len(filtered_df)} hotels")
            return filtered_df, location, {
                'check_in': check_in, 
                'check_out': check_out,
                'adults': adults,
                'rooms': rooms
            }
        else:
            logger.error("No hotels found or error in forming dataframe")
            return None, None, None
    
    def process_hotel_booking(self, offer_id: str, guest_info: Dict[str, Any]) -> Dict[str, Any]:
        """Process a complete hotel booking flow
        
        Args:
            offer_id: The offer ID from hotel search
            guest_info: Guest information for booking
        
        Returns:
            Booking confirmation or error details
        """
        try:
            # Step 1: Validate offer is still available
            logger.info(f"Validating offer {offer_id} before booking")
            offer_details = self.get_hotel_offer_pricing(offer_id)
            
            if not offer_details:
                return {
                    "success": False,
                    "error": "Offer is no longer available"
                }
            
            # Step 2: Create the booking
            booking_result = self.create_hotel_booking(offer_id, guest_info)
            
            if booking_result:
                return {
                    "success": True,
                    "booking_id": booking_result.get("id"),
                    "confirmation_number": booking_result.get("providerConfirmationId"),
                    "hotel_name": booking_result.get("hotel", {}).get("name"),
                    "total_price": booking_result.get("price", {}).get("total"),
                    "currency": booking_result.get("price", {}).get("currency"),
                    "status": "CONFIRMED",
                    "booking_details": booking_result
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to create booking"
                }
                
        except Exception as e:
            logger.error(f"Error in booking process: {e}")
            return {
                "success": False,
                "error": str(e)
            }