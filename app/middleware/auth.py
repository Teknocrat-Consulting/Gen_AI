from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable, List, Optional
import logging

from app.services.auth_service import auth_service

logger = logging.getLogger(__name__)

class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        protected_paths: Optional[List[str]] = None,
        excluded_paths: Optional[List[str]] = None
    ):
        super().__init__(app)
        self.protected_paths = protected_paths or []
        self.excluded_paths = excluded_paths or [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/auth",
            "/health",
            "/"
        ]

    async def dispatch(self, request: Request, call_next: Callable):
        path = request.url.path
        
        # Skip authentication for excluded paths
        if any(path.startswith(excluded_path) for excluded_path in self.excluded_paths):
            return await call_next(request)
        
        # Check if path needs authentication
        if self.protected_paths and not any(path.startswith(protected_path) for protected_path in self.protected_paths):
            return await call_next(request)
        
        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=401,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        token = auth_header.split(" ")[1]
        
        # Validate token
        try:
            result = auth_service.validate_session(token)
            if not result["valid"]:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid or expired token",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            
            # Add user info to request state
            request.state.user = result["user"]
            
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            raise HTTPException(
                status_code=401,
                detail="Authentication failed",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        return await call_next(request)

def require_auth(request: Request):
    """Dependency to require authentication for a specific endpoint"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    token = auth_header.split(" ")[1]
    
    try:
        result = auth_service.validate_session(token)
        if not result["valid"]:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        return result["user"]
        
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"}
        )