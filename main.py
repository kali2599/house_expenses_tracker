from utils import *
from settings import *
from sqlManager import *
import os


def main(args : list):

    ## CHECK DATABASE HAS BEEN CREATED
    if not os.path.isfile(f"./{DATABASE}"):
        print("Database not found. Please run 'sqlite3 data.db < init.sql' to create the database.")
        exit(1)

    ## INSTANTIATE SQL-MANAGER
    try: 
        sql_manager = SQLManager(DATABASE)
    except Exception as e:
        print(f"! Error connecting to the database: {e}")
        return


    ## PRINT DATA AND SELECT MONTH
    print("Select a month:")
    print_months()
    month_id = ""
    while not (month_id.isdigit() and 1 <= int(month_id) <= 12):
        month_id = input("> Insert a month between 1 and 12: ")
    month = MONTHS_INDEX[int(month_id)]

    if args.verbose:
        data = sql_manager.get_data_by_month(month)
        print_row_table(data, SQL_ATTRIBUTES_ALL)


    ## CHOSE ATTRIBUTE
    print("\nChoose an attribute to update:")
    for i in range(0, len(SQL_ATTRIBUTES_EDITABLE)):
        print(f"  {i} {SQL_ATTRIBUTES_EDITABLE[i]}")
    attribute_id = ""
    while not (attribute_id.isdigit() and 0 <= int(attribute_id) <= len(SQL_ATTRIBUTES_EDITABLE)-1):
        attribute_id = input(f"> Insert a value between 0 and {len(SQL_ATTRIBUTES_EDITABLE)-1}: ")
    attribute = SQL_ATTRIBUTES_EDITABLE[int(attribute_id)]
    print(f"Selected attribute: {attribute}\n")


    ## ADD EXPENSE (UPDATE ATTRIBUTE)
    print("Inserting new expense:")
    while True:
        value = input("> Insert a numeric value: ")
        if value.startswith("-") and value[1:].isdigit():
            value = round(float(value), 1)
            break
        elif value.isdigit():
            value = round(float(value), 1)
            break
        else:
            print("! Invalid value. Please insert a numeric value.")

    choice = input("Do you want to add a note for this expense? (y/n): ")
    if choice.lower() == 'y':
        nota = input("Insert your nota: ")
    else:
        nota = "N/A"
    sql_manager.insert_expense_in_registry(attribute, nota, value)
    print("Expense added in the registry")
    
    old_value = sql_manager.get_value_by_attrANDmonth(month, attribute)
    new_value = old_value + value
    sql_manager.update_value_by_attrANDmonth(month, attribute, new_value)
    print(f"Attribute '{attribute}' updated to: {sql_manager.get_value_by_attrANDmonth(month, attribute)}")
    
    if args.verbose:
        data = sql_manager.get_data_by_month(month)
        print_row_table(data, SQL_ATTRIBUTES_ALL)


    ## CLEAN-UP 
    sql_manager.commit()
    sql_manager.close()


if __name__ == "__main__":
    args = handle_args()
    main(args) 