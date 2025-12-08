from utils import *
from settings import *
from sqlManager import *

not_manually_editable = ['mese', 'uscite_variabili', 'uscite_fisse', 'uscite_totali', 'delta']
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
        month_id = input("> ")
    month = months_maps[int(month_id)]
    data = sql_manager.get_data_by_month(month)
    print_row_table(data, SQL_ATTRIBUTES)


    # CHOSE ATTRIBUTE
    # TODO:exclude month, uscite, delta, entrate
    print("Choose an attribute to update:")
    for i in range(0, len(SQL_ATTRIBUTES)):
        if SQL_ATTRIBUTES[i] not in not_manually_editable:
            print(f"  {i} {SQL_ATTRIBUTES[i]}")
    attribute_id = ""
    while not (attribute_id.isdigit() and 0 <= int(attribute_id) <= len(SQL_ATTRIBUTES)-1):
        attribute_id = input("> ")
    attribute = SQL_ATTRIBUTES[int(attribute_id)]
    print(attribute)

    # UPDATE ATTRIBUTE
    #TODO: handle negative values
    #TODO: update the 3 'uscite_*' attributes and 'delta'
    print("Insert the new expense:")
    value = ""
    while not value.isdigit():
        value = input("> ")
    value = int(value)
    old_value = sql_manager.get_value_by_attrANDmonth(month, attribute)
    new_value = old_value + value
    sql_manager.update_value_by_attrANDmonth(month, attribute, new_value)
    print(f"Attribute '{attribute}' updated to: {sql_manager.get_value_by_attrANDmonth(month, attribute)}")

    # clean-up 
    sql_manager.commit()
    sql_manager.close()

if __name__ == "__main__":
    main() 