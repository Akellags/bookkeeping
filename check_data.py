import sqlite3
import os

db_path = "help_u_bookkeeper.db"
if not os.path.exists(db_path):
    print(f"Database {db_path} does not exist.")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("Listing all users:")
    cursor.execute("SELECT whatsapp_id, google_email, active_business_id, created_at FROM users")
    users = cursor.fetchall()
    for user in users:
        print(user)
    
    print("\nListing all businesses:")
    cursor.execute("SELECT id, user_whatsapp_id, business_name FROM businesses")
    businesses = cursor.fetchall()
    for b in businesses:
        print(b)
        
    conn.close()
