from flask import Flask, render_template, request, session, redirect, url_for, flash
from datetime import datetime
import os, functools, sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

from settings import *
from sqlManager import SQLManager
from utils import parse_date_bound, get_color_for_attribute
from init import init_app


# --- Initialize the application
init_app()


# ─── Users DB ───

def get_users_db():
    return sqlite3.connect(USERS_DB)


# ─── App setup ───

app = Flask(__name__)

KEY_FILE = 'flask_secret.key'
if os.path.exists(KEY_FILE):
    with open(KEY_FILE, 'rb') as f:
        app.secret_key = f.read()
else:
    app.secret_key = os.urandom(24)
    with open(KEY_FILE, 'wb') as f:
        f.write(app.secret_key)

app.jinja_env.globals.update(zip=zip)
app.jinja_env.globals.update(get_color_for_attribute=get_color_for_attribute)
app.jinja_env.globals.update(MONTHS_INDEX=MONTHS_INDEX)
app.jinja_env.globals.update(SQL_ATTRIBUTES_ALL=SQL_ATTRIBUTES_ALL)
app.jinja_env.globals.update(SQL_ATTRIBUTES_EDITABLE=SQL_ATTRIBUTES_EDITABLE)
app.jinja_env.globals.update(SESSION=session)


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


# ─── DB helper ───

def get_db():
    return SQLManager(session.get('db_path'))

def ensure_month(sm, month):
    if not sm.check_month_exists(month):
        sm.add_month_entry(month)


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

    user_db_path = os.path.join(USER_DB_DIR, f"{username}.db")
    db_users = get_users_db()

    existing = db_users.execute(
        "SELECT id FROM users WHERE username = ?", (username,)
    ).fetchone()
    if existing or os.path.exists(user_db_path):
        db_users.close()
        flash("Username già esistente.", "error")
        return render_template('signup.html', current_year=session.get('year'))

    os.makedirs(USER_DB_DIR, exist_ok=True)
    new_db = SQLManager(user_db_path)
    init_sql = open('init.sql').read()
    new_db.cursor.executescript(init_sql)

    year = session.get('year', datetime.now().year)
    for m in range(1, 13):
        month_key = f"{year}_{MONTHS_INDEX[m]}"
        new_db.add_month_entry(month_key)
    new_db.close()

    password_hash = generate_password_hash(password)
    db_users.execute(
        "INSERT INTO users (username, password_hash, db_path, role) VALUES (?, ?, ?, 'basic')",
        (username, password_hash, user_db_path)
    )
    db_users.commit()
    user_id = db_users.execute(
        "SELECT id FROM users WHERE username = ?", (username,)
    ).fetchone()[0]
    db_users.close()

    session['user_id'] = user_id
    session['username'] = username
    session['db_path'] = user_db_path
    session['role'] = 'basic'
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
        db.commit()
        flash(f"Utente '{user[1]}' promosso ad Admin.", "success")
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
        db.commit()
        flash(f"Utente '{user[1]}' declassato a Basic.", "success")
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

    db.execute("DELETE FROM group_members WHERE user_id = ?", (uid,))
    db.execute("DELETE FROM groups WHERE created_by = ?", (uid,))
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
            "SELECT g.id, g.name, g.description, u.username, g.created_at FROM groups g JOIN users u ON u.id = g.created_by ORDER BY g.created_at"
        ).fetchall()
    else:
        groups = db.execute(
            "SELECT g.id, g.name, g.description, u.username, g.created_at FROM groups g JOIN users u ON u.id = g.created_by WHERE g.created_by = ? ORDER BY g.created_at",
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
        "SELECT g.id, g.name, g.description, g.created_by FROM groups g WHERE g.id = ?", (gid,)
    ).fetchone()
    if not group:
        db.close()
        flash("Gruppo non trovato.", "error")
        return redirect(url_for('admin_groups'))

    if role != 'super_admin' and group[3] != user_id:
        db.close()
        flash("Accesso negato.", "error")
        return redirect(url_for('admin_groups'))

    if request.method == 'POST':
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

