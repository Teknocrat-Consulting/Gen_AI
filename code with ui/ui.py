import streamlit as st
from streamlit_chat import message
from langchain_openai import OpenAIEmbeddings
from langchain.chat_models import ChatOpenAI
from langchain.chains import ConversationalRetrievalChain
from langchain_community.document_loaders import CSVLoader
from langchain_community.vectorstores import FAISS
from data_script_new import run
import tempfile

# Set OpenAI API Key
OPENAI_API_KEY = "sk-proj-openai-api-key"

# File uploader in the sidebar
#uploaded_file = st.sidebar.file_uploader("Upload CSV", type="csv")
st.title("Flight Booking Chatbot")
query = st.text_input("Enter your query: ").strip()


# Processing the uploaded CSV file 
if query:
    df,tmp_file_path  = run(query)

    # Load the CSV data
    loader = CSVLoader(file_path=tmp_file_path, encoding="utf-8")
    data = loader.load()

    # Initialize embeddings and FAISS vector store
    embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
    vectors = FAISS.from_documents(data, embeddings)

    # Create the conversational retrieval chain
    chain = ConversationalRetrievalChain.from_llm(
        llm=ChatOpenAI(temperature=0.0, model_name='gpt-3.5-turbo', openai_api_key=OPENAI_API_KEY),
        retriever=vectors.as_retriever()
    )

    # Function for handling user queries
    def conversational_chat(query):
        result = chain({"question": query, "chat_history": st.session_state['history']})
        st.session_state['history'].append((query, result["answer"]))
        return result["answer"]

    # Initialize session state
    if 'history' not in st.session_state:
        st.session_state['history'] = []
    if 'generated' not in st.session_state:
        st.session_state['generated'] = ["Hello! Ask me anything about " + tmp_file_path + " 🤗"]
    if 'past' not in st.session_state:
        st.session_state['past'] = ["Hey! 👋"]

    # Containers for chat history and user input
    response_container = st.container()
    container = st.container()

    # Form for user input
    with container:
        with st.form(key='my_form', clear_on_submit=True):
            user_input = st.text_input("Query:", placeholder="Talk about your CSV data here (:", key='input')
            submit_button = st.form_submit_button(label='Send')

        # Handle form submission
        if submit_button and user_input:
            output = conversational_chat(user_input)
            st.session_state['past'].append(user_input)
            st.session_state['generated'].append(output)

    # Display the chat history
    if st.session_state['generated']:
        with response_container:
            for i in range(len(st.session_state['generated'])):
                message(st.session_state["past"][i], is_user=True, key=str(i) + '_user', avatar_style="big-smile")
                message(st.session_state["generated"][i], key=str(i), avatar_style="thumbs")