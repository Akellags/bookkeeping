import os
import sys
import uuid
import asyncio
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

# Only mock the FINAL WhatsApp sending call (to avoid Meta costs/templates)
# BUT keep the REAL AI and REAL Google Service
import src.utils
def safe_print(msg):
    # Strip emojis for Windows console compatibility
    print(msg.encode('ascii', 'ignore').decode('ascii'))

src.utils.send_whatsapp_text = lambda *args, **kwargs: safe_print(f"  [WHATSAPP TEXT] -> {args[1] if len(args)>1 else args}")
src.utils.send_whatsapp_interactive = lambda *args, **kwargs: safe_print(f"  [WHATSAPP INTERACTIVE] -> {args[1] if len(args)>1 else args}")

from src.db_service import Base, User, Business, Transaction
from src.bot.orchestrator import WhatsAppOrchestrator
from src.google_service import GoogleService

class IntegrationBase:
    def __init__(self, db_name="integration_test.db"):
        # We need the REAL DB to get a valid token
        real_engine = create_engine("sqlite:///./help_u_bookkeeper.db")
        RealSession = sessionmaker(bind=real_engine)
        real_db = RealSession()
        
        # Get the first user who has a token
        real_user = real_db.query(User).filter(User.google_refresh_token != None).first()
        if not real_user:
            raise ValueError("No user with a Google Refresh Token found in the real database. Please link an account first.")
        
        real_biz = real_db.query(Business).filter(Business.user_whatsapp_id == real_user.whatsapp_id).first()
        if not real_biz:
            raise ValueError(f"No business found for user {real_user.whatsapp_id}")

        self.refresh_token = real_user.google_refresh_token
        self.sheet_id = real_biz.master_ledger_sheet_id
        real_db.close()

        self.engine = create_engine(f"sqlite:///{db_name}")
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        
        self.user_id = "integration_test_user"
        self.orchestrator = WhatsAppOrchestrator(self.db)
        
        safe_print(f"  [INTEGRATION] Using Token for: {real_user.google_email}")
        safe_print(f"  [INTEGRATION] Using Sheet ID: {self.sheet_id}")

    def setup_real_user(self):
        user = User(
            whatsapp_id=self.user_id, 
            google_refresh_token=self.refresh_token, 
            drive_initialized=True
        )
        self.db.add(user)
        self.db.commit()
        
        business = Business(
            id=str(uuid.uuid4()),
            user_whatsapp_id=self.user_id, 
            business_name="INTEGRATION TEST STORE", 
            master_ledger_sheet_id=self.sheet_id,
            business_gstin="37ABCDE1234F1Z5"
        )
        self.db.add(business)
        self.db.commit()
        
        user.active_business_id = business.id
        self.db.commit()
        return user, business

    async def send_text(self, text):
        safe_print(f"\n[USER SENDS TEXT]: {text}")
        payload = {
            "entry": [{"changes": [{"value": {
                "messages": [{"id": f"MSG_{uuid.uuid4().hex[:6]}", "from": self.user_id, "type": "text", "text": {"body": text}}]
            }}]}]
        }
        await self.orchestrator.handle_payload(payload)

    async def click_button(self, title):
        safe_print(f"\n[USER CLICKS BUTTON]: {title}")
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

    def check_sheet_for_row(self, sheet_name, amount):
        """Verify if a row with the given amount exists in the real Google Sheet"""
        safe_print(f"\n[VERIFYING GOOGLE SHEET] -> Checking {sheet_name} for amount {amount}...")
        gs = GoogleService(self.refresh_token)
        
        # Use the underlying executor for better timeout handling
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{self.sheet_id}/values/{sheet_name}!A:Z"
        data = gs._execute_with_requests("GET", url)
        
        rows = data.get('values', [])
        # Search in the last 10 rows to be efficient
        search_target = str(int(amount)) if float(amount) == int(amount) else str(amount)
        for row in reversed(rows[-10:]):
            if search_target in [str(c) for c in row]:
                safe_print(f"  SUCCESS: Found record in {sheet_name}!")
                return True
        safe_print(f"  FAILURE: Record with amount {amount} not found in {sheet_name}!")
        return False
