from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from app.models.schemas import ChatRequest, ChatResponse, ErrorResponse
from app.services.chat_service import ChatService
from app.core.logging import logger

router = APIRouter(prefix="/api/chat", tags=["chat"])

chat_service = ChatService()


@router.post("/", response_model=ChatResponse)
async def send_message(request: ChatRequest):
    try:
        logger.info(f"Received chat request: {request.message[:50]}...")
        
        result = chat_service.process_message(
            message=request.message,
            session_id=request.session_id
        )
        
        return ChatResponse(**result)
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{session_id}")
async def get_chat_history(session_id: str):
    try:
        history = chat_service.get_session_history(session_id)
        return {"session_id": session_id, "messages": history}
    except Exception as e:
        logger.error(f"Error fetching chat history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/session/{session_id}")
async def clear_session(session_id: str):
    try:
        success = chat_service.clear_session(session_id)
        if success:
            return {"message": "Session cleared successfully"}
        else:
            raise HTTPException(status_code=404, detail="Session not found")
    except Exception as e:
        logger.error(f"Error clearing session: {e}")
        raise HTTPException(status_code=500, detail=str(e))