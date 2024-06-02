from langchain.chains import LLMChain
from langchain_core.prompts import PromptTemplate

from langchain_openai import ChatOpenAI
import json
import warnings
warnings.filterwarnings('ignore')

prompt_template = PromptTemplate(
    template="""
    For the dictionary given below, summarise the information in nice format for the user and include the below points in the summary

    Dictionary: "{text}"

    1. Departure and Arrival location
    2. Date of travel
    3. Total journey duration
    4. Price
    5. Additional info regardings hops like layover duration and location if hops are present.

    Only give the above information and don't give unnecesary information and start the answer with "Please check your flight information for confirmation"
    """,
    input_variables=["text"]
)


llm = ChatOpenAI(model_name="gpt-3.5-turbo")
llm_chain = LLMChain(llm=llm, prompt=prompt_template)

# price_confirm_dict = {'type': 'flight-offers-pricing',
#  'flightOffers': [{'type': 'flight-offer',
#    'id': '1',
#    'source': 'GDS',
#    'instantTicketingRequired': False,
#    'nonHomogeneous': False,
#    'paymentCardRequired': False,
#    'lastTicketingDate': '2024-06-02',
#    'itineraries': [{'segments': [{'departure': {'iataCode': 'BLR',
#         'terminal': '2',
#         'at': '2024-06-10T08:30:00'},
#        'arrival': {'iataCode': 'BOM',
#         'terminal': '2',
#         'at': '2024-06-10T10:10:00'},
#        'carrierCode': 'UK',
#        'number': '846',
#        'aircraft': {'code': '320'},
#        'operating': {'carrierCode': 'UK'},
#        'duration': 'PT1H40M',
#        'id': '98',
#        'numberOfStops': 0,
#        'co2Emissions': [{'weight': 73,
#          'weightUnit': 'KG',
#          'cabin': 'ECONOMY'}]}]}],
#    'price': {'currency': 'EUR',
#     'total': '59.65',
#     'base': '46.00',
#     'fees': [{'amount': '0.00', 'type': 'SUPPLIER'},
#      {'amount': '0.00', 'type': 'TICKETING'},
#      {'amount': '0.00', 'type': 'FORM_OF_PAYMENT'}],
#     'grandTotal': '59.65',
#     'billingCurrency': 'EUR'},
#    'pricingOptions': {'fareType': ['PUBLISHED'],
#     'includedCheckedBagsOnly': True},
#    'validatingAirlineCodes': ['UK'],
#    'travelerPricings': [{'travelerId': '1',
#      'fareOption': 'STANDARD',
#      'travelerType': 'ADULT',
#      'price': {'currency': 'EUR',
#       'total': '59.65',
#       'base': '46.00',
#       'taxes': [{'amount': '2.62', 'code': 'P2'},
#        {'amount': '7.20', 'code': 'IN'},
#        {'amount': '2.38', 'code': 'K3'},
#        {'amount': '1.45', 'code': 'YR'}],
#       'refundableTaxes': '13.65'},
#      'fareDetailsBySegment': [{'segmentId': '98',
#        'cabin': 'ECONOMY',
#        'fareBasis': 'V0GRPRYS',
#        'brandedFare': 'ECOYS',
#        'class': 'V',
#        'includedCheckedBags': {'weight': 15, 'weightUnit': 'KG'}}]}]}],
#  'bookingRequirements': {'emailAddressRequired': True,
#   'mobilePhoneNumberRequired': True}}

def check_final_price(price_confirm_dict):
    response = llm_chain.run(text=price_confirm_dict).strip()
    print(response)
    return response

#check_final_price(price_confirm_dict)