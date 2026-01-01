import flask, os
from sqlManager import *
from settings import *
from datetime import datetime
import utils


app = flask.Flask(__name__)

@app.route('/update', methods=['POST'])
def update_value():

    try:
        sql_manager = SQLManager(DATABASE)
        print("[+] Connected to database successfully.")
    except Exception as e:
        return f"[!] Could not connect to database. Error: {str(e)}", 500
    
    print(flask.request.form)

    # GET PARAMETERS FROM REQUEST FORM
    category = flask.request.form.get('category')
    month = flask.request.form.get('month')
    amount = flask.request.form.get('amount')
    note = flask.request.form.get('note', 'N/A')  # Default to 'N/A' if not provided

    ## INPUT VALIDATION
    if not category or not month or not amount:  # mandatory parameters
        return "Error: 'category', 'month', and 'amount' are required parameters.", 400
    
    print(f"[+] Received parameters - Category: {category}, Month: {month.upper()}, Amount: {amount}, Note: {note}")

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
    args = utils.handle_args()

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

    #TODO: add argparse for host and port. Use default if not provided
    
    verbose = args.verbose
    host = args.host
    port = args.port    
    if verbose:
        print(f"[+] Starting server on {host}:{port}...\n")
    app.run(host=host, port=port, debug=True)