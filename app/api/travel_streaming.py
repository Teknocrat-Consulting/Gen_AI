from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import json
import asyncio
from typing import AsyncGenerator

from app.core.logging import logger
from app.models.schemas import TravelQuery
from app.services.smart_streaming_service import SmartStreamingService

router = APIRouter(prefix="/api/v1/travel", tags=["Travel Streaming"])


async def event_stream(query: str) -> AsyncGenerator[str, None]:
    """Generate Server-Sent Events (SSE) for streaming travel plan"""
    try:
        service = SmartStreamingService()
        
        async for chunk in service.stream_travel_plan(query):
            # Format as Server-Sent Event
            data = json.dumps(chunk)
            yield f"data: {data}\n\n"
            
            # Small delay to prevent overwhelming the client
            await asyncio.sleep(0.1)
        
        # Send final done event
        yield f"data: {json.dumps({'type': 'done', 'message': 'Stream complete'})}\n\n"
        
    except Exception as e:
        logger.error(f"Error in event stream: {e}")
        error_data = json.dumps({"type": "error", "message": str(e)})
        yield f"data: {error_data}\n\n"


@router.post("/stream")
async def stream_travel_plan(travel_query: TravelQuery):
    """
    Stream travel plan components as they become available using Server-Sent Events (SSE)
    
    This endpoint streams results in real-time as they are processed:
    1. Query parsing and summary
    2. Flight search results
    3. Hotel search results
    4. Attractions and dining
    5. Day-by-day itinerary
    6. Budget calculation
    7. Travel tips
    
    Example:
    ```javascript
    const eventSource = new EventSource('/api/v1/travel/stream');
    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log('Received:', data);
    };
    ```
    """
    try:
        logger.info(f"Starting streaming travel plan for query: {travel_query.query}")
        
        return StreamingResponse(
            event_stream(travel_query.query),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable Nginx buffering
            }
        )
        
    except Exception as e:
        logger.error(f"Error initiating stream: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stream-test")
async def test_streaming():
    """Test endpoint to verify streaming works"""
    async def generate():
        for i in range(5):
            data = json.dumps({"message": f"Test message {i+1}", "progress": (i+1)*20})
            yield f"data: {data}\n\n"
            await asyncio.sleep(1)
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )