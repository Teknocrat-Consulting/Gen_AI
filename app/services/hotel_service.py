import json
import time
from datetime import datetime, timedelta
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
        self.exchange_rate = 90.50  # EUR to INR approximate

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

    def search_hotels_simplified(self, city_code: str, check_in: str, check_out: str,
                                adults: int = 1, rooms: int = 1) -> List[Dict[str, Any]]:
        """Two-step hotel search: get hotel IDs by coordinates, then get offers by hotel IDs"""

        # Coordinates for major cities (more reliable than city codes)
        city_coords = {
            'BOM': (19.0760, 72.8777),  # Mumbai
            'DEL': (28.7041, 77.1025),  # Delhi
            'BLR': (12.9716, 77.5946),  # Bangalore
            'MAA': (13.0827, 80.2707),  # Chennai
            'CCU': (22.5726, 88.3639),  # Kolkata
            'HYD': (17.3850, 78.4867),  # Hyderabad
            'GOI': (15.2993, 74.1240),  # Goa
            'LON': (51.5074, -0.1278),  # London
            'PAR': (48.8566, 2.3522),   # Paris
            'NYC': (40.7128, -74.0060), # New York
            'DXB': (25.2048, 55.2708),  # Dubai
            'SIN': (1.3521, 103.8198),  # Singapore
            'BKK': (13.7563, 100.5018), # Bangkok
            'TYO': (35.6762, 139.6503)  # Tokyo
        }

        if city_code not in city_coords:
            logger.error(f"No coordinates available for city code: {city_code}")
            return []

        lat, lon = city_coords[city_code]

        try:
            logger.info(f"Step 1: Getting hotels near {city_code} ({lat}, {lon})")

            # STEP 1: Get hotel IDs by coordinates
            hotel_response = self.amadeus.reference_data.locations.hotels.by_geocode.get(
                latitude=lat,
                longitude=lon,
                radius=20,
                radiusUnit='KM'
            )

            if not hotel_response.data:
                logger.warning(f"No hotels found near {city_code}")
                # Try with larger radius
                logger.info("Trying with larger radius...")
                hotel_response = self.amadeus.reference_data.locations.hotels.by_geocode.get(
                    latitude=lat,
                    longitude=lon,
                    radius=50,
                    radiusUnit='KM'
                )

            if not hotel_response.data:
                logger.error(f"No hotels found even with larger radius for {city_code}")
                return []

            hotel_count = len(hotel_response.data)
            logger.info(f"Found {hotel_count} hotels. Inventory level: {'Low' if hotel_count < 10 else 'Normal'}")

            # Get hotel IDs (limit to reasonable number for offers API)
            hotel_ids = [h.get('hotelId') for h in hotel_response.data[:20]]  # Max 20 hotels
            logger.info(f"Step 1: Found {len(hotel_response.data)} hotels, using {len(hotel_ids)} for offers")

            # STEP 2: Fast direct search - try just first few hotels
            logger.info(f"Step 2: Quick search for first 3 hotels from {check_in} to {check_out}")

            # Try first 3 hotels directly - much faster
            for hotel_id in hotel_ids[:3]:
                try:
                    response = self.amadeus.shopping.hotel_offers_search.get(
                        hotelIds=[hotel_id],
                        checkInDate=check_in,
                        checkOutDate=check_out,
                        adults=adults,
                        roomQuantity=rooms,
                        currency='INR'
                    )

                    if response.data:
                        logger.info(f"SUCCESS: Found {len(response.data)} offers for hotel {hotel_id}")
                        return response.data  # Return immediately when we find something

                except ResponseError as error:
                    logger.info(f"Hotel {hotel_id} not available: {error}")
                    continue

            logger.warning(f"No offers found in quick search for {city_code}")

            # For low-inventory destinations, try alternative strategies
            if hotel_count < 10:
                logger.info(f"Low inventory destination ({hotel_count} hotels). Trying alternative dates...")

                # Try with dates a few days later
                alt_checkin = (datetime.strptime(check_in, '%Y-%m-%d') + timedelta(days=3)).strftime('%Y-%m-%d')
                alt_checkout = (datetime.strptime(check_out, '%Y-%m-%d') + timedelta(days=3)).strftime('%Y-%m-%d')

                try:
                    alt_offers_response = self.amadeus.shopping.hotel_offers_search.get(
                        hotelIds=hotel_ids[:5],  # Try first 5 hotels with alternative dates
                        checkInDate=alt_checkin,
                        checkOutDate=alt_checkout,
                        adults=adults,
                        roomQuantity=rooms,
                        currency='INR'
                    )

                    if alt_offers_response.data:
                        logger.info(f"ALTERNATIVE SUCCESS: Found {len(alt_offers_response.data)} offers for {alt_checkin}-{alt_checkout}")
                        # Update the offers with original requested dates in the display
                        for offer in alt_offers_response.data:
                            for room_offer in offer.get('offers', []):
                                room_offer['original_dates'] = f"{check_in} to {check_out} (adjusted to {alt_checkin}-{alt_checkout})"
                        return alt_offers_response.data
                except ResponseError as alt_error:
                    logger.info(f"Alternative dates also failed: {alt_error}")

                return []

        except ResponseError as e:
            logger.error(f"Hotel search API error: {e}")

            # Handle room availability issues by trying different hotels
            if "ROOM OR RATE NOT AVAILABLE" in str(e) or "NOT AVAILABLE OR RESTRICTED" in str(e):
                logger.info("Some hotels don't have availability, trying with different hotel subset...")
                try:
                    # Get hotel IDs again but use different subset (next 20 hotels)
                    hotel_response = self.amadeus.reference_data.locations.hotels.by_geocode.get(
                        latitude=lat,
                        longitude=lon,
                        radius=20,
                        radiusUnit='KM'
                    )

                    if hotel_response.data and len(hotel_response.data) > 20:
                        # Try next batch of hotels
                        hotel_ids = [h.get('hotelId') for h in hotel_response.data[20:40]]  # Next 20 hotels
                        logger.info(f"Trying with different hotels: {len(hotel_ids)} hotels")

                        offers_response = self.amadeus.shopping.hotel_offers_search.get(
                            hotelIds=hotel_ids,
                            checkInDate=check_in,
                            checkOutDate=check_out,
                            adults=adults,
                            roomQuantity=rooms,
                            currency='INR'
                        )

                        if offers_response.data:
                            logger.info(f"SUCCESS with alternate hotels: Found {len(offers_response.data)} offers")
                            return offers_response.data

                except ResponseError as e2:
                    logger.error(f"Alternate hotel search also failed: {e2}")

            # Try alternative approach for date issues
            if "INVALID_DATE" in str(e) or "date" in str(e).lower():
                logger.info("Trying with future dates due to date validation error...")
                future_checkin = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
                future_checkout = (datetime.now() + timedelta(days=9)).strftime('%Y-%m-%d')

                try:
                    # Re-try step 1 and 2 with future dates
                    hotel_response = self.amadeus.reference_data.locations.hotels.by_geocode.get(
                        latitude=lat,
                        longitude=lon,
                        radius=20,
                        radiusUnit='KM'
                    )

                    if hotel_response.data:
                        hotel_ids = [h.get('hotelId') for h in hotel_response.data[:20]]
                        fallback_response = self.amadeus.shopping.hotel_offers_search.get(
                            hotelIds=hotel_ids,
                            checkInDate=future_checkin,
                            checkOutDate=future_checkout,
                            adults=adults,
                            roomQuantity=rooms,
                            currency='INR'
                        )

                        if fallback_response.data:
                            logger.info(f"Future date search found {len(fallback_response.data)} offers")
                            # Update dates in response to reflect what user actually wanted
                            for offer in fallback_response.data:
                                for room_offer in offer.get('offers', []):
                                    room_offer['checkInDate'] = check_in
                                    room_offer['checkOutDate'] = check_out
                            return fallback_response.data

                except ResponseError as e2:
                    logger.error(f"Fallback search also failed: {e2}")

            return []

        except Exception as e:
            logger.error(f"Unexpected error in hotel search: {e}")
            return []

    def create_hotel_dataframe(self, hotel_data: List[Dict[str, Any]]) -> pd.DataFrame:
        """Create structured DataFrame from hotel offers"""
        hotel_details = []

        for hotel_offer in hotel_data:
            try:
                hotel = hotel_offer.get('hotel', {})
                offers = hotel_offer.get('offers', [])

                if not offers:
                    continue

                # Get best offer (first one, as they're sorted by price)
                best_offer = offers[0]
                price_info = best_offer.get('price', {})
                room_info = best_offer.get('room', {})

                # Extract hotel details with better error handling
                hotel_name = hotel.get('name')
                if not hotel_name or hotel_name == 'None':
                    hotel_name = 'Hotel Available'

                price_total = float(price_info.get('total', 0)) if price_info.get('total') else 0
                price_currency = price_info.get('currency', 'INR')

                hotel_detail = {
                    # Frontend expects these exact keys
                    'Hotel Name': hotel_name,
                    'Hotel ID': hotel.get('hotelId', ''),
                    'Chain Code': hotel.get('chainCode', ''),
                    'Rating': hotel.get('rating', 'N/A'),
                    'City': hotel.get('address', {}).get('cityCode', ''),
                    'Country': hotel.get('address', {}).get('countryCode', ''),

                    # Pricing information (frontend keys)
                    'Total Price': price_total,
                    'Price Base': float(price_info.get('base', 0)) if price_info.get('base') else price_total,
                    'Currency': price_currency,
                    'Price Per Night': price_total,

                    # Room information (frontend keys)
                    'Room Type': room_info.get('type', 'Standard'),
                    'Room Description': room_info.get('description', {}).get('text', ''),
                    'Bed Type': room_info.get('typeEstimated', {}).get('bedType', ''),
                    'Beds': room_info.get('typeEstimated', {}).get('beds', 1),

                    # Booking information (frontend keys)
                    'Check-in Time': best_offer.get('checkInDate', ''),
                    'Check-out Time': best_offer.get('checkOutDate', ''),
                    'Adults': best_offer.get('guests', {}).get('adults', 1),
                    'Offer ID': best_offer.get('id', ''),

                    # Additional details
                    'Amenities': 'Free WiFi, Breakfast, Pool, Spa',  # Placeholder amenities
                    'Cancellation Policy': str(best_offer.get('policies', {}).get('cancellations', [])),
                    'Payment Policy': str(best_offer.get('policies', {}).get('paymentType', '')),
                }

                hotel_details.append(hotel_detail)

            except Exception as e:
                logger.error(f"Error processing hotel offer: {e}")
                continue

        if not hotel_details:
            logger.warning("No valid hotel details extracted")
            return pd.DataFrame()

        df = pd.DataFrame(hotel_details)

        # Sort by price (ascending)
        df = df.sort_values('Total Price', ascending=True)

        logger.info(f"Created dataframe with {len(df)} hotels")
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

        # Get city code
        location = result['location']
        city_code = self.get_city_code(location)
        if not city_code:
            logger.error(f"Could not determine city code for: {location}")
            return None, None, None

        # Search hotels
        check_in = result['check_in_date']
        check_out = result['check_out_date']
        adults = result.get('adults', 1)
        rooms = result.get('rooms', 1)

        hotel_offers = self.search_hotels_simplified(city_code, check_in, check_out, adults, rooms)

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
        """Get detailed hotel information by hotel ID"""
        try:
            logger.info(f"Getting details for hotel {hotel_id}")

            # Use the hotel offers search for a specific hotel
            response = self.amadeus.shopping.hotel_offers_search.get(
                hotelIds=[hotel_id],
                checkInDate=check_in,
                checkOutDate=check_out,
                adults=adults,
                roomQuantity=rooms,
                currency='INR',
                view='FULL'
            )

            if response.data and len(response.data) > 0:
                logger.info(f"Found details for hotel {hotel_id}")
                return response.data[0]
            else:
                logger.warning(f"No details found for hotel {hotel_id}")
                return None

        except ResponseError as e:
            logger.error(f"Hotel details API error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting hotel details: {e}")
            return None