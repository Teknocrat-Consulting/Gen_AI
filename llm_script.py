from data_script import prompt_query
from langchain_experimental.agents import create_pandas_dataframe_agent
from data_script import run
from langchain_openai import ChatOpenAI
#from langchain.memory import ConversationBufferWindowMemory


llm = ChatOpenAI(model="gpt-3.5-turbo-0613")


def get_llm_response(df,query,origin,destination):
        #memory = ConversationBufferWindowMemory(k=5)
        query_to_ask = prompt_query(query,origin,destination)
        # print("Query : ", query_to_ask)
        # print("*"*125)
        agent = create_pandas_dataframe_agent(llm, df, agent_type="openai-tools", verbose=False) # memory=memory
        res = agent.invoke(
            {
                "input": query_to_ask
            }
        )

        print("Query : ", query_to_ask)
        print("Answer : ",res['output'])
        return res['output']


# query = "Give me cheapest flights to fly from Delhi to Mumbai on 30-05-2024"
# df = None
# if df is None:
#     result_df,origin,destination = run(query)
#     df = result_df

# end_result = get_llm_response(result_df,query)

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