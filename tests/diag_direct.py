import sys
import os
import logging
import requests
import time

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.db_service import SessionLocal, User, Business
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_direct_request_test(whatsapp_id):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.whatsapp_id == whatsapp_id).first()
        business = db.query(Business).filter(Business.user_whatsapp_id == whatsapp_id).first()
        
        creds = Credentials(
            token=None,
            refresh_token=user.google_refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=os.getenv("GOOGLE_CLIENT_ID"),
            client_secret=os.getenv("GOOGLE_CLIENT_SECRET")
        )
        
        logger.info("Refreshing token...")
        creds.refresh(Request())
        
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{business.master_ledger_sheet_id}"
        headers = {"Authorization": f"Bearer {creds.token}"}
        
        logger.info(f"Testing direct GET to {url} with 120s timeout...")
        start = time.time()
        try:
            # Use extremely long timeout
            response = requests.get(url, headers=headers, timeout=120)
            duration = time.time() - start
            logger.info(f"SUCCESS in {duration:.2f}s! Status: {response.status_code}")
            sheets = [s.get("properties", {}).get("title") for s in response.json().get("sheets", [])]
            logger.info(f"Sheets: {sheets}")
        except Exception as e:
            duration = time.time() - start
            logger.error(f"FAILED after {duration:.2f}s: {e}")

    finally:
        db.close()

if __name__ == "__main__":
    run_direct_request_test("919000521868")
