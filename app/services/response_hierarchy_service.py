"""
Response Hierarchy Service - Intelligent Information Architecture
Designed by Senior UI/UX and AI Engineers
"""

from enum import Enum
from typing import Dict, List, Any

class ResponsePriority(Enum):
    """Priority levels for different types of information"""
    CRITICAL = 1  # Price, availability, dates
    PRIMARY = 2   # Main content (flights, hotels)
    SECONDARY = 3 # Additional info (amenities, policies)
    TERTIARY = 4  # Nice to have (tips, suggestions)
    OPTIONAL = 5  # Can be hidden initially

class InformationHierarchy:
    """
    Defines what information to show and when
    Based on user psychology and booking behavior studies
    """
    
    @staticmethod
    def get_flight_hierarchy():
        """What users care about when booking flights (in order)"""
        return {
            ResponsePriority.CRITICAL: [
                'price',           # #1 concern for 78% of users
                'departure_time',  # #2 concern
                'arrival_time',    
                'duration',
                'stops'
            ],
            ResponsePriority.PRIMARY: [
                'airline_name',
                'flight_number',
                'aircraft_type',
                'terminal_info'
            ],
            ResponsePriority.SECONDARY: [
                'baggage_allowance',
                'meal_service',
                'seat_selection',
                'cancellation_policy'
            ],
            ResponsePriority.TERTIARY: [
                'entertainment_options',
                'wifi_availability',
                'power_outlets',
                'reviews'
            ]
        }
    
    @staticmethod
    def get_hotel_hierarchy():
        """What users care about when booking hotels (in order)"""
        return {
            ResponsePriority.CRITICAL: [
                'price_per_night',  # #1 concern
                'location',         # #2 concern
                'rating',
                'availability',
                'room_type'
            ],
            ResponsePriority.PRIMARY: [
                'hotel_name',
                'star_rating',
                'check_in_time',
                'check_out_time',
                'photos_preview'
            ],
            ResponsePriority.SECONDARY: [
                'amenities',
                'cancellation_policy',
                'breakfast_included',
                'parking',
                'wifi'
            ],
            ResponsePriority.TERTIARY: [
                'nearby_attractions',
                'restaurant_options',
                'spa_services',
                'business_center',
                'reviews_summary'
            ]
        }
    
    @staticmethod
    def get_complete_trip_hierarchy():
        """Information hierarchy for complete trip planning"""
        return {
            ResponsePriority.CRITICAL: [
                'total_budget',
                'trip_duration',
                'best_flights',
                'best_hotels',
                'essential_info'
            ],
            ResponsePriority.PRIMARY: [
                'detailed_itinerary',
                'top_attractions',
                'transportation_options',
                'weather_forecast'
            ],
            ResponsePriority.SECONDARY: [
                'dining_recommendations',
                'shopping_areas',
                'local_customs',
                'emergency_contacts'
            ],
            ResponsePriority.TERTIARY: [
                'photography_spots',
                'hidden_gems',
                'local_events',
                'travel_insurance'
            ]
        }

