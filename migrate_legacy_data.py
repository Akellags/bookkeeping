import sqlite3
import uuid
import os

db_path = "help_u_bookkeeper.db"
if not os.path.exists(db_path):
    print(f"Database {db_path} does not exist.")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Fetch users with data in users table
    cursor.execute("""
        SELECT whatsapp_id, business_name, business_gstin, drive_folder_id, master_ledger_sheet_id 
        FROM users 
        WHERE drive_folder_id IS NOT NULL 
        OR master_ledger_sheet_id IS NOT NULL
    """)
    rows = cursor.fetchall()
    print(f"Found {len(rows)} users with legacy data.")
    
    for row in rows:
        whatsapp_id, b_name, b_gstin, d_folder, m_sheet = row
        print(f"Migrating user: {whatsapp_id}")
        
        # Check if they already have a business record
        cursor.execute("SELECT id FROM businesses WHERE user_whatsapp_id = ?", (whatsapp_id,))
        if cursor.fetchone():
            print(f"User {whatsapp_id} already has a business record. Skipping.")
            continue
            
        # 2. Create a business record
        business_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO businesses (id, user_whatsapp_id, business_name, business_gstin, drive_folder_id, master_ledger_sheet_id, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (business_id, whatsapp_id, b_name or "Help U Traders", b_gstin or "37ABCDE1234F1Z5", d_folder, m_sheet, 1))
        
        # 3. Update the user with the active_business_id
        cursor.execute("UPDATE users SET active_business_id = ? WHERE whatsapp_id = ?", (business_id, whatsapp_id))
        
    conn.commit()
    conn.close()
    print("Migration complete.")
