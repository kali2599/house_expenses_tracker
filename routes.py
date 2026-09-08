from flask import render_template, request, session, redirect, url_for, flash, send_from_directory
from datetime import datetime
import os, functools, sqlite3, secrets, string, uuid, json
from werkzeug.security import generate_password_hash, check_password_hash

from config.settings import *
from db.sql_manager import SQLManager, generate_user_db_sql
from utils import parse_date_bound, get_color_for_attribute


# ─── Users DB ───

def get_users_db():
    return sqlite3.connect(USERS_DB)


# ─── Auth decorators ───

def login_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return render_template('login.html', current_year=session.get('year'))
        return f(*args, **kwargs)
    return decorated

def role_required(*roles):
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            if 'user_id' not in session:
                return render_template('login.html', current_year=session.get('year'))
            if session.get('role') not in roles:
                flash("Accesso negato.", "error")
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return wrapper
    return decorator


# ─── Permission helpers ───

def can_view_user(target_username):
    role = session.get('role')
    user_id = session.get('user_id')
    own_username = session.get('username')
    if target_username == own_username:
        return True
    if role == 'super_admin':
        return True
    if role == 'admin':
        db = get_users_db()
        target = db.execute("SELECT id FROM users WHERE username = ?", (target_username,)).fetchone()
        if not target:
            db.close()
            return False
        target_id = target[0]
        count = db.execute("""
            SELECT COUNT(*) FROM group_members gm
            JOIN groups g ON g.id = gm.group_id
            WHERE gm.user_id = ? AND g.created_by = ? AND gm.status = 'accepted'
        """, (target_id, user_id)).fetchone()[0]
        db.close()
        return count > 0
    return False


def get_visible_users():
    role = session.get('role')
    user_id = session.get('user_id')
    own_username = session.get('username')
    db = get_users_db()
    if role == 'super_admin':
        users = [r[0] for r in db.execute("SELECT username FROM users ORDER BY username").fetchall()]
    elif role == 'admin':
        users = db.execute("""
            SELECT DISTINCT u.username FROM users u
            LEFT JOIN group_members gm ON gm.user_id = u.id AND gm.status = 'accepted'
            LEFT JOIN groups g ON g.id = gm.group_id AND g.created_by = ?
            WHERE u.id = ? OR (g.id IS NOT NULL)
            ORDER BY u.username
        """, (user_id, user_id)).fetchall()
        users = [r[0] for r in users]
    else:
        users = [own_username]
    db.close()
    return users


def get_db_for_user(target_username):
    if not can_view_user(target_username):
        flash("Accesso negato a questo utente.", "error")
        return None
    db = get_users_db()
    target = db.execute("SELECT db_path FROM users WHERE username = ?", (target_username,)).fetchone()
    db.close()
    if not target:
        flash("Utente non trovato.", "error")
        return None
    if not os.path.isfile(target[0]):
        flash("Database utente non trovato.", "error")
        return None
    return SQLManager(target[0])


def get_user_list():
    db = get_users_db()
    users = db.execute(
        "SELECT id, username, role, blocked, created_at FROM users ORDER BY created_at"
    ).fetchall()
    db.close()
    return users


def get_default_fisse_for_user(username):
    """Return the dict of fixed-expense defaults for a given username."""
    db = get_users_db()
    row = db.execute("SELECT custom_default_fisse FROM users WHERE username = ?", (username,)).fetchone()
    db.close()
    if not row or not row[0]:
        return None
    try:
        return json.loads(row[0])
    except ValueError:
        return None


def get_default_note_for_user(username):
    """Return the dict of per-attribute default notes for a given username."""
    db = get_users_db()
    row = db.execute("SELECT custom_default_fisse_notes FROM users WHERE username = ?", (username,)).fetchone()
    db.close()
    if not row or not row[0]:
        return {}
    try:
        return json.loads(row[0])
    except ValueError:
        return {}


def get_user_attr_meta(username):
    """Return (custom_variabili, custom_fisse, custom_attribute_history) for a user."""
    db = get_users_db()
    row = db.execute(
        "SELECT custom_variabili, custom_fisse, custom_attribute_history FROM users WHERE username = ?",
        (username,)
    ).fetchone()
    db.close()
    if not row:
        return '', '', ''
    return row[0], row[1], row[2]


# ─── Attribute-history helpers ───

MONTH_NUMBER = {name: num for num, name in MONTHS_INDEX.items()}
ATTR_SYSTEM_COLUMNS = ('mese', 'entrate', 'uscite_variabili', 'uscite_fisse',
                       'uscite_totali', 'delta')

def month_tuple(key):
    """Convert a 'YYYY_MESE' month key into a sortable (year, month_number) tuple."""
    if not key or '_' not in key:
        return (0, 0)
    year, month_name = key.split('_', 1)
    return (int(year), MONTH_NUMBER.get(month_name.upper(), 0))


def current_month_key():
    """Return the real current month key, e.g. '2026_SETTEMBRE'."""
    now = datetime.now()
    return f"{now.year}_{MONTHS_INDEX[now.month]}"


def normalize_attribute_history(raw_history, raw_variabili, raw_fisse, all_cols):
    """Return {attr: {'type': ..., 'periods': [[start,end], ...]}}.

    Each period is [start_month, end_month] (inclusive start / exclusive end),
    where null means "from the beginning" / "still active".
    Backfills entries for every physical user column so legacy accounts get
    an 'always active' history without any data migration.
    """
    history = {}
    if raw_history:
        try:
            parsed = json.loads(raw_history)
            if isinstance(parsed, dict):
                for attr, info in parsed.items():
                    if not isinstance(info, dict):
                        continue
                    periods = info.get('periods')
                    if isinstance(periods, list) and periods:
                        norm = []
                        for p in periods:
                            if isinstance(p, (list, tuple)) and len(p) == 2:
                                norm.append([p[0], p[1]])
                            else:
                                norm.append([None, None])
                        history[attr] = {'type': info.get('type', 'fisso'), 'periods': norm}
                    else:
                        history[attr] = {'type': info.get('type', 'fisso'), 'periods': [[None, None]]}
        except ValueError:
            history = {}

    if all_cols:
        variabili, fisse = parse_custom_lists(raw_variabili, raw_fisse, all_cols)
        type_of = {col: 'variabile' for col in variabili}
        type_of.update({col: 'fisso' for col in fisse})
        for col in all_cols:
            if col in ATTR_SYSTEM_COLUMNS:
                continue
            if col not in history:
                history[col] = {'type': type_of.get(col, 'fisso'), 'periods': [[None, None]]}

    return history


def attr_active_in(periods, m_tuple):
    for start, end in periods:
        if (start is None or month_tuple(start) <= m_tuple) and \
           (end is None or m_tuple < month_tuple(end)):
            return True
    return False


def get_active_attrs(history):
    return [attr for attr, info in history.items()
            if any(p[1] is None for p in info['periods'])]


def get_removed_attrs(history):
    return [attr for attr, info in history.items()
            if not any(p[1] is None for p in info['periods'])]


def get_effective_columns(history, month_key):
    """Canonical ordered columns for a specific month (user attrs filtered by activity)."""
    m_tuple = month_tuple(month_key)
    variabili = [a for a in history if history[a]['type'] == 'variabile' and
                 attr_active_in(history[a]['periods'], m_tuple)]
    fisse = [a for a in history if history[a]['type'] == 'fisso' and
             attr_active_in(history[a]['periods'], m_tuple)]
    return ['mese', 'entrate'] + variabili + ['uscite_variabili'] + \
           fisse + ['uscite_fisse', 'uscite_totali', 'delta']


def get_canonical_columns(history):
    """Canonical ordered columns across all attributes (for cross-month views)."""
    variabili = [a for a in history if history[a]['type'] == 'variabile']
    fisse = [a for a in history if history[a]['type'] == 'fisso']
    return ['mese', 'entrate'] + variabili + ['uscite_variabili'] + \
           fisse + ['uscite_fisse', 'uscite_totali', 'delta']


