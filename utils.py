import settings
from argparse import ArgumentParser


def handle_args():
    """
        handle command-line arguments
    """
    parser = ArgumentParser(description="House expenses tracker")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose mode")
    parser.add_argument("-H", "--host", type=str, default=settings.HOST, help="IP address to run the server on")
    parser.add_argument("-p", "--port", type=int, default=settings.PORT, help="Port number to run the server on")
    args = parser.parse_args()
    return args


def print_months():
    """
        Prints the list of months.
    """
    for i in range(1, 13):
        print(f"{i} {settings.MONTHS_INDEX[i]}")


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
    print(f"\n--- ROW {row[0]} DATA -------")
    for attr, value in zip(attributes, row):
        print(f"{attr.ljust(max_attr_len)} : {value}")
    print("------------------------------\n")