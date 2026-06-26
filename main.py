from utils import *
from settings import *
from sqlManager import *
from datetime import datetime
import os, signal


def handle_sigint_aux(signum, frame):
    print("\n\n! Process interrupted. Exiting...")
    sql_manager.close()
    exit(0)

# handle sigint
signal.signal(signal.SIGINT, handle_sigint_aux)


def show_main_menu():
    """Display main menu options"""
    print("\n=== MAIN MENU ===")
    print("1. Add expense to a specific month")
    print("2. Compare months")
    print("3. Track attribute through months")
    print("4. Undo last expense (Beta)") #TODO: it undo always the last expense, not the last expense of the selected month. Fix it.
    print("5. Exit")
    print()

def select_year_and_month(sql_manager):
    """Allow user to select a year and month"""
    year = select_year()
    print_months()
    month_id = ""
    while not (month_id.isdigit() and 1 <= int(month_id) <= 12):
        month_id = input(f"> Select a month (1-12): ")
    month_name = MONTHS_INDEX[int(month_id)]
    month = f"{year}_{month_name}"
    
    if not sql_manager.check_month_exists(month):
        print("[+] Month non present in the database.")
        print("[+] Adding month entry...")
        try:
            sql_manager.add_month_entry(month)
            print("[+] Month entry added successfully.")
        except Exception as e:
            print(f"[!] Error adding month entry: {e}")
    
    return month

def compare_months_flow(sql_manager):
    """Flow for comparing multiple months"""
    year = select_year()
    months = sql_manager.get_months_list(year)
    if not months:
        print("[!] No months found for this year.")
        return
    
    print("\n[+] Available months :")
    for i, month in enumerate(months):
        print(f"  {i+1} {month}")
    
    count = ""
    while not (count.isdigit() and 2 <= int(count) <= len(months)):
        count = input(f"> How many months do you want to compare? (2-{len(months)}): ")
    
    selected = []
    for n in range(1, int(count) + 1):
        idx = ""
        while not (idx.isdigit() and 1 <= int(idx) <= len(months)):
            idx = input(f"> Select month {n} (1-{len(months)}): ")
        m = months[int(idx) - 1]
        if m in selected:
            print("[!] Month already selected.")
            n -= 1
        else:
            selected.append(m)

    months_data = sql_manager.get_months_data(selected)
    print_months_comparison(months_data, SQL_ATTRIBUTES_ALL)

def track_attribute_flow(sql_manager):
    """Flow for tracking an attribute through months"""
    year = select_year()
    months = sql_manager.get_months_list(year)
    if not months:
        print("[!] No months found for this year.")
        return
    
    print("\n[+] Choose an attribute to track:")
    for i, attr in enumerate(SQL_ATTRIBUTES_EDITABLE):
        print(f"  {i} {attr}")
    
    attr_id = ""
    while not (attr_id.isdigit() and 0 <= int(attr_id) < len(SQL_ATTRIBUTES_EDITABLE)):
        attr_id = input(f"> Insert a value between 0 and {len(SQL_ATTRIBUTES_EDITABLE)-1}: ")
    attribute = SQL_ATTRIBUTES_EDITABLE[int(attr_id)]
    
    month_values = sql_manager.get_attribute_through_months(attribute, months)
    print_attribute_tracking(attribute, month_values)

def undo_expense_flow(sql_manager):
    """Flow for undoing the last expense"""
    month = select_year_and_month(sql_manager)
    last_expense = sql_manager.get_last_expense()
    if not last_expense:
        print("[!] No expenses to undo.")
        return
    
    expense_id, category, nota, amount = last_expense
    print(f"\n[+] Last expense:")
    print(f"    ID: {expense_id}")
    print(f"    Category: {category}")
    print(f"    Note: {nota}")
    print(f"    Amount: {amount}")
    
    confirm = input("\n> Are you sure you want to undo this expense? (y/n): ")
    if confirm.lower() == 'y':
        sql_manager.undo_last_expense(month)
        sql_manager.commit()
        print("[+] Expense undone successfully!")
    else:
        print("[+] Undo cancelled.")

