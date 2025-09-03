import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from app.core.config import settings


def setup_logging():
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL),
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
            RotatingFileHandler(
                settings.LOG_FILE,
                maxBytes=10485760,  
                backupCount=5
            )
        ]
    )
    
    logging.getLogger("uvicorn.access").handlers = []
    
    return logging.getLogger(__name__)


logger = setup_logging()