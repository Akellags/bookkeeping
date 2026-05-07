import os
import sys
import logging
from sqlalchemy import create_engine, Column, String, Text, DateTime, JSON, ForeignKey, Boolean
from sqlalchemy.orm import Session, declarative_base
from sqlalchemy import select
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), 'src')))

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 1. Define SQL Models (Source)
SQL_Base = declarative_base()

class SQLUser(SQL_Base):
    __tablename__ = "users"
    whatsapp_id = Column(String, primary_key=True)
    google_email = Column(String)
    google_refresh_token = Column(Text)
    active_business_id = Column(String)
    drive_initialized = Column(Boolean)
    subscription_status = Column(String)
    created_at = Column(DateTime)
    last_interaction_type = Column(String)
    last_interaction_data = Column(JSON)
    link_token = Column(String)
    link_token_expires_at = Column(DateTime)

class SQLBusiness(SQL_Base):
    __tablename__ = "businesses"
    id = Column(String, primary_key=True)
    user_whatsapp_id = Column(String)
    business_name = Column(String)
    business_gstin = Column(String)
    drive_folder_id = Column(String)
    master_ledger_sheet_id = Column(String)
    invoice_template_id = Column(String)
    is_active = Column(Boolean)
    created_at = Column(DateTime)

class SQLTransaction(SQL_Base):
    __tablename__ = "transactions"
    id = Column(String, primary_key=True)
    user_whatsapp_id = Column(String)
    business_id = Column(String)
    transaction_type = Column(String)
    media_url = Column(Text)
    extracted_json = Column(JSON)
    status = Column(String)
    extraction_provider = Column(String)
    provider_model = Column(String)
    confidence_score = Column(JSON)
    field_confidence = Column(JSON)
    needs_review = Column(Boolean)
    review_reason = Column(String)
    created_at = Column(DateTime)

class SQLProcessedMessage(SQL_Base):
    __tablename__ = "processed_messages"
    message_id = Column(String, primary_key=True)
    created_at = Column(DateTime)

# 2. Import Firestore Models (Target)
# Set DB_BACKEND to FIREBASE before importing
os.environ["DB_BACKEND"] = "FIREBASE"
from firestore_service import User, Business, Transaction, ProcessedMessage, FirestoreSession

def main():
    # Setup SQL Source
    instance_name = os.getenv("INSTANCE_CONNECTION_NAME")
    if instance_name:
        logger.info(f"Connecting to Cloud SQL: {instance_name}")
        from google.cloud.sql.connector import Connector, IPTypes
        from google.oauth2 import service_account
        
        # Explicitly use google_creds.json for Cloud SQL to avoid 403 from firebase_key
        sql_creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_SQL", "google_creds.json")
        creds = service_account.Credentials.from_service_account_file(sql_creds_path)
        connector = Connector(credentials=creds)
        
        def getconn():
            return connector.connect(
                instance_name,
                "pg8000",
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASS"),
                db=os.getenv("DB_NAME"),
                ip_type=IPTypes.PUBLIC
            )
        sql_engine = create_engine("postgresql+pg8000://", creator=getconn)
    else:
        db_url = os.getenv("DATABASE_URL", "sqlite:///./help_u_bookkeeper.db")
        logger.info(f"Connecting to Local SQL: {db_url}")
        sql_engine = create_engine(db_url)

    firestore_session = FirestoreSession()

    with Session(sql_engine) as sql_session:
        # Migrate Users
        logger.info("Migrating Users...")
        sql_users = sql_session.query(SQLUser).all()
        for u in sql_users:
            data = {c.name: getattr(u, c.name) for c in u.__table__.columns}
            # Remove keys with None values if preferred, but Firestore handles them
            firestore_session.add(User(**data))
        logger.info(f"Queued {len(sql_users)} users")

        # Migrate Businesses
        logger.info("Migrating Businesses...")
        sql_businesses = sql_session.query(SQLBusiness).all()
        for b in sql_businesses:
            data = {c.name: getattr(b, c.name) for c in b.__table__.columns}
            firestore_session.add(Business(**data))
        logger.info(f"Queued {len(sql_businesses)} businesses")

        # Migrate Transactions
        logger.info("Migrating Transactions...")
        sql_transactions = sql_session.query(SQLTransaction).all()
        for t in sql_transactions:
            data = {c.name: getattr(t, c.name) for c in t.__table__.columns}
            firestore_session.add(Transaction(**data))
        logger.info(f"Queued {len(sql_transactions)} transactions")

        # Migrate ProcessedMessages
        logger.info("Migrating ProcessedMessages...")
        sql_messages = sql_session.query(SQLProcessedMessage).all()
        for m in sql_messages:
            data = {c.name: getattr(m, c.name) for c in m.__table__.columns}
            firestore_session.add(ProcessedMessage(**data))
        logger.info(f"Queued {len(sql_messages)} processed messages")

        logger.info("Committing to Firestore (this may take a moment)...")
        firestore_session.commit()
        logger.info("Migration successful!")

if __name__ == "__main__":
    main()
