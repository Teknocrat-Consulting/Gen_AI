from typing import Optional, Dict, Any, List
import pandas as pd
from langchain_experimental.agents import create_pandas_dataframe_agent
from langchain_openai import ChatOpenAI
from app.core.logging import logger
from app.services.flight_service import FlightService
from app.core.config import settings
import uuid
from datetime import datetime, timedelta


class ChatService:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o-mini", api_key=settings.OPENAI_API_KEY)
        self.flight_service = FlightService()
        self.sessions: Dict[str, Dict[str, Any]] = {}
        
    def get_or_create_session(self, session_id: Optional[str] = None) -> str:
        if session_id and session_id in self.sessions:
            self.sessions[session_id]['last_activity'] = datetime.now()
            return session_id
        
        new_session_id = str(uuid.uuid4())
        self.sessions[new_session_id] = {
            'created_at': datetime.now(),
            'last_activity': datetime.now(),
            'messages': [],
            'context': {}
        }
        return new_session_id
    
    def clean_expired_sessions(self):
        current_time = datetime.now()
        expired_sessions = []
        
        for session_id, session_data in self.sessions.items():
            if (current_time - session_data['last_activity']).seconds > settings.SESSION_TIMEOUT:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self.sessions[session_id]
            logger.info(f"Cleaned expired session: {session_id}")
    
    def create_prompt(self, query: str, origin: str, destination: str) -> str:
        main_prompt = f"""
        You are a professional flight booking assistant specializing in helping users find and analyze flight information. You have access to real-time flight data and can provide detailed analysis and recommendations.

        CURRENT CONTEXT:
        - Flight data from {origin} to {destination}
        - Real-time pricing and availability information
        - All prices are shown in Indian Rupees (INR)

        CAPABILITIES:
        - Analyze flight data including prices, airlines, stops, cabin classes
        - Provide comparative analysis and recommendations
        - Identify best deals and optimal flight options
        - Handle follow-up questions about the same flight search

        RESPONSE GUIDELINES:
        - DO NOT create a numbered list of flights with departure/arrival times and prices
        - Analyze the ACTUAL flight data available and provide specific insights
        - Mention specific prices in INR (₹), airlines, and key differences you find in the data
        - Highlight the cheapest options, direct flights, and best value choices
        - Provide actionable recommendations based on the real flight options
        - Keep it concise but informative
        - Flight cards will show the detailed flight information, but your text should reference the actual data

        ANALYSIS FOCUS:
        - Identify the cheapest flights available and their prices
        - Point out direct flights vs flights with stops
        - Highlight time differences and convenience factors
        - Mention specific airlines operating this route
        - Compare value propositions of different options

        IMPORTANT: Base your response on the ACTUAL flight data in the dataframe. Don't give generic advice - analyze the real flights available for this specific route and date.

        Provide specific insights about the available flight options to help users choose the best flight for their needs.
        """
        
        return f"System Prompt: {main_prompt}\nQuery: {query}"
    
    def get_llm_response(self, df: pd.DataFrame, query: str, origin: str, destination: str) -> str:
        query_to_ask = self.create_prompt(query, origin, destination)
        logger.info(f"Sending query to LLM: {query_to_ask}")
        
        try:
            agent = create_pandas_dataframe_agent(
                self.llm, 
                df, 
                agent_type="openai-tools", 
                verbose=False, 
                allow_dangerous_code=True
            )
            
            res = agent.invoke({"input": query_to_ask})
            response = res['output']
            logger.info(f"LLM Response: {response}")
            return response
        except Exception as e:
            logger.error(f"Error getting LLM response: {e}")
            raise
    
    def process_message(self, message: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        self.clean_expired_sessions()
        
        session_id = self.get_or_create_session(session_id)
        session = self.sessions[session_id]
        
        session['messages'].append({
            'role': 'user',
            'content': message,
            'timestamp': datetime.now().isoformat()
        })
        
        try:
            if 'flight_df' not in session['context'] or session['context']['flight_df'] is None:
                logger.info("No existing flight data in session, fetching new data")
                flight_df, origin, destination = self.flight_service.process_flight_search(message)
                
                if flight_df is not None:
                    session['context']['flight_df'] = flight_df
                    session['context']['origin'] = origin
                    session['context']['destination'] = destination
                else:
                    return {
                        'response': "I couldn't find any flights based on your query. Please make sure you've provided valid origin and destination cities along with a departure date.",
                        'session_id': session_id,
                        'timestamp': datetime.now().isoformat(),
                        'flight_data': None,
                        'show_flight_cards': False,
                        'metadata': {'error': 'No flights found'}
                    }
            else:
                flight_df = session['context']['flight_df']
                origin = session['context']['origin']
                destination = session['context']['destination']
            
            response = self.get_llm_response(flight_df, message, origin, destination)
            
            session['messages'].append({
                'role': 'assistant',
                'content': response,
                'timestamp': datetime.now().isoformat()
            })
            
            flight_data = flight_df.to_dict('records') if isinstance(flight_df, pd.DataFrame) else None
            
            # Debug logging
            logger.info(f"Flight data prepared: {flight_data is not None}")
            logger.info(f"Flight data length: {len(flight_data) if flight_data else 0}")
            if flight_data and len(flight_data) > 0:
                logger.info(f"First flight record: {flight_data[0]}")
            
            result = {
                'response': response,
                'session_id': session_id,
                'timestamp': datetime.now().isoformat(),
                'flight_data': flight_data[:5] if flight_data else None,  
                'show_flight_cards': True,  # Add flag to show flight cards
                'metadata': {
                    'origin': origin,
                    'destination': destination,
                    'total_flights': len(flight_df) if isinstance(flight_df, pd.DataFrame) else 0
                }
            }
            
            logger.info(f"Returning result with show_flight_cards: {result.get('show_flight_cards')}")
            return result
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return {
                'response': f"I encountered an error while processing your request. Please try again. Error: {str(e)}",
                'session_id': session_id,
                'timestamp': datetime.now().isoformat(),
                'flight_data': None,
                'show_flight_cards': False,
                'metadata': {'error': str(e)}
            }
    
    def get_session_history(self, session_id: str) -> List[Dict[str, Any]]:
        if session_id in self.sessions:
            return self.sessions[session_id]['messages']
        return []
    
    def clear_session(self, session_id: str) -> bool:
        if session_id in self.sessions:
            self.sessions[session_id]['context'] = {}
            self.sessions[session_id]['messages'] = []
            logger.info(f"Cleared session: {session_id}")
            return True
        return False