def save_attribute_history(username, history, db=None):
    """Persist history and the derived active lists for a user (reusing an open connection)."""
    active = get_active_attrs(history)
    variabili = [a for a in active if history[a]['type'] == 'variabile']
    fisse = [a for a in active if history[a]['type'] == 'fisso']
    owns = db is None
    if owns:
        db = get_users_db()
    db.execute(
        "UPDATE users SET custom_variabili = ?, custom_fisse = ?, custom_attribute_history = ? WHERE username = ?",
        (json.dumps(variabili), json.dumps(fisse), json.dumps(history), username)
    )
    db.commit()
    if owns:
        db.close()


def effective_month_view(sm, target_user, month):
    """Return (columns, aligned_data_row, editable_columns) for a single month.

    Columns are ordered canonically and masked to the attributes active in that
    month; the row is realigned against the physical column order.
    """
    raw_var, raw_fiss, raw_hist = get_user_attr_meta(target_user)
    history = normalize_attribute_history(raw_hist, raw_var, raw_fiss, sm.get_column_names())
    columns = get_effective_columns(history, month)
    data = sm.get_data_by_month(month)
    if data:
        phys = sm.get_column_names()
        d = dict(zip(phys, data))
        ordered = tuple(d.get(c, 0) for c in columns)
    else:
        ordered = tuple(0 for _ in columns)
    editable = ['entrate'] + [c for c in columns if c not in ATTR_SYSTEM_COLUMNS]
    return columns, ordered, editable


# ─── DB helper ───

def get_db():
    return SQLManager(session.get('db_path'))

def parse_custom_lists(variabili_raw, fisse_raw, all_cols=None):
    """Parse stored custom attribute lists, falling back to the canonical column
    layout for legacy accounts whose lists were never persisted."""
    try:
        variabili = json.loads(variabili_raw or '[]')
    except ValueError:
        variabili = []
    try:
        fisse = json.loads(fisse_raw or '[]')
    except ValueError:
        fisse = []

    # Derive canonical lists from the column layout, usable as a fallback.
    derived_variabili, derived_fisse = [], []
    if all_cols:
        try:
            iv = all_cols.index('uscite_variabili')
            iff = all_cols.index('uscite_fisse')
            derived_variabili = list(all_cols[2:iv])
            derived_fisse = list(all_cols[iv + 1:iff])
        except ValueError:
            derived_variabili = [c for c in all_cols if c not in SQL_SYSTEM_COLUMNS]
            derived_fisse = derived_variabili

    # Fall back per-list for legacy accounts (empty stored list but columns exist).
    if not variabili and derived_variabili:
        variabili = derived_variabili
    if not fisse and derived_fisse:
        fisse = derived_fisse

    return variabili, fisse

def defaults_for_month(sm, month, defaults, username):
    """Return the subset of fixed defaults valid for a given month.

    Defaults apply only from the month AFTER the current real one onwards and
    only for attributes that are active in that month (so a stale default of a
    removed attribute never leaks into a month where the attribute is off).
    """
    if not defaults:
        return None
    if month_tuple(month) <= month_tuple(current_month_key()):
        return None
    raw_var, raw_fiss, raw_hist = get_user_attr_meta(username)
    history = normalize_attribute_history(raw_hist, raw_var, raw_fiss, sm.get_column_names())
    m_tuple = month_tuple(month)
    applicable = {}
    for col, val in defaults.items():
        info = history.get(col)
        if info and info['type'] == 'fisso' and attr_active_in(info['periods'], m_tuple):
            applicable[col] = val
    return applicable or None


def sync_default_months(sm, username, defaults=None):
    """Make fixed-expense defaults authoritative for every existing future month.

    For each active fisso column (> current real month) the cell is set to the
    current default value (or 0.0 when cleared).  A ``registro_spese`` entry with
    ``is_default=1`` is created, updated or removed so that defaults also appear
    in the storico.  Columns that contain user-entered data (any registro entry
    with ``is_default=0``) are never touched.
    """
    if not defaults:
        defaults = get_default_fisse_for_user(username)
    defaults = defaults or {}
    notes = get_default_note_for_user(username)
    raw_var, raw_fiss, raw_hist = get_user_attr_meta(username)
    history = normalize_attribute_history(raw_hist, raw_var, raw_fiss, sm.get_column_names())
    current = current_month_key()
    for month in sm.get_all_months():
        if month_tuple(month) <= month_tuple(current):
            continue
        m_tuple = month_tuple(month)
        active_fisse = [col for col, info in history.items()
                        if info['type'] == 'fisso' and attr_active_in(info['periods'], m_tuple)]
        if not active_fisse:
            continue
        all_entries = sm.get_expenses_for_month(month)
        manual_cats = {e[2] for e in all_entries if not e[6]}
        default_entries = {e[2]: e for e in all_entries if e[6]}
        year, month_name = month.split('_')
        month_num = sm._get_month_number(month_name)
        mese_data = f"{month_num:02d}-{year}"
        for col in active_fisse:
            if col in manual_cats:
                continue
            target = float(defaults.get(col, 0.0))
            note = notes.get(col, 'Default')
            existing = default_entries.get(col)
            if existing:
                old_amt = existing[4]
                if target == old_amt and existing[3] == note:
                    continue
                if target == 0:
                    sm.cursor.execute("DELETE FROM registro_spese WHERE id = ?", (existing[0],))
                    sm.update_value_by_attrANDmonth(month, col, 0.0)
                else:
                    sm.update_expense_in_registry(existing[0], note, target)
                    cur = sm.get_value_by_attrANDmonth(month, col)
                    sm.update_value_by_attrANDmonth(month, col, round(cur + (target - old_amt), 2))
            else:
                if target != 0:
                    sm.insert_expense_in_registry(col, note, target, mese_data, is_default=1)
                    sm.update_value_by_attrANDmonth(month, col, float(target))
                elif float(sm.get_value_by_attrANDmonth(month, col)) != 0.0:
                    sm.update_value_by_attrANDmonth(month, col, 0.0)
    sm.commit()


def ensure_month(sm, month, defaults=None, username=None):
    applicable = defaults_for_month(sm, month, defaults, username)
    if not sm.check_month_exists(month):
        notes = get_default_note_for_user(username) if username else {}
        sm.add_month_entry(month, default_fisse=applicable, default_notes=notes)
    sync_default_months(sm, username, defaults)


# ─── Register all routes ───

