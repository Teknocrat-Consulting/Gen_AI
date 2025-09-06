import os
from typing import Optional, Dict, Any
from descope import DescopeClient
from descope.exceptions import AuthException
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class AuthService:
    def __init__(self):
        self.project_id = settings.DESCOPE_PROJECT_ID
        if not self.project_id:
            raise ValueError("DESCOPE_PROJECT_ID is required in settings")
        
        self.descope_client = DescopeClient(project_id=self.project_id)
    
    async def send_magic_link(self, email: str, redirect_url: Optional[str] = None) -> Dict[str, Any]:
        """Send magic link for passwordless authentication"""
        logger.info(f"[AUTH] Magic link requested for email: {email}")
        try:
            response = self.descope_client.magic_link.sign_up_or_in(
                delivery_method="email",
                login_id=email,
                uri=redirect_url
            )
            logger.info(f"[AUTH] Magic link sent successfully to: {email}")
            return {
                "success": True,
                "masked_email": response.get("maskedEmail", email),
                "message": "Magic link sent successfully"
            }
        except AuthException as e:
            logger.error(f"[AUTH] Failed to send magic link to {email}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def verify_magic_link(self, token: str) -> Dict[str, Any]:
        """Verify magic link token and return session"""
        logger.info(f"[AUTH] Verifying magic link token")
        try:
            jwt_response = self.descope_client.magic_link.verify(token)
            user_email = jwt_response.user.get('email', 'unknown') if hasattr(jwt_response.user, 'get') else 'unknown'
            logger.info(f"[AUTH] Magic link verified successfully for user: {user_email}")
            logger.info(f"[AUTH] User logged in: {user_email} - Session created")
            return {
                "success": True,
                "session_token": jwt_response.session_jwt,
                "refresh_token": jwt_response.refresh_jwt,
                "user": jwt_response.user
            }
        except AuthException as e:
            logger.error(f"[AUTH] Failed to verify magic link: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def send_otp(self, email: str, method: str = "email") -> Dict[str, Any]:
        """Send OTP for authentication"""
        logger.info(f"[AUTH] OTP requested for email: {email}")
        try:
            response = self.descope_client.otp.sign_up_or_in(
                delivery_method=method,
                login_id=email
            )
            logger.info(f"[AUTH] OTP sent successfully to: {email}")
            return {
                "success": True,
                "masked_email": response.get("maskedEmail", email),
                "message": "OTP sent successfully"
            }
        except AuthException as e:
            logger.error(f"[AUTH] Failed to send OTP to {email}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def verify_otp(self, email: str, code: str) -> Dict[str, Any]:
        """Verify OTP code and return session"""
        logger.info(f"[AUTH] Verifying OTP for email: {email}")
        try:
            jwt_response = self.descope_client.otp.verify_code(
                delivery_method="email",
                login_id=email,
                code=code
            )
            user_email = jwt_response.user.get('email', email) if hasattr(jwt_response.user, 'get') else email
            logger.info(f"[AUTH] OTP verified successfully for user: {user_email}")
            logger.info(f"[AUTH] User logged in: {user_email} - Session created")
            return {
                "success": True,
                "session_token": jwt_response.session_jwt,
                "refresh_token": jwt_response.refresh_jwt,
                "user": jwt_response.user
            }
        except AuthException as e:
            logger.error(f"[AUTH] Failed to verify OTP for {email}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def validate_session(self, session_token: str) -> Dict[str, Any]:
        """Validate session token"""
        try:
            jwt_response = self.descope_client.validate_session(session_token)
            user = jwt_response.get("user") if isinstance(jwt_response, dict) else getattr(jwt_response, "user", {})
            user_email = user.get('email', 'unknown') if isinstance(user, dict) else 'unknown'
            logger.debug(f"[AUTH] Session validated for user: {user_email}")
            return {
                "valid": True,
                "user": user
            }
        except AuthException as e:
            logger.warning(f"[AUTH] Invalid session token: {str(e)}")
            return {"valid": False, "error": str(e)}
    
    async def refresh_session(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh session token"""
        try:
            jwt_response = self.descope_client.refresh_session(refresh_token)
            return {
                "success": True,
                "session_token": jwt_response.session_jwt,
                "refresh_token": jwt_response.refresh_jwt
            }
        except AuthException as e:
            logger.error(f"Failed to refresh session: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def logout(self, refresh_token: str) -> Dict[str, Any]:
        """Logout user and invalidate refresh token"""
        logger.info(f"[AUTH] Logout requested for refresh token")
        try:
            # Try to get user info from the refresh token before logout
            try:
                jwt_response = self.descope_client.validate_session(refresh_token)
                user = jwt_response.get("user") if isinstance(jwt_response, dict) else getattr(jwt_response, "user", {})
                user_email = user.get('email', 'unknown') if isinstance(user, dict) else 'unknown'
                logger.info(f"[AUTH] User logging out: {user_email}")
            except:
                logger.info(f"[AUTH] User logging out (email unavailable)")
            
            self.descope_client.logout(refresh_token)
            logger.info(f"[AUTH] Logout successful - Session terminated")
            return {"success": True, "message": "Logged out successfully"}
        except AuthException as e:
            logger.error(f"[AUTH] Failed to logout: {str(e)}")
            return {"success": False, "error": str(e)}

# Global auth service instance
auth_service = AuthService()