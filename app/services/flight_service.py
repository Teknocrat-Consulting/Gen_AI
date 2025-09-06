import os
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import pandas as pd
from amadeus import Client, ResponseError
from openai import OpenAI
from dotenv import load_dotenv
import requests
from app.core.logging import logger
from app.core.config import settings

load_dotenv()


class FlightService:
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
            # You can use a free API like exchangerate-api.com or fixer.io
            # For now, using a fallback rate
            # To use a real API, uncomment and add your API key:
            # response = requests.get('https://api.exchangerate-api.com/v4/latest/EUR')
            # data = response.json()
            # return data['rates']['INR']
            
            # Using a reasonable approximate rate
            return 90.50
        except Exception as e:
            logger.warning(f"Could not fetch exchange rate: {e}, using default")
            return 90.50
    
    def get_airport_code(self, location: str) -> Optional[str]:
        try:
            response = self.amadeus.reference_data.locations.get(
                keyword=location,
                subType='AIRPORT'
            )
            if response.data:
                return response.data[0]['iataCode']
            else:
                logger.warning(f"No airport code found for {location}")
                return None
        except ResponseError as error:
            logger.error(f"Error finding airport code for {location}: {error}")
            return None
    
    def extract_flight_info_from_query(self, query: str) -> Optional[Dict[str, Any]]:
        today = datetime.now()
        current_date_str = today.strftime('%Y-%m-%d')
        
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an assistant that helps extract flight information from user queries. "
                    f"CRITICAL: Today's date is {current_date_str}. The current year is {today.year}. "
                    f"ALL dates MUST be in {today.year} or later. NEVER use years like 2022, 2023, or 2024. "
                    "Extract the following details from the query: "
                    "1. location_origin: The departure city or airport (use IATA codes like BOM for Mumbai, DEL for Delhi, etc.) "
                    "   IMPORTANT: If origin is not specified in the query, return 'MISSING' as the value. "
                    "2. location_destination: The destination city or airport (use IATA codes) "
                    "   For states like Rajasthan, use JAI (Jaipur), for Goa use GOI, for Kerala use COK (Kochi) "
                    f"3. departure_date: The date of departure (MUST be {current_date_str} or later, format: YYYY-MM-DD) "
                    "4. adults: The number of adult passengers (default is 1 if not specified) "
                    f"For relative dates: 'tomorrow' = {(today + timedelta(days=1)).strftime('%Y-%m-%d')}, "
                    f"'next week' = {(today + timedelta(days=7)).strftime('%Y-%m-%d')}, "
                    f"'next monday' = calculate from today {current_date_str}. "
                    "Provide the information in JSON format ONLY, no extra text: "
                    '{"location_origin": "XXX", "location_destination": "XXX", "departure_date": "YYYY-MM-DD", "adults": number}'
                )
            },
            {
                "role": "user",
                "content": query
            }
        ]
        
        try:
            logger.info(f"Calling OpenAI with model: gpt-4o-mini")
            logger.info(f"System message: {messages[0]['content'][:200]}...")
            logger.info(f"User message: {messages[1]['content']}")
            
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
                logger.error(f"Full response object: {response}")
                return None
            
            if not response_text:
                logger.error("Response content is empty string")
                return None
                
            response_text = response_text.strip()
            logger.info(f"OpenAI response: {response_text}")
            
            # Handle potential markdown code blocks or extra text
            if "```json" in response_text:
                # Extract JSON from markdown code block
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                if end != -1:
                    response_text = response_text[start:end].strip()
            elif "```" in response_text:
                # Extract from generic code block
                start = response_text.find("```") + 3
                end = response_text.find("```", start)
                if end != -1:
                    response_text = response_text[start:end].strip()
            
            # If response contains extra text before JSON, try to extract just the JSON part
            if response_text and not response_text.startswith("{"):
                # Look for the first { and last }
                start_idx = response_text.find("{")
                end_idx = response_text.rfind("}")
                if start_idx != -1 and end_idx != -1:
                    response_text = response_text[start_idx:end_idx+1]
            
            flight_info = json.loads(response_text)
            
            required_keys = ["location_origin", "location_destination", "departure_date", "adults"]
            if not all(key in flight_info for key in required_keys):
                raise ValueError("Incomplete response from LLM")
            
            # Check if origin is missing
            if flight_info.get("location_origin") in ["MISSING", "XXX", "", None] or len(str(flight_info.get("location_origin", ""))) != 3:
                logger.warning(f"Origin not specified or invalid: {flight_info.get('location_origin')}")
                return None  # Return None to indicate origin is missing
            
            # Handle state names in destination
            state_to_airport = {
                "RAJ": "JAI",  # Rajasthan -> Jaipur
                "GOA": "GOI",  # Goa
                "KER": "COK",  # Kerala -> Kochi
                "PUN": "PNQ",  # Punjab -> Pune
                "GUJ": "AMD",  # Gujarat -> Ahmedabad
            }
            
            dest = flight_info.get("location_destination", "")
            if dest in state_to_airport:
                logger.info(f"Converting state code {dest} to airport {state_to_airport[dest]}")
                flight_info["location_destination"] = state_to_airport[dest]
            
            # Validate and fix departure date
            today = datetime.now()
            tomorrow = today + timedelta(days=1)
            
            try:
                dep_date = datetime.strptime(flight_info["departure_date"], "%Y-%m-%d")
                # If date is in the past, use tomorrow
                if dep_date.date() < today.date():
                    logger.warning(f"Departure date {flight_info['departure_date']} is in the past, using tomorrow")
                    flight_info["departure_date"] = tomorrow.strftime("%Y-%m-%d")
            except:
                logger.warning(f"Invalid date format, using tomorrow")
                flight_info["departure_date"] = tomorrow.strftime("%Y-%m-%d")
            
            return flight_info
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            logger.error(f"Failed to parse response: {response_text if 'response_text' in locals() else 'No response text'}")
            return None
        except ValueError as e:
            logger.error(f"Value error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error extracting flight info: {e}")
            return None
    
    def get_flight_info(self, location_origin: str, location_destination: str, 
                       departure_date: str, adults: int = 1) -> List[Dict[str, Any]]:
        origin_code = location_origin
        destination_code = location_destination
        
        if not origin_code or not destination_code:
            logger.error("Could not find airport codes for the provided locations.")
            return []
        
        try:
            response = self.amadeus.shopping.flight_offers_search.get(
                originLocationCode=origin_code,
                destinationLocationCode=destination_code,
                departureDate=departure_date,
                adults=adults,
                max=10
            )
            return response.data if response.data else []
        except ResponseError as error:
            logger.error(f"Flight search error: {error}")
            return []
    
    def create_flight_dataframe(self, flight_data: List[Dict[str, Any]]) -> pd.DataFrame:
        flight_details = []
        
        # Use the exchange rate from initialization
        EUR_TO_INR = self.exchange_rate
        
        airlines = set()
        for offer in flight_data:
            for segment in offer['itineraries'][0]['segments']:
                airlines.add(segment['carrierCode'])
        
        airline_names = {}
        for airline_code in airlines:
            try:
                airline_response = self.amadeus.reference_data.airlines.get(airlineCodes=airline_code)
                if airline_response.data:
                    airline_names[airline_code] = airline_response.data[0]['commonName']
            except Exception as e:
                logger.warning(f"Could not fetch airline name for {airline_code}: {e}")
                airline_names[airline_code] = airline_code
        
        for flight in flight_data:
            total_price = flight['price'].get('total', '')
            currency = flight['price'].get('currency', '')
            
            # Convert EUR to INR
            if currency == 'EUR' and total_price:
                try:
                    price_eur = float(total_price)
                    price_inr = price_eur * EUR_TO_INR
                    total_price = f"{price_inr:.2f}"
                    currency = 'INR'
                except (ValueError, TypeError):
                    logger.warning(f"Could not convert price: {total_price}")
            
            one_way = len(flight['itineraries']) == 1
            
            for itinerary in flight['itineraries']:
                num_stops = len(itinerary['segments']) - 1
                
                for segment in itinerary['segments']:
                    airline_code = segment.get('carrierCode', '')
                    airline_name = airline_names.get(airline_code, airline_code)
                    departure = segment['departure'].get('at', '')
                    arrival = segment['arrival'].get('at', '')
                    
                    cabin = ''
                    if flight.get('travelerPricings'):
                        for pricing in flight['travelerPricings']:
                            if pricing.get('fareDetailsBySegment'):
                                cabin = pricing['fareDetailsBySegment'][0].get('cabin', '')
                                break
                    
                    flight_details.append({
                        "Airline Code": airline_code,
                        "Airline Name": airline_name,
                        "Departure": departure,
                        "Arrival": arrival,
                        "Total Price": total_price,
                        "Currency": currency,
                        "Number of Stops": num_stops,
                        "Cabin": cabin,
                        "One Way": one_way
                    })
        
        df = pd.DataFrame(flight_details)
        df.drop_duplicates(inplace=True)
        return df
    
    def process_flight_search(self, query: str) -> tuple:
        logger.info(f"Processing flight search query: {query}")
        
        result = self.extract_flight_info_from_query(query)
        if not result:
            logger.warning("Could not extract flight info - origin might be missing")
            return None, None, None
        
        logger.info(f"Extracted flight info: {result}")
        
        origin = result['location_origin']
        destination = result['location_destination']
        departure_date = result['departure_date']
        adults = result['adults']
        
        flight_info = self.get_flight_info(origin, destination, departure_date, adults)
        
        if isinstance(flight_info, list) and flight_info:
            flight_df = self.create_flight_dataframe(flight_info)
            logger.info(f"Created dataframe with {len(flight_df)} flights")
            return flight_df, origin, destination
        else:
            logger.error("No flights found or error in forming dataframe")
            return None, None, None