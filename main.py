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

    if request.method == 'POST':
        month_raw = request.form.get('month')
        action = request.form.get('action', '')

        if month_raw and month_raw.isdigit():
            month_num = int(month_raw)
            month_name = MONTHS_INDEX[month_num]
            month = f"{year}_{month_name}"

        if action == 'select_month':
            ensure_month(sm, month)
            data = sm.get_data_by_month(month)
            return render_template('add_expense.html', month=month,
                month_name=month_name, data_row=data, current_year=year)

        if action == 'add':
            attribute = request.form.get('attribute')
            value = round(float(request.form.get('value', 0)), 1)
            nota = request.form.get('nota', '').strip() or 'N/A'
            sm.insert_expense_in_registry(attribute, nota, value)
            old_val = sm.get_value_by_attrANDmonth(month, attribute)
            sm.update_value_by_attrANDmonth(month, attribute, old_val + value)
            sm.commit()
            flash("Expense added successfully!", "success")
            return render_template('add_expense.html', done=True,
                attribute=attribute, value=value, current_year=year)

    return render_template('add_expense.html', month=None, current_year=year)


# ---- Compare Months ----

@app.route('/compare-months', methods=['GET', 'POST'])
def compare_months():
    sm = get_db()
    year = session.get('year')
    months = sm.get_months_list(year)

    if request.method == 'POST':
        selected = request.form.getlist('selected_months')
        if not selected:
            flash("Select at least one month.", "error")
        else:
            months_data = sm.get_months_data(selected)
            sorted_months = sorted(selected)
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
                    rows.append((attr, values, mean))
            return render_template('compare_months.html', months=months,
                selected=selected, sorted_months=sorted_months,
                rows=rows, current_year=year)

    return render_template('compare_months.html', months=months,
        selected=[], rows=None, current_year=year)


# ---- Track Attribute ----

@app.route('/track-attribute', methods=['GET', 'POST'])
def track_attribute():
    sm = get_db()
    year = session.get('year')
    months = sm.get_months_list(year)

    selected_attr = None
    month_values = None
    if request.method == 'POST':
        selected_attr = request.form.get('attribute')
        month_values = sm.get_attribute_through_months(selected_attr, months)

    return render_template('track_attribute.html',
        selected_attr=selected_attr, month_values=month_values,
        current_year=year)


# ---- Undo Expense ----

@app.route('/undo-expense', methods=['GET', 'POST'])
def undo_expense():
    sm = get_db()
    year = session.get('year')

    if request.method == 'POST':
        month_raw = request.form.get('month')
        action = request.form.get('action', '')

        if month_raw and month_raw.isdigit():
            month_num = int(month_raw)
            month = f"{year}_{MONTHS_INDEX[month_num]}"

        if action == 'show':
            last = sm.get_last_expense()
            if not last:
                flash("No expenses to undo.", "error")
                return render_template('undo_expense.html',
                    last_expense=None, current_year=year)
            return render_template('undo_expense.html',
                last_expense=last, month=month, current_year=year)

        if action == 'undo':
            last = sm.get_last_expense()
            if last:
                expense_id, data, category, nota, amount = last
                sm.cursor.execute("DELETE FROM registro_spese WHERE id = ?", (expense_id,))
                cur_val = sm.get_value_by_attrANDmonth(month, category)
                sm.update_value_by_attrANDmonth(month, category, cur_val - amount)
                sm.commit()
                flash("Expense undone successfully!", "success")
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

    return render_template('show_history.html',
        entries=entries, start_date=start, end_date=end, current_year=session.get('year'))


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
