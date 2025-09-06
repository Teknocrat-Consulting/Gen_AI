import json
from datetime import datetime
from typing import Optional, Dict, Any, List
import requests
import pandas as pd
from amadeus import Client, ResponseError
from openai import OpenAI
from dotenv import load_dotenv
from app.core.logging import logger
from app.core.config import settings

load_dotenv()


class AttractionsService:
    def __init__(self):
        self.amadeus = Client(
            client_id=settings.API_Key,
            client_secret=settings.API_Secret
        )
        api_key = settings.OPENAI_API_KEY
        if not api_key:
            logger.error("OPENAI_API_KEY is not set!")
            raise ValueError("OPENAI_API_KEY is required")
        logger.info(f"Initializing OpenAI client with key: {api_key[:10]}...")
        self.openai_client = OpenAI(api_key=api_key)
    
    def get_city_coordinates(self, city_name: str) -> Optional[Dict[str, float]]:
        """Get city coordinates for attractions search"""
        try:
            response = self.amadeus.reference_data.locations.get(
                keyword=city_name,
                subType='CITY'
            )
            if response.data:
                location = response.data[0]
                return {
                    'latitude': location.get('geoCode', {}).get('latitude'),
                    'longitude': location.get('geoCode', {}).get('longitude')
                }
            return None
        except ResponseError as error:
            logger.error(f"Error finding coordinates for {city_name}: {error}")
            return None
    
    def search_points_of_interest(self, latitude: float, longitude: float, 
                                 radius: int = 5) -> List[Dict[str, Any]]:
        """Search for points of interest using Amadeus API"""
        try:
            # Try the correct Amadeus API endpoint for POI
            response = self.amadeus.reference_data.locations.points_of_interest.get(
                latitude=latitude,
                longitude=longitude,
                radius=radius
            )
            return response.data if response.data else []
        except Exception as error:
            logger.error(f"Error searching points of interest with Amadeus API: {error}")
            logger.info("Falling back to OpenAI knowledge for attractions")
            return []
    
    def get_popular_attractions_fallback(self, city_name: str) -> List[Dict[str, Any]]:
        """Fallback method to get popular attractions using OpenAI knowledge"""
        try:
            messages = [
                {
                    "role": "system",
                    "content": (
                        f"You are a travel guide expert. Provide a list of top 10 popular attractions, "
                        f"landmarks, and activities in {city_name}. For each attraction, provide: "
                        f"1. name: The name of the attraction "
                        f"2. category: The type (e.g., 'SIGHTS', 'RESTAURANT', 'SHOPPING', 'ENTERTAINMENT') "
                        f"3. description: A brief description (50-100 words) "
                        f"4. estimated_time: Suggested time to spend (in hours) "
                        f"5. best_time: Best time to visit (morning/afternoon/evening) "
                        f"6. popularity_score: Score from 1-10 based on popularity "
                        f"Provide the response in valid JSON format as an array of objects."
                    )
                },
                {
                    "role": "user",
                    "content": f"Give me popular attractions in {city_name}"
                }
            ]
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=2000,
                temperature=0.3
            )
            
            if response and response.choices:
                response_text = response.choices[0].message.content.strip()
                
                # Handle potential markdown code blocks
                if "```json" in response_text:
                    start = response_text.find("```json") + 7
                    end = response_text.find("```", start)
                    if end != -1:
                        response_text = response_text[start:end].strip()
                elif "```" in response_text:
                    start = response_text.find("```") + 3
                    end = response_text.find("```", start)
                    if end != -1:
                        response_text = response_text[start:end].strip()
                
                # Extract JSON part
                if response_text and not response_text.startswith("["):
                    start_idx = response_text.find("[")
                    end_idx = response_text.rfind("]")
                    if start_idx != -1 and end_idx != -1:
                        response_text = response_text[start_idx:end_idx+1]
                
                attractions = json.loads(response_text)
                return attractions if isinstance(attractions, list) else []
            
            return []
        except Exception as e:
            logger.error(f"Error getting fallback attractions for {city_name}: {e}")
            return []
    
    def get_attractions_for_city(self, city_name: str) -> List[Dict[str, Any]]:
        """Get attractions for a city using Amadeus API or fallback"""
        # First try Amadeus API
        coordinates = self.get_city_coordinates(city_name)
        if coordinates and coordinates['latitude'] and coordinates['longitude']:
            poi_data = self.search_points_of_interest(
                coordinates['latitude'], 
                coordinates['longitude']
            )
            
            if poi_data:
                formatted_attractions = []
                for poi in poi_data[:10]:  # Limit to top 10
                    formatted_attractions.append({
                        'name': poi.get('name', 'Unknown'),
                        'category': poi.get('category', 'SIGHTS'),
                        'description': poi.get('shortDescription', 'No description available'),
                        'estimated_time': 2,  # Default 2 hours
                        'best_time': 'morning',
                        'popularity_score': 7,  # Default score
                        'latitude': poi.get('geoCode', {}).get('latitude'),
                        'longitude': poi.get('geoCode', {}).get('longitude')
                    })
                return formatted_attractions
        
        # Fallback to OpenAI knowledge
        logger.info(f"Using fallback method for attractions in {city_name}")
        return self.get_popular_attractions_fallback(city_name)
    
    def get_local_experiences(self, city_name: str, interests: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Get local experiences and cultural activities"""
        interests_str = ", ".join(interests) if interests else "general tourism"
        
        try:
            messages = [
                {
                    "role": "system",
                    "content": (
                        f"You are a local travel expert for {city_name}. Provide authentic local experiences "
                        f"based on these interests: {interests_str}. Include: "
                        f"1. name: Experience name "
                        f"2. type: Type of experience (cultural, food, adventure, shopping, etc.) "
                        f"3. description: Detailed description (100-150 words) "
                        f"4. duration: Duration in hours "
                        f"5. cost_estimate: Rough cost estimate in INR "
                        f"6. best_time: Best time of day "
                        f"7. tips: Local tips or recommendations "
                        f"Provide 5-8 unique experiences in JSON format."
                    )
                },
                {
                    "role": "user",
                    "content": f"Recommend local experiences in {city_name} for someone interested in {interests_str}"
                }
            ]
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=1500,
                temperature=0.4
            )
            
            if response and response.choices:
                response_text = response.choices[0].message.content.strip()
                
                # Handle markdown code blocks
                if "```json" in response_text:
                    start = response_text.find("```json") + 7
                    end = response_text.find("```", start)
                    if end != -1:
                        response_text = response_text[start:end].strip()
                elif "```" in response_text:
                    start = response_text.find("```") + 3
                    end = response_text.find("```", start)
                    if end != -1:
                        response_text = response_text[start:end].strip()
                
                if response_text and not response_text.startswith("["):
                    start_idx = response_text.find("[")
                    end_idx = response_text.rfind("]")
                    if start_idx != -1 and end_idx != -1:
                        response_text = response_text[start_idx:end_idx+1]
                
                experiences = json.loads(response_text)
                return experiences if isinstance(experiences, list) else []
            
            return []
        except Exception as e:
            logger.error(f"Error getting local experiences for {city_name}: {e}")
            return []
    
    def get_dining_recommendations(self, city_name: str, cuisine_preferences: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Get dining recommendations for the city"""
        cuisine_str = ", ".join(cuisine_preferences) if cuisine_preferences else "local and popular cuisines"
        
        try:
            messages = [
                {
                    "role": "system",
                    "content": (
                        f"You are a food expert for {city_name}. Recommend the best restaurants and food experiences "
                        f"focusing on: {cuisine_str}. For each recommendation, provide: "
                        f"1. name: Restaurant/food place name "
                        f"2. cuisine_type: Type of cuisine "
                        f"3. description: What makes it special (80-120 words) "
                        f"4. price_range: budget/moderate/expensive "
                        f"5. must_try_dishes: List of 2-3 signature dishes "
                        f"6. location_area: General area/neighborhood "
                        f"7. meal_type: breakfast/lunch/dinner/snacks "
                        f"Include a mix of high-end and local budget options. Provide 6-8 recommendations in JSON format."
                    )
                },
                {
                    "role": "user",
                    "content": f"Recommend the best dining experiences in {city_name} for {cuisine_str}"
                }
            ]
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=1500,
                temperature=0.3
            )
            
            if response and response.choices:
                response_text = response.choices[0].message.content.strip()
                
                # Handle markdown code blocks
                if "```json" in response_text:
                    start = response_text.find("```json") + 7
                    end = response_text.find("```", start)
                    if end != -1:
                        response_text = response_text[start:end].strip()
                elif "```" in response_text:
                    start = response_text.find("```") + 3
                    end = response_text.find("```", start)
                    if end != -1:
                        response_text = response_text[start:end].strip()
                
                if response_text and not response_text.startswith("["):
                    start_idx = response_text.find("[")
                    end_idx = response_text.rfind("]")
                    if start_idx != -1 and end_idx != -1:
                        response_text = response_text[start_idx:end_idx+1]
                
                dining = json.loads(response_text)
                return dining if isinstance(dining, list) else []
            
            return []
        except Exception as e:
            logger.error(f"Error getting dining recommendations for {city_name}: {e}")
            return []