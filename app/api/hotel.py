from fastapi import APIRouter, HTTPException
from typing import Optional
from app.models.schemas import ChatRequest, ChatResponse
from app.services.hotel_service import HotelService
from app.core.logging import logger

router = APIRouter(prefix="/api/hotel", tags=["hotel"])

hotel_service = HotelService()


@router.post("/search", response_model=ChatResponse)
async def search_hotels(request: ChatRequest):
    """Search for hotels based on user query"""
    try:
        logger.info(f"Received hotel search request: {request.message[:50]}...")
        
        # Process hotel search using the hotel service
        result_df, location, dates = hotel_service.process_hotel_search(request.message)
        
        if result_df is not None and not result_df.empty:
            # Convert DataFrame to HTML for display
            html_result = result_df.to_html(index=False, classes='hotel-table', escape=False)
            
            response_text = f"Found {len(result_df)} hotels in {location}"
            if dates:
                response_text += f" for {dates['check_in']} to {dates['check_out']}"
            
            return ChatResponse(
                message=response_text,
                html_content=html_result,
                session_id=request.session_id,
                message_type="hotel_results"
            )
        else:
            return ChatResponse(
                message="I couldn't find any hotels matching your criteria. Please try with different dates or location.",
                session_id=request.session_id,
                message_type="error"
            )
        
    except Exception as e:
        logger.error(f"Error in hotel search endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/city-code/{location}")
async def get_city_code(location: str):
    """Get city code for a location"""
    try:
        city_code = hotel_service.get_city_code(location)
        if city_code:
            return {"location": location, "city_code": city_code}
        else:
            raise HTTPException(status_code=404, detail=f"No city code found for {location}")
    except Exception as e:
        logger.error(f"Error getting city code: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/details/{hotel_id}")
async def get_hotel_details(
    hotel_id: str, 
    check_in: str, 
    check_out: str, 
    adults: int = 1, 
    rooms: int = 1
):
    """Get detailed information about a specific hotel"""
    try:
        hotel_details = hotel_service.get_hotel_details(hotel_id, check_in, check_out, adults, rooms)
        
        if hotel_details:
            return {"hotel_id": hotel_id, "details": hotel_details}
        else:
            raise HTTPException(status_code=404, detail=f"No details found for hotel {hotel_id}")
    except Exception as e:
        logger.error(f"Error getting hotel details: {e}")
        raise HTTPException(status_code=500, detail=str(e))