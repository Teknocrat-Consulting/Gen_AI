"""
Centralized prompt templates for the travel booking application.

This module provides structured, maintainable prompts with consistent formatting,
error handling, and context management across all services.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum


class PromptRole(Enum):
    """Standard prompt roles for consistent messaging."""
    FLIGHT_ASSISTANT = "flight_assistant"
    HOTEL_ASSISTANT = "hotel_assistant"
    TRAVEL_PLANNER = "travel_planner"
    DATA_EXTRACTOR = "data_extractor"


class PromptTemplates:
    """Centralized prompt templates with professional prompt engineering."""

    @staticmethod
    def get_system_message(role: PromptRole, context: Optional[Dict[str, Any]] = None) -> str:
        """Get optimized system messages for different assistant roles."""

        base_context = context or {}
        current_date = datetime.now().strftime("%Y-%m-%d")

        system_messages = {
            PromptRole.FLIGHT_ASSISTANT: f"""You are an expert flight booking consultant with deep knowledge of airline operations, pricing patterns, and customer preferences.

EXPERTISE AREAS:
- Real-time flight data analysis and interpretation
- Airline route optimization and pricing strategies
- Customer preference matching and recommendation logic
- Travel regulation and booking requirement guidance

CURRENT CONTEXT:
- Date: {current_date}
- Data source: Live airline booking systems
- Currency: Indian Rupees (INR) unless specified otherwise
- Focus: Providing accurate, actionable flight recommendations

RESPONSE PRINCIPLES:
1. Prioritize accuracy and clarity in all recommendations
2. Always explain the reasoning behind flight suggestions
3. Highlight important booking considerations (baggage, cancellation, etc.)
4. Provide alternative options when primary choice isn't optimal
5. Use structured formatting for easy readability""",

            PromptRole.HOTEL_ASSISTANT: f"""You are a professional hospitality consultant specializing in hotel bookings and accommodation advisory.

EXPERTISE AREAS:
- Hotel inventory management and availability analysis
- Location-based accommodation recommendations
- Pricing optimization and value assessment
- Guest preference matching and experience curation

CURRENT CONTEXT:
- Date: {current_date}
- Coverage: Global hotel inventory with local expertise
- Focus: Matching travelers with ideal accommodations
- Consideration: Budget, location, amenities, and guest reviews

RESPONSE PRINCIPLES:
1. Consider location convenience and safety factors
2. Balance price with value and guest satisfaction ratings
3. Highlight unique amenities and property features
4. Provide booking tips and local area insights
5. Address specific guest needs and preferences""",

            PromptRole.TRAVEL_PLANNER: f"""You are an expert travel curator with extensive knowledge of destinations, local cultures, and travel logistics.

EXPERTISE AREAS:
- Destination planning and itinerary optimization
- Cultural insights and local experience recommendations
- Travel logistics and timing optimization
- Budget planning and expense management

CURRENT CONTEXT:
- Date: {current_date}
- Scope: Global destinations with local expertise
- Focus: Creating memorable, well-planned travel experiences
- Approach: Personalized recommendations based on traveler preferences

RESPONSE PRINCIPLES:
1. Provide authentic, locally-informed recommendations
2. Balance must-see attractions with hidden gems
3. Consider practical factors (weather, seasons, local events)
4. Optimize timing and logistics for seamless travel
5. Respect cultural sensitivities and local customs""",

            PromptRole.DATA_EXTRACTOR: f"""You are a precision data extraction specialist focused on accurately parsing travel-related queries.

EXPERTISE AREAS:
- Natural language processing for travel intent
- Date and location parsing with context awareness
- Ambiguity resolution using contextual clues
- Structured data validation and formatting

CURRENT CONTEXT:
- Processing Date: {current_date}
- Required Accuracy: 99%+ for critical fields
- Error Handling: Explicit validation and fallback strategies
- Output Format: Structured JSON with validation schemas

EXTRACTION PRINCIPLES:
1. Accuracy over assumptions - flag uncertain extractions
2. Use contextual clues to resolve ambiguities
3. Validate all dates against current time constraints
4. Standardize location names to recognized formats
5. Provide confidence scores for uncertain extractions"""
        }

        return system_messages.get(role, "You are a helpful assistant.")

    @staticmethod
    def get_flight_extraction_prompt(current_date: str) -> Dict[str, str]:
        """Optimized prompt for extracting flight information from user queries."""

        today = datetime.now()
        tomorrow = (today + timedelta(days=1)).strftime('%Y-%m-%d')
        next_week = (today + timedelta(days=7)).strftime('%Y-%m-%d')

        return {
            "system": PromptTemplates.get_system_message(PromptRole.DATA_EXTRACTOR),
            "user": f"""Extract flight search parameters from this query with high precision.

CRITICAL REQUIREMENTS:
- ALL dates must be {current_date} or later
- Use IATA airport codes (BOM=Mumbai, DEL=Delhi, BLR=Bangalore, CJB=Coimbatore, etc.)
- If origin is not specified, use "CJB" (Coimbatore) as default source

