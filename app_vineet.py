import streamlit as st
from streamlit_chat import message
from langchain.chat_models import ChatOpenAI
from data_script_new import run, prompt_query
import pandas as pd
import os
import pickle
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_experimental.agents import create_pandas_dataframe_agent
from langchain_community.utilities import SerpAPIWrapper
from langchain_openai import ChatOpenAI
import warnings
warnings.filterwarnings('ignore')

llm = ChatOpenAI(model="gpt-3.5-turbo-0613")

search = SerpAPIWrapper(serpapi_api_key="0ed8ec9c15be4500a7cb42ab2568f2d820fa0de9273db1c45686cacc613c432e")

DATAFRAME_FILE = 'session_dataframe.pkl'

def save_dataframe(df):
    """Save the dataframe to disk."""
    with open(DATAFRAME_FILE, 'wb') as f:
        pickle.dump(df, f)

def load_dataframe():
    """Load the dataframe from disk."""
    if os.path.exists(DATAFRAME_FILE):
        with open(DATAFRAME_FILE, 'rb') as f:
            return pickle.load(f)
    return None

def delete_flights_file():
    """Delete the flights.csv file if it exists."""
    if os.path.exists('flights.csv'):
        os.remove('flights.csv')

def main():
    st.title("Flight Booking Chatbot")

    # Initialize session state
    if 'history' not in st.session_state:
        st.session_state['history'] = []
    if 'generated' not in st.session_state:
        st.session_state['generated'] = ["Hello! Ask me anything about flight bookings 🤗"]
    if 'past' not in st.session_state:
        st.session_state['past'] = ["Hey! 👋"]
    if 'df' not in st.session_state:
        st.session_state['df'] = load_dataframe()
    if 'origin' not in st.session_state:
        st.session_state['origin'] = None
    if 'destination' not in st.session_state:
        st.session_state['destination'] = None
    history = []

    menu = ["Enter Query", "Process Query"]
    choice = st.sidebar.selectbox("Menu", menu)

    if choice == "Enter Query":
        st.subheader("Enter your query")
        with st.form(key='query_form'):
            query = st.text_input("Enter your query (or type 'quit' to exit): ").strip()
            submit_button = st.form_submit_button(label='Submit')

        if submit_button:
            st.session_state.query = query
            st.success(f"Query saved: {query}")

    elif choice == "Process Query":
        st.subheader("Process your query")

        if 'query' in st.session_state and st.session_state.query:
            query = st.session_state.query
            if query.lower() in ["quit", "exit"]:
                st.write("Exiting chat. Goodbye!")
            else:
                if st.session_state['df'] is None:
                    df, origin, destination = run(query)
                    st.session_state['df'] = df
                    st.session_state['origin'] = origin
                    st.session_state['destination'] = destination
                    save_dataframe(df)  # Save the dataframe to disk
                    df.head(10)
                else:
                    df = st.session_state['df']
                    origin = st.session_state['origin']
                    destination = st.session_state['destination']

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
                    return parser.invoke(result)

                def update_conversation_history(history, query, response):
                    history.append((query, response))
                    if len(history) > 2:
                        history.pop(0)

                def generate_prompt_with_history(query, history):
                    conversation = "\n".join([f"User: {q}\nBot: {r}" for q, r in history])
                    return f"{query}\n***Previous chat history** : \n{conversation}"

                def get_llm_response(df, query, origin, destination, history):
                    currency_query_answer = check_currency_conversion(query)
                    if currency_query_answer != "False":
                        conversion_result = search.run(query)
                        return conversion_result
                    query_to_ask = generate_prompt_with_history(prompt_query(query, origin, destination), history)
                    agent = create_pandas_dataframe_agent(llm, df, agent_type="openai-tools", verbose=False, agent_executor_kwargs={"handle_parsing_errors": True})
                    
                    res = agent.invoke({"input": query_to_ask})
                    st.session_state['history'].append((query_to_ask, res["output"]))
                    print(query)
                    print(res['output'])
                    return res['output']

                response_container = st.container()
                container = st.container()

                with container:
                    with st.form(key='my_form', clear_on_submit=True):
                        user_input = st.text_input("Query:", placeholder="Talk about your CSV data here (:", key='input')
                        submit_button = st.form_submit_button(label='Send')

                    if submit_button and user_input:
                        output = get_llm_response(st.session_state['df'], user_input, origin, destination, history)
                        update_conversation_history(history, user_input, output)
                        st.session_state['past'].append(user_input)
                        st.session_state['generated'].append(output)

                    if st.session_state['generated']:
                        with response_container:
                            for i in range(len(st.session_state['generated'])):
                                message(st.session_state["past"][i], is_user=True, key=str(i) + '_user', avatar_style="big-smile")
                                message(st.session_state["generated"][i], key=str(i), avatar_style="thumbs")
        else:
            st.warning("Please enter a query first in the 'Enter Query' section.")

if __name__ == "__main__":
    main()