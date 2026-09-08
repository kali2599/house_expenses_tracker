#!/bin/bash

# backup_db.sh — Export house_expenses_tracker databases in lossless text format.
#
# Usage:
#   ./backup_db.sh                       # backup ALL users, structure + data (default)
#   ./backup_db.sh all                   # backup ALL users, structure + data
#   ./backup_db.sh <username>            # backup only <username>
#
# Mode flags (pick one):
#   --data         only the tables data (INSERT statements, run against an existing schema)
#   --schema       only the database structure (CREATE TABLE / TRIGGER / ..., no data)
#   --both         structure + data (default)
#
# Other options:
#   --out <dir>        Write backups to <dir> (overrides BACKUP_DIR env var)
#
# Output dir resolution (first match wins):
#   1. --out <dir>
#   2. $BACKUP_DIR
#   3. ./backups (relative to the project root)
#
# The central users.db is included in the backup only when running for all users.

set -u

# ─── Resolve project root (works when called from anywhere) ───
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

DATA_DIR="data"
USER_DB_DIR="$DATA_DIR/user_data"
USERS_DB="$DATA_DIR/users.db"

# ─── Check sqlite3 availability ───
if ! command -v sqlite3 >/dev/null 2>&1; then
    echo "[!] Errore: sqlite3 non trovato nel PATH."
    exit 1
fi

# ─── Parse arguments ───
TARGET_USER=""
OUTPUT_DIR=""
MODE="both"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --out)
            shift
            if [[ $# -lt 1 ]]; then
                echo "[!] Errore: --out richiede un percorso."
                exit 1
            fi
            OUTPUT_DIR="$1"
            ;;
        --data)
            MODE="data"
            ;;
        --schema)
            MODE="schema"
            ;;
        --both)
            MODE="both"
            ;;
        *)
            TARGET_USER="$1"
            ;;
    esac
    shift
done

# ─── Output dir resolution ───
if [[ -z "$OUTPUT_DIR" ]]; then
    OUTPUT_DIR="${BACKUP_DIR:-./backups}"
fi
mkdir -p "$OUTPUT_DIR" || { echo "[!] Errore: impossibile creare $OUTPUT_DIR"; exit 1; }

TIMESTAMP="$(date +%Y-%m-%d_%H%M%S)"

# ─── Helpers ───
user_db_file() {
    echo "$USER_DB_DIR/$1.db"
}

mode_suffix() {
    case "$MODE" in
        data)   echo ".data" ;;
        schema) echo ".schema" ;;
        *)      echo "" ;;
    esac
}

dump_by_mode() {
    local db_file="$1"
    case "$MODE" in
        data)
            sqlite3 "$db_file" .dump | grep '^INSERT INTO'
            ;;
        schema)
            # Skip the internal sqlite_sequence table, which cannot be re-created via SQL.
            sqlite3 "$db_file" .schema | grep -v '^CREATE TABLE sqlite_sequence'
            ;;
        *)
            sqlite3 "$db_file" .dump
            ;;
    esac
}

build_user_list() {
    local list=()
    if [[ -n "$TARGET_USER" && "$TARGET_USER" != "all" ]]; then
        list=("$TARGET_USER")
    else
        if [[ ! -f "$USERS_DB" ]]; then
            echo "[!] Errore: $USERS_DB non trovato."
            exit 1
        fi
        mapfile -t list < <(sqlite3 "$USERS_DB" "SELECT username FROM users ORDER BY username;")
    fi
    printf '%s\n' "${list[@]}"
}

backup_user() {
    local user="$1"
    local db_file db_out rows_part rows_reg

    db_file="$(user_db_file "$user")"
    db_out="$OUTPUT_DIR/${user}_${TIMESTAMP}$(mode_suffix).sql"

    if [[ ! -f "$db_file" ]]; then
        echo "[!] Utente '$user': database non trovato ($db_file) — salto."
        return 2
    fi

    if ! dump_by_mode "$db_file" > "$db_out"; then
        echo "[!] Errore durante il backup di '$user'."
        return 1
    fi

    rows_part="$(sqlite3 "$db_file" "SELECT COUNT(*) FROM spese_mensili;" 2>/dev/null)"
    rows_part="${rows_part:-0}"
    rows_reg="$(sqlite3 "$db_file" "SELECT COUNT(*) FROM registro_spese;" 2>/dev/null)"
    rows_reg="${rows_reg:-0}"

    echo "[+] Backup '$user' [$MODE]: $db_out (spese_mensili: $rows_part, registro_spese: $rows_reg)"
    return 0
}

# ─── Backup all target users ───
echo "[+] Directory di backup: $OUTPUT_DIR"
echo "---------------------------------------------------------"

overall=0
mapfile -t USERS < <(build_user_list)

if [[ ${#USERS[@]} -eq 0 ]]; then
    echo "[!] Nessun utente da elaborare."
    exit 0
fi

some_failure=0
for u in "${USERS[@]}"; do
    backup_user "$u"
    [[ $? -ne 0 ]] && some_failure=1
done

# ─── Central users.db (only when backing up all users) ───
if [[ -z "$TARGET_USER" || "$TARGET_USER" == "all" ]]; then
    if [[ -f "$USERS_DB" ]]; then
        users_out="$OUTPUT_DIR/users_${TIMESTAMP}$(mode_suffix).sql"
        if ! dump_by_mode "$USERS_DB" > "$users_out"; then
            echo "[!] Errore durante il backup di users.db"
            some_failure=1
        else
            echo "[+] Backup centrale [$MODE]: $users_out"
        fi
    else
        echo "[!] users.db non trovato ($USERS_DB)."
        some_failure=1
    fi
fi

echo "---------------------------------------------------------"
if [[ $some_failure -eq 1 ]]; then
    echo "[!] Backup completato con alcuni avvisi/errori."
else
    echo "[OK] Backup completato con successo."
fi

exit $some_failure
