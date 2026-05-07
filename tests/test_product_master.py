import sys
import os
import logging
import asyncio
import json

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.db_service import SessionLocal, User, Business
from src.google_service import GoogleService

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_product_master_flow(whatsapp_id):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.whatsapp_id == whatsapp_id).first()
        business = db.query(Business).filter(Business.user_whatsapp_id == whatsapp_id).first()
        
        if not user or not business:
            logger.error(f"User or Business not found for {whatsapp_id}")
            return
            
        gs = GoogleService(user.google_refresh_token)
        sheet_id = business.master_ledger_sheet_id
        
        logger.info(f"--- 1. Testing Header Repair/Initialization ---")
        # This will trigger the header repair logic we added
        await gs.initialize_user_drive(business.business_name)
        
        logger.info(f"--- 2. Testing Bulk Update ---")
        test_products = [
            {
                "shortcode": "KBD",
                "description": "Logitech Keyboard",
                "hsn_code": "8471",
                "gst_rate": 18,
                "uqc": "NOS",
                "unit_price": 1200
            },
            {
                "shortcode": "MSE",
                "description": "Logitech Mouse",
                "hsn_code": "8471",
                "gst_rate": 12,
                "uqc": "PCS",
                "unit_price": 600
            }
        ]
        
        logger.info("Uploading 2 products to Product Master...")
        await gs.bulk_update_product_master(sheet_id, test_products)
        
        logger.info(f"--- 3. Testing Get Product Master ---")
        master = await gs.get_product_master(sheet_id)
        logger.info(f"Retrieved Master: {json.dumps(master, indent=2)}")
        
        assert "KBD" in master
        assert "MSE" in master
        assert master["KBD"]["description"] == "Logitech Keyboard"
        assert master["MSE"]["gst_rate"] == 12.0
        assert master["KBD"]["last_updated"] != ""
        
        logger.info("\n[SUCCESS] Product Master Phase 2 tests passed!")
            
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
    finally:
        db.close()

if __name__ == "__main__":
    # Using the same test ID as before
    asyncio.run(test_product_master_flow("919000521868"))
