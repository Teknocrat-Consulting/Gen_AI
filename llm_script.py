from data_script import prompt_query
from langchain_experimental.agents import create_pandas_dataframe_agent
from data_script import run
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferWindowMemory
import re
import os
from langchain_community.utilities import SerpAPIWrapper
# import warnings
# warnings.filterwarnings('ignore')

serpapi_api_key = os.getenv("SERPAPI_API_KEY")
llm = ChatOpenAI(model="gpt-3.5-turbo-0613")
search = SerpAPIWrapper(serpapi_api_key = serpapi_api_key)


def get_llm_response(df,query,origin,destination):

    def is_currency_conversion_query(query):
        return bool(re.search(r'convert\s+\d+(\.\d+)?\s+\w+\s+to\s+\w+', query, re.IGNORECASE))
    
    if is_currency_conversion_query(query):
        print("SERPAPI being used : ")
        conversion_result = search.run(query)
        print("Query : ", query)
        print("Answer : ", conversion_result)
        return conversion_result
    
    memory = ConversationBufferWindowMemory(k=5)
    query_to_ask = prompt_query(query,origin,destination)
    # print("Query : ", query_to_ask)
    # print("*"*125)
    agent = create_pandas_dataframe_agent(llm, df, agent_type="openai-tools",memory=memory, verbose=False, temperature=0) # memory=memory
    res = agent.invoke(
        {
            "input": query_to_ask
        }
    )

    print("Query : ", query_to_ask)
    print("Answer : ",res['output'])
    return res['output']

def main():
    df = None
    origin = None
    destination = None

    while True:
        query = input("Enter your query (or type 'quit' to exit): ").strip()
        
        if query.lower() == "quit":
            print("Exiting chat. Goodbye!")
            break

        if df is None:
            df, origin, destination = run(query)
            
        
        get_llm_response(df, query, origin, destination)

if __name__ == "__main__":
    main()