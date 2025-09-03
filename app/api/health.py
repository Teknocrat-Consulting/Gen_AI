from fastapi import APIRouter
from app.models.schemas import HealthResponse
from app.core.config import settings
from app.core.logging import logger
from datetime import datetime

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("/", response_model=HealthResponse)
async def health_check():
    try:
        services_status = {
            "api": True,
            "openai": True,
            "amadeus": True,
        }
        
        return HealthResponse(
            status="healthy",
            timestamp=datetime.now(),
            version=settings.APP_VERSION,
            services=services_status
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            timestamp=datetime.now(),
            version=settings.APP_VERSION,
            services={"api": False}
        )