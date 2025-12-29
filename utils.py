import settings
from argparse import ArgumentParser


def handle_args():
    """
        handle command-line arguments
    """
    parser = ArgumentParser(description="House expenses tracker")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose mode")
    args = parser.parse_args()
    return args


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
    color = settings.PRINT_ROW_MONTH_COLOR
    print(f"\n{color}--- ROW {row[0]} DATA -------\033[0m")
    for attr, value in zip(attributes, row):
        print(f"{attr.ljust(max_attr_len)} : {value}")
    print(f"{color}--------------------------------\033[0m\n")