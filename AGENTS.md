# House Expenses Tracker — Agent Guide

## TL;DR
```bash
pip install -r requirements.txt   # install flask
sqlite3 data.db < init.sql        # create schema
python3 main.py                   # run web server
```

Open browser at `http://localhost:443` (port set in `settings.py`).

## Architecture

| File | Role |
|---|---|
| `main.py` | Flask app — routes, request handling, server startup |
| `sqlManager.py` | SQLite data access layer (unchanged) |
| `utils.py` | Helpers: `parse_date_bound`, `get_color_for_attribute` (no terminal output) |
| `settings.py` | Constants: `PORT`, `MONTHS_INDEX`, attribute lists |
| `templates/` | Jinja2 HTML templates (one per feature) |
| `static/style.css` | Minimal CSS |

## Key facts

- **Language**: Italian — month names (`GENNAIO`, `FEBBRAIO`, …), all UI strings. Keep it consistent.
- **DB**: SQLite only. Flask is the only external dependency.
- **DB path**: Stored in `database_path` file (gitignored). App reads it at startup.
- **Port**: Set via `settings.py:PORT` (default `443`). Change to `5000` for dev without sudo.
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
