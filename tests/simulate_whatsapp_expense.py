import sys
import os
import asyncio
import logging
import uuid
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.db_service import SessionLocal, User, Business, Transaction
from src.bot.handlers.interactive import _finalize_transaction

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def simulate_expense_flow(whatsapp_id):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.whatsapp_id == whatsapp_id).first()
        business = db.query(Business).filter(Business.user_whatsapp_id == whatsapp_id).first()
        
        if not user or not business:
            logger.error("User or Business not found.")
            return

        # 1. Create a dummy transaction
        tx_id = str(uuid.uuid4())
        tx = Transaction(
            id=tx_id,
            user_whatsapp_id=whatsapp_id,
            business_id=business.id,
            transaction_type="Expense",
            status="PENDING_CONFIRM",
            extracted_json={
                "vendor_name": "Office Rent",
                "total_amount": 5000,
                "date": "23-03-2026",
                "items": None
            }
        )
        db.add(tx)
        db.commit()

        logger.info(f"--- Simulating Finalize for Transaction: {tx_id} ---")
        
        # 2. Mock GoogleService to see how it's called
        with patch('src.bot.handlers.interactive.GoogleService') as MockGS:
            mock_gs_inst = MockGS.return_value
            mock_gs_inst.get_last_ledger_row.return_value = ([], 10) # Mock last row index
            
            # 3. Call _finalize_transaction
            # We want to see if it reaches the GoogleService.append_to_master_ledger call
            result = await _finalize_transaction(db, user, business, tx, tx.extracted_json)
            
            logger.info(f"Finalization Result: {result}")
            
            # Verify mocks
            if mock_gs_inst.append_to_master_ledger.called:
                args, kwargs = mock_gs_inst.append_to_master_ledger.call_args
                logger.info(f"SUCCESS: append_to_master_ledger called with row: {args[1]}")
                logger.info(f"Target Sheet: {kwargs.get('sheet_name')}")
            else:
                logger.error("FAILED: append_to_master_ledger was NOT called.")

    finally:
        # Cleanup
        db.query(Transaction).filter(Transaction.id == tx_id).delete()
        db.commit()
        db.close()

if __name__ == "__main__":
    target_id = "919000521868"
    asyncio.run(simulate_expense_flow(target_id))