def add_expense_flow(sql_manager):
    """Flow for adding expenses"""
    month = select_year_and_month(sql_manager)
    
    # Display current month values
    data = sql_manager.get_data_by_month(month)
    print_row_table(data, SQL_ATTRIBUTES_ALL)
    
    insert = True
    while insert:
        print("\n[+] Choose an attribute to update")
        for i in range(0, len(SQL_ATTRIBUTES_EDITABLE)):
            print(f"  {i} {SQL_ATTRIBUTES_EDITABLE[i]}")
        attribute_id = ""
        while not (attribute_id.isdigit() and 0 <= int(attribute_id) <= len(SQL_ATTRIBUTES_EDITABLE)-1):
            attribute_id = input(f"> Insert a value between 0 and {len(SQL_ATTRIBUTES_EDITABLE)-1}: ")
        attribute = SQL_ATTRIBUTES_EDITABLE[int(attribute_id)]
        print(f"[+] Selected attribute: {attribute}\n")

        # ADD EXPENSE VALUE
        while True:
            value = input("> Insert a numeric value: ")
            try:
                value = float(value)
                value = round(value, 1)
                break
            except:
                print("[!] Invalid value. Please insert a numeric value.")

        # ADD NOTA
        nota = input("> Add a note for this expense (enter to skip): ")
        nota = 'N/A' if nota == "" else nota
        sql_manager.insert_expense_in_registry(attribute, nota, value)
        print("[+] Expense added in the registry")
        
        # UPDATE ATTRIBUTE
        old_value = sql_manager.get_value_by_attrANDmonth(month, attribute)
        new_value = old_value + value
        sql_manager.update_value_by_attrANDmonth(month, attribute, new_value)
        print(f"[+] Attribute '{attribute}' updated to: {sql_manager.get_value_by_attrANDmonth(month, attribute)}")

        # ASK TO CONTINUE
        choice = input("\n> Do you want to insert another expense? (y/n): ")
        if choice.lower() != 'y':
            insert = False


def main(args : list):
    print(f"\n=== HOUSE EXPENSES TRACKER {datetime.now().year} ===\n")
    global sql_manager

    ## CHECK DATABASE PATH FILE EXISTS
    if not os.path.exists("./database_path"):
        print("[!] Database path file not found. Please insert the database path here and the file will be created automatically.\n")
        db_path = input(">Insert database path (PATH/data.db): ").strip()
        print()
        open("./database_path", "w").write(db_path)
    
    DATABASE = open("./database_path", "r").read().strip()


    ## CHECK DATABASE HAS BEEN CREATED
    if not os.path.isfile(f"{DATABASE}"):
        print("Database not found. Please run 'sqlite3 data.db < init.sql' and 'sqlite3 data.db < populate.sql' to create the database.")
        exit(1)


    ## INSTANTIATE SQL-MANAGER
    try: 
        sql_manager = SQLManager(DATABASE)
    except Exception as e:
        print(f"! Error connecting to the database: {e}")
        return


    # MAIN MENU LOOP
    while True:
        show_main_menu()
        menu_choice = input("> Select an option (1-5): ")
        
        if menu_choice == "1":
            add_expense_flow(sql_manager)
            sql_manager.commit()
        elif menu_choice == "2":
            compare_months_flow(sql_manager)
        elif menu_choice == "3":
            track_attribute_flow(sql_manager)
        elif menu_choice == "4":
            undo_expense_flow(sql_manager)
            sql_manager.commit()
        elif menu_choice == "5":
            print("[+] Exiting...")
            break
        else:
            print("[!] Invalid option. Please try again.")
        
    
    ## CLEAN-UP 
    sql_manager.close()



if __name__ == "__main__":
    args = handle_args()
    main(args)
