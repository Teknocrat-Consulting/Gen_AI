from data_script import prompt_query
from langchain_experimental.agents import create_pandas_dataframe_agent
from data_script_new import run
from langchain_openai import ChatOpenAI
import re
import pandas as pd
import os
from langchain_community.utilities import SerpAPIWrapper 
from langchain_community.utilities import SerpAPIWrapper
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, SystemMessage

import warnings
warnings.filterwarnings('ignore')


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

    print("Query : ", query_to_ask)
    print("Answer : ", res['output'])
    return res['output']

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
            df, origin, destination = run(query)
        
        try:
            #df = pd.read_csv("LHR_BLR_Main.csv")
            #print(df)
            response = get_llm_response(df, query, origin, destination, history)
            #print(response)
            update_conversation_history(history, query, response)
        except Exception as e:
            print(f"Cannot proceed with answer because --> {e}")

if __name__ == "__main__":
    main()


    # give me cheapest flight from Mumbai to Bangalore on 1st June