@app.route('/profile')
@app.route('/profile/<username>')
@login_required
def profile(username=None):
    if username is None:
        username = session['username']

    if username != session['username'] and session.get('role') != 'super_admin':
        flash("Accesso negato.", "error")
        return redirect(url_for('profile'))

    db = get_users_db()
    user_info = db.execute(
        "SELECT id, username, password_hash, db_path, role, blocked, created_at FROM users WHERE username = ?",
        (username,)
    ).fetchone()
    db.close()

    if not user_info:
        flash("Utente non trovato.", "error")
        return redirect(url_for('add_expense'))

    return render_template('user_profile.html', user_info=user_info, current_year=session.get('year'))


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
            ensure_month(sm, month)
            data = sm.get_data_by_month(month)
            return render_template('add_expense.html', month=month,
                month_name=month_name, month_num=month_num, data_row=data,
                visible_users=visible_users, target_user=target_user,
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

    ensure_month(sm, month)
    data = sm.get_data_by_month(month)
    return render_template('add_expense.html', month=month,
        month_name=month_name, month_num=month_num, data_row=data,
        visible_users=visible_users, target_user=target_user,
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

    rows = []
    for attr_idx, attr in enumerate(SQL_ATTRIBUTES_ALL):
        if attr == 'mese':
            continue
        values = []
        for m in sorted_months:
            row = months_data.get(m)
            if row and row[attr_idx] is not None:
                v = round(float(row[attr_idx]), 2)
                values.append(v)
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

    return render_template('comparison.html', months=all_sorted,
        selected=selected, sorted_months=sorted_months,
        rows=rows, month_labels=month_labels,
        month_short_labels=month_short_labels,
        visible_users=visible_users, target_user=target_user,
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
    trackable_attrs = [a for a in SQL_ATTRIBUTES_ALL if a != 'mese']
    tracking_data = {}
    for attr in trackable_attrs:
        attr_idx = SQL_ATTRIBUTES_ALL.index(attr)
        values = []
        for m in all_sorted:
            row = all_months_data.get(m)
            if row and row[attr_idx] is not None:
                values.append(round(float(row[attr_idx]), 2))
            else:
                values.append(None)
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


# ─── Undo Expense ───

@app.route('/undo-expense', methods=['GET', 'POST'])
@login_required
def undo_expense():
    target_user = request.args.get('target_user') or request.form.get('target_user') or session['username']

    if target_user != session['username']:
        sm = get_db_for_user(target_user)
        if not sm:
            return redirect(url_for('undo_expense'))
    else:
        sm = get_db()

    visible_users = get_visible_users()
    year = session.get('year')
    months = sm.get_months_list(year)

    expenses = None
    selected_month = None

    if request.method == 'POST':
        action = request.form.get('action', '')
        month_raw = request.form.get('month', '')

        if month_raw:
            if '_' in month_raw:
                selected_month = month_raw
            elif month_raw.isdigit():
                month_num = int(month_raw)
                month_name = MONTHS_INDEX[month_num]
                selected_month = f"{year}_{month_name}"

        if action == 'show':
            if not selected_month:
                flash("Select a month.", "error")
            else:
                expenses = sm.get_expenses_for_month(selected_month)
                if not expenses:
                    flash("No expenses found for this month.", "info")

        elif action == 'delete':
            expense_id = request.form.get('expense_id')
            if not expense_id or not selected_month:
                flash("Missing expense data.", "error")
            else:
                expense = sm.cursor.execute(
                    "SELECT categoria, importo FROM registro_spese WHERE id = ?",
                    (expense_id,)
                ).fetchone()
                if expense:
                    category, amount = expense
                    sm.cursor.execute("DELETE FROM registro_spese WHERE id = ?", (expense_id,))
                    cur_val = sm.get_value_by_attrANDmonth(selected_month, category)
                    sm.update_value_by_attrANDmonth(selected_month, category, cur_val - amount)
                    sm.commit()
                    flash("Expense deleted successfully!", "success")
                    expenses = sm.get_expenses_for_month(selected_month)
                else:
                    flash("Expense not found.", "error")

    return render_template('undo_expense.html',
        expenses=expenses,
        selected_month=selected_month,
        months=months,
        visible_users=visible_users, target_user=target_user,
        current_year=year)


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
                m = e[1][:7]
                month_counts[m] = month_counts.get(m, 0) + 1

    return render_template('show_history.html',
        entries=entries, start_date=start, end_date=end,
        month_counts=month_counts,
        months=months,
        selected_months=selected_months,
        visible_users=visible_users, target_user=target_user,
        active_view='history',
        current_year=year)


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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=True)
