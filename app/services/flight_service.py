import os
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


class FlightService:
    def __init__(self):
        self.amadeus = Client(
            client_id=settings.API_Key,
            client_secret=settings.API_Secret
        )
        self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
    
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
                    f"Today is {current_date_str}. Extract the following details from the query: "
                    "1. location_origin: The departure city or airport, ensure it corresponds to a valid airport code "
                    "2. location_destination: The destination city or airport, ensure it corresponds to a valid airport code "
                    "3. departure_date: The date of departure "
                    "4. adults: The number of adult passengers. (If there is no information regarding this then consider only 1 Adult is there)"
                    "If the query specifies a relative date (e.g., 'next Monday'), convert it to an absolute date. "
                    "Provide the information in JSON format as follows: "
                    '{"location_origin": "origin", "location_destination": "destination", "departure_date": "YYYY-MM-DD", "adults": number_of_adults}'
                )
            },
            {
                "role": "user",
                "content": query
            }
        ]
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=300,
                temperature=0.1
            )
            
            response_text = response.choices[0].message.content.strip()
            flight_info = json.loads(response_text)
            
            required_keys = ["location_origin", "location_destination", "departure_date", "adults"]
            if not all(key in flight_info for key in required_keys):
                raise ValueError("Incomplete response from LLM")
            
            return flight_info
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Error extracting flight info: {e}")
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