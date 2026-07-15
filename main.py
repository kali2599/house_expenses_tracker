from flask import Flask, render_template, request, session, redirect, url_for, flash
from datetime import datetime
import os

from settings import *
from sqlManager import SQLManager
from utils import parse_date_bound, get_color_for_attribute


def get_db():
    global _sql_manager
    if '_sql_manager' not in globals() or _sql_manager is None:
        db_path = open("./database_path", "r").read().strip()
        if not os.path.isfile(db_path):
            print(f"Database not found: {db_path}")
            exit(1)
        _sql_manager = SQLManager(db_path)
    return _sql_manager


app = Flask(__name__)
app.secret_key = os.urandom(24)

app.jinja_env.globals.update(zip=zip)
app.jinja_env.globals.update(get_color_for_attribute=get_color_for_attribute)
app.jinja_env.globals.update(MONTHS_INDEX=MONTHS_INDEX)
app.jinja_env.globals.update(SQL_ATTRIBUTES_ALL=SQL_ATTRIBUTES_ALL)
app.jinja_env.globals.update(SQL_ATTRIBUTES_EDITABLE=SQL_ATTRIBUTES_EDITABLE)


def ensure_month(sm, month):
    if not sm.check_month_exists(month):
        sm.add_month_entry(month)


@app.before_request
def ensure_year():
    if 'year' not in session:
        session['year'] = datetime.now().year


@app.route('/')
def index():
    return redirect(url_for('add_expense'))


# ---- Add Expense ----

@app.route('/add-expense', methods=['GET', 'POST'])
def add_expense():
    sm = get_db()
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
            data = sm.get_data_by_month(month)
            return render_template('add_expense.html', month=month,
                month_name=month_name, month_num=month_num, data_row=data,
                done=True, inserted=[(attribute, value, nota)], current_year=year)

        if action == 'add_all':
            attributes = request.form.getlist('attribute[]')
            values = request.form.getlist('value[]')
            notes = request.form.getlist('nota[]')
            inserted = []
            for attr, val_raw, nota_raw in zip(attributes, values, notes):
                val = round(float(val_raw), 1)
                nota = nota_raw.strip() or 'N/A'
                mese_data = f"{month_num:02d}-{month.split('_')[0]}"
                sm.insert_expense_in_registry(attr, nota, val, mese_data)
                old_val = sm.get_value_by_attrANDmonth(month, attr)
                sm.update_value_by_attrANDmonth(month, attr, old_val + val)
                inserted.append((attr, val, nota))
            sm.commit()
            flash(f"{len(inserted)} spese aggiunte!", "success")
            data = sm.get_data_by_month(month)
            return render_template('add_expense.html', month=month,
                month_name=month_name, month_num=month_num, data_row=data,
                done=True, inserted=inserted, current_year=year)

    ensure_month(sm, month)
    data = sm.get_data_by_month(month)
    return render_template('add_expense.html', month=month,
        month_name=month_name, month_num=month_num, data_row=data,
        current_year=year)


# ---- Data Analysis / Comparison ----

@app.route('/data-analysis/comparison', methods=['GET', 'POST'])
def data_analysis_comparison():
    sm = get_db()
    year = session.get('year')
    all_sorted = sm.get_months_list(year)

    if request.method == 'POST':
        selected = request.form.getlist('selected_months')
        if not selected:
            flash("Seleziona almeno un mese.", "error")
            selected = all_sorted[-3:] if len(all_sorted) >= 3 else all_sorted[:]
    else:
        from datetime import datetime
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
            if len(values) >= 2 and values[0] != 0:
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
        active_view='comparison', current_year=year)


# ---- Data Analysis / Tracking ----

@app.route('/data-analysis/tracking')
def data_analysis_tracking():
    sm = get_db()
    year = session.get('year')
    all_sorted = sm.get_months_list(year)

    all_months_data = sm.get_months_data(all_sorted)
    tracking_data = {}
    for attr in SQL_ATTRIBUTES_EDITABLE:
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
        months=all_sorted, active_view='tracking', current_year=year)


# ---- Redirects ----

@app.route('/compare-months', methods=['GET', 'POST'])
def compare_months_redirect():
    return redirect(url_for('data_analysis_comparison'))

@app.route('/track-attribute', methods=['GET', 'POST'])
def track_attribute_redirect():
    return redirect(url_for('data_analysis_tracking'))


# ---- Undo Expense ----

@app.route('/undo-expense', methods=['GET', 'POST'])
def undo_expense():
    sm = get_db()
    year = session.get('year')

    month_num = None
    month = None

    if request.method == 'POST':
        month_raw = request.form.get('month')
        action = request.form.get('action', '')

        if month_raw:
            if '_' in month_raw:
                month = month_raw
                month_name = month.split('_')[1]
                month_num = int(request.form.get('month_num', 0))
            elif month_raw.isdigit():
                month_num = int(month_raw)
                month_name = MONTHS_INDEX[month_num]
                month = f"{year}_{month_name}"

        if action == 'show':
            if not month_num:
                flash("Select a month.", "error")
                return render_template('undo_expense.html',
                    last_expense=None, current_year=year)
            last = sm.get_last_expense_for_month(month)
            if not last:
                flash("No expenses to undo for this month.", "error")
                return render_template('undo_expense.html',
                    last_expense=None, current_year=year)
            return render_template('undo_expense.html',
                last_expense=last, month=month, month_num=month_num,
                current_year=year)

        if action == 'undo':
            if not month:
                flash("Invalid month.", "error")
                return render_template('undo_expense.html',
                    last_expense=None, current_year=year)
            last = sm.get_last_expense_for_month(month)
            if last:
                expense_id, ts, category, nota, amount, mese_data = last
                sm.cursor.execute("DELETE FROM registro_spese WHERE id = ?", (expense_id,))
                cur_val = sm.get_value_by_attrANDmonth(month, category)
                sm.update_value_by_attrANDmonth(month, category, cur_val - amount)
                sm.commit()
                flash("Expense undone successfully!", "success")
            else:
                flash("No expenses to undo for this month.", "error")
            return render_template('undo_expense.html',
                done=True, current_year=year)

    return render_template('undo_expense.html',
        last_expense=None, current_year=year)


# ---- Show History ----

@app.route('/show-history', methods=['GET', 'POST'])
def show_history():
    sm = get_db()

    start = end = None
    entries = None
    month_counts = {}
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
        current_year=session.get('year'))


# ---- Change Year ----

@app.route('/change-year', methods=['GET', 'POST'])
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
    if not os.path.exists("./database_path"):
        print("Database path file not found. Create it with the path to your .db file.")
        exit(1)
    _sql_manager = None
    app.run(host="0.0.0.0", port=PORT, debug=True)
