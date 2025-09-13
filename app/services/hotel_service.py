import json
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import pandas as pd
from serpapi import GoogleSearch
from openai import OpenAI
from dotenv import load_dotenv
from app.core.logging import logger
from app.core.config import settings

load_dotenv()


class HotelService:
    def __init__(self):
        # Initialize SerpAPI client
        self.serpapi_key = settings.SERPAPI
        if not self.serpapi_key:
            logger.error("SERPAPI key is not set!")
            raise ValueError("SERPAPI key is required")

        # Initialize OpenAI client
        api_key = settings.OPENAI_API_KEY
        if not api_key:
            logger.error("OPENAI_API_KEY is not set!")
            raise ValueError("OPENAI_API_KEY is required")
        logger.info(f"Initializing OpenAI client with key: {api_key[:10]}...")
        logger.info(f"Initializing SerpAPI client with key: {self.serpapi_key[:10]}...")
        self.openai_client = OpenAI(api_key=api_key)

    def get_city_code(self, location: str) -> Optional[str]:
        """Get city code for hotel search with improved mappings"""
        city_mappings = {
            # Mumbai variations
            'mumbai': 'BOM', 'mumdai': 'BOM', 'mumbay': 'BOM', 'bombay': 'BOM',
            # Delhi variations
            'delhi': 'DEL', 'new delhi': 'DEL', 'newdelhi': 'DEL', 'dehli': 'DEL',
            # Bangalore variations
            'bangalore': 'BLR', 'bengaluru': 'BLR', 'banglore': 'BLR',
            # Chennai variations
            'chennai': 'MAA', 'madras': 'MAA',
            # Goa variations
            'goa': 'GOI', 'panaji': 'GOI', 'panjim': 'GOI',
            # Kolkata variations
            'kolkata': 'CCU', 'calcutta': 'CCU',
            # Hyderabad variations
            'hyderabad': 'HYD', 'hyd': 'HYD',
            # International cities
            'london': 'LON', 'paris': 'PAR', 'new york': 'NYC', 'dubai': 'DXB',
            'singapore': 'SIN', 'bangkok': 'BKK', 'tokyo': 'TYO'
        }

        location_clean = location.lower().strip()
        city_code = city_mappings.get(location_clean)

        if city_code:
            logger.info(f"Using mapped city code {city_code} for {location}")
            return city_code

        # If no direct mapping, try to use as-is (might be already a code)
        if len(location) == 3:
            return location.upper()

        logger.warning(f"No city code mapping found for: {location}")
        return None

    def extract_hotel_info_from_query(self, query: str) -> Optional[Dict[str, Any]]:
        """Extract hotel search parameters from natural language query"""
        current_date_str = datetime.now().strftime('%Y-%m-%d')

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a hotel search assistant. Extract hotel search parameters from queries. "
                    f"Today is {current_date_str}. Extract and return ONLY JSON: "
                    "{"
                    '"location": "destination city name", '
                    '"check_in_date": "YYYY-MM-DD", '
                    '"check_out_date": "YYYY-MM-DD", '
                    '"adults": number, '
                    '"rooms": number, '
                    '"price_range": "budget|moderate|expensive|luxury"'
                    "}"
                )
            },
            {
                "role": "user",
                "content": query
            }
        ]

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.1,
                max_tokens=300,
                response_format={"type": "json_object"}
            )

            response_text = response.choices[0].message.content
            if not response_text:
                return None

            hotel_info = json.loads(response_text)

            # Set defaults
            hotel_info.setdefault('adults', 1)
            hotel_info.setdefault('rooms', 1)
            hotel_info.setdefault('price_range', 'moderate')

            return hotel_info

        except Exception as e:
            logger.error(f"Error extracting hotel info: {e}")
            return None

    def search_hotels_simplified(self, location: str, check_in: str, check_out: str,
                                adults: int = 1, rooms: int = 1) -> List[Dict[str, Any]]:
        """Simple and fast hotel search using SerpAPI Google Hotels"""

        logger.info(f"Searching hotels in {location} from {check_in} to {check_out} for {adults} adults")

        try:
            # Create search parameters
            search_params = {
                "engine": "google_hotels",
                "q": f"hotels in {location}",
                "check_in_date": check_in,
                "check_out_date": check_out,
                "adults": adults,
                "currency": "INR",
                "api_key": self.serpapi_key
            }

            logger.info("Making SerpAPI call for hotel search...")

            # Execute search
            search = GoogleSearch(search_params)
            results = search.get_dict()

            # Debug: Log the response structure
            logger.info(f"SerpAPI response keys: {list(results.keys())}")

            # Handle different response scenarios
            if 'error' in results:
                logger.error(f"SerpAPI error: {results['error']}")
                return []

            # Extract properties from results
            properties = results.get('properties', [])

            if properties:
                logger.info(f"SUCCESS: Found {len(properties)} hotels via SerpAPI")
                return properties[:5]  # Return first 5 hotels for speed
            else:
                # Debug: Check if results exist but with different structure
                if 'hotels' in results:
                    hotels = results.get('hotels', [])
                    logger.info(f"Found hotels in 'hotels' key: {len(hotels)}")
                    return hotels[:5]
                elif 'local_results' in results:
                    local_results = results.get('local_results', [])
                    logger.info(f"Found local_results: {len(local_results)}")
                    # Transform local_results to properties format if needed
                    return local_results[:5]
                else:
                    logger.warning(f"No hotels found for {location}. Available keys: {list(results.keys())}")
                    return []

        except Exception as e:
            logger.error(f"SerpAPI hotel search error: {e}")
            return []

    def create_hotel_dataframe(self, hotel_data: List[Dict[str, Any]]) -> pd.DataFrame:
        """Create structured DataFrame from hotel offers"""
        hotel_details = []

        # Process SerpAPI format instead of Amadeus format
        for property_data in hotel_data:
            try:
                # Extract data from SerpAPI format
                name = property_data.get('name', 'Hotel Available')

                # Extract pricing
                rate_per_night = property_data.get('rate_per_night', {})
                price = 0
                price_str = rate_per_night.get('lowest', '$0')

                # Parse price from string like "$40" or "₹3500"
                if 'extracted_lowest' in rate_per_night:
                    price = float(rate_per_night['extracted_lowest'])
                elif price_str:
                    # Extract number from price string
                    import re
                    price_match = re.search(r'\d+', price_str.replace(',', ''))
                    if price_match:
                        price = float(price_match.group())

                # Extract rating and reviews
                rating = property_data.get('overall_rating', 'N/A')
                reviews = property_data.get('reviews', 0)

                # Extract amenities
                amenities = property_data.get('amenities', [])
                amenities_str = ', '.join(amenities[:4]) if amenities else 'Standard amenities'

                # Extract essential info
                essential_info = property_data.get('essential_info', [])
                room_info = ', '.join(essential_info[:2]) if essential_info else 'Standard Room'

                hotel_detail = {
                    # Frontend expects these exact keys
                    'Hotel Name': name,
                    'Hotel ID': property_data.get('property_token', ''),
                    'Chain Code': property_data.get('type', ''),
                    'Rating': rating,
                    'City': 'Location Available',  # SerpAPI doesn't provide separate city
                    'Country': '',

                    # Pricing information (frontend keys)
                    'Total Price': price,
                    'Price Base': price,
                    'Currency': 'INR',  # We requested INR currency
                    'Price Per Night': price,

                    # Room information (frontend keys)
                    'Room Type': room_info,
                    'Room Description': f"{rating} rating • {reviews} reviews" if reviews else '',
                    'Bed Type': 'Standard',
                    'Beds': 1,

                    # Booking information (frontend keys)
                    'Check-in Time': 'Standard',
                    'Check-out Time': 'Standard',
                    'Adults': 1,
                    'Offer ID': property_data.get('property_token', ''),

                    # Additional details
                    'Amenities': amenities_str,
                    'Cancellation Policy': 'Check with hotel',
                    'Payment Policy': 'Standard payment terms',
                }

                hotel_details.append(hotel_detail)

            except Exception as e:
                logger.error(f"Error processing SerpAPI hotel data: {e}")
                continue

        if not hotel_details:
            logger.warning("No valid hotel details extracted from SerpAPI")
            return pd.DataFrame()

        df = pd.DataFrame(hotel_details)

        # Sort by price (ascending) - handle non-numeric values
        df['Total Price'] = pd.to_numeric(df['Total Price'], errors='coerce').fillna(0)
        df = df.sort_values('Total Price', ascending=True)

        logger.info(f"Created dataframe with {len(df)} hotels from SerpAPI")
        return df

    def process_hotel_search(self, query: str) -> tuple:
        """Main method to process hotel search queries"""
        logger.info(f"Processing hotel search query: {query}")

        # Extract information from query
        result = self.extract_hotel_info_from_query(query)
        if not result:
            logger.error("Failed to extract hotel information from query")
            return None, None, None

        logger.info(f"Extracted hotel info: {result}")

        # Extract search parameters
        location = result['location']
        check_in = result['check_in_date']
        check_out = result['check_out_date']
        adults = result.get('adults', 1)
        rooms = result.get('rooms', 1)

        # Search hotels using SerpAPI (no need for city code conversion)
        hotel_offers = self.search_hotels_simplified(location, check_in, check_out, adults, rooms)

        if not hotel_offers:
            logger.error("No hotel offers found")
            return None, None, None

        # Create DataFrame
        hotel_df = self.create_hotel_dataframe(hotel_offers)

        if hotel_df.empty:
            logger.warning(f"No hotel availability found in {location} for {result['check_in_date']} to {result['check_out_date']}")
            return None, location, result

        logger.info(f"Found {len(hotel_df)} hotels from Amadeus API")
        if len(hotel_df) > 0:
            sample_hotel = hotel_df.iloc[0]
            logger.info(f"Sample hotel data - Name: {sample_hotel['Hotel Name']}, Price: {sample_hotel['Total Price']}, Currency: {sample_hotel['Currency']}")

        return hotel_df, location, result

    def get_hotel_details(self, hotel_id: str, check_in: str, check_out: str,
                         adults: int = 1, rooms: int = 1) -> Optional[Dict[str, Any]]:
        """Get detailed hotel information by hotel ID (SerpAPI doesn't support individual hotel lookup)"""
        logger.info(f"Hotel details not supported with SerpAPI for hotel {hotel_id}")
        return {
            "message": "Hotel details available on booking",
            "hotel_id": hotel_id,
            "status": "available"
        }