from data_script import extract_flight_info_from_query,get_flight_info,create_flight_dataframe

query = "flight details from LHR to BLR for 19th July"

result = extract_flight_info_from_query(query)
print("Information extracted from query : ",result)
print("*"*125)

origin = result['location_origin']
destination = result['location_destination']
departure_date = result['departure_date']
adults = result['adults']

flight_info = get_flight_info(origin, destination, departure_date)

# # Convert the flight info to a DataFrame
if isinstance(flight_info, list):
    flight_df = create_flight_dataframe(flight_info)
    print(flight_df)
else:
    print("Error in forming Dataframe")

#print(flight_info[:10])