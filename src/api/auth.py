import os
import logging
import uuid
import secrets
from datetime import datetime, timedelta
import urllib.parse
from fastapi import APIRouter, Request, HTTPException, Query, Depends, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from src.db_service import get_db, User, Business, SessionLocal, save_user_token
from src.google_service import GoogleService
from src.utils import sign_state, verify_state, create_access_token

logger = logging.getLogger(__name__)

router = APIRouter()

# Google OAuth2 Configuration - Read directly from environment
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/callback")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")

SCOPES = ["https://www.googleapis.com/auth/drive.file", "openid", "https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/documents"]

DEFAULT_BUSINESS_NAME = os.getenv("DEFAULT_BUSINESS_NAME", "Help U Traders")
DEFAULT_BUSINESS_GSTIN = os.getenv("DEFAULT_BUSINESS_GSTIN", "37ABCDE1234F1Z5")

@router.get("/auth/google")
async def google_login(whatsapp_id: str = Query(...)):
    """Initializes Google OAuth2 flow with manual URL construction to bypass PKCE issues"""
    if not GOOGLE_CLIENT_ID:
        return {"error": "Google Client ID not configured"}
    
    # Use JWT to sign the state to prevent spoofing
    signed_state = sign_state(whatsapp_id)
    
    # Manually construct authorization URL to avoid any PKCE/library-specific issues
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "state": signed_state,
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true"
    }
    
    auth_url = f"https://accounts.google.com/o/oauth2/auth?{urllib.parse.urlencode(params)}"
    logger.info(f"Redirecting user to Google Auth for: {whatsapp_id}")
    return RedirectResponse(auth_url)

@router.get("/auth/callback")
async def google_callback(code: str, state: str = None):
    """Handles Google OAuth2 callback and links to WhatsApp ID"""
    try:
        if not state:
             return RedirectResponse(url="/auth-error?message=Missing identification state")
        
        # Verify the signed state
        whatsapp_id = verify_state(state)
        if not whatsapp_id:
             return RedirectResponse(url="/auth-error?message=Invalid or expired session. Please try again.")

        # For non-WhatsApp signups, generate a unique ID
        if whatsapp_id == "new_user":
             whatsapp_id = f"web_{uuid.uuid4().hex[:12]}"

        # Standard OAuth2 token exchange using requests
        import requests
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code"
        }
        
        logger.info(f"Exchanging code for tokens for user: {whatsapp_id}")
        response = requests.post(token_url, data=data)
        token_data = response.json()
        
        if "error" in token_data:
            logger.error(f"Token exchange error: {token_data}")
            return RedirectResponse(url=f"/auth-error?message={token_data.get('error_description', 'Token exchange failed')}")
            
        # Get refresh token and ID token
        refresh_token = token_data.get("refresh_token")
        id_token = token_data.get("id_token")
        
        # Get user info using the access token
        access_token = token_data.get("access_token")
        user_info_res = requests.get(
            "https://www.googleapis.com/oauth2/v1/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        user_info = user_info_res.json()
        email = user_info.get("email", "user@example.com")
        
        # Save user to DB
        user = save_user_token(whatsapp_id, email, refresh_token)
        whatsapp_id = user.whatsapp_id
        
        # Use context manager for DB session to prevent leaks
        link_token = None
        with SessionLocal() as db:
            db_user = db.query(User).filter(User.whatsapp_id == whatsapp_id).first()
            existing_business = db.query(Business).filter(Business.user_whatsapp_id == whatsapp_id).first()
            
            # Generate link token if it's a web user
            if whatsapp_id.startswith("web_") and db_user:
                link_token = secrets.token_hex(3).upper()
                db_user.link_token = link_token
                db_user.link_token_expires_at = datetime.utcnow() + timedelta(minutes=30)
                db.commit()

            if not existing_business:
                # Initialize Google Drive Folder/Sheet/Template
                gs = GoogleService(refresh_token)
                folder_id, sheet_id, template_id = await gs.initialize_user_drive()
                
                # Update user with first business
                business_id = str(uuid.uuid4())
                new_business = Business(
                    id=business_id,
                    user_whatsapp_id=whatsapp_id,
                    business_name=DEFAULT_BUSINESS_NAME,
                    business_gstin=DEFAULT_BUSINESS_GSTIN,
                    drive_folder_id=folder_id,
                    master_ledger_sheet_id=sheet_id,
                    invoice_template_id=template_id
                )
                db.add(new_business)
                if db_user:
                    db_user.active_business_id = business_id
                    db_user.drive_initialized = True
                db.commit()

        logger.info(f"Successfully linked Google account for {whatsapp_id}")
        
        # Issue a session JWT
        token = create_access_token(whatsapp_id)
        
        # Redirect to React Success Page with the token
        redirect_url = f"{FRONTEND_URL}/onboarding-success?whatsapp_id={whatsapp_id}&token={token}"
        if link_token:
            redirect_url += f"&link_token={link_token}"
            
        return RedirectResponse(url=redirect_url)
    except Exception as e:
        logger.error(f"OAuth callback error: {e}", exc_info=True)
        # Return a friendly error redirect instead of JSON
        error_msg = str(e)
        if "active_business_id" in error_msg:
             error_msg = "Database schema mismatch. Please contact support."
        elif "Google Docs API" in error_msg:
             error_msg = "Google Docs API is disabled in your project. Please enable it in Google Cloud Console and try again."
        elif "invalid_grant" in error_msg:
             error_msg = "Google authentication expired. Please try again."
        return RedirectResponse(url=f"{FRONTEND_URL}/auth-error?message={error_msg}")

@router.post("/api/auth/logout")
async def logout():
    """Clears user session/tokens"""
    # In a real app with cookies/JWT, we would clear them here
    return {"status": "success", "message": "Logged out successfully"}
