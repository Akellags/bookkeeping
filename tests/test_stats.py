import sys
import os
import logging

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.db_service import SessionLocal, User, Business
from src.google_service import GoogleService

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_stats_fix(whatsapp_id):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.whatsapp_id == whatsapp_id).first()
        business = db.query(Business).filter(Business.user_whatsapp_id == whatsapp_id).first()
        
        if not user or not business:
            logger.error("User or Business not found.")
            return

        gs = GoogleService(user.google_refresh_token)
        
        logger.info(f"Fetching stats for spreadsheet {business.master_ledger_sheet_id}")
        stats = gs.get_ledger_stats(business.master_ledger_sheet_id)
        
        logger.info(f"Stats keys: {list(stats.keys())}")
        if "count" in stats:
            logger.info(f"SUCCESS: 'count' found in stats: {stats['count']}")
        else:
            logger.error("FAILED: 'count' NOT found in stats")
            
        # Verify frontend return structure simulation
        result = {
            "bills": stats["count"],
            "sales": stats["total_sales"],
            "purchases": stats["total_purchases"]
        }
        logger.info(f"Simulated FE response: {result}")
        
    except Exception as e:
        logger.error(f"CRITICAL FAILED: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_stats_fix("919000521868")
