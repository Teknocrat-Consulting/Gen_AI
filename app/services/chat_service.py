from typing import Optional, Dict, Any, List
import pandas as pd
from langchain_openai import ChatOpenAI
from app.core.logging import logger
from app.services.flight_service import FlightService
from app.services.hotel_service import HotelService
from app.core.config import settings
import uuid
from datetime import datetime, timedelta


class ChatService:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o-mini", api_key=settings.OPENAI_API_KEY)
        self.flight_service = FlightService()
        self.hotel_service = HotelService()
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
    
    def detect_query_type(self, message: str) -> str:
        """Detect whether the user is asking about flights or hotels"""
        message_lower = message.lower()
        
        hotel_keywords = [
            'hotel', 'hotels', 'accommodation', 'stay', 'room', 'rooms',
            'resort', 'lodge', 'inn', 'motel', 'booking.com', 'airbnb',
            'check-in', 'check-out', 'night', 'nights', 'bed', 'suite'
        ]
        
        flight_keywords = [
            'flight', 'flights', 'airline', 'airways', 'fly', 'flying',
            'departure', 'arrival', 'ticket', 'tickets', 'trip', 'travel',
            'airport', 'plane', 'aircraft', 'round trip', 'one way'
        ]
        
        hotel_score = sum(1 for keyword in hotel_keywords if keyword in message_lower)
        flight_score = sum(1 for keyword in flight_keywords if keyword in message_lower)
        
        logger.info(f"Query type detection - Hotel score: {hotel_score}, Flight score: {flight_score}")
        
        if hotel_score > flight_score and hotel_score > 0:
            return 'hotel'
        elif flight_score > 0:
            return 'flight'
        else:
            # Default to flight if unclear
            return 'flight'
    
    def create_prompt(self, query: str, origin: str, destination: str) -> str:
        main_prompt = f"""
        You are a professional flight booking assistant specializing in helping users find and analyze flight information. You have access to real-time flight data and can provide detailed analysis and recommendations.

        CURRENT CONTEXT:
        - Flight data from {origin} to {destination}
        - Real-time pricing and availability information
        - All prices are shown in Indian Rupees (INR)

        RESPONSE FORMAT REQUIREMENTS:
        You MUST structure your response with these EXACT section headers and format. The frontend parses these specific patterns:

        🎯 Best Deal
        Price: ₹4067
        Airline: AIR INDIA (AI)
        Time: 11:00 - 11:50
        Stops: 1 stop
        Duration: 50m

        ✈️ Available Flights

        Option 1
        Airline: AIR INDIA (AI)
        Price: ₹4067
        Departure: 11:00
        Arrival: 11:50
        Stops: 1 stop

        Option 2
        Airline: AIR INDIA (AI)  
        Price: ₹4067
        Departure: 18:00
        Arrival: 20:00
        Stops: 1 stop

        Option 3
        [Continue for all available flights...]

        KEY_INSIGHTS_START
        - Cheapest flights available from ₹4067
        - Price range: ₹4067 to ₹4858
        - All flights require 1 stop
        - Morning departures offer good timing
        KEY_INSIGHTS_END

        COMPARISON_START
        cheapest: ₹4067
        fastest: 50m
        bestValue: Best balance of price and convenience
        COMPARISON_END

        RECOMMENDATIONS_START
        budget: Choose the morning flight at ₹4067 for best value
        business: Consider the evening flight for convenience  
        flexible: Morning departure offers more flexibility for connections
        RECOMMENDATIONS_END

        CRITICAL REQUIREMENTS:
        1. Use EXACT section markers: KEY_INSIGHTS_START/END, COMPARISON_START/END, RECOMMENDATIONS_START/END
        2. Include specific prices, times, and airline data from the actual flight data
        3. NO markdown formatting (**, ##, ###, *, _) anywhere
        4. Use plain text with emoji section headers only
        5. Include all flights as Option 1, Option 2, etc.
        6. Frontend will parse these markers to populate tabs
        
        The frontend specifically looks for these patterns to populate the Key Insights, Quick Comparison, and Recommendations tabs.
        """
        
        return f"System Prompt: {main_prompt}\nQuery: {query}"
    
    def create_hotel_prompt(self, query: str, location: str, dates: Dict[str, str]) -> str:
        main_prompt = f"""
        You are a professional hotel booking assistant specializing in helping users find and analyze hotel information. You have access to real-time hotel data and can provide detailed analysis and recommendations.

        CURRENT CONTEXT:
        - Hotel data for {location}
        - Check-in: {dates.get('check_in', 'N/A')} | Check-out: {dates.get('check_out', 'N/A')}
        - All prices are shown in Indian Rupees (INR)

        RESPONSE FORMAT REQUIREMENTS:
        You MUST structure your response with these EXACT section headers and format. The frontend parses these specific patterns:

        🏨 Best Deal
        Price: ₹3500 per night
        Hotel: Grand Plaza Hotel
        Rating: 4.2/5 stars
        Location: City Center
        Amenities: WiFi, Pool, Gym

        🏠 Available Hotels

        Option 1
        Hotel: Grand Plaza Hotel
        Price: ₹3500 per night
        Rating: 4.2/5 stars
        Room Type: Deluxe Room
        Amenities: WiFi, Pool, Gym, Spa

        Option 2
        Hotel: Luxury Resort
        Price: ₹5200 per night
        Rating: 4.8/5 stars
        Room Type: Suite
        Amenities: WiFi, Pool, Gym, Spa, Restaurant

        Option 3
        [Continue for all available hotels...]

        KEY_INSIGHTS_START
        - Hotels available from ₹3500 per night
        - Price range: ₹3500 to ₹8500 per night
        - Multiple 4+ star properties available
        - Free WiFi available at most hotels
        KEY_INSIGHTS_END

        COMPARISON_START
        cheapest: ₹3500 per night
        highest_rated: 4.8/5 stars
        bestValue: Best balance of price, rating and amenities
        COMPARISON_END

        RECOMMENDATIONS_START
        budget: Choose Grand Plaza Hotel at ₹3500 for good value
        business: Consider Luxury Resort for premium amenities
        flexible: City center locations offer easy access to attractions
        RECOMMENDATIONS_END

        CRITICAL REQUIREMENTS:
        1. Use EXACT section markers: KEY_INSIGHTS_START/END, COMPARISON_START/END, RECOMMENDATIONS_START/END
        2. Include specific prices, ratings, and hotel data from the actual hotel data
        3. NO markdown formatting (**, ##, ###, *, _) anywhere
        4. Use plain text with emoji section headers only
        5. Include all hotels as Option 1, Option 2, etc.
        6. Frontend will parse these markers to populate tabs
        
        The frontend specifically looks for these patterns to populate the Key Insights, Quick Comparison, and Recommendations tabs.
        """
        
        return f"System Prompt: {main_prompt}\nQuery: {query}"
    
    def get_llm_response(self, df: pd.DataFrame, query: str, origin: str, destination: str) -> str:
        main_prompt = self.create_prompt(query, origin, destination)
        
        # Pre-process flight data for the LLM
        flight_summary = self._create_flight_summary(df, origin, destination)
        
        # Create a focused prompt with summarized data
        focused_prompt = f"{main_prompt}\n\nFlight Data Summary:\n{flight_summary}\n\nUser Query: {query}"
        
        logger.info(f"Sending focused query to LLM (length: {len(focused_prompt)} chars)")
        
        try:
            # Use direct ChatOpenAI call instead of pandas agent to avoid multiple API calls
            messages = [
                {"role": "system", "content": focused_prompt}
            ]
            
            response = self.llm.invoke(messages)
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            logger.info(f"LLM Response received (length: {len(response_text)} chars)")
            return response_text
        except Exception as e:
            logger.error(f"Error getting LLM response: {e}")
            # Provide fallback response instead of crashing
            return self._create_fallback_response(df, origin, destination)
    
    def _create_flight_summary(self, df: pd.DataFrame, origin: str, destination: str) -> str:
        """Create a concise summary of flight data for the LLM"""
        if df.empty:
            return "No flight data available."
        
        try:
            # Get key statistics
            total_flights = len(df)
            cheapest_price = df['Total Price'].astype(float).min()
            most_expensive_price = df['Total Price'].astype(float).max()
            airlines = df['Airline Name'].unique()
            direct_flights = len(df[df['Number of Stops'] == 0])
            
            # Convert Total Price to numeric and get top 5 cheapest flights
            df['Total Price'] = pd.to_numeric(df['Total Price'], errors='coerce')
            top_flights = df.nsmallest(5, 'Total Price')
            
            summary = f"""
ROUTE: {origin} to {destination}
TOTAL FLIGHTS: {total_flights}
PRICE RANGE: ₹{cheapest_price:.2f} - ₹{most_expensive_price:.2f}
AIRLINES: {', '.join(airlines[:5])}{'...' if len(airlines) > 5 else ''}
DIRECT FLIGHTS: {direct_flights}

TOP 5 FLIGHTS BY PRICE:
"""
            
            for idx, flight in top_flights.iterrows():
                dept_time = pd.to_datetime(flight['Departure']).strftime('%H:%M')
                arr_time = pd.to_datetime(flight['Arrival']).strftime('%H:%M')
                stops_text = 'Direct' if flight['Number of Stops'] == 0 else f"{flight['Number of Stops']} stop(s)"
                
                summary += f"- {flight['Airline Name']} ({flight['Airline Code']}): ₹{float(flight['Total Price']):.2f}, {dept_time}→{arr_time}, {stops_text}\n"
            
            return summary
        except Exception as e:
            logger.error(f"Error creating flight summary: {e}")
            return f"Flight data available for {origin} to {destination} route with {len(df)} options."
    
    def get_hotel_llm_response(self, df: pd.DataFrame, query: str, location: str, dates: Dict[str, str]) -> str:
        main_prompt = self.create_hotel_prompt(query, location, dates)
        
        # Pre-process hotel data for the LLM
        hotel_summary = self._create_hotel_summary(df, location, dates)
        
        # Create a focused prompt with summarized data
        focused_prompt = f"{main_prompt}\n\nHotel Data Summary:\n{hotel_summary}\n\nUser Query: {query}"
        
        logger.info(f"Sending hotel query to LLM (length: {len(focused_prompt)} chars)")
        
        try:
            messages = [
                {"role": "system", "content": focused_prompt}
            ]
            
            response = self.llm.invoke(messages)
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            logger.info(f"Hotel LLM Response received (length: {len(response_text)} chars)")
            return response_text
        except Exception as e:
            logger.error(f"Error getting hotel LLM response: {e}")
            return self._create_hotel_fallback_response(df, location, dates)
    
    def _create_hotel_summary(self, df: pd.DataFrame, location: str, dates: Dict[str, str]) -> str:
        """Create a concise summary of hotel data for the LLM"""
        if df.empty:
            return "No hotel data available."
        
        try:
            total_hotels = len(df)
            
            # Convert price to numeric for analysis
            df['Price_Numeric'] = df['Total Price'].apply(
                lambda x: float(str(x).replace(',', '')) if x and str(x) != 'N/A' else float('inf')
            )
            
            valid_prices = df[df['Price_Numeric'] != float('inf')]
            if not valid_prices.empty:
                cheapest_price = valid_prices['Price_Numeric'].min()
                most_expensive_price = valid_prices['Price_Numeric'].max()
            else:
                cheapest_price = most_expensive_price = 0
            
            # Get top 5 hotels by price
            if not valid_prices.empty:
                top_hotels = valid_prices.nsmallest(5, 'Price_Numeric')
            else:
                top_hotels = df.head(5)
            
            summary = f"""
LOCATION: {location}
CHECK-IN: {dates.get('check_in', 'N/A')} | CHECK-OUT: {dates.get('check_out', 'N/A')}
TOTAL HOTELS: {total_hotels}
PRICE RANGE: ₹{cheapest_price:.2f} - ₹{most_expensive_price:.2f} per night
RATINGS AVAILABLE: {len(df[df['Rating'] != 'N/A'])} hotels

TOP 5 HOTELS BY PRICE:
"""
            
            for idx, hotel in top_hotels.iterrows():
                price_str = f"₹{float(hotel['Price_Numeric']):.2f}" if hotel['Price_Numeric'] != float('inf') else "Price on request"
                rating_str = f"{hotel['Rating']}/5" if hotel['Rating'] != 'N/A' else "No rating"
                
                summary += f"- {hotel['Hotel Name']}: {price_str} per night, {rating_str}, {hotel['Room Type']}\n"
            
            return summary
        except Exception as e:
            logger.error(f"Error creating hotel summary: {e}")
            return f"Hotel data available for {location} with {len(df)} options."
    
    def _create_hotel_fallback_response(self, df: pd.DataFrame, location: str, dates: Dict[str, str]) -> str:
        """Create a basic hotel response when LLM fails"""
        if df.empty:
            return f"I couldn't find any hotels in {location} for your dates. Please try different dates or location."
        
        try:
            # Convert prices to numeric
            df['Price_Numeric'] = df['Total Price'].apply(
                lambda x: float(str(x).replace(',', '')) if x and str(x) != 'N/A' else float('inf')
            )
            
            valid_prices = df[df['Price_Numeric'] != float('inf')]
            if not valid_prices.empty:
                cheapest = valid_prices.loc[valid_prices['Price_Numeric'].idxmin()]
                cheapest_price = valid_prices['Price_Numeric'].min()
            else:
                cheapest = df.iloc[0]
                cheapest_price = 0
            
            total_hotels = len(df)
            rated_hotels = len(df[df['Rating'] != 'N/A'])
            
            response = f"""🏨 Best Deal
Price: ₹{cheapest_price:.2f} per night
Hotel: {cheapest['Hotel Name']}
Rating: {cheapest['Rating']}/5 stars
Room Type: {cheapest['Room Type']}

🏠 Available Hotels
Found {total_hotels} hotels in {location}.
{rated_hotels} hotels have customer ratings.

💡 Key Insights
- Hotels available from ₹{cheapest_price:.2f} per night
- Multiple accommodation options in {location}
- Various room types and amenities available

📊 Quick Comparison
Cheapest: ₹{cheapest_price:.2f} ({cheapest['Hotel Name']})

🎁 Recommendations  
Budget Travelers: Book {cheapest['Hotel Name']} at ₹{cheapest_price:.2f} per night
Business Travelers: Look for hotels with business amenities
Flexible Schedule: Multiple check-in/checkout options available"""
            
            return response
        except Exception as e:
            logger.error(f"Error creating hotel fallback response: {e}")
            return f"Found {len(df)} hotel options in {location}. Please try your search again."
    
    def _create_fallback_response(self, df: pd.DataFrame, origin: str, destination: str) -> str:
        """Create a basic response when LLM fails"""
        if df.empty:
            return f"I couldn't find any flights from {origin} to {destination}. Please try a different route or date."
        
        try:
            cheapest = df.loc[df['Total Price'].astype(float).idxmin()]
            total_flights = len(df)
            direct_flights = len(df[df['Number of Stops'] == 0])
            
            response = f"""🎯 Best Deal
Price: ₹{float(cheapest['Total Price']):.2f}
Airline: {cheapest['Airline Name']} ({cheapest['Airline Code']})
Stops: {'Direct' if cheapest['Number of Stops'] == 0 else f"{cheapest['Number of Stops']} stop(s)"}

✈️ Available Flights
Found {total_flights} flights from {origin} to {destination}.
{direct_flights} direct flights available.

💡 Key Insights
- Cheapest option starts from ₹{float(cheapest['Total Price']):.2f}
- Multiple airlines available for this route
- Both direct and connecting flights are available

📊 Quick Comparison
Cheapest: ₹{float(cheapest['Total Price']):.2f} ({cheapest['Airline Name']})

🎁 Recommendations  
Budget Travelers: Book the {cheapest['Airline Name']} flight at ₹{float(cheapest['Total Price']):.2f}
Business Travelers: Check direct flight options for convenience
Flexible Schedule: Multiple timing options available"""
            
            return response
        except Exception as e:
            logger.error(f"Error creating fallback response: {e}")
            return f"Found {len(df)} flight options from {origin} to {destination}. Please try your search again."
    
    def process_message(self, message: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        self.clean_expired_sessions()
        
        session_id = self.get_or_create_session(session_id)
        session = self.sessions[session_id]
        
        session['messages'].append({
            'role': 'user',
            'content': message,
            'timestamp': datetime.now().isoformat()
        })
        
        # Detect query type
        query_type = self.detect_query_type(message)
        logger.info(f"Detected query type: {query_type}")
        
        try:
            if query_type == 'hotel':
                return self._process_hotel_message(message, session_id, session)
            else:
                return self._process_flight_message(message, session_id, session)
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return {
                'response': f"I encountered an error while processing your request. Please try again. Error: {str(e)}",
                'session_id': session_id,
                'timestamp': datetime.now().isoformat(),
                'data': None,
                'show_cards': False,
                'message_type': 'error',
                'metadata': {'error': str(e)}
            }
    
    def _process_flight_message(self, message: str, session_id: str, session: Dict[str, Any]) -> Dict[str, Any]:
        """Process flight-related queries"""
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
                        'data': None,
                        'show_cards': False,
                        'message_type': 'flight_error',
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
            
            return {
                'response': response,
                'session_id': session_id,
                'timestamp': datetime.now().isoformat(),
                'data': flight_data[:5] if flight_data else None,
                'show_cards': True,
                'message_type': 'flight_results',
                'metadata': {
                    'origin': origin,
                    'destination': destination,
                    'total_flights': len(flight_df) if isinstance(flight_df, pd.DataFrame) else 0
                }
            }
        except Exception as e:
            logger.error(f"Error processing flight message: {e}")
            raise
    
    def _process_hotel_message(self, message: str, session_id: str, session: Dict[str, Any]) -> Dict[str, Any]:
        """Process hotel-related queries"""
        try:
            if 'hotel_df' not in session['context'] or session['context']['hotel_df'] is None:
                logger.info("No existing hotel data in session, fetching new data")
                hotel_df, location, dates = self.hotel_service.process_hotel_search(message)
                
                if hotel_df is not None:
                    session['context']['hotel_df'] = hotel_df
                    session['context']['location'] = location
                    session['context']['dates'] = dates
                else:
                    return {
                        'response': "I couldn't find any hotels based on your query. Please make sure you've provided a valid location and dates.",
                        'session_id': session_id,
                        'timestamp': datetime.now().isoformat(),
                        'data': None,
                        'show_cards': False,
                        'message_type': 'hotel_error',
                        'metadata': {'error': 'No hotels found'}
                    }
            else:
                hotel_df = session['context']['hotel_df']
                location = session['context']['location']
                dates = session['context']['dates']
            
            response = self.get_hotel_llm_response(hotel_df, message, location, dates)
            
            session['messages'].append({
                'role': 'assistant',
                'content': response,
                'timestamp': datetime.now().isoformat()
            })
            
            hotel_data = hotel_df.to_dict('records') if isinstance(hotel_df, pd.DataFrame) else None
            
            return {
                'response': response,
                'session_id': session_id,
                'timestamp': datetime.now().isoformat(),
                'data': hotel_data[:5] if hotel_data else None,
                'show_cards': True,
                'message_type': 'hotel_results',
                'metadata': {
                    'location': location,
                    'dates': dates,
                    'total_hotels': len(hotel_df) if isinstance(hotel_df, pd.DataFrame) else 0
                }
            }
        except Exception as e:
            logger.error(f"Error processing hotel message: {e}")
            raise
    
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