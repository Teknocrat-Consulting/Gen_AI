from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from contextlib import asynccontextmanager
import os
from pathlib import Path

from app.core.config import settings
from app.core.logging import logger
from app.api import chat, health, hotel, travel_itinerary, travel_streaming


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    yield
    logger.info("Shutting down application")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(health.router)
app.include_router(hotel.router)
app.include_router(travel_itinerary.router)
app.include_router(travel_streaming.router)

static_path = Path(__file__).parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    # Serve the premium booking UI as default
    template_path = Path(__file__).parent / "templates" / "premium_booking.html"
    if template_path.exists():
        with open(template_path, "r") as f:
            return HTMLResponse(content=f.read())
    
    # Fallback to v2 template
    template_path = Path(__file__).parent / "templates" / "travel_planner_v2.html"
    if template_path.exists():
        with open(template_path, "r") as f:
            return HTMLResponse(content=f.read())
    
    # Original fallback
    streaming_path = Path(__file__).parent / "templates" / "streaming_travel.html"
    if streaming_path.exists():
        with open(streaming_path, "r") as f:
            return HTMLResponse(content=f.read())
    
    travel_planner_path = Path(__file__).parent / "templates" / "travel_planner.html"
    if travel_planner_path.exists():
        with open(travel_planner_path, "r") as f:
            return HTMLResponse(content=f.read())
    
    index_path = Path(__file__).parent / "templates" / "index.html"
    if index_path.exists():
        with open(index_path, "r") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>AI Travel Planner</h1><p>Visit /docs for API documentation</p>")


@app.get("/chat", response_class=HTMLResponse)
async def chat_page():
    index_path = Path(__file__).parent / "templates" / "index.html"
    if index_path.exists():
        with open(index_path, "r") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Flight Booking Assistant API</h1><p>Visit /docs for API documentation</p>")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception handler caught: {exc}")
    return {
        "error": "Internal server error",
        "detail": str(exc) if settings.DEBUG else "An unexpected error occurred"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8001,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )