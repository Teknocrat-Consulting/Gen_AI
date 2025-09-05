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
    message: str
    session_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    html_content: Optional[str] = None
    message_type: str = "response"
    data: Optional[List[Dict[str, Any]]] = None
    show_cards: bool = False
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


class HotelSearchRequest(BaseModel):
    location: str
    check_in_date: str
    check_out_date: str
    adults: int = 1
    rooms: int = 1
    price_range: Optional[str] = "moderate"
    amenities: Optional[List[str]] = None
    hotel_rating: Optional[int] = None
    
    @validator('check_in_date', 'check_out_date')
    def validate_date(cls, v):
        try:
            datetime.strptime(v, '%Y-%m-%d')
        except ValueError:
            raise ValueError('Date must be in YYYY-MM-DD format')
        return v
    
    @validator('adults', 'rooms')
    def validate_positive_int(cls, v):
        if v < 1:
            raise ValueError('Value must be at least 1')
        return v
    
    @validator('hotel_rating')
    def validate_rating(cls, v):
        if v is not None and (v < 1 or v > 5):
            raise ValueError('Hotel rating must be between 1 and 5')
        return v


class HotelInfo(BaseModel):
    hotel_name: str
    hotel_id: str
    rating: str
    city: str
    country: str
    room_type: str
    total_price: str
    currency: str
    amenities: str
    check_in_time: str
    check_out_time: str


class HotelSearchResponse(BaseModel):
    hotels: List[HotelInfo]
    location: str
    check_in_date: str
    check_out_date: str
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