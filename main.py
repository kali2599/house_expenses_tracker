from utils import *
from settings import *
from sqlManager import *

def main():
    # Instantiate SQL-manager object
    sql_manager = SQLManager(DATABASE)

    print("Select a month:")
    print(" 1 GENNAIO")
    print(" 2 FEBBRAIO")
    print(" 3 MARZO")
    print(" 4 APRILE")
    print(" 5 MAGGIO")
    print(" 6 GIUGNO")
    print(" 7 LUGLIO")
    print(" 8 AGOSTO")
    print(" 9 SETTEMBRE")
    print(" 10 OTTOBRE ")
    print(" 11 NOVEMBRE")
    print(" 12 DICEMBRE")
    
    # PRINT DATA MONTH
    month_id = ""
    while not (month_id.isdigit() and 1 <= int(month_id) <= 12):
        month_id = input("> Insert a month between 1 and 12: ")
    month = MONTHS_MAP[int(month_id)]
    data = sql_manager.get_data_by_month(month)
    print_row_table(data, SQL_ATTRIBUTES_ALL)


    # CHOSE ATTRIBUTE
    print("Choose an attribute to update:")
    for i in range(0, len(SQL_ATTRIBUTES_EDITABLE)):
        print(f"  {i} {SQL_ATTRIBUTES_EDITABLE[i]}")
    attribute_id = ""
    while not (attribute_id.isdigit() and 0 <= int(attribute_id) <= len(SQL_ATTRIBUTES_EDITABLE)-1):
        attribute_id = input(f"> Insert a value between 0 and {len(SQL_ATTRIBUTES_EDITABLE)-1}: ")
    attribute = SQL_ATTRIBUTES_EDITABLE[int(attribute_id)]
    print(f"Selected attribute: {attribute}\n")


    # UPDATE ATTRIBUTE
    #TODO: handle negative values
    print("Inserting new expense:")
    value = ""
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
    
    old_value = sql_manager.get_value_by_attrANDmonth(month, attribute)
    new_value = old_value + value
    sql_manager.update_value_by_attrANDmonth(month, attribute, new_value)
    print(f"Attribute '{attribute}' updated to: {sql_manager.get_value_by_attrANDmonth(month, attribute)}")
    data = sql_manager.get_data_by_month(month)
    print_row_table(data, SQL_ATTRIBUTES_ALL)

    # clean-up 
    sql_manager.commit()
    sql_manager.close()

if __name__ == "__main__":
    main() 