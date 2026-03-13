import sqlite3
import os

db_path = "help_u_bookkeeper.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT whatsapp_id, business_name, business_gstin, drive_folder_id, master_ledger_sheet_id FROM users WHERE whatsapp_id = '919703333319'")
    row = cursor.fetchone()
    print(f"Data for user 919703333319: {row}")
    conn.close()
