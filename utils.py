import settings
from argparse import ArgumentParser
from datetime import  datetime

def handle_args():
    """
        handle command-line arguments

        :return: parsed arguments
    """
    parser = ArgumentParser(description="House expenses tracker")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose mode")
    args = parser.parse_args()
    return args


def select_year() -> int:
    """
        Prompts the user to select a year.

        :return: selected year as integer
    """
    year = datetime.now().year
    year_input = input(f"> Update current year? (ENTER/n): ")
    if year_input.lower() == 'y' or year_input == '':
        print()
    else:
        year_input = input("> Insert year (e.g., 2024): ")
        try:
            year = int(year_input)
        except:
            print("[!] Invalid year. Using current year.")
        print()

    return year


def print_months():
    """
        Prints the list of months.
    """
    for i in range(1, 13):
        print(f"- {i} {settings.MONTHS_INDEX[i]}")


def print_row_table(row, attributes):
    """
        Prints a clean table of attributes and values.

        :param row: a tuple representing the row from SQLite
        :param attributes: list of column names in correct order
    """
    if len(row) != len(attributes):
        print("Error: row length and attribute list length do not match.")
        return

    max_attr_len = max(len(attr) for attr in attributes) # compute max width for alignment
    head_color = settings.MONTH_HEADER_COLOR
    print(f"\n{head_color}--- ROW {row[0]} DATA -------\033[0m")
    for attr, value in zip(attributes, row):
        if attr == 'entrate':
            color = settings.ENTRATE_COLOR
        elif attr == 'uscite_variabili':
            color = settings.USCITE_VARIABILI_COLOR
        elif attr == 'uscite_fisse':
            color = settings.USCITE_FISSE_COLOR
        elif attr == 'uscite_totali':
            color = settings.USCITE_TOTALI_COLOR
        elif attr == 'delta':
            color = settings.DELTA_RED_COLOR if value < 0 else settings.DELTA_GREEN_COLOR
        else:
            color = "\033[0m"
        print(f"{color}{attr.ljust(max_attr_len)} : {value}\033[0m")
    print(f"{head_color}--------------------------------\033[0m\n")