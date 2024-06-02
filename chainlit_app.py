import chainlit as cl
import streamlit as st
from data_script_new import run,prompt_query
from llm_script import get_llm_response,update_conversation_history,check_currency_conversion
from streamlit_chat import message

@cl.on_message
async def main(message:str):
    query = message.content
    print("Query : ",query)
    cb = cl.AsyncLangchainCallbackHandler(
        stream_final_answer=True, answer_prefix_tokens=["FINAL", "ANSWER"]
    )
    cb.answer_reached = True

    pdf_file = cl.user_session.get("pdf_file")
    chat = PDF_chat(pdf_file,message)
    result = chat.main()
    await cl.Message(content=result).send()

# give me flight information for Bangalore to Mumbai on 9th June
# 