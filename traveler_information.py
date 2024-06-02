from langchain.chains import LLMChain
from langchain_core.prompts import PromptTemplate

from langchain_openai import ChatOpenAI
import json
import warnings
warnings.filterwarnings('ignore')

prompt_template = PromptTemplate(
    template="""
    Extract the following information from the text and provide the output as a dictionary with the specified keys:
    - First Name
    - Last Name
    - Date of Birth
    - Gender
    - Email Address
    - Phone Number
    - Country Calling Code

    Text: "{text}"

    Output dictionary format:
    {{
        "id": "1",
        "dateOfBirth": "<Date of Birth>",
        "name": {{
            "firstName": "<First Name>" (This should be in capital letters),
            "lastName": "<Last Name>" (This should be in capital letters)
        }},
        "gender": "<Gender>", (This should be in capital letters)
        "contact": {{
            "emailAddress": "<Email Address>",
            "phones": [{{
                "deviceType": "MOBILE",
                "countryCallingCode": "<Country Calling Code>",
                "number": "<Phone Number>"
            }}]
        }}
    }}
    """,
    input_variables=["text"]
)


llm = ChatOpenAI(model_name="gpt-3.5-turbo")
llm_chain = LLMChain(llm=llm, prompt=prompt_template)

# Function to convert input text to JSON using GPT
def convert_to_dict(text):
    response = llm_chain.run(text=text).strip()
    try:
        # Directly parse the response into a dictionary
        parsed_response = json.loads(response)
        return parsed_response
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON from response: {response}") from e
    
def get_info(input_text):
    traveler_short_dict = convert_to_dict(input_text)
    return traveler_short_dict

# Print the resulting JSON
#print(traveler_short_dict)

# Verify that the output is a dictionary
#print(type(traveler_short_dict))