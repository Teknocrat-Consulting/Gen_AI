from langchain_experimental.agents import create_pandas_dataframe_agent
from data_script_new import run,prompt_query,extract_data_json
from langchain_openai import ChatOpenAI
import re
import pandas as pd
import os
from langchain_community.utilities import SerpAPIWrapper 
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser,ListOutputParser
from langchain_core.messages import HumanMessage, SystemMessage
from traveler_information import get_info
import ast
from amadeus import Client, ResponseError 
from price_confirm import check_final_price

import warnings
warnings.filterwarnings('ignore')

amadeus = Client(
    client_id='H4S446vjDRHVJn8C0ZDRkXSLt03AvOGp',
    client_secret='2MCfJEBzkSLqYla0'

 )

# Initialize the LLM
llm = ChatOpenAI(model="gpt-3.5-turbo-0613")

# Initialize the SerpAPIWrapper with your API key
search = SerpAPIWrapper(serpapi_api_key="0ed8ec9c15be4500a7cb42ab2568f2d820fa0de9273db1c45686cacc613c432e")

def check_currency_conversion(query):
    messages = [
        SystemMessage(content="""
                      You are an intelligent assistant. Determine if the query is asking for currency conversion. If it is, then extract the relevant information needed to convert currency from the following query and format 
                      it in the way "convert {currency} {amount} price to {target_currency}. Otherwise respond as "False"
                      """),  
        HumanMessage(content=query),  
    ]

    result = llm.invoke(messages)
    parser = StrOutputParser()
    #print(parser.invoke(result))
    return parser.invoke(result)

def update_conversation_history(history, query, response):
    history.append((query, response))
    if len(history) > 2:
        history.pop(0)

def generate_prompt_with_history(query, history):
    conversation = "\n".join([f"User: {q}\nBot: {r}" for q, r in history])
    return f"{query}\n********Previous chat history******* : \n{conversation}"

def get_llm_response(df, query, origin, destination, history):
    currency_query_answer = check_currency_conversion(query)
    if  currency_query_answer != "False":
        print("SERPAPI being used : ")
        conversion_result = search.run(query)
        #print("Query : ", query)
        print("Answer : ", conversion_result)
        return conversion_result
    
    query_to_ask = generate_prompt_with_history(prompt_query(query, origin, destination), history)
    agent = create_pandas_dataframe_agent(llm, df, agent_type="openai-tools", verbose=False,agent_executor_kwargs={"handle_parsing_errors": True})
    res = agent.invoke({"input": query_to_ask})

    #print("Query : ", query_to_ask)
    #print(res['output'])
    if 'book' in query.lower() or 'booking' in query.lower():
        main_result = ast.literal_eval(res['output'])
        index = main_result[0]
        print("Answer : ", main_result[1])
        return main_result,index
        #print("Answer : ", type(main_result))
    #print(parser.invoke(result))
    else:
        main_result = res['output']
        print("Answer : ", main_result)
    #print("Answer : ", type(main_result))
        return main_result,"None"

def main():
    df = None
    origin = None
    destination = None
    history = []

    while True:
        query = input("Enter your query (or type 'quit' to exit): ").strip()
        
        if query.lower() == "quit" or query.lower() == "exit":
            print("Exiting chat. Goodbye!")
            break

        if df is None:
            df, origin, destination,flight_info = run(query)
        
        try:
            #df = pd.read_csv("BLR_BOM.csv")
            #print(df)

            response,idx = get_llm_response(df, query, origin, destination, history)
            if idx != "None":
                booked_flight = flight_info[idx]
                #print(booked_flight)
                travel_query  = input("Please enter your first name, last name, DOB, email and phone number along with country code.").strip()
                print("************************Getting traveler info***********************************")
                traveler_info_fetched = get_info(travel_query)
                print("************************Checking Final Price***********************************")
                price_confirm = amadeus.shopping.flight_offers.pricing.post(
                booked_flight).data
                print(check_final_price(price_confirm))
                print("************************Get ID and PNR***********************************")
                final_booking = amadeus.booking.flight_orders.post(booked_flight, traveler_info_fetched).data
                id_ = final_booking['id']
                pnr_no = final_booking['associatedRecords'][0]['reference']
                print("ID : ",id_)
                print("PNR Number : ",pnr_no)


            #print(response)
            update_conversation_history(history, query, response)
        except Exception as e:
            print(f"Cannot proceed with answer because --> {e}")

if __name__ == "__main__":
    main()


# give me cheapest flight from Mumbai to Bangalore on 1st July

# give me flight info from Bangalore to Mumbai on 9th June
# give me cheapest flight
# give me flight with low price and less travel duration