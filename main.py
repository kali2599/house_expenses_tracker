from utils import *
from settings import *
from sqlManager import *
from datetime import datetime
import os, signal



def handle_sigint_aux(signum, frame):
    print("\n\n! Process interrupted. Exiting...")
    sql_manager.close()
    exit(0)


def main(args : list):
    year = datetime.now().year
    print(f"\n=== HOUSE EXPENSES TRACKER {year} ===\n")
    global sql_manager

    ## CHECK DATABASE HAS BEEN CREATED
    if not os.path.isfile(f"./{DATABASE}"):
        print("Database not found. Please run 'sqlite3 data.db < init.sql' and 'sqlite3 data.db < populate.sql' to create the database.")
        exit(1)

    ## INSTANTIATE SQL-MANAGER
    try: 
        sql_manager = SQLManager(DATABASE)
    except Exception as e:
        print(f"! Error connecting to the database: {e}")
        return

    ## HANDLE SIGINT
    signal.signal(signal.SIGINT, handle_sigint_aux)


    ## PRINT DATA AND SELECT MONTH
    
    print_months()
    month_id = ""
    while not (month_id.isdigit() and 1 <= int(month_id) <= 12):
        month_id = input(f"> Select a month (1-12): ")
    month = MONTHS_INDEX[int(month_id)]
    month = f"{year}_{month}"

    if args.verbose:
        data = sql_manager.get_data_by_month(month)
        print_row_table(data, SQL_ATTRIBUTES_ALL)

    insert = True
    while insert:
        ## CHOSE ATTRIBUTE
        print("\n[+] Choose an attribute to update")
        for i in range(0, len(SQL_ATTRIBUTES_EDITABLE)):
            print(f"  {i} {SQL_ATTRIBUTES_EDITABLE[i]}")
        attribute_id = ""
        while not (attribute_id.isdigit() and 0 <= int(attribute_id) <= len(SQL_ATTRIBUTES_EDITABLE)-1):
            attribute_id = input(f"> Insert a value between 0 and {len(SQL_ATTRIBUTES_EDITABLE)-1}: ")
        attribute = SQL_ATTRIBUTES_EDITABLE[int(attribute_id)]
        print(f"[+] Selected attribute: {attribute}\n")


        ## ADD EXPENSE (UPDATE ATTRIBUTE)
        while True:
            value = input("> Insert a numeric value: ")
            try:
                value = float(value)
                value = round(value, 1)
                break
            except:
                print("[!] Invalid value. Please insert a numeric value.")


        nota = input("> Add a note for this expense (enter to skip): ")
        nota = 'N/A' if nota == "" else nota
        sql_manager.insert_expense_in_registry(attribute, nota, value)
        print("[+] Expense added in the registry")
        
        old_value = sql_manager.get_value_by_attrANDmonth(month, attribute)
        new_value = old_value + value
        sql_manager.update_value_by_attrANDmonth(month, attribute, new_value)
        print(f"[+] Attribute '{attribute}' updated to: {sql_manager.get_value_by_attrANDmonth(month, attribute)}")

        ## ASK TO CONTINUE
        choice = input("\n> Do you want to insert another expense? (y/n): ")
        if choice.lower() != 'y':
            insert = False
        
    if args.verbose:
        data = sql_manager.get_data_by_month(month)
        print_row_table(data, SQL_ATTRIBUTES_ALL)

    
    ## CLEAN-UP 
    sql_manager.commit()
    sql_manager.close()


if __name__ == "__main__":
    args = handle_args()
    main(args) 