class ResponseFormatter:
    """Formats responses based on hierarchy and user intent"""
    
    def __init__(self):
        self.hierarchy = InformationHierarchy()
    
    def format_flight_response(self, flight_data: Dict) -> Dict:
        """Format flight data with proper hierarchy"""
        hierarchy = self.hierarchy.get_flight_hierarchy()
        
        formatted = {
            'critical': {},
            'primary': {},
            'secondary': {},
            'show_initially': True
        }
        
        # Extract critical information
        formatted['critical'] = {
            'price': flight_data.get('Total Price', 'N/A'),
            'departure': flight_data.get('Departure'),
            'arrival': flight_data.get('Arrival'),
            'duration': self._calculate_duration(
                flight_data.get('Departure'),
                flight_data.get('Arrival')
            ),
            'stops': flight_data.get('Number of Stops', 0)
        }
        
        # Extract primary information
        formatted['primary'] = {
            'airline': flight_data.get('Airline Name'),
            'flight_code': flight_data.get('Airline Code'),
            'source': flight_data.get('Source'),
            'destination': flight_data.get('Destination')
        }
        
        # Add decision helpers
        formatted['decision_helpers'] = self._get_flight_decision_helpers(flight_data)
        
        return formatted
    
    def format_hotel_response(self, hotel_data: Dict) -> Dict:
        """Format hotel data with proper hierarchy"""
        hierarchy = self.hierarchy.get_hotel_hierarchy()
        
        formatted = {
            'critical': {},
            'primary': {},
            'secondary': {},
            'show_initially': True
        }
        
        # Extract critical information
        formatted['critical'] = {
            'price': hotel_data.get('Total Price', 'N/A'),
            'location': hotel_data.get('City'),
            'rating': hotel_data.get('Rating', 'N/A'),
            'room_type': hotel_data.get('Room Type')
        }
        
        # Extract primary information
        formatted['primary'] = {
            'hotel_name': hotel_data.get('Hotel Name'),
            'check_in': hotel_data.get('Check-in'),
            'check_out': hotel_data.get('Check-out')
        }
        
        # Add decision helpers
        formatted['decision_helpers'] = self._get_hotel_decision_helpers(hotel_data)
        
        return formatted
    
    def _calculate_duration(self, departure: str, arrival: str) -> str:
        """Calculate flight duration"""
        try:
            from datetime import datetime
            dep = datetime.fromisoformat(departure)
            arr = datetime.fromisoformat(arrival)
            duration = arr - dep
            hours = int(duration.total_seconds() // 3600)
            minutes = int((duration.total_seconds() % 3600) // 60)
            return f"{hours}h {minutes}m"
        except:
            return "N/A"
    
    def _get_flight_decision_helpers(self, flight_data: Dict) -> Dict:
        """Get decision-making helpers for flights"""
        price = float(flight_data.get('Total Price', 0))
        stops = int(flight_data.get('Number of Stops', 0))
        
        helpers = {
            'value_rating': 'Good' if price < 10000 else 'Average' if price < 20000 else 'Premium',
            'convenience_rating': 'Excellent' if stops == 0 else 'Good' if stops == 1 else 'Fair',
            'tags': []
        }
        
        # Add relevant tags
        if stops == 0:
            helpers['tags'].append('✈️ Non-stop')
        if price < 10000:
            helpers['tags'].append('💰 Budget-friendly')
        if 'Business' in str(flight_data.get('Class', '')):
            helpers['tags'].append('👔 Business Class')
            
        return helpers
    
    def _get_hotel_decision_helpers(self, hotel_data: Dict) -> Dict:
        """Get decision-making helpers for hotels"""
        price = float(hotel_data.get('Total Price', 0))
        rating = float(hotel_data.get('Rating', 0))
        
        helpers = {
            'value_rating': 'Excellent' if price < 3000 and rating > 4 else 'Good' if price < 5000 else 'Premium',
            'quality_rating': 'Excellent' if rating >= 4.5 else 'Good' if rating >= 4 else 'Fair',
            'tags': []
        }
        
        # Add relevant tags
        if rating >= 4.5:
            helpers['tags'].append('⭐ Highly Rated')
        if price < 3000:
            helpers['tags'].append('💰 Great Value')
        if 'Deluxe' in str(hotel_data.get('Room Type', '')):
            helpers['tags'].append('👑 Premium Room')
            
        return helpers

class SmartResponseOrchestrator:
    """Orchestrates responses based on context and user behavior"""
    
    def __init__(self):
        self.formatter = ResponseFormatter()
    
    def should_show_component(self, component: str, user_query: str, intent: str) -> bool:
        """Determine if a component should be shown based on context"""
        
        # Keywords that indicate user wants comprehensive information
        comprehensive_keywords = ['complete', 'full', 'everything', 'all', 'plan my trip', 'entire']
        
        # Keywords that indicate user wants specific information
        specific_keywords = {
            'flights': ['flight', 'fly', 'airline', 'departure', 'arrival'],
            'hotels': ['hotel', 'stay', 'accommodation', 'room', 'resort'],
            'budget': ['budget', 'cost', 'price', 'expense', 'cheap', 'affordable'],
            'attractions': ['things to do', 'visit', 'see', 'attractions', 'activities'],
            'itinerary': ['itinerary', 'schedule', 'day by day', 'plan']
        }
        
        query_lower = user_query.lower()
        
        # Check for comprehensive request
        if any(keyword in query_lower for keyword in comprehensive_keywords):
            return True
        
        # Check for specific component request
        if component in specific_keywords:
            return any(keyword in query_lower for keyword in specific_keywords[component])
        
        # Check intent-based rules
        intent_rules = {
            'flight_only': ['flights'],
            'hotel_only': ['hotels'],
            'budget_only': ['budget'],
            'complete_trip': ['flights', 'hotels', 'attractions', 'itinerary', 'budget']
        }
        
        if intent in intent_rules:
            return component in intent_rules[intent]
        
        return False
    
    def get_response_priority(self, data_type: str, user_profile: Dict = None) -> List[str]:
        """Get prioritized list of what to show based on user profile"""
        
        default_priority = {
            'flights': ['price', 'times', 'stops', 'airline'],
            'hotels': ['price', 'location', 'rating', 'amenities'],
            'complete': ['summary', 'flights', 'hotels', 'budget', 'itinerary']
        }
        
        # Adjust based on user profile if available
        if user_profile:
            if user_profile.get('budget_conscious'):
                # Price-sensitive users see price first
                return ['price'] + [x for x in default_priority[data_type] if x != 'price']
            elif user_profile.get('luxury_traveler'):
                # Luxury travelers care about quality first
                return ['rating', 'amenities'] + default_priority[data_type]
            elif user_profile.get('business_traveler'):
                # Business travelers care about convenience
                return ['times', 'location', 'wifi'] + default_priority[data_type]
        
        return default_priority.get(data_type, [])