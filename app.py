import flask, os
from sqlManager import *
from settings import *
from datetime import datetime

app = flask.Flask(__name__)

@app.route('/update')
def update_value():

    try:
        sql_manager = SQLManager(DATABASE)
        print("[+] Connected to database successfully.")
    except Exception as e:
        return f"[!] Could not connect to database. Error: {str(e)}", 500
    
    # GET PARAMETERS FROM URL
    category = flask.request.args.get('category')
    month = flask.request.args.get('month')
    amount = flask.request.args.get('amount')
    note = flask.request.args.get('note', 'N/A')  # Default to 'N/A' if not provided

    ## INPUT VALIDATION
    if not category or not month or not amount:  # mandatory parameters
        return "Error: 'category', 'month', and 'amount' are required parameters.", 400
    
    if month.upper() not in MONTHS_INDEX.values():
        return f"Error: '{month}' is not a valid month.", 400
    
    if category not in SQL_ATTRIBUTES_EDITABLE:
        return f"Error: '{category}' is not a valid editable attribute.", 400
    
    try:
        amount = float(amount)
        amount = round(amount, 1)
    except:
        return "[!] Invalid value. Please insert a numeric value.", 400


    ## DATABASE UPDATE
    month = f"{datetime.now().year}_{month.upper()}"  
    old_value = sql_manager.get_value_by_attrANDmonth(month, category)
    new_value = old_value + amount
    sql_manager.update_value_by_attrANDmonth(month, category, new_value)
    sql_manager.insert_expense_in_registry(category, note, amount)
    
    ## CLEAN-UP
    sql_manager.commit()
    sql_manager.close()

    return f"Category: {category}, Month: {month}, Amount: {amount}, Note: {note}"






if __name__ == "__main__":

    global DATABASE
    
    if not os.path.exists("./database_path"):
        print("[!] Database path file not found. Please insert the database path here and the file will be created automatically.\n")
        db_path = input(">Insert database path (PATH/data.db): ").strip()
        print()
        open("./database_path", "w").write(db_path)
    
    DATABASE = open("./database_path", "r").read().strip()

    ## CHECK DATABASE HAS BEEN CREATED
    if not os.path.isfile(f"{DATABASE}"):
        print(f"[!]Database not found.\nPlease run 'sqlite3 {DATABASE}< init.sql' and 'sqlite3 {DATABASE}< populate.sql' to create the database.")
        exit(1)

    print(f"[+] Loading sql database from: {DATABASE}\n")

    app.run(host=HOST, port=PORT, debug=True)