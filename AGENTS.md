# House Expenses Tracker — Agent Guide

## TL;DR
```bash
sqlite3 data.db < init.sql    # create schema
sqlite3 data.db < populate.sql  # seed with zero rows
python main.py                # run CLI
```

## Key facts

- **Language**: Italian — month names (`GENNAIO`, `FEBBRAIO`, …), all UI strings, column comments. Keep it consistent.
- **DB**: SQLite only. No external deps. `requirements.txt` is intentionally empty.
- **DB path**: Stored in `database_path` file (gitignored). App reads it at startup. Create it if missing.
- **Computed columns**: `uscite_variabili`, `uscite_fisse`, `uscite_totali`, `delta` are maintained by SQLite triggers (see `init.sql`). Do not touch them from Python.
- **Editable attributes** (defined in `settings.py:SQL_ATTRIBUTES_EDITABLE`): `entrate, spesa, pasti_fuori, svago, shopping, inaspettate, varie, salute, vacanze, abbonamenti, investimenti, assicurazioni, condominio, luce, gas, mutuo, lenti, telefonia, parrucchiere, palestra`.

## Gotchas

- `populate.sql` is **out of sync** with `init.sql` — it has a `cometa` column instead of `abbonamenti, investimenti`. If you regenerate the DB, update `populate.sql` to match the current schema or skip it and insert rows manually.
- `push_db.sh` and `test.sh` are local-only scripts, gitignored, not part of the project workflow.
- No tests, no CI, no linter, no formatter.

## Conventions

- All SQL queries use **f-strings with direct interpolation** (`f"SELECT ... WHERE mese = '{month}'"`) — be careful with quoting when editing.
- Entries in the expense registry (`registro_spese`) are NOT linked to a specific month; the undo feature always undoes the **global last** expense, not the last one for the selected month (known bug documented in `main.py:23`).
- Month format in DB: `YYYY_MESE` (e.g. `2026_GENNAIO`).
