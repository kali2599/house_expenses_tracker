from utils import *
from settings import *



def show_main_menu():
    """Display main menu options"""
    print("\n=== MAIN MENU ===")
    print("1. Add expense to a specific month")
    print("2. Compare months")
    print("3. Track attribute through months")
    print("4. Undo last expense (Beta)") 
    print("5. Show expense history")
    print("6. Exit")
    print()


################################
#### MENU OPTIONS FUNCTIONS ####
################################


## OPTIONS 1 : add expense for a specific month
def add_expense_option(sql_manager):
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
                value = round(float(value),1)
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


## OPTIONS 2: compare months expenses
def compare_months_option(sql_manager):
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


## OPTION 3: track a specific attribute over time
def track_attribute_option(sql_manager):
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


## OPTIONS 4: undo last expense (BETA)
def undo_expense_option(sql_manager):
    #TODO: link last expense to the selected month, not globally. 
    #To do it is it necessary to alter the table registro_spese to include the month
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


## OPTIONS 5: show expense history
def show_expense_history_option(sql_manager):
    """Flow for viewing expense history with optional date range"""
    start_raw = input("> Start date (YYYY-MM-DD, ENTER for no bound): ").strip()
    end_raw = input("> End date (YYYY-MM-DD, ENTER for no bound): ").strip()
    start = parse_date_bound(start_raw, "start")
    end = parse_date_bound(end_raw, "end")
    if start_raw and not start:
        return
    if end_raw and not end:
        return
    entries = sql_manager.get_registro_entries(start, end)
    print_registro_entries(entries)



