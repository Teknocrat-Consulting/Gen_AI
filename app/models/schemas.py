from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatMessage(BaseModel):
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    
    @validator('message')
    def message_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Message cannot be empty')
        return v.strip()


class ChatResponse(BaseModel):
    response: str
    session_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    flight_data: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None


class FlightSearchRequest(BaseModel):
    origin: str
    destination: str
    departure_date: str
    adults: int = 1
    
    @validator('departure_date')
    def validate_date(cls, v):
        try:
            datetime.strptime(v, '%Y-%m-%d')
        except ValueError:
            raise ValueError('Date must be in YYYY-MM-DD format')
        return v
    
    @validator('adults')
    def validate_adults(cls, v):
        if v < 1 or v > 9:
            raise ValueError('Number of adults must be between 1 and 9')
        return v


class FlightInfo(BaseModel):
    airline_code: str
    airline_name: str
    departure: datetime
    arrival: datetime
    total_price: float
    currency: str
    number_of_stops: int
    cabin: str
    one_way: bool


class FlightSearchResponse(BaseModel):
    flights: List[FlightInfo]
    origin: str
    destination: str
    departure_date: str
    total_results: int


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime = Field(default_factory=datetime.now)
    version: str
    services: Dict[str, bool]