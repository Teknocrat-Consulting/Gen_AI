import os
import json
import openai
from datetime import datetime, timedelta
from dotenv import load_dotenv
from openai import OpenAI
import pandas as pd
import time
from amadeus import Client, ResponseError
from langchain_experimental.agents import create_pandas_dataframe_agent
from langchain_openai import ChatOpenAI

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
client_id = os.getenv("client_id")
client_secret = os.getenv("client_secret")

amadeus = Client(
    client_id='H4S446vjDRHVJn8C0ZDRkXSLt03AvOGp',
    client_secret='2MCfJEBzkSLqYla0'

 )

client = OpenAI()

df_reference = pd.read_csv("code_reference.csv")
df_reference = df_reference[["IATA","Airline"]]

airline = list(df_reference.Airline.values)
code = list(df_reference.IATA.values)

code_dict = dict(zip(code,airline))

def get_airport_code(location):
    """Get the airport code for a given location string."""
    try:
        response = amadeus.reference_data.locations.get(
            keyword=location,
            subType='AIRPORT'
        )
        if response.data:
            # Return the first matching airport code
            return response.data[0]['iataCode']
        else:
            print(f"No airport code found for {location}")
            return None
    except ResponseError as error:
        print(f"Error finding airport code for {location}: {error}")
        return None

def extract_flight_info_from_query(query):
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

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        max_tokens=300,
        temperature=0.1 
    )

    response_text = response.choices[0].message.content.strip()
    try:
        flight_info = json.loads(response_text)
        # Basic validation
        required_keys = ["location_origin", "location_destination", "departure_date", "adults"]
        if not all(key in flight_info for key in required_keys):
            raise ValueError("Incomplete response from LLM")
        return flight_info
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Error extracting flight info: {e}")
        return None

def get_flight_info(location_origin, location_destination, departure_date, adults=1,retries=3, delay=2):
    """Get flight information between two locations."""
    origin_code = location_origin
    destination_code = location_destination
    
    if not origin_code or not destination_code:
        return "Could not find airport codes for the provided locations."

    try:
        response = amadeus.shopping.flight_offers_search.get(
            originLocationCode=origin_code,
            destinationLocationCode=destination_code,
            departureDate=departure_date,
            adults=adults
        )
        return response.data
    except Exception as error:
        if retries > 0:
            print(f"Rate limit exceeded. Retrying in {delay} seconds...")
            time.sleep(delay)
            return get_flight_info(location_origin, location_destination, departure_date, retries - 1, delay * 2)
        else:
            print(f"Failed to get flight information: {error}")
            return None

def create_flight_dataframe(flight_data):
    """Create a Pandas DataFrame from the flight data."""
    flight_details = []

    # Get the airline names from the flight offers
    airlines = set()
    for offer in flight_data:
        for segment in offer['itineraries'][0]['segments']:
            airlines.add(segment['carrierCode'])

    #print("Airlines :", airlines)

    # Fetch Airline names using reference data
    airline_names_f1 = {}
    for airline_code in airlines:
        if airline_code in code_dict:
            airline_names_f1[airline_code] = code_dict[airline_code]

    #print("airline_names_f1 : ",airline_names_f1)
    
    airline_new = set(airline_names_f1.keys())
    airline_names_2 = airlines - airline_new    


    # Fetch airline names using the IATA codes
    airline_names_f2 = {}
    for airline_code in airline_names_2:
        try:
            time.sleep(3)
            airline_response = amadeus.reference_data.airlines.get(airlineCodes=airline_code)
            if airline_response.data:
                    airline_names_f2[airline_code] = airline_response.data[0]['commonName']
        except Exception as e:
            airline_names_f2[airline_code] = ""

    #print("airline_names_f2 : ",airline_names_f2)

    airline_names_final = airline_names_f1 | airline_names_f2

    # print("Airline names : ",airline_names)

    for flight in flight_data:
        total_price = flight['price'].get('total', '')
        currency = flight['price'].get('currency', '')
        one_way = len(flight['itineraries']) == 1
        
        for itinerary in flight['itineraries']:
            num_stops = len(itinerary['segments']) - 1
            
            for segment in itinerary['segments']:
                airline_code = segment.get('carrierCode', '')
                airline_name =  airline_names_final.get(segment['carrierCode'], '')
                from_ = segment.get(0, {}).get('departure', {}).get('iataCode', '')
                from_terminal = segment.get(0, {}).get('departure', {}).get('terminal', '')
                to = segment.get(0, {}).get('arrival', {}).get('iataCode', '')
                to_terminal = segment.get(0, {}).get('arrival', {}).get('terminal', '')
                departure = segment['departure'].get('at', '')
                arrival = segment['arrival'].get('at', '')
                cabin = segment.get('travelerPricings', [{}])[0].get('fareDetailsBySegment', [{}])[0].get('cabin', '')
                pricing_detail = segment.get('pricingDetailPerAdult', {})
               

                flight_details.append({
                    "Airline Code": airline_code,
                    "Airline Name": airline_name,
                    "Departure": departure,
                    "Arrival": arrival,
                    "Total Price": total_price,
                    "Currency": currency,
                    "Number of Stops": num_stops,
                    #"Cabin": cabin,
                    "One Way": one_way})
                   
    data = pd.DataFrame(flight_details)
    data.drop_duplicates(inplace=True)
    return data




def prompt_query(query,origin,destination):
    main_prompt = f"""
    "You are an assistant that helps to answer queries based on the flight information dataframe provided. 
    This is a dataframe containing flight information from {origin} to {destination}. 
    So answer the question by analyzing dataframe and give direct answers to query and please refrain from explaining how things are calculated. 
    Don't give the code but analyze the dataframe, if asked about travel time or journey duration, use the "Journey Duration" column and display it.
    Also display the arrival and departure time in nice format and stick to just answering the questions, don't give unnecessary information
    When the user asks flight information about location which differ from what the dataframe has information about then tell the user to enter "quit" and start a new conversation"
   
    """
    system_prompt = "System Prompt : " + main_prompt
    query_ask = "Query : " + query
    return f"{system_prompt}\n{query_ask}"

def run(query):
    print("Extracting fields from Query")
    print("*"*125)
    result = extract_flight_info_from_query(query)
    print("Information extracted from query : ",result)
    print("*"*125)

    origin = result['location_origin']
    destination = result['location_destination']
    departure_date = result['departure_date']
    adults = result['adults']

    flight_info = get_flight_info(origin, destination, departure_date)

    # Convert the flight info to a DataFrame
    if isinstance(flight_info, list):
        flight_df = create_flight_dataframe(flight_info)
        flight_df['Departure'] = pd.to_datetime(flight_df['Departure'])
        flight_df['Arrival'] = pd.to_datetime(flight_df['Arrival'])

        # Calculate the journey duration
        flight_df['Journey Duration'] = flight_df['Arrival'] - flight_df['Departure']
        print("Dataframe : ",flight_df)
        print("*"*125)
        flight_df.to_csv(f"{origin}" + "_" + f"{destination}.csv")
        return flight_df,origin,destination
    else:
        print("Error in forming Dataframe")

    print("Dataframe : ",flight_df)
    print("*"*125)

