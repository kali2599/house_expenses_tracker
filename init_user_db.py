"""
Prepare the environment for first use.
Creates required directories and database infrastructure.
Users can then sign up via the web interface.

Safe to run multiple times (idempotent).
"""

import os, sqlite3
from settings import USER_DB_DIR, USERS_DB


def main():
    os.makedirs(USER_DB_DIR, exist_ok=True)
    print(f"✓ Created {USER_DB_DIR}/")

    db = sqlite3.connect(USERS_DB)
    db.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        db_path TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    db.commit()
    db.close()
    print(f"✓ Created {USERS_DB}")

    print("\nReady! Start the app and sign up via the web interface:")
    print("  python3 main.py")


if __name__ == "__main__":
    main()