def register_routes(app):

    # ─── Context processor ───

    @app.context_processor
    def inject_globals():
        inv_count = 0
        if session.get('user_id'):
            db = get_users_db()
            inv_count = db.execute(
                "SELECT COUNT(*) FROM group_members WHERE user_id = ? AND status = 'pending'",
                (session['user_id'],)
            ).fetchone()[0]
            db.close()
        return dict(pending_invites_count=inv_count)


    # ─── Before request ───

    @app.before_request
    def ensure_year():
        if 'year' not in session:
            session['year'] = datetime.now().year


    # ─── Auth routes ───

    @app.route('/')
    def index():
        if 'user_id' in session:
            return redirect(url_for('add_expense'))
        return render_template('login.html', current_year=session.get('year'))


    @app.route('/login', methods=['POST'])
    def login():
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            flash("Inserisci username e password.", "error")
            return render_template('login.html', current_year=session.get('year'))

        db = get_users_db()
        user = db.execute(
            "SELECT id, username, password_hash, db_path, role, blocked FROM users WHERE username = ?",
            (username,)
        ).fetchone()
        db.close()

        if not user or not check_password_hash(user[2], password):
            flash("Username o password errati.", "error")
            return render_template('login.html', current_year=session.get('year'))

        if user[5]:
            flash("Account bloccato. Contatta un amministratore.", "error")
            return render_template('login.html', current_year=session.get('year'))

        session['user_id'] = user[0]
        session['username'] = user[1]
        session['db_path'] = user[3]
        session['role'] = user[4]
        flash(f"Benvenuto, {user[1]}!", "success")
        return redirect(url_for('add_expense'))


    @app.route('/signup', methods=['GET', 'POST'])
    def signup():
        if request.method == 'GET':
            return render_template('signup.html', current_year=session.get('year'))

        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            flash("Inserisci username e password.", "error")
            return render_template('signup.html', current_year=session.get('year'))

        if not username.isalnum():
            flash("Lo username può contenere solo lettere e numeri.", "error")
            return render_template('signup.html', current_year=session.get('year'))

        db_users = get_users_db()
        existing = db_users.execute(
            "SELECT id FROM users WHERE username = ?", (username,)
        ).fetchone()
        if existing:
            db_users.close()
            flash("Username già esistente.", "error")
            return render_template('signup.html', current_year=session.get('year'))

        password_hash = generate_password_hash(password)
        db_users.execute(
            "INSERT INTO users (username, password_hash, db_path, role) VALUES (?, ?, ?, 'basic')",
            (username, password_hash, 'pending')
        )
        db_users.commit()
        user_id = db_users.execute(
            "SELECT id FROM users WHERE username = ?", (username,)
        ).fetchone()[0]
        db_users.close()

        session['signup_user_id'] = user_id
        session['signup_username'] = username
        session['signup_password'] = password
        return redirect(url_for('signup_configure'))


    @app.route('/signup/configure', methods=['GET', 'POST'])
    def signup_configure():
        user_id = session.get('signup_user_id')
        username = session.get('signup_username')
        if not user_id or not username:
            flash("Sessione di registrazione scaduta. Riprova.", "error")
            return redirect(url_for('signup'))

        if request.method == 'GET':
            return render_template('signup_configure.html',
                default_variabili=DEFAULT_VARIABILI,
                default_fisse=DEFAULT_FISSE,
                current_year=session.get('year'))

        variabili_raw = request.form.getlist('variabili')
        fisse_raw = request.form.getlist('fisse')

        variabili = [v.strip() for v in variabili_raw if v.strip()]
        fisse = [f.strip() for f in fisse_raw if f.strip()]

        if not variabili:
            flash("Devi avere almeno un attributo variabile.", "error")
            return render_template('signup_configure.html',
                default_variabili=DEFAULT_VARIABILI, default_fisse=DEFAULT_FISSE,
                selected_variabili=variabili_raw, selected_fisse=fisse_raw,
                current_year=session.get('year'))

        if not fisse:
            flash("Devi avere almeno un attributo fisso.", "error")
            return render_template('signup_configure.html',
                default_variabili=DEFAULT_VARIABILI, default_fisse=DEFAULT_FISSE,
                selected_variabili=variabili_raw, selected_fisse=fisse_raw,
                current_year=session.get('year'))

        all_names = variabili + fisse
        if len(all_names) != len(set(all_names)):
            flash("Nomi attributi duplicati.", "error")
            return render_template('signup_configure.html',
                default_variabili=DEFAULT_VARIABILI, default_fisse=DEFAULT_FISSE,
                selected_variabili=variabili_raw, selected_fisse=fisse_raw,
                current_year=session.get('year'))

        invalid_chars = set(' ,;\'"()[]{}|\\/<>&=%#?!@`~')
        for name in variabili + fisse:
            if not name.isalnum() and not all(c not in invalid_chars for c in name):
                flash(f"Nome attributo '{name}' contiene caratteri non validi. Usa solo lettere e numeri.", "error")
                return render_template('signup_configure.html',
                    default_variabili=DEFAULT_VARIABILI, default_fisse=DEFAULT_FISSE,
                    selected_variabili=variabili_raw, selected_fisse=fisse_raw,
                    current_year=session.get('year'))

        user_db_path = os.path.join(USER_DB_DIR, f"{username}.db")
        os.makedirs(USER_DB_DIR, exist_ok=True)

        db_users = get_users_db()
        db_users.execute(
            "UPDATE users SET db_path = ?, custom_variabili = ?, custom_fisse = ? WHERE id = ?",
            (user_db_path, json.dumps(variabili), json.dumps(fisse), user_id)
        )
        db_users.commit()
        db_users.close()

        sql = generate_user_db_sql(variabili, fisse)
        new_db = SQLManager(user_db_path)
        new_db.cursor.executescript(sql)

        year = session.get('year', datetime.now().year)
        for m in range(1, 13):
            month_key = f"{year}_{MONTHS_INDEX[m]}"
            new_db.add_month_entry(month_key)
        new_db.close()

        password = session.get('signup_password', '')
        password_hash = generate_password_hash(password)
        db_users = get_users_db()
        db_users.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (password_hash, user_id)
        )
        db_users.commit()
        db_users.close()

        session['user_id'] = user_id
        session['username'] = username
        session['db_path'] = user_db_path
        session['role'] = 'basic'
        session.pop('signup_user_id', None)
        session.pop('signup_username', None)
        session.pop('signup_password', None)
        flash(f"Account creato! Benvenuto, {username}!", "success")
        return redirect(url_for('add_expense'))


    @app.route('/logout')
    def logout():
        session.clear()
        flash("Logout effettuato.", "info")
        return redirect(url_for('index'))


    # ─── Admin: User management ───

    @app.route('/admin/users')
    @login_required
    @role_required('super_admin')
    def admin_users():
        users = get_user_list()
        return render_template('admin_users.html', users=users, current_year=session.get('year'))


    @app.route('/admin/users/<int:uid>/promote', methods=['POST'])
    @login_required
    @role_required('super_admin')
    def admin_user_promote(uid):
        db = get_users_db()
        user = db.execute("SELECT id, username, role FROM users WHERE id = ?", (uid,)).fetchone()
        if user and user[2] == 'basic':
            db.execute("UPDATE users SET role = 'admin' WHERE id = ?", (uid,))
            db.execute("UPDATE groups SET blocked = 0 WHERE created_by = ?", (uid,))
            db.commit()
            flash(f"Utente '{user[1]}' promosso ad Admin. Gruppi riattivati.", "success")
        else:
            flash("Utente non trovato o già Admin.", "error")
        db.close()
        return redirect(url_for('admin_users'))


    @app.route('/admin/users/<int:uid>/demote', methods=['POST'])
    @login_required
    @role_required('super_admin')
    def admin_user_demote(uid):
        db = get_users_db()
        user = db.execute("SELECT id, username, role FROM users WHERE id = ?", (uid,)).fetchone()
        if user and user[2] == 'admin':
            db.execute("UPDATE users SET role = 'basic' WHERE id = ?", (uid,))
            db.execute("UPDATE groups SET blocked = 1 WHERE created_by = ?", (uid,))
            db.commit()
            flash(f"Utente '{user[1]}' declassato a Basic. Gruppi creati bloccati.", "success")
        else:
            flash("Utente non trovato o non è Admin.", "error")
        db.close()
        return redirect(url_for('admin_users'))


    @app.route('/admin/users/<int:uid>/remove', methods=['POST'])
    @login_required
    @role_required('super_admin')
    def admin_user_remove(uid):
        if uid == session['user_id']:
            flash("Non puoi rimuovere te stesso.", "error")
            return redirect(url_for('admin_users'))

        db = get_users_db()
        user = db.execute("SELECT id, username, db_path, role FROM users WHERE id = ?", (uid,)).fetchone()
        if not user:
            db.close()
            flash("Utente non trovato.", "error")
            return redirect(url_for('admin_users'))

        if user[3] == 'super_admin':
            db.close()
            flash("Non puoi rimuovere un Super Admin.", "error")
            return redirect(url_for('admin_users'))

        username = user[1]
        db_path = user[2]

        group_ids = [r[0] for r in db.execute("SELECT id FROM groups WHERE created_by = ?", (uid,)).fetchall()]
        for gid in group_ids:
            db.execute("DELETE FROM group_members WHERE group_id = ?", (gid,))
        db.execute("DELETE FROM groups WHERE created_by = ?", (uid,))
        db.execute("DELETE FROM group_members WHERE user_id = ?", (uid,))
        db.execute("DELETE FROM users WHERE id = ?", (uid,))
        db.commit()
        db.close()

        if os.path.exists(db_path):
            os.remove(db_path)

        flash(f"Utente '{username}' rimosso.", "success")
        return redirect(url_for('admin_users'))


    # ─── Admin: Groups ───

    @app.route('/admin/groups', methods=['GET', 'POST'])
    @login_required
    @role_required('admin', 'super_admin')
    def admin_groups():
        user_id = session['user_id']
        role = session['role']
        db = get_users_db()

        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            if name:
                try:
                    db.execute("INSERT INTO groups (name, description, created_by) VALUES (?, ?, ?)", (name, description, user_id))
                    db.commit()
                    flash(f"Gruppo '{name}' creato.", "success")
                except sqlite3.IntegrityError:
                    flash("Nome gruppo già esistente.", "error")
            else:
                flash("Inserisci un nome per il gruppo.", "error")

        if role == 'super_admin':
            groups = db.execute(
                "SELECT g.id, g.name, g.description, u.username, g.created_at, g.blocked FROM groups g JOIN users u ON u.id = g.created_by ORDER BY g.blocked, g.created_at"
            ).fetchall()
        else:
            groups = db.execute(
                "SELECT g.id, g.name, g.description, u.username, g.created_at, g.blocked FROM groups g JOIN users u ON u.id = g.created_by WHERE g.created_by = ? ORDER BY g.blocked, g.created_at",
                (user_id,)
            ).fetchall()
        db.close()
        return render_template('admin_groups.html', groups=groups, current_year=session.get('year'))


    @app.route('/admin/groups/<int:gid>', methods=['GET', 'POST'])
    @login_required
    @role_required('admin', 'super_admin')
    def admin_group_detail(gid):
        user_id = session['user_id']
        role = session['role']
        db = get_users_db()

        group = db.execute(
            "SELECT g.id, g.name, g.description, g.created_by, g.blocked FROM groups g WHERE g.id = ?", (gid,)
        ).fetchone()
        if not group:
            db.close()
            flash("Gruppo non trovato.", "error")
            return redirect(url_for('admin_groups'))

        if role != 'super_admin' and group[3] != user_id:
            db.close()
            flash("Accesso negato.", "error")
            return redirect(url_for('admin_groups'))

        creator = db.execute("SELECT username FROM users WHERE id = ?", (group[3],)).fetchone()
        creator_username = creator[0] if creator else '?'
        is_blocked = group[4]

        if request.method == 'POST':
            if is_blocked:
                flash("Il gruppo è bloccato. Impossibile eseguire azioni.", "error")
            else:
                action = request.form.get('action', '')

            if action == 'invite':
                target_username = request.form.get('username', '').strip()
                target = db.execute("SELECT id FROM users WHERE username = ?", (target_username,)).fetchone()
                if target:
                    try:
                        db.execute(
                            "INSERT INTO group_members (group_id, user_id, invited_by, status) VALUES (?, ?, ?, 'pending')",
                            (gid, target[0], user_id)
                        )
                        db.commit()
                        flash(f"Inviato invito a '{target_username}'.", "success")
                    except sqlite3.IntegrityError:
                        flash("Utente già membro o già invitato.", "error")
                else:
                    flash("Utente non trovato.", "error")

            elif action == 'block':
                member_id = int(request.form.get('member_id'))
                db.execute("UPDATE group_members SET status = 'blocked' WHERE id = ? AND group_id = ?",
                           (member_id, gid))
                db.commit()
                flash("Utente bloccato nel gruppo.", "success")

            elif action == 'unblock':
                member_id = int(request.form.get('member_id'))
                db.execute("UPDATE group_members SET status = 'accepted' WHERE id = ? AND group_id = ?",
                           (member_id, gid))
                db.commit()
                flash("Utente sbloccato nel gruppo.", "success")

            elif action == 'remove_member':
                member_id = int(request.form.get('member_id'))
                db.execute("DELETE FROM group_members WHERE id = ? AND group_id = ?", (member_id, gid))
                db.commit()
                flash("Membro rimosso dal gruppo.", "success")

        members = db.execute("""
            SELECT gm.id, u.id, u.username, gm.status
            FROM group_members gm
            JOIN users u ON u.id = gm.user_id
            WHERE gm.group_id = ?
            ORDER BY gm.created_at
        """, (gid,)).fetchall()

        candidates = db.execute(
            "SELECT username FROM users WHERE id NOT IN (SELECT user_id FROM group_members WHERE group_id = ?) AND id != ? ORDER BY username",
            (gid, group[3])
        ).fetchall()
        db.close()

        return render_template('admin_group_detail.html',
            group=group, members=members, candidates=candidates,
            creator_username=creator_username,
            current_year=session.get('year'))


    # ─── Invitations ───

    @app.route('/invitations', methods=['GET', 'POST'])
    @login_required
    def invitations():
        user_id = session['user_id']
        db = get_users_db()

        if request.method == 'POST':
            action = request.form.get('action', '')
            member_id = int(request.form.get('member_id'))

            if action == 'accept':
                db.execute("UPDATE group_members SET status = 'accepted' WHERE id = ? AND user_id = ? AND status = 'pending'",
                           (member_id, user_id))
                db.commit()
                flash("Invito accettato.", "success")
            elif action == 'decline':
                db.execute("UPDATE group_members SET status = 'declined' WHERE id = ? AND user_id = ? AND status = 'pending'",
                           (member_id, user_id))
                db.commit()
                flash("Invito rifiutato.", "info")

        invites = db.execute("""
            SELECT gm.id, g.name, u.username
            FROM group_members gm
            JOIN groups g ON g.id = gm.group_id
            JOIN users u ON u.id = gm.invited_by
            WHERE gm.user_id = ? AND gm.status = 'pending'
        """, (user_id,)).fetchall()
        db.close()

        return render_template('invitations.html', invites=invites, current_year=session.get('year'))


    # ─── Profile ───

    @app.route('/profile', methods=['GET', 'POST'])
    @app.route('/profile/<username>', methods=['GET', 'POST'])
    @login_required
    def profile(username=None):
        if username is None:
            username = session['username']

        if username != session['username'] and session.get('role') != 'super_admin':
            flash("Accesso negato.", "error")
            return redirect(url_for('profile'))

        db = get_users_db()
        user_info = db.execute(
            "SELECT id, username, password_hash, db_path, role, blocked, created_at, "
            "first_name, last_name, date_of_birth, bio, profile_photo, security_question, "
            "custom_variabili, custom_fisse, custom_default_fisse, custom_attribute_history, "
            "custom_default_fisse_notes "
            "FROM users WHERE username = ?",
            (username,)
        ).fetchone()

        if not user_info:
            db.close()
            flash("Utente non trovato.", "error")
            return redirect(url_for('add_expense'))

        is_own = (username == session['username'])

        if request.method == 'POST':
            action = request.form.get('action', '')

            if action == 'update_profile' and is_own:
                first_name = request.form.get('first_name', '').strip()
                last_name = request.form.get('last_name', '').strip()
                date_of_birth = request.form.get('date_of_birth', '').strip()
                bio = request.form.get('bio', '').strip()
                security_question = request.form.get('security_question', '').strip()
                security_answer = request.form.get('security_answer', '').strip()

                security_answer_hash = ''
                if security_answer:
                    security_answer_hash = generate_password_hash(security_answer.lower().strip())

                db.execute(
                    "UPDATE users SET first_name=?, last_name=?, date_of_birth=?, bio=?, "
                    "security_question=?, security_answer_hash=? WHERE id=?",
                    (first_name, last_name, date_of_birth, bio,
                     security_question, security_answer_hash, user_info[0])
                )
                db.commit()
                db.close()
                flash("Profilo aggiornato.", "success")
                return redirect(url_for('profile', username=username))

            elif action == 'upload_photo' and is_own:
                photo = request.files.get('profile_photo')
                if photo and photo.filename:
                    ext = photo.filename.rsplit('.', 1)[-1].lower()
                    if ext not in ('jpg', 'jpeg', 'png', 'gif'):
                        db.close()
                        flash("Formato non supportato. Usa JPG, PNG o GIF.", "error")
                        return redirect(url_for('profile', username=username))

                    photo.seek(0, 2)
                    size = photo.tell()
                    photo.seek(0)
                    if size > 5 * 1024 * 1024:
                        db.close()
                        flash("La foto non deve superare 5MB.", "error")
                        return redirect(url_for('profile', username=username))

                    old_photo = user_info[11]
                    if old_photo:
                        old_path = os.path.join(DATA_DIR, 'uploads', 'profiles', old_photo)
                        if os.path.exists(old_path):
                            os.remove(old_path)

                    filename = f"{user_info[0]}_{uuid.uuid4().hex[:8]}.{ext}"
                    upload_dir = os.path.join(DATA_DIR, 'uploads', 'profiles')
                    os.makedirs(upload_dir, exist_ok=True)
                    photo.save(os.path.join(upload_dir, filename))

                    db.execute("UPDATE users SET profile_photo=? WHERE id=?", (filename, user_info[0]))
                    db.commit()
                    db.close()
                    flash("Foto profilo aggiornata.", "success")
                    return redirect(url_for('profile', username=username))
                else:
                    db.close()
                    flash("Nessuna foto selezionata.", "error")
                    return redirect(url_for('profile', username=username))

            elif action == 'remove_photo' and is_own:
                old_photo = user_info[11]
                if old_photo:
                    old_path = os.path.join(DATA_DIR, 'uploads', 'profiles', old_photo)
                    if os.path.exists(old_path):
                        os.remove(old_path)
                    db.execute("UPDATE users SET profile_photo='' WHERE id=?", (user_info[0],))
                    db.commit()
                db.close()
                flash("Foto profilo rimossa.", "success")
                return redirect(url_for('profile', username=username))

            elif action == 'change_password' and is_own:
                current_password = request.form.get('current_password', '')
                new_password = request.form.get('new_password', '')
                confirm_password = request.form.get('confirm_password', '')

                if not current_password or not new_password or not confirm_password:
                    db.close()
                    flash("Compila tutti i campi password.", "error")
                    return redirect(url_for('profile', username=username))

                if not check_password_hash(user_info[2], current_password):
                    db.close()
                    flash("Password attuale errata.", "error")
                    return redirect(url_for('profile', username=username))

                if new_password != confirm_password:
                    db.close()
                    flash("Le nuove password non corrispondono.", "error")
                    return redirect(url_for('profile', username=username))

                if len(new_password) < 6:
                    db.close()
                    flash("La nuova password deve avere almeno 6 caratteri.", "error")
                    return redirect(url_for('profile', username=username))

                new_hash = generate_password_hash(new_password)
                db.execute("UPDATE users SET password_hash=? WHERE id=?", (new_hash, user_info[0]))
                db.commit()
                db.close()
                flash("Password cambiata.", "success")
                return redirect(url_for('profile', username=username))

            elif action == 'add_attribute' and is_own:
                attribute_name = request.form.get('attribute_name', '').strip()
                attribute_type = request.form.get('attribute_type', '')

                if not attribute_name or attribute_type not in ('variabile', 'fisso'):
                    db.close()
                    flash("Specifica un nome e un tipo valido.", "error")
                    return redirect(url_for('profile', username=username))

                if not attribute_name.isalnum():
                    db.close()
                    flash("Il nome attributo deve contenere solo lettere e numeri.", "error")
                    return redirect(url_for('profile', username=username))

                db_path = user_info[3]
                if not os.path.isfile(db_path):
                    db.close()
                    flash("Database utente non trovato.", "error")
                    return redirect(url_for('profile', username=username))

                try:
                    sm = SQLManager(db_path)
                    all_cols = sm.get_column_names()
                    history = normalize_attribute_history(
                        user_info[16], user_info[13], user_info[14], all_cols)
                    effective_from = current_month_key()

                    if attribute_name in ATTR_SYSTEM_COLUMNS:
                        raise ValueError(f"'{attribute_name}' è una colonna di sistema.")

                    if attribute_name in history:
                        if any(p[1] is None for p in history[attribute_name]['periods']):
                            raise ValueError(f"L'attributo '{attribute_name}' è già attivo.")
                        history[attribute_name]['periods'].append([effective_from, None])
                        save_attribute_history(username, history, db=db)
                        sm.close()
                        db.close()
                        flash("Attributo riattivato.", "success")
                    else:
                        if attribute_name in all_cols:
                            raise ValueError(f"L'attributo '{attribute_name}' esiste già.")
                        trigger_variabili = [a for a in history if history[a]['type'] == 'variabile']
                        trigger_fisse = [a for a in history if history[a]['type'] == 'fisso']
                        sm.add_attribute(attribute_name, attribute_type, trigger_variabili, trigger_fisse)
                        history[attribute_name] = {'type': attribute_type, 'periods': [[effective_from, None]]}
                        save_attribute_history(username, history, db=db)
                        sm.close()
                        db.close()
                        flash("Attributo aggiunto.", "success")
                except ValueError as e:
                    db.close()
                    flash(str(e), "error")
                return redirect(url_for('profile', username=username))

            elif action == 'remove_attribute' and is_own:
                attribute_name = request.form.get('attribute_name', '').strip()
                if not attribute_name:
                    db.close()
                    flash("Specifica un attributo.", "error")
                    return redirect(url_for('profile', username=username))

                db_path = user_info[3]
                if not os.path.isfile(db_path):
                    db.close()
                    flash("Database utente non trovato.", "error")
                    return redirect(url_for('profile', username=username))

                try:
                    sm = SQLManager(db_path)
                    all_cols = sm.get_column_names()
                    history = normalize_attribute_history(
                        user_info[16], user_info[13], user_info[14], all_cols)
                    effective_from = current_month_key()

                    if attribute_name not in history:
                        raise ValueError(f"L'attributo '{attribute_name}' non esiste.")
                    hist = history[attribute_name]
                    if not any(p[1] is None for p in hist['periods']):
                        raise ValueError(f"L'attributo '{attribute_name}' è già disattivato.")

                    active = [a for a in get_active_attrs(history) if a != attribute_name]
                    if hist['type'] == 'variabile':
                        if not any(history[a]['type'] == 'variabile' for a in active):
                            raise ValueError("Devi avere almeno un attributo variabile.")
                    else:
                        if not any(history[a]['type'] == 'fisso' for a in active):
                            raise ValueError("Devi avere almeno un attributo fisso.")

                    sm.remove_attribute(attribute_name, effective_from)

                    for p in hist['periods']:
                        if p[1] is None:
                            p[1] = effective_from

                    defaults = json.loads(user_info[15] or '{}')
                    if attribute_name in defaults:
                        defaults.pop(attribute_name, None)
                        db.execute("UPDATE users SET custom_default_fisse = ? WHERE id = ?",
                                   (json.dumps(defaults), user_info[0]))

                    save_attribute_history(username, history, db=db)
                    sm.close()
                    db.close()
                    flash("Attributo rimosso.", "success")
                except ValueError as e:
                    db.close()
                    flash(str(e), "error")
                return redirect(url_for('profile', username=username))

            elif action == 'reintegrate_attribute' and is_own:
                attribute_name = request.form.get('attribute_name', '').strip()
                if not attribute_name:
                    db.close()
                    flash("Specifica un attributo.", "error")
                    return redirect(url_for('profile', username=username))

                db_path = user_info[3]
                if not os.path.isfile(db_path):
                    db.close()
                    flash("Database utente non trovato.", "error")
                    return redirect(url_for('profile', username=username))

                try:
                    sm = SQLManager(db_path)
                    all_cols = sm.get_column_names()
                    history = normalize_attribute_history(
                        user_info[16], user_info[13], user_info[14], all_cols)
                    effective_from = current_month_key()

                    if attribute_name not in history:
                        raise ValueError(f"L'attributo '{attribute_name}' non esiste.")
                    hist = history[attribute_name]
                    if any(p[1] is None for p in hist['periods']):
                        raise ValueError(f"L'attributo '{attribute_name}' è già attivo.")

                    hist['periods'].append([effective_from, None])
                    save_attribute_history(username, history, db=db)
                    sm.close()
                    db.close()
                    flash("Attributo riattivato.", "success")
                except ValueError as e:
                    db.close()
                    flash(str(e), "error")
                return redirect(url_for('profile', username=username))

            elif action == 'set_default_fisse' and is_own:
                all_cols = []
                history = None
                sm = None
                if os.path.isfile(user_info[3]):
                    sm = SQLManager(user_info[3])
                    all_cols = sm.get_column_names()
                    history = normalize_attribute_history(
                        user_info[16], user_info[13], user_info[14], all_cols)
                active_fisse = []
                if history is not None:
                    active_fisse = [a for a in get_active_attrs(history)
                                    if history[a]['type'] == 'fisso']
                defaults = {}
                notes = {}
                for col in active_fisse:
                    val = request.form.get(f'default_{col}', '').strip()
                    if val != '':
                        try:
                            defaults[col] = float(val)
                        except ValueError:
                            pass
                    note = request.form.get(f'note_{col}', '').strip()
                    if note:
                        notes[col] = note
                db.execute("UPDATE users SET custom_default_fisse = ?, custom_default_fisse_notes = ? WHERE id = ?",
                           (json.dumps(defaults), json.dumps(notes), user_info[0]))
                db.commit()
                if sm is not None:
                    sync_default_months(sm, username, defaults)
                    sm.close()
                db.close()
                flash("Default spese fisse salvati.", "success")
                return redirect(url_for('profile', username=username))

        # Load attribute data for display (own profile)
        profile_attributes = None
        profile_defaults = None
        profile_notes = None
        removed_attributes = []
        effective_from = None
        if is_own:
            all_cols = []
            if os.path.isfile(user_info[3]):
                sm = SQLManager(user_info[3])
                all_cols = sm.get_column_names()
                sm.close()
            try:
                profile_defaults = json.loads(user_info[15] or '{}')
            except ValueError:
                profile_defaults = {}
            try:
                profile_notes = json.loads(user_info[17] or '{}')
            except ValueError:
                profile_notes = {}

            history = normalize_attribute_history(
                user_info[16], user_info[13], user_info[14], all_cols)
            active = get_active_attrs(history)
            effective_from = current_month_key()

            profile_attributes = {
                'variabili': [a for a in active if history[a]['type'] == 'variabile'],
                'fisse': [a for a in active if history[a]['type'] == 'fisso'],
                'system': [c for c in all_cols if c in ATTR_SYSTEM_COLUMNS],
            }
            removed_attributes = [
                {'name': a, 'type': history[a]['type'], 'periods': history[a]['periods']}
                for a in get_removed_attrs(history)
            ]
        
        user_groups = db.execute("""
            SELECT g.id, g.name, g.description,
                CASE WHEN g.created_by = ? THEN 'Creatore' ELSE 'Membro' END,
                g.blocked
            FROM groups g
            WHERE g.created_by = ?
            UNION
            SELECT g.id, g.name, g.description, 'Membro', g.blocked
            FROM groups g
            JOIN group_members gm ON gm.group_id = g.id
            WHERE gm.user_id = ? AND gm.status = 'accepted'
            ORDER BY 2
        """, (user_info[0], user_info[0], user_info[0])).fetchall()

        group_members_map = {}
        for gid, gname, gdesc, grole, gblocked in user_groups:
            members = db.execute("""
                SELECT u.username,
                    CASE WHEN g.created_by = u.id THEN 'Creatore'
                         WHEN u.role = 'super_admin' THEN 'Super Admin'
                         WHEN u.role = 'admin' THEN 'Admin'
                         ELSE 'Basic'
                    END
                FROM group_members gm
                JOIN users u ON u.id = gm.user_id
                JOIN groups g ON g.id = gm.group_id
                WHERE gm.group_id = ? AND gm.status = 'accepted'
                UNION
                SELECT u.username,
                    CASE WHEN u.role = 'super_admin' THEN 'Super Admin'
                         WHEN u.role = 'admin' THEN 'Admin'
                         ELSE 'Basic'
                    END
                FROM groups g
                JOIN users u ON u.id = g.created_by
                WHERE g.id = ?
                ORDER BY 1
            """, (gid, gid)).fetchall()
            group_members_map[gid] = members

        db.close()
        return render_template('user_profile.html', user_info=user_info, is_own=is_own,
                               user_groups=user_groups, group_members_map=group_members_map,
                               profile_attributes=profile_attributes,
                               profile_defaults=profile_defaults,
                               profile_notes=profile_notes,
                               removed_attributes=removed_attributes,
                               effective_from=effective_from,
                               current_year=session.get('year'))


    @app.route('/uploads/profiles/<filename>')
    def uploaded_profile_photo(filename):
        return send_from_directory(os.path.join(DATA_DIR, 'uploads', 'profiles'), filename)


    # ─── Forgot Password ───

    @app.route('/forgot-password', methods=['GET', 'POST'])
    def forgot_password():
        if 'user_id' in session:
            return redirect(url_for('add_expense'))

        step = request.args.get('step', 'username')
        username = request.form.get('username', '').strip() or request.args.get('username', '').strip()

        if request.method == 'POST':
            action = request.form.get('action', '')

            if action == 'lookup':
                if not username:
                    flash("Inserisci lo username.", "error")
                    return render_template('forgot_password.html', step='username',
                                           current_year=session.get('year'))

                db = get_users_db()
                user = db.execute(
                    "SELECT id, username, security_question, security_answer_hash FROM users WHERE username = ?",
                    (username,)
                ).fetchone()
                db.close()

                if not user:
                    flash("Utente non trovato.", "error")
                    return render_template('forgot_password.html', step='username',
                                           current_year=session.get('year'))

                if not user[2]:
                    flash("Nessuna domanda di sicurezza impostata. Contatta un amministratore.",
                          "error")
                    return render_template('forgot_password.html', step='username',
                                           current_year=session.get('year'))

                return render_template('forgot_password.html', step='answer',
                                       username=username, security_question=user[2],
                                       current_year=session.get('year'))

            elif action == 'answer':
                answer = request.form.get('answer', '').strip()
                if not answer:
                    flash("Inserisci la risposta.", "error")
                    return render_template('forgot_password.html', step='answer',
                                           username=username,
                                           security_question=request.form.get('security_question', ''),
                                           current_year=session.get('year'))

                db = get_users_db()
                user = db.execute(
                    "SELECT id, security_answer_hash FROM users WHERE username = ?",
                    (username,)
                ).fetchone()
                db.close()

                if not user or not user[1] or not check_password_hash(user[1], answer.lower().strip()):
                    flash("Risposta errata.", "error")
                    return render_template('forgot_password.html', step='answer',
                                           username=username,
                                           security_question=request.form.get('security_question', ''),
                                           current_year=session.get('year'))

                return render_template('forgot_password.html', step='reset',
                                       username=username, current_year=session.get('year'))

            elif action == 'reset':
                new_password = request.form.get('new_password', '')
                confirm_password = request.form.get('confirm_password', '')

                if not new_password or not confirm_password:
                    flash("Compila tutti i campi.", "error")
                    return render_template('forgot_password.html', step='reset',
                                           username=username, current_year=session.get('year'))

                if new_password != confirm_password:
                    flash("Le password non corrispondono.", "error")
                    return render_template('forgot_password.html', step='reset',
                                           username=username, current_year=session.get('year'))

                if len(new_password) < 6:
                    flash("La password deve avere almeno 6 caratteri.", "error")
                    return render_template('forgot_password.html', step='reset',
                                           username=username, current_year=session.get('year'))

                db = get_users_db()
                new_hash = generate_password_hash(new_password)
                db.execute("UPDATE users SET password_hash=? WHERE username=?", (new_hash, username))
                db.commit()
                db.close()
                flash("Password reimpostata. Ora puoi accedere.", "success")
                return redirect(url_for('index'))

        return render_template('forgot_password.html', step=step, username=username,
                               current_year=session.get('year'))


    # ─── Admin: Reset Password ───

    @app.route('/admin/users/<int:uid>/reset-password', methods=['POST'])
    @login_required
    @role_required('super_admin')
    def admin_user_reset_password(uid):
        db = get_users_db()
        user = db.execute("SELECT id, username FROM users WHERE id = ?", (uid,)).fetchone()
        if not user:
            db.close()
            flash("Utente non trovato.", "error")
            return redirect(url_for('admin_users'))

        temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(10))
        temp_hash = generate_password_hash(temp_password)
        db.execute("UPDATE users SET password_hash=? WHERE id=?", (temp_hash, uid))
        db.commit()
        db.close()

        flash(f"Password temporanea per '{user[1]}': {temp_password}", "success")
        return redirect(url_for('admin_users'))


    # ─── Add Expense ───

    @app.route('/add-expense', methods=['GET', 'POST'])
    @login_required
    def add_expense():
        target_user = request.args.get('target_user') or request.form.get('target_user') or session['username']

        if target_user != session['username']:
            sm = get_db_for_user(target_user)
            if not sm:
                return redirect(url_for('add_expense'))
        else:
            sm = get_db()

        visible_users = get_visible_users()
        year = session.get('year')
        default_fisse = get_default_fisse_for_user(target_user)

        now = datetime.now()
        month_num = now.month
        month_name = MONTHS_INDEX[month_num]
        month = f"{year}_{month_name}"

        if request.method == 'POST':
            month_raw = request.form.get('month')
            action = request.form.get('action', '')

            if month_raw:
                if '_' in month_raw:
                    month = month_raw
                    month_name = month.split('_')[1]
                    month_num = int(request.form.get('month_num', month_num))
                elif month_raw.isdigit():
                    month_num = int(month_raw)
                    month_name = MONTHS_INDEX[month_num]
                    month = f"{year}_{month_name}"

            if action == 'select_month':
                ensure_month(sm, month, defaults=default_fisse, username=target_user)
                columns, ordered, editable = effective_month_view(sm, target_user, month)
                return render_template('add_expense.html', month=month,
                    month_name=month_name, month_num=month_num, data_row=ordered,
                    visible_users=visible_users, target_user=target_user,
                    user_columns=columns, user_editable=editable,
                    current_year=year)

            if action == 'add':
                attribute = request.form.get('attribute')
                value = round(float(request.form.get('value', 0)), 1)
                nota = request.form.get('nota', '').strip() or 'N/A'
                mese_data = f"{month_num:02d}-{month.split('_')[0]}"
                sm.insert_expense_in_registry(attribute, nota, value, mese_data)
                old_val = sm.get_value_by_attrANDmonth(month, attribute)
                sm.update_value_by_attrANDmonth(month, attribute, old_val + value)
                sm.commit()
                flash("Spesa aggiunta!", "success")
                return redirect(url_for('add_expense', month=month, target_user=target_user))

            if action == 'add_all':
                attributes = request.form.getlist('attribute[]')
                values = request.form.getlist('value[]')
                notes = request.form.getlist('nota[]')
                for attr, val_raw, nota_raw in zip(attributes, values, notes):
                    val = round(float(val_raw), 1)
                    nota = nota_raw.strip() or 'N/A'
                    mese_data = f"{month_num:02d}-{month.split('_')[0]}"
                    sm.insert_expense_in_registry(attr, nota, val, mese_data)
                    old_val = sm.get_value_by_attrANDmonth(month, attr)
                    sm.update_value_by_attrANDmonth(month, attr, old_val + val)
                sm.commit()
                flash(f"{len(attributes)} spese aggiunte!", "success")
                return redirect(url_for('add_expense', month=month, target_user=target_user))

        month_param = request.args.get('month')
        if month_param and '_' in month_param:
            parts = month_param.split('_')
            if parts[1] in MONTHS_INDEX.values():
                month = month_param
                month_name = parts[1]
                for num, name in MONTHS_INDEX.items():
                    if name == month_name:
                        month_num = num
                        break

        ensure_month(sm, month, defaults=default_fisse, username=target_user)
        columns, ordered, editable = effective_month_view(sm, target_user, month)
        return render_template('add_expense.html', month=month,
            month_name=month_name, month_num=month_num, data_row=ordered,
            visible_users=visible_users, target_user=target_user,
            user_columns=columns, user_editable=editable,
            current_year=year)


    # ─── Data Analysis / Comparison ───

    @app.route('/data-analysis/comparison', methods=['GET', 'POST'])
    @login_required
    def data_analysis_comparison():
        target_user = request.args.get('target_user') or request.form.get('target_user') or session['username']

        if target_user != session['username']:
            sm = get_db_for_user(target_user)
            if not sm:
                return redirect(url_for('data_analysis_comparison'))
        else:
            sm = get_db()

        visible_users = get_visible_users()
        year = session.get('year')
        all_sorted = sm.get_months_list(year)

        if request.method == 'POST':
            selected = request.form.getlist('selected_months')
            if not selected:
                flash("Seleziona almeno un mese.", "error")
                selected = all_sorted[-3:] if len(all_sorted) >= 3 else all_sorted[:]
        else:
            current_month_key = f"{year}_{MONTHS_INDEX[datetime.now().month]}"
            if current_month_key in all_sorted:
                selected = [current_month_key]
            else:
                selected = all_sorted[-1:] if all_sorted else []

        months_data = sm.get_months_data(selected)
        sorted_months = [m for m in all_sorted if m in selected]
        raw_var, raw_fiss, raw_hist = get_user_attr_meta(target_user)
        history = normalize_attribute_history(raw_hist, raw_var, raw_fiss, sm.get_column_names())
        user_columns = get_canonical_columns(history)
        phys = sm.get_column_names()

        rows = []
        for attr in user_columns:
            if attr == 'mese':
                continue
            is_user_attr = attr in history
            values = []
            for m in sorted_months:
                row = months_data.get(m)
                if not row:
                    continue
                d = dict(zip(phys, row))
                visible = (not is_user_attr) or attr_active_in(history[attr]['periods'], month_tuple(m))
                val = d.get(attr)
                if visible and val is not None:
                    values.append(round(float(val), 2))
            if values:
                mean = round(sum(values) / len(values), 2)
                pct = None
                if len(values) >= 2:
                    if values[0] == 0:
                        pct = 1e10 if values[-1] > 0 else (-1e10 if values[-1] < 0 else 0.0)
                    else:
                        pct = round(((values[-1] - values[0]) / values[0]) * 100, 1)
                rows.append((attr, values, mean, pct))

        month_labels = []
        month_short_labels = []
        for m in sorted_months:
            y, mn = m.split('_')
            month_labels.append(f"{mn.capitalize()} {y}")
            month_short_labels.append(mn[:3].capitalize())

        active = get_active_attrs(history)
        user_variabili = [a for a in active if history[a]['type'] == 'variabile']
        user_fisse = [a for a in active if history[a]['type'] == 'fisso']
        return render_template('comparison.html', months=all_sorted,
            selected=selected, sorted_months=sorted_months,
            rows=rows, month_labels=month_labels,
            month_short_labels=month_short_labels,
            visible_users=visible_users, target_user=target_user,
            user_variabili=user_variabili, user_fisse=user_fisse,
            active_view='comparison', current_year=year)


    # ─── Data Analysis / Tracking ───

    @app.route('/data-analysis/tracking')
    @login_required
    def data_analysis_tracking():
        target_user = request.args.get('target_user') or session['username']

        if target_user != session['username']:
            sm = get_db_for_user(target_user)
            if not sm:
                return redirect(url_for('data_analysis_tracking'))
        else:
            sm = get_db()

        visible_users = get_visible_users()
        year = session.get('year')
        all_sorted = sm.get_months_list(year)

        all_months_data = sm.get_months_data(all_sorted)
        raw_var, raw_fiss, raw_hist = get_user_attr_meta(target_user)
        history = normalize_attribute_history(raw_hist, raw_var, raw_fiss, sm.get_column_names())
        trackable_attrs = [a for a in get_canonical_columns(history) if a != 'mese']
        tracking_data = {}
        phys = sm.get_column_names()
        for attr in trackable_attrs:
            is_user_attr = attr in history
            values = []
            for m in all_sorted:
                row = all_months_data.get(m)
                val = None
                if row:
                    d = dict(zip(phys, row))
                    visible = (not is_user_attr) or attr_active_in(history[attr]['periods'], month_tuple(m))
                    if visible and d.get(attr) is not None:
                        val = round(float(d[attr]), 2)
                values.append(val)
            tracking_data[attr] = values

        all_month_labels = []
        for m in all_sorted:
            y, mn = m.split('_')
            all_month_labels.append(f"{mn.capitalize()} {y}")

        return render_template('tracking.html',
            tracking_data=tracking_data, all_month_labels=all_month_labels,
            trackable_attrs=trackable_attrs,
            months=all_sorted,
            visible_users=visible_users, target_user=target_user,
            active_view='tracking', current_year=year)


    # ─── Redirects ───

    @app.route('/compare-months', methods=['GET', 'POST'])
    @login_required
    def compare_months_redirect():
        return redirect(url_for('data_analysis_comparison'))

    @app.route('/track-attribute', methods=['GET', 'POST'])
    @login_required
    def track_attribute_redirect():
        return redirect(url_for('data_analysis_tracking'))

    @app.route('/show-history', methods=['GET', 'POST'])
    @login_required
    def show_history_redirect():
        return redirect(url_for('data_analysis_history'))


    # ─── Data Analysis / History ───

    @app.route('/data-analysis/history', methods=['GET', 'POST'])
    @login_required
    def data_analysis_history():
        target_user = request.args.get('target_user') or request.form.get('target_user') or session['username']

        if target_user != session['username']:
            sm = get_db_for_user(target_user)
            if not sm:
                return redirect(url_for('data_analysis_history'))
        else:
            sm = get_db()

        visible_users = get_visible_users()
        year = session.get('year')
        months = sm.get_months_list(year)

        start = end = None
        entries = None
        month_counts = {}
        selected_months = request.form.getlist('selected_months') if request.method == 'POST' else []
        if request.method == 'POST':
            start_raw = request.form.get('start_date', '').strip()
            end_raw = request.form.get('end_date', '').strip()
            start = parse_date_bound(start_raw, "start")
            end = parse_date_bound(end_raw, "end")
            if start_raw and not start:
                flash("Invalid start date.", "error")
            elif end_raw and not end:
                flash("Invalid end date.", "error")
            else:
                entries = sm.get_registro_entries(start, end)
                for e in entries:
                    m = e[5][3:7] + '-' + e[5][0:2]
                    month_counts[m] = month_counts.get(m, 0) + 1
        elif request.method == 'GET':
            start_raw = request.args.get('start_date', '').strip()
            end_raw = request.args.get('end_date', '').strip()
            if start_raw or end_raw:
                start = parse_date_bound(start_raw, "start")
                end = parse_date_bound(end_raw, "end")
                entries = sm.get_registro_entries(start, end)
                for e in entries:
                    m = e[5][3:7] + '-' + e[5][0:2]
                    month_counts[m] = month_counts.get(m, 0) + 1

        return render_template('show_history.html',
            entries=entries, start_date=start, end_date=end,
            month_counts=month_counts,
            months=months,
            selected_months=selected_months,
            visible_users=visible_users, target_user=target_user,
            active_view='history',
            current_year=year)


    @app.route('/edit-expense', methods=['POST'])
    @login_required
    def edit_expense():
        target_user = request.form.get('target_user') or session['username']

        if target_user != session['username']:
            sm = get_db_for_user(target_user)
            if not sm:
                return redirect(url_for('data_analysis_history'))
        else:
            sm = get_db()

        expense_id = request.form.get('expense_id', '').strip()
        new_nota = request.form.get('nota', '').strip() or 'N/A'
        new_importo_raw = request.form.get('importo', '').strip()

        if not expense_id or not new_importo_raw:
            flash("Dati mancanti.", "error")
            return redirect(url_for('data_analysis_history'))

        try:
            new_importo = round(float(new_importo_raw), 2)
        except ValueError:
            flash("Importo non valido.", "error")
            return redirect(url_for('data_analysis_history'))

        result = sm.update_expense_in_registry(expense_id, new_nota, new_importo)
        if not result:
            flash("Spesa non trovata.", "error")
            return redirect(url_for('data_analysis_history'))

        old_categoria, old_importo, data = result

        if new_importo != old_importo:
            month_num = int(data[:2])
            month_year = data[3:]
            month_key = f"{month_year}_{MONTHS_INDEX[month_num]}"
            ensure_month(sm, month_key, defaults=get_default_fisse_for_user(target_user), username=target_user)
            current_val = sm.get_value_by_attrANDmonth(month_key, old_categoria)
            delta = new_importo - old_importo
            sm.update_value_by_attrANDmonth(month_key, old_categoria, round(current_val + delta, 2))

        sm.commit()
        flash("Spesa modificata con successo!", "success")

        start_raw = request.form.get('start_date', '').strip()
        end_raw = request.form.get('end_date', '').strip()
        return redirect(url_for('data_analysis_history',
            target_user=target_user, start_date=start_raw, end_date=end_raw))


    @app.route('/delete-expense', methods=['POST'])
    @login_required
    def delete_expense():
        target_user = request.form.get('target_user') or session['username']

        if target_user != session['username']:
            sm = get_db_for_user(target_user)
            if not sm:
                return redirect(url_for('data_analysis_history'))
        else:
            sm = get_db()

        expense_id = request.form.get('expense_id', '').strip()
        if not expense_id:
            flash("Dati mancanti.", "error")
            return redirect(url_for('data_analysis_history'))

        expense = sm.cursor.execute(
            "SELECT categoria, importo, data FROM registro_spese WHERE id = ?",
            (expense_id,)
        ).fetchone()

        if not expense:
            flash("Spesa non trovata.", "error")
            return redirect(url_for('data_analysis_history'))

        category, amount, data = expense
        sm.cursor.execute("DELETE FROM registro_spese WHERE id = ?", (expense_id,))

        month_num = int(data[:2])
        month_year = data[3:]
        month_key = f"{month_year}_{MONTHS_INDEX[month_num]}"
        ensure_month(sm, month_key, defaults=get_default_fisse_for_user(target_user), username=target_user)
        cur_val = sm.get_value_by_attrANDmonth(month_key, category)
        sm.update_value_by_attrANDmonth(month_key, category, round(cur_val - amount, 2))

        sm.commit()
        flash("Spesa eliminata con successo!", "success")

        start_raw = request.form.get('start_date', '').strip()
        end_raw = request.form.get('end_date', '').strip()
        return redirect(url_for('data_analysis_history',
            target_user=target_user, start_date=start_raw, end_date=end_raw))


    # ─── Change Year ───

    @app.route('/change-year', methods=['GET', 'POST'])
    @login_required
    def change_year():
        if request.method == 'POST':
            try:
                new_year = int(request.form.get('year'))
                session['year'] = new_year
                flash(f"Year changed to {new_year}.", "success")
            except (ValueError, TypeError):
                flash("Invalid year.", "error")
            return redirect(url_for('index'))
        return render_template('change_year.html', current_year=session.get('year'))
