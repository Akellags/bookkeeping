import sys
import os
import logging

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.db_service import SessionLocal, User, Business
from src.google_service import GoogleService

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_internal_requests(whatsapp_id):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.whatsapp_id == whatsapp_id).first()
        business = db.query(Business).filter(Business.user_whatsapp_id == whatsapp_id).first()
        
        gs = GoogleService(user.google_refresh_token)
        
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{business.master_ledger_sheet_id}"
        logger.info(f"Testing GoogleService._execute_with_requests directly for {url}")
        
        result = gs._execute_with_requests("GET", url)
        if result:
            logger.info("SUCCESS: Method works inside GoogleService!")
            logger.info(f"Sheets: {[s.get('properties', {}).get('title') for s in result.get('sheets', [])]}")
        else:
            logger.error("FAILED: Method returned None")
            
    except Exception as e:
        logger.error(f"CRITICAL FAILED: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_internal_requests("919000521868")
