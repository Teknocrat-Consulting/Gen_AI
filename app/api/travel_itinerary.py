from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
import traceback

from app.core.logging import logger
from app.models.schemas import TravelQuery
from app.services.travel_service_optimized import OptimizedTravelService

router = APIRouter(prefix="/api/v1/travel", tags=["Travel Itinerary"])


@router.post("/plan")
async def create_travel_plan(travel_query: TravelQuery):
    """
    Create a complete travel itinerary from natural language query
    
    Example queries:
    - "I want to go from Mumbai to Delhi next Monday for 2 days, 2 people"
    - "Plan a romantic weekend trip from Bangalore to Goa for 2 adults"
    - "Business trip from Chennai to Hyderabad next week, staying 3 days"
    """
    try:
        logger.info(f"Creating travel plan for query: {travel_query.query}")
        
        # Initialize the optimized travel service
        travel_service = OptimizedTravelService()
        
        # Create complete itinerary
        result = travel_service.create_travel_plan(travel_query.query)
        
        if not result['success']:
            raise HTTPException(
                status_code=400, 
                detail=result.get('error', 'Failed to create travel itinerary')
            )
        
        logger.info("Successfully created travel itinerary")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating travel plan: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        return {
            "success": False,
            "error": f"Internal server error: {str(e)}",
            "data": None
        }


@router.post("/plan-simple", response_model=dict)
async def create_simple_travel_plan(travel_query: TravelQuery):
    """
    Create a simple travel plan with basic formatting for easy frontend consumption
    """
    try:
        logger.info(f"Creating simple travel plan for query: {travel_query.query}")
        
        # Initialize the optimized travel service
        travel_service = OptimizedTravelService()
        
        # Create complete itinerary
        result = travel_service.create_travel_plan(travel_query.query)
        
        if not result['success']:
            return {
                "success": False,
                "error": result.get('error', 'Failed to create travel itinerary'),
                "data": None
            }
        
        # Simplify the response for easier frontend handling
        # Handle both old and new response formats
        if 'data' in result:
            data = result['data']
            summary_key = 'trip_summary'
        else:
            data = result
            summary_key = 'summary'
            
        simplified_response = {
            "success": True,
            "error": None,
            "summary": data.get(summary_key, {}),
            "flights": {
                "outbound": data.get('flights', {}).get('outbound_flights', [])[:3],  # Top 3 options
                "return": data.get('flights', {}).get('return_flights', [])[:3],
                "total_options": data.get('flights', {}).get('total_options', 0)
            },
            "hotels": {
                "options": data.get('hotels', {}).get('hotels', [])[:5],  # Top 5 options
                "total_options": data.get('hotels', {}).get('total_options', 0)
            },
            "attractions": {
                "must_visit": data.get('attractions', {}).get('must_visit', [])[:5],
                "experiences": data.get('attractions', {}).get('experiences', [])[:3],
                "dining": data.get('attractions', {}).get('dining', [])[:4]
            },
            "itinerary": data.get('itinerary', []),
            "budget": data.get('budget', {}),
            "tips": data.get('tips', {})
        }
        
        logger.info("Successfully created simple travel itinerary")
        return simplified_response
        
    except Exception as e:
        logger.error(f"Error creating simple travel plan: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        return {
            "success": False,
            "error": f"Internal server error: {str(e)}",
            "data": None
        }


@router.get("/sample-queries")
async def get_sample_queries():
    """
    Get sample queries that users can try
    """
    return {
        "sample_queries": [
            "I want to go from Mumbai to Delhi next Monday for 2 days, 2 people",
            "Plan a romantic weekend trip from Bangalore to Goa for 2 adults",
            "Business trip from Chennai to Hyderabad next week, staying 3 days",
            "Family vacation from Pune to Jaipur next month for 4 days, 4 people",
            "Adventure trip from Delhi to Manali next Friday for a week, 3 people",
            "Cultural tour from Kolkata to Varanasi next Tuesday for 3 days",
            "Luxury honeymoon trip from Mumbai to Udaipur for 5 days",
            "Budget backpacking from Bangalore to Hampi for 3 days, 2 people"
        ],
        "tips": [
            "Be specific about dates (e.g., 'next Monday', 'December 15th')",
            "Mention number of travelers",
            "Include duration or return date",
            "Add preferences like 'luxury', 'budget', 'romantic', 'adventure'",
            "Specify interests like 'food tour', 'historical sites', 'nightlife'"
        ]
    }


@router.get("/destinations/popular")
async def get_popular_destinations():
    """
    Get list of popular destinations in India
    """
    return {
        "domestic_destinations": [
            {"name": "Delhi", "type": "Historical & Cultural", "best_for": "First-time visitors, History buffs"},
            {"name": "Mumbai", "type": "Metropolitan", "best_for": "Business, Entertainment, Food"},
            {"name": "Goa", "type": "Beach & Leisure", "best_for": "Relaxation, Nightlife, Beaches"},
            {"name": "Jaipur", "type": "Royal Heritage", "best_for": "Architecture, Culture, Shopping"},
            {"name": "Kerala", "type": "Backwaters & Nature", "best_for": "Nature lovers, Ayurveda, Romance"},
            {"name": "Manali", "type": "Hill Station", "best_for": "Adventure, Honeymoon, Nature"},
            {"name": "Udaipur", "type": "Royal & Romantic", "best_for": "Luxury travel, Honeymoon, History"},
            {"name": "Varanasi", "type": "Spiritual", "best_for": "Cultural immersion, Spirituality"},
            {"name": "Agra", "type": "Historical", "best_for": "Taj Mahal, Monuments, Day trips"},
            {"name": "Rishikesh", "type": "Spiritual & Adventure", "best_for": "Yoga, Adventure sports, Spirituality"}
        ],
        "international_destinations": [
            {"name": "Dubai", "type": "Modern & Luxury", "best_for": "Shopping, Luxury, Family"},
            {"name": "Singapore", "type": "Urban & Family", "best_for": "Family travel, City breaks, Food"},
            {"name": "Thailand", "type": "Tropical & Cultural", "best_for": "Beaches, Culture, Budget travel"},
            {"name": "Maldives", "type": "Beach & Luxury", "best_for": "Honeymoon, Luxury, Relaxation"},
            {"name": "Nepal", "type": "Adventure & Spiritual", "best_for": "Trekking, Spirituality, Budget travel"}
        ]
    }


@router.get("/health")
async def travel_service_health():
    """
    Check health of travel planning services
    """
    try:
        # Test service initialization
        OptimizedTravelService()
        
        return {
            "status": "healthy",
            "services": {
                "travel_parser": True,
                "flight_service": True,
                "hotel_service": True,
                "attractions_service": True,
                "itinerary_generator": True
            },
            "message": "All travel services are operational"
        }
    except Exception as e:
        logger.error(f"Travel service health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "message": "One or more travel services are not operational"
            }
        )