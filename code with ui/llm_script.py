import streamlit as st
from data_script_new import prompt_query
from langchain_experimental.agents import create_pandas_dataframe_agent
from data_script_new import run
from langchain_openai import ChatOpenAI
import re
import os
from langchain_community.utilities import SerpAPIWrapper 
import warnings

warnings.filterwarnings('ignore')

# Initialize the LLM
llm = ChatOpenAI(model="gpt-3.5-turbo-0613")

# Initialize the SerpAPIWrapper with your API key
search = SerpAPIWrapper(serpapi_api_key="serpapi_api_key")

def is_currency_conversion_query(query):
    return bool(re.search(r'convert\s+\d+(\.\d+)?\s+\w+\s+to\s+\w+', query, re.IGNORECASE))

def update_conversation_history(history, query, response):
    history.append((query, response))
    if len(history) > 3:
        history.pop(0)

def generate_prompt_with_history(query, history):
    conversation = "\n".join([f"User: {q}\nBot: {r}" for q, r in history])
    return f"{query}\n********Previous chat history******* : \n{conversation}"

def get_llm_response(df, query, origin, destination, history):
    if is_currency_conversion_query(query):
        conversion_result = search.run(query)
        return conversion_result
    
    query_to_ask = generate_prompt_with_history(prompt_query(query, origin, destination), history)
    agent = create_pandas_dataframe_agent(llm, df, agent_type="openai-tools", verbose=False)
    res = agent.invoke({"input": query_to_ask})
    return res['output']

def main():
    st.title("Chatbot Application")
    st.write("Ask me anything about flight information and currency conversion!")

    history = []

    if "df" not in st.session_state:
        st.session_state.df = None
        st.session_state.origin = None
        st.session_state.destination = None

    query = st.text_input("Enter your query", "")

    if st.button("Submit"):
        if query:
            if st.session_state.df is None:
                st.session_state.df, st.session_state.origin, st.session_state.destination = run(query)

            try:
                response = get_llm_response(st.session_state.df, query, st.session_state.origin, st.session_state.destination, history)
                update_conversation_history(history, query, response)
                st.write("Response: ", response)
            except Exception as e:
                st.write(f"Cannot proceed with answer because: {e}")

    if st.button("Clear History"):
        history.clear()
        st.session_state.df = None
        st.session_state.origin = None
        st.session_state.destination = None

if __name__ == "__main__":
    main()
