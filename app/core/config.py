from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import os


class Settings(BaseSettings):
    APP_NAME: str = "Flight Booking Assistant"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    OPENAI_API_KEY: str
    API_Key: str = Field(alias="API_Key")  
    API_Secret: str = Field(alias="API_Secret")  
    
    CORS_ORIGINS: list[str] = ["*"]
    
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "app.log"
    
    REDIS_URL: Optional[str] = None
    
    SESSION_TIMEOUT: int = 3600
    
    MAX_WORKERS: int = 4
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        

settings = Settings()