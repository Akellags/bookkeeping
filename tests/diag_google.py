import sys
import os
import logging

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.db_service import SessionLocal, User, Business
from src.google_service import GoogleService
from googleapiclient.errors import HttpError

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_diagnostic(whatsapp_id):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.whatsapp_id == whatsapp_id).first()
        if not user:
            logger.error(f"User with WhatsApp ID {whatsapp_id} not found in database.")
            return

        business = db.query(Business).filter(Business.user_whatsapp_id == whatsapp_id).first()
        if not business:
            logger.error(f"No business found for user {whatsapp_id}")
            return

        logger.info(f"--- Diagnostic for User: {user.google_email} ---")
        logger.info(f"Master Ledger ID: {business.master_ledger_sheet_id}")
        
        gs = GoogleService(user.google_refresh_token)
        
        # 1. Test Connection & List Sheets
        logger.info("Step 1: Fetching spreadsheet metadata (listing tabs) via requests...")
        try:
            url = f"https://sheets.googleapis.com/v4/spreadsheets/{business.master_ledger_sheet_id}"
            spreadsheet = gs._execute_with_requests("GET", url)
            if not spreadsheet:
                logger.error("FAILED Step 1: Received no data from Google")
                return
            sheets = [s.get("properties", {}).get("title") for s in spreadsheet.get("sheets", [])]
            logger.info(f"SUCCESS: Found sheets: {sheets}")
            
            if "Expenses" not in sheets:
                logger.warning("WARNING: 'Expenses' tab not found in the list!")
            else:
                logger.info("SUCCESS: 'Expenses' tab exists.")
        except Exception as e:
            logger.error(f"FAILED Step 1: Could not fetch spreadsheet metadata: {e}")
            return

        # 2. Test Reading Headers from Expenses
        logger.info("Step 2: Reading headers from 'Expenses' tab via requests...")
        try:
            resolved_name = gs._resolve_sheet_name(business.master_ledger_sheet_id, "Expenses")
            val_url = f"https://sheets.googleapis.com/v4/spreadsheets/{business.master_ledger_sheet_id}/values/'{resolved_name}'!A1:U1"
            val_result = gs._execute_with_requests("GET", val_url)
            headers = val_result.get("values", [[]])[0] if val_result else []
            logger.info(f"SUCCESS: Headers found: {headers}")
        except Exception as e:
            logger.error(f"FAILED Step 2: Could not read from 'Expenses' tab: {e}")

        # 3. Test Appending a Diagnostic Row
        logger.info("Step 3: Appending diagnostic row to 'Expenses'...")
        diag_row = ["DIAGNOSTIC", "Test User", "DIAG-001", "23-03-2026", "0.01", "37", "N", "B2C", "Expense", "0000", "Diagnostic Test", "OTH", "1", "0", "0.01", "0", "0", "0", "0", "Completed", "N/A"]
        try:
            gs.append_to_master_ledger(business.master_ledger_sheet_id, diag_row, sheet_name="Expenses")
            logger.info("SUCCESS: Diagnostic row appended to 'Expenses'.")
        except Exception as e:
            logger.error(f"FAILED Step 3: Could not append to 'Expenses': {e}")

    finally:
        db.close()

if __name__ == "__main__":
    target_id = "919000521868" # From error.md logs
    run_diagnostic(target_id)
