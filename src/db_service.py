import os
import logging
from sqlalchemy import create_engine, Column, String, Text, DateTime, JSON, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from dotenv import load_dotenv
from google.cloud.sql.connector import Connector, IPTypes

load_dotenv()

logger = logging.getLogger(__name__)

# Cloud SQL Python Connector configuration
INSTANCE_CONNECTION_NAME = os.getenv("INSTANCE_CONNECTION_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME")

def get_engine():
    # Use Connector if connection details are provided
    if INSTANCE_CONNECTION_NAME and DB_USER and DB_PASS:
        logger.info(f"Connecting to Cloud SQL via Python Connector: {INSTANCE_CONNECTION_NAME}")
        
        # This will use GOOGLE_APPLICATION_CREDENTIALS env var if set, 
        # or fall back to ADC (gcloud auth application-default login)
        connector = Connector()
        
        def getconn():
            conn = connector.connect(
                INSTANCE_CONNECTION_NAME,
                "pg8000",
                user=DB_USER,
                password=DB_PASS,
                db=DB_NAME,
                ip_type=IPTypes.PUBLIC  # Use PUBLIC for local dev without private networking
            )
            return conn

        return create_engine(
            "postgresql+pg8000://",
            creator=getconn,
        )
    else:
        # Fallback to local SQLite or standard DATABASE_URL
        db_url = os.getenv("DATABASE_URL", "sqlite:///./help_u_bookkeeper.db")
        logger.info(f"Connecting to database via URL: {db_url}")
        return create_engine(db_url)

engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    whatsapp_id = Column(String, primary_key=True, index=True)
    google_email = Column(String, unique=True, index=True)
    google_refresh_token = Column(Text)
    active_business_id = Column(String, nullable=True) # ID of current selected business
    drive_initialized = Column(Boolean, default=False) # True if Google Drive structure is correct
    subscription_status = Column(String, default="FREE_TRIAL")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # State tracking for WhatsApp commands (e.g., AWAITING_EDIT)
    last_interaction_type = Column(String, nullable=True)
    last_interaction_data = Column(JSON, nullable=True)

    # Verification Handover for web-onboarded users
    link_token = Column(String, unique=True, index=True, nullable=True)
    link_token_expires_at = Column(DateTime, nullable=True)
    
    businesses = relationship("Business", back_populates="user")

class Business(Base):
    __tablename__ = "businesses"
    id = Column(String, primary_key=True, index=True)
    user_whatsapp_id = Column(String, ForeignKey("users.whatsapp_id"))
    business_name = Column(String, default="Help U Traders")
    business_gstin = Column(String, default="37ABCDE1234F1Z5")
    drive_folder_id = Column(String)
    master_ledger_sheet_id = Column(String)
    invoice_template_id = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="businesses")

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(String, primary_key=True, index=True)
    user_whatsapp_id = Column(String, ForeignKey("users.whatsapp_id"))
    business_id = Column(String, ForeignKey("businesses.id"), nullable=True)
    transaction_type = Column(String)
    media_url = Column(Text)
    extracted_json = Column(JSON)
    status = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class ProcessedMessage(Base):
    __tablename__ = "processed_messages"
    message_id = Column(String, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

# Tables should be created via Alembic migrations in production.
# For local SQLite development, you can still call Base.metadata.create_all(bind=engine) 
# but it's better to use migrations for everything now.
# Base.metadata.create_all(bind=engine) 

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def save_user_token(whatsapp_id: str, email: str, refresh_token: str):
    db = SessionLocal()
    try:
        # 1. Check if user exists by whatsapp_id
        user = db.query(User).filter(User.whatsapp_id == whatsapp_id).first()
        
        # 2. Check if another user exists with the same email
        existing_user_by_email = db.query(User).filter(User.google_email == email).first()
        
        if existing_user_by_email and existing_user_by_email.whatsapp_id != whatsapp_id:
            # Case: Found account by email, but ID is different (e.g. was 'web_...')
            # If the new ID is a 'real' ID (not web_) and existing is 'web_', we migrate
            old_id = existing_user_by_email.whatsapp_id
            if not whatsapp_id.startswith("web_") and old_id.startswith("web_"):
                logger.info(f"Migrating web user {old_id} to real WhatsApp ID {whatsapp_id} for email {email}")
                
                # 1. If we have a shell user with the target whatsapp_id, delete it first
                if user:
                    db.delete(user)
                    db.commit()
                
                # Capture data before deletion
                captured_active_business_id = existing_user_by_email.active_business_id
                captured_subscription_status = existing_user_by_email.subscription_status
                
                # Delete old web user first to clear the email constraint
                db.delete(existing_user_by_email)
                db.commit() # Commit the deletion
                
                # Create new user record
                new_user = User(
                    whatsapp_id=whatsapp_id,
                    google_email=email,
                    google_refresh_token=refresh_token,
                    active_business_id=captured_active_business_id,
                    subscription_status=captured_subscription_status
                )
                db.add(new_user)
                
                # Move businesses and transactions to the new ID
                db.query(Business).filter(Business.user_whatsapp_id == old_id).update({"user_whatsapp_id": whatsapp_id})
                db.query(Transaction).filter(Transaction.user_whatsapp_id == old_id).update({"user_whatsapp_id": whatsapp_id})
                
                db.commit()
                db.refresh(new_user)
                return new_user
            else:
                # Just update the token
                existing_user_by_email.google_refresh_token = refresh_token
                db.commit()
                db.refresh(existing_user_by_email)
                return existing_user_by_email
                
        elif user:
            user.google_refresh_token = refresh_token
            user.google_email = email
            db.commit()
            db.refresh(user)
            return user
        else:
            user = User(whatsapp_id=whatsapp_id, google_email=email, google_refresh_token=refresh_token)
            db.add(user)
            db.commit()
            db.refresh(user)
            return user
    finally:
        db.close()

def get_user(whatsapp_id: str):
    db = SessionLocal()
    user = db.query(User).filter(User.whatsapp_id == whatsapp_id).first()
    db.close()
    return user

def get_active_business(whatsapp_id: str):
    db = SessionLocal()
    user = db.query(User).filter(User.whatsapp_id == whatsapp_id).first()
    if not user:
        db.close()
        return None
    
    if user.active_business_id:
        business = db.query(Business).filter(Business.id == user.active_business_id).first()
    else:
        # Fallback to first business if no active one set
        business = db.query(Business).filter(Business.user_whatsapp_id == whatsapp_id).first()
        
    db.close()
    return business