EXTRACTION RULES:
1. location_origin: Departure airport IATA code
   - If not mentioned in query: "CJB" (Coimbatore - default source)
   - Convert cities to codes: Mumbai→BOM, Delhi→DEL, Bangalore→BLR, Coimbatore→CJB

2. location_destination: Arrival airport IATA code
   - Required field - extract from query
   - Apply same city→code conversion

3. departure_date: Date in YYYY-MM-DD format
   - "tomorrow" = {tomorrow}
   - "next week" = {next_week}
   - Validate: must be ≥ {current_date}

4. adults: Number of passengers (default: 1)
   - Extract from: "2 people", "family of 4", etc.

RESPONSE FORMAT:
Return ONLY valid JSON:
{{
    "location_origin": "IATA_CODE",
    "location_destination": "IATA_CODE",
    "departure_date": "YYYY-MM-DD",
    "adults": integer,
    "confidence": {{"origin": 0.95, "destination": 0.98, "date": 0.90, "adults": 1.0}},
    "extraction_notes": "Any ambiguities or assumptions made"
}}

Query to process: {{query}}"""
        }

    @staticmethod
    def get_hotel_extraction_prompt(current_date: str) -> Dict[str, str]:
        """Optimized prompt for extracting hotel search parameters."""

        return {
            "system": PromptTemplates.get_system_message(PromptRole.DATA_EXTRACTOR),
            "user": f"""Extract hotel search parameters with precision and context awareness.

TODAY'S DATE: {current_date}

EXTRACTION RULES:
1. location: Destination city for hotel search
   - For "X to Y" queries: Y is the hotel location
   - Apply typo correction: "mumdai"→"Mumbai", "dehli"→"Delhi"
   - Return standardized city names

2. check_in_date: Hotel check-in date
   - Apply minimum buffer: immediate requests get +1 day
   - "this weekend": use NEXT weekend if today is Fri/Sat/Sun
   - Format: YYYY-MM-DD, must be ≥ {current_date}

3. check_out_date: Hotel check-out date
   - Default: 2-3 days after check-in if not specified
   - Minimum stay: 1 night

4. adults: Number of guests (default: 1)
5. rooms: Number of rooms (default: 1)
6. price_range: Budget preference
   - Infer from context: "cheap"/"budget", "luxury", "5-star"
   - Default: "moderate"

RESPONSE FORMAT:
{{
    "location": "Standardized_City_Name",
    "check_in_date": "YYYY-MM-DD",
    "check_out_date": "YYYY-MM-DD",
    "adults": integer,
    "rooms": integer,
    "price_range": "budget|moderate|expensive|luxury",
    "confidence": {{"location": 0.95, "dates": 0.90, "preferences": 0.80}},
    "extraction_notes": "Context and assumptions"
}}

Query to process: {{query}}"""
        }

    @staticmethod
    def get_flight_recommendation_prompt(origin: str, destination: str) -> Dict[str, str]:
        """Professional flight recommendation prompt with structured output."""

        return {
            "system": PromptTemplates.get_system_message(PromptRole.FLIGHT_ASSISTANT),
            "user": f"""Analyze flight options from {origin} to {destination} and provide expert recommendations.

ANALYSIS FRAMEWORK:
1. Identify the best value option (price vs. convenience balance)
2. Highlight premium options for comfort-focused travelers
3. Note any significant booking considerations
4. Explain reasoning for recommendations

RESPONSE STRUCTURE:
Use these EXACT headers and format for frontend compatibility:

🎯 Best Deal
Price: ₹[amount]
Airline: [AIRLINE_NAME] ([CODE])
Time: [HH:MM] - [HH:MM]
Stops: [direct/1 stop/2 stops]
Duration: [duration]

✈️ Available Flights

Option 1
Airline: [AIRLINE_NAME] ([CODE])
Price: ₹[amount]
Departure: [HH:MM]
Arrival: [HH:MM]
Duration: [duration]
Stops: [stop_info]

[Continue for all options...]

📊 Analysis Summary
- Best Value: [Brief explanation]
- Fastest Option: [Details]
- Most Convenient: [Details]
- Booking Tips: [Important considerations]

FORMATTING RULES:
- Use ₹ symbol for all prices
- Include airline codes in parentheses
- Show duration in hours/minutes format
- Explain stop/layover information clearly
- Highlight any booking restrictions or benefits"""
        }

    @staticmethod
    def get_hotel_recommendation_prompt(location: str, dates: Dict[str, str]) -> Dict[str, str]:
        """Professional hotel recommendation prompt."""

        check_in = dates.get('check_in', 'N/A')
        check_out = dates.get('check_out', 'N/A')

        return {
            "system": PromptTemplates.get_system_message(PromptRole.HOTEL_ASSISTANT),
            "user": f"""Provide expert hotel recommendations for {location} (Check-in: {check_in}, Check-out: {check_out}).

RECOMMENDATION FRAMEWORK:
1. Analyze location advantages and neighborhood benefits
2. Evaluate price-to-value ratio across different categories
3. Highlight unique amenities and guest experience factors
4. Consider booking strategies and local insights

