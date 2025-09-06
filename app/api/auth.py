from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional
import logging

from app.services.auth_service import auth_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()

class MagicLinkRequest(BaseModel):
    email: EmailStr
    redirect_url: Optional[str] = None

class VerifyMagicLinkRequest(BaseModel):
    token: str

class OTPRequest(BaseModel):
    email: EmailStr

class VerifyOTPRequest(BaseModel):
    email: EmailStr
    code: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

@router.post("/magic-link/send")
async def send_magic_link(request: MagicLinkRequest):
    """Send magic link for passwordless authentication"""
    logger.info(f"[AUTH API] Magic link request received for email: {request.email}")
    try:
        result = await auth_service.send_magic_link(
            email=request.email,
            redirect_url=request.redirect_url
        )
        if result["success"]:
            logger.info(f"[AUTH API] Magic link sent successfully to: {request.email}")
            return {"message": result["message"], "masked_email": result.get("masked_email")}
        else:
            logger.warning(f"[AUTH API] Failed to send magic link to {request.email}: {result['error']}")
            raise HTTPException(status_code=400, detail=result["error"])
    except Exception as e:
        logger.error(f"[AUTH API] Error sending magic link to {request.email}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to send magic link")

@router.post("/magic-link/verify")
async def verify_magic_link(request: VerifyMagicLinkRequest):
    """Verify magic link token and return session"""
    logger.info(f"[AUTH API] Magic link verification attempt")
    try:
        result = await auth_service.verify_magic_link(request.token)
        if result["success"]:
            user_email = result["user"].get("email", "unknown") if isinstance(result["user"], dict) else "unknown"
            logger.info(f"[AUTH API] Magic link verified successfully - User logged in: {user_email}")
            return {
                "session_token": result["session_token"],
                "refresh_token": result["refresh_token"],
                "user": result["user"]
            }
        else:
            logger.warning(f"[AUTH API] Magic link verification failed: {result['error']}")
            raise HTTPException(status_code=400, detail=result["error"])
    except Exception as e:
        logger.error(f"[AUTH API] Error verifying magic link: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to verify magic link")

@router.post("/otp/send")
async def send_otp(request: OTPRequest):
    """Send OTP for authentication"""
    try:
        result = await auth_service.send_otp(request.email)
        if result["success"]:
            return {"message": result["message"], "masked_email": result.get("masked_email")}
        else:
            raise HTTPException(status_code=400, detail=result["error"])
    except Exception as e:
        logger.error(f"Error sending OTP: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to send OTP")

@router.post("/otp/verify")
async def verify_otp(request: VerifyOTPRequest):
    """Verify OTP code and return session"""
    try:
        result = await auth_service.verify_otp(request.email, request.code)
        if result["success"]:
            return {
                "session_token": result["session_token"],
                "refresh_token": result["refresh_token"],
                "user": result["user"]
            }
        else:
            raise HTTPException(status_code=400, detail=result["error"])
    except Exception as e:
        logger.error(f"Error verifying OTP: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to verify OTP")

@router.post("/refresh")
async def refresh_token(request: RefreshTokenRequest):
    """Refresh session token"""
    try:
        result = await auth_service.refresh_session(request.refresh_token)
        if result["success"]:
            return {
                "session_token": result["session_token"],
                "refresh_token": result["refresh_token"]
            }
        else:
            raise HTTPException(status_code=400, detail=result["error"])
    except Exception as e:
        logger.error(f"Error refreshing token: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to refresh token")

@router.post("/logout")
async def logout(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Logout user and invalidate refresh token"""
    logger.info(f"[AUTH API] Logout request received")
    try:
        # Use the bearer token as refresh token for logout
        result = await auth_service.logout(credentials.credentials)
        if result["success"]:
            logger.info(f"[AUTH API] User logged out successfully")
            return {"message": result["message"]}
        else:
            logger.warning(f"[AUTH API] Logout failed: {result['error']}")
            raise HTTPException(status_code=400, detail=result["error"])
    except Exception as e:
        logger.error(f"[AUTH API] Error during logout: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to logout")

@router.get("/validate")
async def validate_session(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Validate current session token"""
    try:
        result = auth_service.validate_session(credentials.credentials)
        if result["valid"]:
            user_email = result["user"].get("email", "unknown") if isinstance(result["user"], dict) else "unknown"
            logger.debug(f"[AUTH API] Session validated for user: {user_email}")
            return {"user": result["user"], "valid": True}
        else:
            logger.warning(f"[AUTH API] Invalid session token provided")
            raise HTTPException(status_code=401, detail="Invalid session token")
    except Exception as e:
        logger.error(f"[AUTH API] Error validating session: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to validate session")

@router.post("/validate-session")
async def validate_session_post(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Validate session token from Descope Web Component"""
    try:
        result = auth_service.validate_session(credentials.credentials)
        if result["valid"]:
            return {"user": result["user"], "valid": True}
        else:
            raise HTTPException(status_code=401, detail="Invalid session token")
    except Exception as e:
        logger.error(f"Error validating session: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to validate session")

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Dependency to get current authenticated user"""
    try:
        result = auth_service.validate_session(credentials.credentials)
        if result["valid"]:
            return result["user"]
        else:
            raise HTTPException(status_code=401, detail="Invalid session token")
    except Exception as e:
        logger.error(f"Error getting current user: {str(e)}")
        raise HTTPException(status_code=401, detail="Authentication required")