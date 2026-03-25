import os
import sys
import uuid
import asyncio
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

# Force MOCK before any imports
import src.utils
def safe_print(msg):
    # Strip emojis for Windows console compatibility
    print(msg.encode('ascii', 'ignore').decode('ascii'))

src.utils.send_whatsapp_text = lambda *args, **kwargs: safe_print(f"  [MOCK TEXT] -> {args[1] if len(args)>1 else args}")
src.utils.send_whatsapp_interactive = lambda *args, **kwargs: safe_print(f"  [MOCK INTERACTIVE] -> {args[1] if len(args)>1 else args}")
src.utils.handle_google_error = lambda *args, **kwargs: False # Don't handle as error

# Mock GoogleService
import src.google_service
class MockGoogleService:
    def __init__(self, *args, **kwargs): pass
    def initialize_user_drive(self): return "folder_id", "sheet_id", "template_id"
    def append_to_master_ledger(self, *args, **kwargs): pass
    def get_last_ledger_row(self, *args, **kwargs): return [], 100
    def update_ledger_row(self, *args, **kwargs): pass
    def upload_bill_image(self, *args, **kwargs): pass
    def generate_sales_invoice(self, *args, **kwargs): pass
    def get_business_summary(self, *args, **kwargs): return {"total_sales": 5000}

src.google_service.GoogleService = MockGoogleService

# Mock AIProcessor
import src.ai_processor
class MockAIProcessor:
    def __init__(self, *args, **kwargs): pass
    def process_sales_text(self, text):
        if "560" in text: amount = 560.0
        elif "1500" in text: amount = 1500.0
        elif "5000" in text: amount = 5000.0
        else: amount = 100.0
        
        return {
            "is_transaction": True,
            "transaction_type": "Sale" if "Sale" in text or "Sold" in text else "Expense",
            "total_amount": amount,
            "items": [{"total_amount": amount, "taxable_value": amount, "gst_rate": 18}],
            "vendor_name": "Mock Vendor",
            "customer_name": "Mock Customer",
            "date": datetime.now().strftime("%d-%m-%Y")
        }
    def process_purchase_image(self, *args, **kwargs):
        return self.process_sales_text("Image with 1000")

src.ai_processor.AIProcessor = MockAIProcessor

from src.db_service import Base, User, Business, Transaction
from src.bot.orchestrator import WhatsAppOrchestrator

class SimulationBase:
    def __init__(self, db_name="test_sim.db"):
        self.engine = create_engine(f"sqlite:///{db_name}")
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.user_id = "sim_user_999"
        self.orchestrator = WhatsAppOrchestrator(self.db)

    def setup_user(self):
        user = User(whatsapp_id=self.user_id, google_refresh_token="mock_token", drive_initialized=True)
        self.db.add(user)
        self.db.commit()
        
        business = Business(
            id=str(uuid.uuid4()),
            user_whatsapp_id=self.user_id, 
            business_name="Simulation Store", 
            master_ledger_sheet_id="mock_ledger_id",
            business_gstin="37ABCDE1234F1Z5"
        )
        self.db.add(business)
        self.db.commit()
        
        user.active_business_id = business.id
        self.db.commit()
        return user, business

    async def send_text(self, text):
        safe_print(f"\nUSER SENDS: {text}")
        payload = {
            "entry": [{"changes": [{"value": {
                "messages": [{"id": f"MSG_{uuid.uuid4().hex[:6]}", "from": self.user_id, "type": "text", "text": {"body": text}}]
            }}]}]
        }
        await self.orchestrator.handle_payload(payload)

    async def click_button(self, title):
        safe_print(f"\nUSER CLICKS: {title}")
        payload = {
            "entry": [{"changes": [{"value": {
                "messages": [{"id": f"BTN_{uuid.uuid4().hex[:6]}", "from": self.user_id, "type": "interactive", "interactive": {
                    "type": "button_reply", "button_reply": {"title": title}
                }}]
            }}]}]
        }
        await self.orchestrator.handle_payload(payload)

    def get_latest_tx(self):
        return self.db.query(Transaction).filter(
            Transaction.user_whatsapp_id == self.user_id
        ).order_by(Transaction.created_at.desc()).first()

    def print_state(self):
        tx = self.get_latest_tx()
        if tx:
            print(f"STATE: Type={tx.transaction_type}, Status={tx.status}")
        else:
            print("STATE: No active transaction")