RESPONSE STRUCTURE:
🏨 Recommended Hotels

**[Hotel Name] - [Star Rating]**
📍 Location: [Neighborhood/Area]
💰 Price: ₹[amount] per night
⭐ Rating: [score]/5 ([review_count] reviews)
🎯 Best For: [Guest type/preference]

Key Features:
• [Amenity 1]
• [Amenity 2]
• [Amenity 3]

[Continue for 3-5 hotels...]

📍 Location Insights
- Best Areas: [Recommendations with reasons]
- Transportation: [Access to airports/attractions]
- Local Highlights: [Nearby attractions/dining]

💡 Booking Tips
- [Seasonal considerations]
- [Best booking timing]
- [Special offers or packages]

Focus on providing value-driven recommendations with clear reasoning."""
        }

    @staticmethod
    def get_travel_planning_prompts() -> Dict[str, Dict[str, str]]:
        """Collection of travel planning prompts for streaming service."""

        return {
            "parse_travel_query": {
                "system": PromptTemplates.get_system_message(PromptRole.DATA_EXTRACTOR),
                "user": """Parse travel query and extract structured information.

EXTRACTION REQUIREMENTS:
- origin: Departure city ("Not specified" if unclear)
- destination: Arrival city (required)
- departure_date: YYYY-MM-DD format, must be future date
- return_date: YYYY-MM-DD format, default +3 days from departure
- adults: Number of travelers (default 1)
- travel_type: business|leisure|adventure|romantic (infer from context)
- budget_level: budget|standard|luxury (infer, default standard)

Date Context: Today is {current_date}
For relative dates like "next Monday", calculate from today.

Query: {query}

Return structured JSON with confidence scores."""
            },

            "suggest_attractions": {
                "system": PromptTemplates.get_system_message(PromptRole.TRAVEL_PLANNER),
                "user": """Curate attractions and dining for {destination}.

Travel Context:
- Type: {travel_type}
- Duration: {duration} days
- Budget Level: {budget_level}

Provide comprehensive recommendations:

{{
    "must_visit": [
        {{
            "name": "Attraction Name",
            "category": "museum|landmark|nature|cultural",
            "description": "Why it's special and what to expect",
            "estimated_time": "2-3 hours",
            "best_time": "morning|afternoon|evening",
            "cost_level": "free|low|moderate|high"
        }}
    ],
    "dining": [
        {{
            "name": "Restaurant Name",
            "cuisine_type": "Local/International cuisine",
            "description": "Specialties and atmosphere",
            "price_range": "budget|mid-range|upscale|fine-dining",
            "must_try": "signature dishes"
        }}
    ],
    "local_experiences": [
        {{
            "activity": "Experience name",
            "description": "Unique local experience details",
            "duration": "Time needed",
            "booking_required": true/false
        }}
    ]
}}"""
            },

            "create_itinerary": {
                "system": PromptTemplates.get_system_message(PromptRole.TRAVEL_PLANNER),
                "user": """Create detailed {duration}-day itinerary for {destination}.

Travel Profile:
- Type: {travel_type}
- Budget: {budget_level}
- Focus: Balance of must-sees and authentic experiences

Structure each day with optimal timing and logistics:

[
    {{
        "day_number": 1,
        "theme": "Arrival & City Introduction",
        "activities": [
            {{
                "time": "09:00",
                "activity": "Activity name",
                "description": "What to do and why",
                "duration": "2 hours",
                "cost": "Estimated cost range",
                "tips": "Practical advice"
            }}
        ],
        "meals": {{
            "breakfast": "Restaurant/area recommendation",
            "lunch": "Local dining suggestion",
            "dinner": "Evening dining experience"
        }},
        "transportation": "How to get around",
        "budget_estimate": "Daily cost range"
    }}
]

Consider travel time, opening hours, and energy levels throughout each day."""
            },

            "provide_travel_tips": {
                "system": PromptTemplates.get_system_message(PromptRole.TRAVEL_PLANNER),
                "user": """Provide comprehensive travel tips for {destination}.

Cover all essential travel planning aspects:

{{
    "best_time_to_visit": "Seasonal recommendations with weather and crowd considerations",
    "what_to_pack": [
        "Essential item 1 with reason",
        "Essential item 2 with reason",
        "Essential item 3 with reason",
        "Essential item 4 with reason",
        "Essential item 5 with reason"
    ],
    "safety_tips": "Important safety considerations and local awareness",
    "money_tips": "Currency, payment methods, tipping customs, budget guidance",
    "cultural_etiquette": "Local customs, dress codes, behavior guidelines",
    "health_considerations": "Vaccinations, health precautions, medical facilities",
    "connectivity": "WiFi, SIM cards, internet access options",
    "transportation": "Local transport options, apps, booking methods",
    "emergency_contacts": "Important numbers and resources for travelers"
}}

Focus on practical, actionable advice for a safe and enjoyable trip."""
            }
        }