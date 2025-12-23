import flask, os
from sqlManager import *
from settings import *
from datetime import datetime

app = flask.Flask(__name__)

@app.route('/update')
def update_value():

    ## CHECK DATABASE HAS BEEN CREATED
    if not os.path.isfile(f"./{DATABASE}"):
        print("Database not found. Please run 'sqlite3 data.db < init.sql' and 'sqlite3 data.db < populate.sql' to create the database.")
        exit(1)

    # GET PARAMETERS FROM URL
    category = flask.request.args.get('category')
    month = flask.request.args.get('month')
    amount = flask.request.args.get('amount')
    note = flask.request.args.get('note', 'N/A')  # Default to 'N/A' if not provided

    ## INPUT VALIDATION
    if not category or not month or not amount:  # mandatory parameters
        return "Error: 'category', 'month', and 'amount' are required parameters.", 400
    if not amount.isnumeric():
        return "Error: 'amount' must be a numeric value.", 400
    if month.upper() not in MONTHS_INDEX.values():
        return f"Error: '{month}' is not a valid month.", 400
    if category not in SQL_ATTRIBUTES_EDITABLE:
        return f"Error: '{category}' is not a valid editable attribute.", 400

    amount = round(float(amount), 1)
    month = f"{datetime.now().year}_{month.upper()}"  

    ## DATABASE UPDATE
    sql_manager = SQLManager(DATABASE)
    old_value = sql_manager.get_value_by_attrANDmonth(month, category)
    new_value = old_value + amount
    sql_manager.update_value_by_attrANDmonth(month, category, new_value)
    sql_manager.insert_expense_in_registry(category, note, amount)
    
    ## CLEAN-UP
    sql_manager.commit()
    sql_manager.close()

    return f"Category: {category}, Month: {month}, Amount: {amount}, Note: {note}"





app.run(host='localhost', port=8080, debug=True)