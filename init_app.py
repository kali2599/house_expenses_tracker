"""
House Expenses Tracker — Initialization script.

Creates required directories, database infrastructure, and secret key.
Safe to run multiple times (idempotent).

Usage:
    python3 init_app.py          # standalone initialization
    python3 main.py              # auto-initializes at startup via init_app()
"""

import os, sqlite3
from config.settings import USER_DB_DIR, USERS_DB, DATA_DIR


def init_app():
    """Initialize all required directories and database tables."""
    os.makedirs(USER_DB_DIR, exist_ok=True)
    os.makedirs(os.path.join(DATA_DIR, 'uploads', 'profiles'), exist_ok=True)

    db = sqlite3.connect(USERS_DB)

    db.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        db_path TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'basic',
        blocked INTEGER NOT NULL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    for col in ["role TEXT NOT NULL DEFAULT 'basic'", "blocked INTEGER NOT NULL DEFAULT 0",
                 "first_name TEXT DEFAULT ''", "last_name TEXT DEFAULT ''",
                 "date_of_birth TEXT DEFAULT ''", "bio TEXT DEFAULT ''",
                 "profile_photo TEXT DEFAULT ''", "security_question TEXT DEFAULT ''",
                 "security_answer_hash TEXT DEFAULT ''",
                 "custom_variabili TEXT DEFAULT ''", "custom_fisse TEXT DEFAULT ''",
                 "custom_default_fisse TEXT DEFAULT ''", "custom_attribute_history TEXT DEFAULT ''"]:
        try:
            db.execute(f"ALTER TABLE users ADD COLUMN {col}")
        except sqlite3.OperationalError:
            pass

    db.executescript("""
        CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT DEFAULT '',
            created_by INTEGER NOT NULL REFERENCES users(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS group_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER NOT NULL REFERENCES groups(id),
            user_id INTEGER NOT NULL REFERENCES users(id),
            invited_by INTEGER NOT NULL REFERENCES users(id),
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(group_id, user_id)
        );
    """)
    try:
        db.execute("ALTER TABLE groups ADD COLUMN description TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    try:
        db.execute("ALTER TABLE groups ADD COLUMN blocked INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    db.execute("UPDATE users SET role = 'basic' WHERE role IS NULL")
    db.commit()
    db.close()

    key_file = 'flask_secret.key'
    if not os.path.exists(key_file):
        with open(key_file, 'wb') as f:
            f.write(os.urandom(24))


if __name__ == '__main__':
    init_app()
    print(f"✓ {USER_DB_DIR}/ created")
    print(f"✓ {USERS_DB} initialized")
    print(f"✓ flask_secret.key ready")
    print("\nReady! Run: python3 main.py")
