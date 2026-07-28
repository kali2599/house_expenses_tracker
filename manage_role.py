#!/usr/bin/env python3
"""
Gestione ruoli utente da riga di comando.

Usage:
    python3 manage_role.py list                         # lista utenti e ruoli
    python3 manage_role.py set-role <username> <role>   # cambia ruolo
    python3 manage_role.py help                         # mostra help
"""

import sys, sqlite3, os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "users.db")
VALID_ROLES = ("basic", "admin", "super_admin")


def get_db():
    return sqlite3.connect(DB_PATH)


def cmd_list():
    db = get_db()
    users = db.execute(
        "SELECT id, username, role, blocked FROM users ORDER BY id"
    ).fetchall()
    db.close()

    if not users:
        print("Nessun utente trovato.")
        return

    print(f"  {'ID':<4} {'Username':<16} {'Role':<14} {'Blocked'}")
    print(f"{'----':<4} {'-'*16:<16} {'-'*14:<14} {'-'*7}")
    for uid, username, role, blocked in users:
        print(f"  {uid:<4} {username:<16} {role:<14} {'Yes' if blocked else 'No'}")


def cmd_set_role(username, new_role):
    if new_role not in VALID_ROLES:
        print(f"Ruolo non valido: '{new_role}'. Ruoli disponibili: {', '.join(VALID_ROLES)}")
        sys.exit(1)

    db = get_db()
    user = db.execute(
        "SELECT id, username, role FROM users WHERE username = ?", (username,)
    ).fetchone()

    if not user:
        db.close()
        print(f"Utente '{username}' non trovato.")
        sys.exit(1)

    uid, uname, old_role = user

    if old_role == new_role:
        db.close()
        print(f"Utente '{uname}' ha gia' il ruolo '{new_role}'. Nessuna modifica.")
        return

    print(f"Utente: {uname}")
    print(f"Ruolo attuale: {old_role} -> nuovo ruolo: {new_role}")

    db.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, uid))

    # Gestione gruppi: sblocca se promosso a admin/super_admin, blocca se declassato a basic
    if new_role in ("admin", "super_admin") and old_role == "basic":
        result = db.execute(
            "UPDATE groups SET blocked = 0 WHERE created_by = ?", (uid,)
        )
        groups_affected = result.rowcount
        if groups_affected:
            print(f"Gruppi creati sbloccati: {groups_affected}")

    elif new_role == "basic" and old_role in ("admin", "super_admin"):
        result = db.execute(
            "UPDATE groups SET blocked = 1 WHERE created_by = ?", (uid,)
        )
        groups_affected = result.rowcount
        if groups_affected:
            print(f"Gruppi creati bloccati: {groups_affected}")

    db.commit()
    db.close()
    print("Done.")


def cmd_help():
    print(__doc__.strip())


def main():
    if len(sys.argv) < 2:
        cmd_help()
        sys.exit(0)

    command = sys.argv[1]

    if command == "list":
        cmd_list()
    elif command == "set-role":
        if len(sys.argv) != 4:
            print("Usage: python3 manage_role.py set-role <username> <role>")
            print(f"Ruoli disponibili: {', '.join(VALID_ROLES)}")
            sys.exit(1)
        cmd_set_role(sys.argv[2], sys.argv[3])
    elif command == "help":
        cmd_help()
    else:
        print(f"Comando sconosciuto: '{command}'")
        cmd_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
