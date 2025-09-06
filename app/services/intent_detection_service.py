"""
Intent Detection Service for Travel Queries
Identifies what the user is asking for: flights only, hotels only, or complete trip planning
"""

import re
from typing import Dict, List, Set
from enum import Enum

class QueryIntent(Enum):
    FLIGHT_ONLY = "flight_only"
    HOTEL_ONLY = "hotel_only"
    ATTRACTIONS_ONLY = "attractions_only"
    COMPLETE_TRIP = "complete_trip"
    ITINERARY_ONLY = "itinerary_only"
    BUDGET_ONLY = "budget_only"

class IntentDetectionService:
    def __init__(self):
        # Keywords for different intents
        self.flight_keywords = {
            'flight', 'flights', 'fly', 'flying', 'airline', 'airlines', 
            'airfare', 'plane', 'ticket', 'tickets', 'book flight',
            'flight booking', 'flight price', 'flight cost', 'cheapest flight'
        }
        
        self.hotel_keywords = {
            'hotel', 'hotels', 'accommodation', 'stay', 'lodging', 
            'resort', 'resorts', 'motel', 'hostel', 'guesthouse',
            'where to stay', 'book hotel', 'hotel booking', 'room', 'rooms',
            'hotel price', 'hotel cost', 'cheapest hotel'
        }
        
        self.attraction_keywords = {
            'attraction', 'attractions', 'things to do', 'places to visit',
            'tourist', 'sightseeing', 'activities', 'what to do',
            'must see', 'must visit', 'landmarks', 'monuments',
            'restaurants', 'dining', 'food', 'eat', 'cuisine'
        }
        
        self.itinerary_keywords = {
            'itinerary', 'schedule', 'plan', 'day by day', 'timeline',
            'agenda', 'program', 'route', 'journey'
        }
        
        self.budget_keywords = {
            'budget', 'cost', 'price', 'expense', 'spend', 'money',
            'how much', 'affordable', 'cheap', 'expensive'
        }
        
        self.complete_trip_keywords = {
            'trip', 'vacation', 'holiday', 'travel', 'tour', 'journey',
            'getaway', 'weekend', 'package', 'complete', 'full',
            'plan my trip', 'travel planning', 'help me plan'
        }
        
        # Exclusion patterns - if these are present, it's likely NOT a single intent
        self.multi_intent_patterns = [
            r'\band\b.*\b(flight|hotel|accommodation|things to do)',
            r'(flight|hotel).*\b(and|with|plus|including)\b',
            r'complete|full|entire|whole|all',
            r'everything|package|comprehensive'
        ]

    def detect_intent(self, query: str) -> Dict:
        """
        Detect the intent of a travel query
        Returns a dictionary with intent type and components to include
        """
        query_lower = query.lower()
        
        # Check for multi-intent patterns first
        is_multi_intent = any(re.search(pattern, query_lower) 
                              for pattern in self.multi_intent_patterns)
        
        # Count matches for each category
        flight_matches = self._count_keyword_matches(query_lower, self.flight_keywords)
        hotel_matches = self._count_keyword_matches(query_lower, self.hotel_keywords)
        attraction_matches = self._count_keyword_matches(query_lower, self.attraction_keywords)
        itinerary_matches = self._count_keyword_matches(query_lower, self.itinerary_keywords)
        budget_matches = self._count_keyword_matches(query_lower, self.budget_keywords)
        complete_matches = self._count_keyword_matches(query_lower, self.complete_trip_keywords)
        
        # Determine components to include
        components = {
            'flights': False,
            'hotels': False,
            'attractions': False,
            'itinerary': False,
            'budget': False,
            'tips': False,
            'summary': True  # Always show summary
        }
        
        intent = None
        
        # If query explicitly mentions complete trip or has multi-intent patterns
        if is_multi_intent or complete_matches > 0:
            intent = QueryIntent.COMPLETE_TRIP
            components = {
                'flights': True,
                'hotels': True,
                'attractions': True,
                'itinerary': True,
                'budget': True,
                'tips': True,
                'summary': True
            }
        
        # Check for specific single intents
        elif flight_matches > 0 and hotel_matches == 0 and attraction_matches == 0:
            intent = QueryIntent.FLIGHT_ONLY
            components['flights'] = True
            
        elif hotel_matches > 0 and flight_matches == 0 and attraction_matches == 0:
            intent = QueryIntent.HOTEL_ONLY
            components['hotels'] = True
            
        elif attraction_matches > 0 and flight_matches == 0 and hotel_matches == 0:
            intent = QueryIntent.ATTRACTIONS_ONLY
            components['attractions'] = True
            
        elif itinerary_matches > 1 and flight_matches == 0 and hotel_matches == 0:
            intent = QueryIntent.ITINERARY_ONLY
            components['itinerary'] = True
            components['attractions'] = True  # Include attractions in itinerary
            
        elif budget_matches > 1 and flight_matches == 0 and hotel_matches == 0:
            intent = QueryIntent.BUDGET_ONLY
            components['budget'] = True
            
        # If multiple components are mentioned or unclear, default to complete trip
        else:
            intent_count = sum([
                flight_matches > 0,
                hotel_matches > 0,
                attraction_matches > 0,
                itinerary_matches > 0,
                budget_matches > 0
            ])
            
            if intent_count >= 2:
                intent = QueryIntent.COMPLETE_TRIP
                components = {
                    'flights': True,
                    'hotels': True,
                    'attractions': True,
                    'itinerary': True,
                    'budget': True,
                    'tips': True,
                    'summary': True
                }
            elif intent_count == 1:
                # Set components based on what was detected
                components['flights'] = flight_matches > 0
                components['hotels'] = hotel_matches > 0
                components['attractions'] = attraction_matches > 0
                components['itinerary'] = itinerary_matches > 0
                components['budget'] = budget_matches > 0
                
                if flight_matches > 0:
                    intent = QueryIntent.FLIGHT_ONLY
                elif hotel_matches > 0:
                    intent = QueryIntent.HOTEL_ONLY
                elif attraction_matches > 0:
                    intent = QueryIntent.ATTRACTIONS_ONLY
                elif itinerary_matches > 0:
                    intent = QueryIntent.ITINERARY_ONLY
                elif budget_matches > 0:
                    intent = QueryIntent.BUDGET_ONLY
            else:
                # Default to complete trip if no specific intent detected
                intent = QueryIntent.COMPLETE_TRIP
                components = {
                    'flights': True,
                    'hotels': True,
                    'attractions': True,
                    'itinerary': True,
                    'budget': True,
                    'tips': True,
                    'summary': True
                }
        
        return {
            'intent': intent.value if intent else QueryIntent.COMPLETE_TRIP.value,
            'components': components,
            'confidence': self._calculate_confidence(query_lower, intent),
            'detected_keywords': {
                'flights': flight_matches,
                'hotels': hotel_matches,
                'attractions': attraction_matches,
                'itinerary': itinerary_matches,
                'budget': budget_matches,
                'complete': complete_matches
            }
        }
    
    def _count_keyword_matches(self, text: str, keywords: Set[str]) -> int:
        """Count how many keywords are present in the text"""
        count = 0
        for keyword in keywords:
            if keyword in text:
                count += 1
        return count
    
    def _calculate_confidence(self, query: str, intent: QueryIntent) -> float:
        """Calculate confidence score for the detected intent"""
        if not intent:
            return 0.0
            
        # Simple confidence calculation based on keyword matches
        if intent == QueryIntent.COMPLETE_TRIP:
            if any(word in query for word in ['complete', 'full', 'entire', 'package']):
                return 0.95
            return 0.85
            
        # For specific intents, higher confidence if only that type is mentioned
        keyword_counts = {
            QueryIntent.FLIGHT_ONLY: self._count_keyword_matches(query, self.flight_keywords),
            QueryIntent.HOTEL_ONLY: self._count_keyword_matches(query, self.hotel_keywords),
            QueryIntent.ATTRACTIONS_ONLY: self._count_keyword_matches(query, self.attraction_keywords),
            QueryIntent.ITINERARY_ONLY: self._count_keyword_matches(query, self.itinerary_keywords),
            QueryIntent.BUDGET_ONLY: self._count_keyword_matches(query, self.budget_keywords)
        }
        
        if intent in keyword_counts:
            intent_count = keyword_counts[intent]
            other_counts = sum(c for k, c in keyword_counts.items() if k != intent)
            
            if intent_count > 0 and other_counts == 0:
                return 0.95
            elif intent_count > other_counts:
                return 0.85
            else:
                return 0.70
                
        return 0.75
    
    def get_response_message(self, intent: str) -> str:
        """Get appropriate response message based on intent"""
        messages = {
            QueryIntent.FLIGHT_ONLY.value: "Searching for the best flight options...",
            QueryIntent.HOTEL_ONLY.value: "Finding the perfect accommodations for your stay...",
            QueryIntent.ATTRACTIONS_ONLY.value: "Discovering amazing things to do and places to visit...",
            QueryIntent.ITINERARY_ONLY.value: "Creating your day-by-day travel itinerary...",
            QueryIntent.BUDGET_ONLY.value: "Calculating your travel budget and expenses...",
            QueryIntent.COMPLETE_TRIP.value: "Planning your complete travel experience..."
        }
        return messages.get(intent, "Processing your travel request...")