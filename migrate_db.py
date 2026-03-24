import sqlite3
import os

db_path = "help_u_bookkeeper.db"
if os.path.exists(db_path):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("ALTER TABLE users ADD COLUMN drive_initialized BOOLEAN DEFAULT 0")
        conn.commit()
        conn.close()
        print("Successfully added drive_initialized column to users table.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("Column drive_initialized already exists.")
        else:
            print(f"Error: {e}")
else:
    print(f"Database {db_path} not found.")
