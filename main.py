from datetime import datetime
import os, signal

from utils import *
from settings import *
from sqlManager import *
from menu_options import *


def handle_sigint_aux(signum, frame):
    print("\n\n! Process interrupted. Exiting...")
    sql_manager.close()
    exit(0)

# handle sigint
signal.signal(signal.SIGINT, handle_sigint_aux)



def main(args : list):
    print(f"\n=== HOUSE EXPENSES TRACKER {datetime.now().year} ===\n")
    global sql_manager

    ## CHECK DATABASE PATH FILE EXISTS
    if not os.path.exists("./database_path"):
        print("[!] Database path file not found. Please insert the database path here and the file will be created automatically.\n")
        db_path = input("> Insert database path (PATH/data.db): ").strip()
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
        menu_choice = input("> Select an option (1-6): ")
        
        if menu_choice == "1":
            add_expense_option(sql_manager)
            sql_manager.commit()

        elif menu_choice == "2":
            compare_months_option(sql_manager)

        elif menu_choice == "3":
            track_attribute_option(sql_manager)

        elif menu_choice == "4":
            undo_expense_option(sql_manager)
            sql_manager.commit()

        elif menu_choice == "5":
            show_expense_history_option(sql_manager)

        elif menu_choice == "6":
            print("[+] Exiting...")
            break

        else:
            print("[!] Invalid option. Please try again.")
        
    
    ## CLEAN-UP 
    sql_manager.close()



if __name__ == "__main__":
    args = handle_args()
    main(args)
