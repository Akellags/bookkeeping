import os
import sys
import uuid
import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add src to path
sys.path.append(os.getcwd())

# Force MOCK before any imports
import src.utils
src.utils.send_whatsapp_text = lambda *args, **kwargs: None
src.utils.send_whatsapp_interactive = lambda *args, **kwargs: None

from src.db_service import Base, User, Business, Transaction
from src.bot.orchestrator import WhatsAppOrchestrator

def setup_test_db():
    engine = create_engine("sqlite:///test_bookkeeper.db")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()

async def diag_flow():
    db = setup_test_db()
    
    # 1. Setup Mock User
    user_id = "test_user_123"
    user = User(whatsapp_id=user_id, google_refresh_token="mock_token", drive_initialized=True)
    db.add(user)
    db.commit()
    
    business = Business(
        id=str(uuid.uuid4()),
        user_whatsapp_id=user_id, 
        business_name="Test Shop", 
        master_ledger_sheet_id="mock_sheet"
    )
    db.add(business)
    db.commit()
    
    user.active_business_id = business.id
    db.commit()

    orchestrator = WhatsAppOrchestrator(db)

    print("\n--- 1. User sends 'Sale 560' ---")
    payload_text = {
        "entry": [{"changes": [{"value": {
            "messages": [{"id": "MSG_1", "from": user_id, "type": "text", "text": {"body": "Sale 560"}}]
        }}]}]
    }
    await orchestrator.handle_payload(payload_text)
    
    tx = db.query(Transaction).filter(Transaction.user_whatsapp_id == user_id).order_by(Transaction.created_at.desc()).first()
    print(f"Result: TX Type={tx.transaction_type}, Status={tx.status}")

    print("\n--- 2. User clicks 'Money In' button ---")
    payload_btn = {
        "entry": [{"changes": [{"value": {
            "messages": [{"id": "MSG_2", "from": user_id, "type": "interactive", "interactive": {
                "type": "button_reply", "button_reply": {"title": "💰 Money In"}
            }}]
        }}]}]
    }
    await orchestrator.handle_payload(payload_btn)
    
    tx = db.query(Transaction).get(tx.id)
    print(f"Result: TX Status after 'Money In' click={tx.status}")

    print("\n--- 3. User sends 'Paid 5000 for office rent' ---")
    payload_expense = {
        "entry": [{"changes": [{"value": {
            "messages": [{"id": "MSG_3", "from": user_id, "type": "text", "text": {"body": "Paid 5000 for office rent"}}]
        }}]}]
    }
    await orchestrator.handle_payload(payload_expense)
    
    new_tx = db.query(Transaction).filter(Transaction.user_whatsapp_id == user_id).order_by(Transaction.created_at.desc()).first()
    print(f"Result: New TX Type={new_tx.transaction_type}, Status={new_tx.status}")
    
    print("\n--- 4. Checking if old TX was cancelled ---")
    old_tx = db.query(Transaction).get(tx.id)
    print(f"Result: Old TX Status={old_tx.status}")

    print("\n--- 5. User sends 'Hi' (Menu) then clicks 'Money In' ---")
    payload_hi = {
        "entry": [{"changes": [{"value": {
            "messages": [{"id": "MSG_HI", "from": user_id, "type": "text", "text": {"body": "Hi"}}]
        }}]}]
    }
    await orchestrator.handle_payload(payload_hi)
    
    payload_money_in = {
        "entry": [{"changes": [{"value": {
            "messages": [{"id": "MSG_BT", "from": user_id, "type": "interactive", "interactive": {
                "type": "button_reply", "button_reply": {"title": "💰 Money In"}
            }}]
        }}]}]
    }
    await orchestrator.handle_payload(payload_money_in)
    
    # This should find a NEW transaction created by the button click
    newest_tx = db.query(Transaction).filter(Transaction.user_whatsapp_id == user_id).order_by(Transaction.created_at.desc()).first()
    print(f"Result: Newest TX Type={newest_tx.transaction_type}, Status={newest_tx.status}")

    print("\n--- 6. User clicks 'Sale' button (from Money In submenu) ---")
    payload_sale = {
        "entry": [{"changes": [{"value": {
            "messages": [{"id": "MSG_SALE", "from": user_id, "type": "interactive", "interactive": {
                "type": "button_reply", "button_reply": {"title": "Sale"}
            }}]
        }}]}]
    }
    await orchestrator.handle_payload(payload_sale)
    tx = db.query(Transaction).get(newest_tx.id)
    print(f"Result: TX Type={tx.transaction_type}, Status={tx.status}")

    print("\n--- 7. User sends text details 'Sold 560 to ABC Corp' ---")
    payload_details = {
        "entry": [{"changes": [{"value": {
            "messages": [{"id": "MSG_DET", "from": user_id, "type": "text", "text": {"body": "Sold 560 to ABC Corp"}}]
        }}]}]
    }
    await orchestrator.handle_payload(payload_details)
    tx = db.query(Transaction).get(tx.id)
    print(f"Result: TX Type={tx.transaction_type}, Status={tx.status}, Extracted={tx.extracted_json.get('total_amount')}")

if __name__ == "__main__":
    asyncio.run(diag_flow())
