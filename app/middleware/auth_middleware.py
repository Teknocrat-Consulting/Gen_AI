from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger(__name__)

class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce authentication on protected routes"""
    
    # Routes that don't require authentication
    PUBLIC_ROUTES = [
        "/auth",
        "/api/auth",
        "/health",
        "/api/health",
        "/docs",
        "/openapi.json",
        "/static",
        "/favicon.ico",
        "/redoc"
    ]
    
    # HTML pages that require authentication
    PROTECTED_PAGES = [
        "/",
        "/premium-booking"
    ]
    
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        
        # Check if route is public
        is_public = any(path.startswith(route) for route in self.PUBLIC_ROUTES)
        
        if not is_public:
            # Check for authentication
            auth_header = request.headers.get("Authorization")
            session_cookie = request.cookies.get("session_token")
            
            # For API routes (excluding auth endpoints), check Authorization header
            if path.startswith("/api/") and not path.startswith("/api/auth"):
                if not auth_header and not session_cookie:
                    raise HTTPException(
                        status_code=401,
                        detail="Authentication required",
                        headers={"WWW-Authenticate": "Bearer"}
                    )
            
            # For HTML pages, check session cookie and redirect if not authenticated
            elif any(path == page or (path.startswith(page) and page != "/") for page in self.PROTECTED_PAGES):
                if not session_cookie:
                    # Redirect to auth page with return URL
                    return RedirectResponse(url=f"/auth?redirect={path}", status_code=302)
        
        response = await call_next(request)
        return response