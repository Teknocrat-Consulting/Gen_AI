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
import re
from datetime import timedelta
from dateutil import parser

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
# client_id = os.getenv("client_id")
# client_secret = os.getenv("client_secret")

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
        
def extract_data_json(json_str):
    extracted_info = {
    'itineraries': [
        {
            'duration': item['duration'],
            'segments': [
                {
                    'departure': {
                        'iataCode': seg['departure']['iataCode'],
                        'at': seg['departure']['at']
                    },
                    'arrival': {
                        'iataCode': seg['arrival']['iataCode'],
                        'at': seg['arrival']['at']
                    },
                    'carrierCode': seg['carrierCode'],
                    'duration': seg['duration'],
                    'numberOfStops': seg['numberOfStops']
                } for seg in item['segments']
            ]
        } for item in json_str['itineraries']
    ],
    'price': json_str['price']
}

# Convert the extracted info to a JSON string with proper formatting
    extracted_info_json_str = json.dumps(extracted_info, indent=1)
    return extracted_info_json_str

def parse_json_to_df(json_objects):
    records = []

    for obj in json_objects:
        itineraries = obj.get('itineraries', [])
        price_info = obj.get('price', {})

        for itinerary in itineraries:
            itinerary_duration = itinerary.get('duration', '')
            segments = itinerary.get('segments', [])
            
            # Initialize record with general fields
            record = {
                'itinerary_duration': itinerary_duration,
                'price_currency': price_info.get('currency', ''),
                'price_total': price_info.get('total', ''),
                'price_base': price_info.get('base', ''),
                'price_grandTotal': price_info.get('grandTotal', '')
            }

            # Add segment-specific fields
            for i, segment in enumerate(segments):
                departure = segment.get('departure', {})
                arrival = segment.get('arrival', {})

                # Create hop-specific columns
                record[f'hop{i+1}_departure_iata'] = departure.get('iataCode', '')
                record[f'hop{i+1}_departure_time'] = departure.get('at', '')
                record[f'hop{i+1}_arrival_iata'] = arrival.get('iataCode', '')
                record[f'hop{i+1}_arrival_time'] = arrival.get('at', '')
                record[f'hop{i+1}_carrier_code'] = segment.get('carrierCode', '')
                record[f'hop{i+1}_duration'] = segment.get('duration', '')
                record[f'hop{i+1}_number_of_stops'] = segment.get('numberOfStops', '')

            records.append(record)

    return pd.DataFrame(records)

def convert_duration(duration_str):
    if pd.isna(duration_str):
        return None
    match = re.match(r'PT(\d+H)?(\d+M)?', duration_str)
    if not match:
        return None
    hours = int(match.group(1)[:-1]) if match.group(1) else 0
    minutes = int(match.group(2)[:-1]) if match.group(2) else 0
    return timedelta(hours=hours, minutes=minutes)


# Calculate layover time
def calculate_layover(row, dep_col, arr_col):
    if pd.isna(row[dep_col]) or pd.isna(row[arr_col]):
        return None
    return parser.parse(row[dep_col]) - parser.parse(row[arr_col])

