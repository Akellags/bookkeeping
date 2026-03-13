import os
import logging
from sqlalchemy import create_engine, Column, String, Text, DateTime, JSON, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Use SQLite for local development, fallback to PostgreSQL in production
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./help_u_bookkeeper.db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    whatsapp_id = Column(String, primary_key=True, index=True)
    google_email = Column(String, unique=True, index=True)
    google_refresh_token = Column(Text)
    active_business_id = Column(String, nullable=True) # ID of current selected business
    subscription_status = Column(String, default="FREE_TRIAL")
    created_at = Column(DateTime, default=datetime.utcnow)
    
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

# Create tables
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def save_user_token(whatsapp_id: str, email: str, refresh_token: str):
    db = SessionLocal()
    # 1. Check if user exists by whatsapp_id
    user = db.query(User).filter(User.whatsapp_id == whatsapp_id).first()
    
    # 2. Check if another user exists with the same email
    existing_user_by_email = db.query(User).filter(User.google_email == email).first()
    
    if existing_user_by_email and existing_user_by_email.whatsapp_id != whatsapp_id:
        # If email exists with different ID, we link it to the existing record
        # This prevents the UNIQUE constraint error and merges the account
        existing_user_by_email.google_refresh_token = refresh_token
        # If the incoming ID is a "real" whatsapp ID (doesn't start with web_), 
        # and existing is a "web_" ID, we might want to migrate.
        # For now, let's just return the existing user's ID to keep consistency.
        db.commit()
        actual_user = existing_user_by_email
    elif user:
        user.google_refresh_token = refresh_token
        user.google_email = email
        db.commit()
        actual_user = user
    else:
        user = User(whatsapp_id=whatsapp_id, google_email=email, google_refresh_token=refresh_token)
        db.add(user)
        db.commit()
        actual_user = user
        
    # Refresh to get updated state
    db.refresh(actual_user)
    db.close()
    return actual_user

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
