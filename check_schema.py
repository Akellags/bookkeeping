import sqlite3
import os

db_path = "help_u_bookkeeper.db"
if not os.path.exists(db_path):
    print(f"Database {db_path} does not exist.")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check businesses table
    cursor.execute("PRAGMA table_info(businesses)")
    cols = cursor.fetchall()
    print("Columns in 'businesses':")
    for col in cols:
        print(col[1], col[2])
    
    # Check if there's any data in businesses
    cursor.execute("SELECT COUNT(*) FROM businesses")
    count = cursor.fetchone()[0]
    print(f"\nTotal businesses found: {count}")
    
    # Check users columns again
    cursor.execute("PRAGMA table_info(users)")
    u_cols = cursor.fetchall()
    print("\nColumns in 'users':")
    for col in u_cols:
        print(col[1], col[2])

    conn.close()
