import os
import logging
import uuid
import secrets
from datetime import datetime, timedelta
from fastapi import APIRouter, Request, HTTPException, Query, Depends, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from google_auth_oauthlib.flow import Flow

from src.db_service import get_db, User, Business, SessionLocal, save_user_token
from src.google_service import GoogleService
from src.utils import sign_state, verify_state, create_access_token

logger = logging.getLogger(__name__)

router = APIRouter()

# Google OAuth2 Configuration
GOOGLE_CLIENT_CONFIG = {
    "web": {
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": [os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/callback")]
    }
}
SCOPES = ["https://www.googleapis.com/auth/drive.file", "openid", "https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/documents"]

DEFAULT_BUSINESS_NAME = os.getenv("DEFAULT_BUSINESS_NAME", "Help U Traders")
DEFAULT_BUSINESS_GSTIN = os.getenv("DEFAULT_BUSINESS_GSTIN", "37ABCDE1234F1Z5")

@router.get("/auth/google")
async def google_login(whatsapp_id: str = Query(...)):
    """Initializes Google OAuth2 flow with signed whatsapp_id in state"""
    if not GOOGLE_CLIENT_CONFIG["web"]["client_id"]:
        return {"error": "Google Client ID not configured"}
    
    flow = Flow.from_client_config(
        GOOGLE_CLIENT_CONFIG,
        scopes=SCOPES,
        redirect_uri=GOOGLE_CLIENT_CONFIG["web"]["redirect_uris"][0]
    )
    # Use JWT to sign the state to prevent spoofing
    signed_state = sign_state(whatsapp_id)
    auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline', state=signed_state)
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

        flow = Flow.from_client_config(
            GOOGLE_CLIENT_CONFIG,
            scopes=SCOPES,
            redirect_uri=GOOGLE_CLIENT_CONFIG["web"]["redirect_uris"][0]
        )
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        # Get actual user info (Email/Name)
        session = flow.authorized_session()
        user_info = session.get('https://www.googleapis.com/oauth2/v1/userinfo').json()
        email = user_info.get("email", "user@example.com")
        
        # Save user to DB (handles merging if email already exists)
        user = save_user_token(whatsapp_id, email, credentials.refresh_token)
        whatsapp_id = user.whatsapp_id # Use the ID from DB (might have been merged)
        
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
                gs = GoogleService(credentials.refresh_token)
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
        redirect_url = f"/onboarding-success?whatsapp_id={whatsapp_id}&token={token}"
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
        return RedirectResponse(url=f"/auth-error?message={error_msg}")

@router.post("/api/auth/logout")
async def logout():
    """Clears user session/tokens"""
    # In a real app with cookies/JWT, we would clear them here
    return {"status": "success", "message": "Logged out successfully"}