def process_dataframe(flight_df):
    if "hop3_number_of_stops" in list(flight_df.columns):
        flight_df.drop(["hop1_number_of_stops",	"hop2_number_of_stops",	"hop3_number_of_stops"],axis=1,inplace=True)
    elif "hop2_number_of_stops" in list(flight_df.columns) and "hop3_number_of_stops" not in list(flight_df.columns): 
        flight_df.drop(["hop1_number_of_stops",	"hop2_number_of_stops"],axis=1,inplace=True)
    stops = [x for x in flight_df.columns if "number_of_stops" in x.lower()]
    for col in flight_df.columns:
        if 'duration' in col:
            flight_df[col] = flight_df[col].apply(convert_duration)

    # Rename columns
    flight_df.rename(columns={
        'hop1_departure_iata': 'origin_departure_iata',
        'hop1_departure_time': 'origin_departure_time',
        'hop1_arrival_iata': 'origin_arrival_iata',
        'hop1_arrival_time': 'origin_arrival_time',
        'hop1_carrier_code': 'origin_carrier_code',
        'hop1_duration': 'origin_duration',
        'hop2_departure_iata': 'hop1_departure_iata',
        'hop2_departure_time': 'hop1_departure_time',
        'hop2_arrival_iata': 'hop1_arrival_iata',
        'hop2_arrival_time': 'hop1_arrival_time',
        'hop2_carrier_code': 'hop1_carrier_code',
        'hop2_duration': 'hop1_duration',
        'hop3_departure_iata': 'hop2_departure_iata',
        'hop3_departure_time': 'hop2_departure_time',
        'hop3_arrival_iata': 'hop2_arrival_iata',
        'hop3_arrival_time': 'hop2_arrival_time',
        'hop3_carrier_code': 'hop2_carrier_code',
        'hop3_duration': 'hop2_duration'
    }, inplace=True)

    # Calculate the number of hops
    if "hop2_departure_iata" in list(flight_df.columns):
        flight_df['number_of_hops'] = flight_df[['origin_departure_iata', 'hop1_departure_iata', 'hop2_departure_iata']].notna().sum(axis=1) - 1
    elif "hop1_departure_iata" in list(flight_df.columns) and "hop2_departure_iata" not in list(flight_df.columns): 
        flight_df['number_of_hops'] = flight_df[['origin_departure_iata', 'hop1_departure_iata']].notna().sum(axis=1) - 1

    flight_df['layover_1_duration'] = flight_df.apply(lambda row: calculate_layover(row, 'hop1_departure_time', 'origin_arrival_time'), axis=1)
    if "hop2_departure_time" in list(flight_df.columns):
        flight_df['layover_2_duration'] = flight_df.apply(lambda row: calculate_layover(row, 'hop2_departure_time', 'hop1_arrival_time'), axis=1)
    

    carrier_codes_cols = [cols for cols in flight_df.columns if "carrier_code" in cols.lower()]
    airlines = []
    for x in carrier_codes_cols:
        #print(pd.unique(df1[x]))
        airlines.extend(pd.unique(flight_df[x]))


    airlines = [x for x in airlines if type(x)!=float]
    airlines = set(airlines)

    airline = list(df_reference.Airline.values)
    code = list(df_reference.IATA.values)

    code_dict = dict(zip(code,airline))
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

    flight_df['origin_airline'] = flight_df['origin_carrier_code'].map(airline_names_final)
    flight_df['hop1_airline'] = flight_df['hop1_carrier_code'].map(airline_names_final)

    if "hop2_carrier_code" in list(flight_df.columns):
        flight_df['hop2_airline'] = flight_df['hop2_carrier_code'].map(airline_names_final)
    

    flight_df.drop(carrier_codes_cols,axis=1,inplace=True)
    flight_df.drop(['price_base','price_grandTotal'],axis=1,inplace=True)

    flight_df.rename(columns={
    "itinerary_duration" : "Total Journey Duration",
    "origin_departure_iata" : "Origin Departure Location",
    "origin_arrival_iata" : "First Arrival Location",
    "origin_duration" : "First Flight Duration",
    "hop1_departure_iata" : "hop1_departure_location",
    "hop1_arrival_iata" : "hop1_arrival_location",
    "hop2_departure_iata" : "hop2_departure_location",
    "hop2_arrival_iata" : "hop2_arrival_location"
},inplace=True)

    flight_df.drop_duplicates(inplace=True)

    return flight_df

def prompt_query(query,origin,destination):
    main_prompt = f"""
    You are a flight booking assistant that helps answer queries using a flight information dataframe for trips from {origin} to {destination}. Analyze the dataframe and provide direct answers with clear departure and arrival times. Avoid unnecessary information.
    IMPORTANT:
    If the user asks about different locations, tell them to start a new conversation.
    Use previous chat history for follow-up questions. Refer to the Bot's last response, locate the corresponding row, and provide the relevant details.
    For example: If the user asks for the 3 flights with the least travel time and then asks, "What are the prices of these flights," understand they're referring to the previously mentioned flights. Select those rows and give the prices.
    Remember:
    For direct flights (where "First Arrival Location" is the same as {destination}), provide arrival and departure times directly.
    For flights with hops, give details for all hops, including locations, times, durations, layovers, final destination, and total travel time. Provide answers in a clear and structured manner.

    IMPORTANT: When the user says "book this flight" or "Book flight number x" when you provide a list of options, mark that specific row from the dataframe and get the value from the "INDEX" column.
    Finally, return a list where the 0th entry is the INDEX value and the 1st entry is the answer to the query.
    Example query: book this flight for me
    Expected response: [0, "The flight you requested has been booked..."]
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

    clean_json = [extract_data_json(x) for x in flight_info]
    list_of_dicts = [json.loads(json_str) for json_str in clean_json]

    flight_df = parse_json_to_df(list_of_dicts)
    final_df = process_dataframe(flight_df)
    final_df['INDEX'] = [i for i in range(len(final_df))]


    print("Dataframe : ",final_df)
    print("*"*125)
    save_string = f"{origin}" + "_" + f"{destination}.csv"
    final_df.to_csv(save_string)
    return flight_df,origin,destination,flight_info

    # print("Dataframe : ",flight_df)
    # print("*"*125)

# give me flights from Bangalore to Mumbai on 15th june