import settings

def print_row_table(row, attributes):
    """
    Prints a clean table of attributes and values.

    :param row: a tuple representing the row from SQLite
    :param attributes: list of column names in correct order
    """
    if len(row) != len(attributes):
        print("Error: row length and attribute list length do not match.")
        return

    # compute max width for alignment
    max_attr_len = max(len(attr) for attr in attributes)

    print(f"\n--- ROW {row[0]} DATA -------")
    for attr, value in zip(attributes, row):
        print(f"{attr.ljust(max_attr_len)} : {value}")
    print("------------------------------\n")