import os
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from src.db_service import SessionLocal, User, Business
from src.utils import send_whatsapp_text
from src.google_service import GoogleService

logger = logging.getLogger(__name__)

def send_overdue_reminders():
    """Daily task to check for overdue payments and notify users"""
    db = SessionLocal()
    try:
        users = db.query(User).all()
        for user in users:
            if not user.google_refresh_token: continue
            
            # Get active business
            business = db.query(Business).filter(Business.id == user.active_business_id).first()
            if not business:
                business = db.query(Business).filter(Business.user_whatsapp_id == user.whatsapp_id).first()
            
            if not business: continue

            try:
                gs = GoogleService(user.google_refresh_token)
                summary = gs.get_business_summary(business.master_ledger_sheet_id)
                
                if summary and summary.get("overdue_payments"):
                    overdue_list = summary["overdue_payments"]
                    # Limit to 3 reminders to avoid spam
                    items = overdue_list[:3]
                    msg = "⚠️ *Overdue Payment Reminder*\n\n"
                    for item in items:
                        msg += f"• *{item['entity']}*: ₹{item['amount']} (Due: {item['due']})\n"
                    
                    if len(overdue_list) > 3:
                        msg += f"...and {len(overdue_list)-3} more."
                    
                    msg += "\nWould you like me to draft a reminder message for them? Type 'Advice' to discuss."
                    send_whatsapp_text(user.whatsapp_id, msg)
                    logger.info(f"Sent overdue reminder to {user.whatsapp_id}")
            except Exception as e:
                logger.error(f"Error processing overdue for {user.whatsapp_id}: {e}")
    finally:
        db.close()

def send_monthly_gst_reminder():
    """Iterates through all users and sends a GSTR-1 reminder on the 5th"""
    db = SessionLocal()
    try:
        users = db.query(User).all()
        for user in users:
            try:
                # Use base URL from redirect URI
                redirect_uri = os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:8000/auth/callback')
                base_url = redirect_uri.split('/auth/callback')[0]
                report_url = f"{base_url}/reports"
                
                message = (
                    f"📅 Monthly GST Reminder!\n\n"
                    f"It's the 5th of the month. Your GSTR-1 report for the previous month is ready.\n\n"
                    f"Download it here: {report_url}\n\n"
                    f"Keep your bookkeeping updated! 🚀"
                )
                send_whatsapp_text(user.whatsapp_id, message)
                logger.info(f"Sent monthly reminder to {user.whatsapp_id}")
            except Exception as e:
                logger.error(f"Failed to send reminder to {user.whatsapp_id}: {e}")
    finally:
        db.close()

def init_scheduler():
    """Starts the background scheduler for monthly tasks"""
    scheduler = BackgroundScheduler()
    
    # Run on the 5th of every month at 10:00 AM
    scheduler.add_job(
        send_monthly_gst_reminder, 
        'cron', 
        day=5, 
        hour=10, 
        minute=0
    )

    # Run daily at 10:30 AM
    scheduler.add_job(
        send_overdue_reminders,
        'cron',
        hour=10,
        minute=30
    )
    
    scheduler.start()
    logger.info("Monthly reminder scheduler initialized.")
    return scheduler
