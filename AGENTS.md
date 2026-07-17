# House Expenses Tracker — Agent Guide

## TL;DR
```bash
pip install -r requirements.txt   # install flask
python3 main.py                   # run web server — sign up via browser
```

Open browser at `http://localhost:5000` (port set in `settings.py`).

## Architecture

| File | Role |
|---|---|
| `main.py` | Flask app — routes, request handling, auth, server startup |
| `sqlManager.py` | SQLite data access layer (per-user database) |
| `utils.py` | Helpers: `parse_date_bound`, `get_color_for_attribute` (no terminal output) |
| `settings.py` | Constants: `PORT`, `MONTHS_INDEX`, attribute lists, `USER_DB_DIR`, `USERS_DB` |
| `templates/` | Jinja2 HTML templates (one per feature) |
| `static/style.css` | Minimal CSS |

## Key facts

- **Language**: Italian — month names (`GENNAIO`, `FEBBRAIO`, …), all UI strings. Keep it consistent.
- **DB**: SQLite only. Flask is the only external dependency.
- **Auth**: Multi-user via `users.db` (central) + per-user SQLite DB in `user_data/`. Signup creates a fresh DB from `init.sql`. Login sets `session['db_path']`.
- **Legacy DB path**: Stored in `database_path` file (gitignored). Used only by `init_user_db.py` to migrate existing data to user `davide`.
- **Port**: Set via `settings.py:PORT` (default `5000`).
- **Secret key**: Persisted in `flask_secret.key` so sessions survive server restarts.
- **Computed columns**: `uscite_variabili`, `uscite_fisse`, `uscite_totali`, `delta` are maintained by SQLite triggers (see `init.sql`). Do not touch them from Python.
- **Year**: Stored in Flask session (`session['year']`). Defaults to current year on first visit. Change via `/change-year`.

## Gotchas

- `populate.sql` is **out of sync** with `init.sql` — it has a `cometa` column instead of `abbonamenti, investimenti`. If you regenerate the DB, update `populate.sql` to match the current schema or skip it and insert rows manually.
- `push_db.sh` and `test.sh` are local-only scripts, gitignored, not part of the project workflow.
- No tests, no CI, no linter, no formatter.

## Conventions

- All SQL queries use **parameterized `?` placeholders** — never interpolate values directly. Dynamic column names are validated against `SQL_ATTRIBUTES_ALL` in `settings.py`.
- Month format in DB: `YYYY_MESE` (e.g. `2026_GENNAIO`).
- Routes are named after the feature. Each page handles both display (GET) and action (POST) — results render on the same page.
- New features: add route `@app.route('/feature-name', methods=['GET', 'POST'])` in `main.py`, create template in `templates/`.
