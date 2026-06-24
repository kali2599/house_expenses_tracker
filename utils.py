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

        :param row: a tuple representing the row values from SQLite
        :param attributes: list of column names in correct order
    """
    if len(row) != len(attributes):
        print("Error: row data length and attribute list length do not match.")
        return 
    

    max_attr_len = max(len(attr) for attr in attributes) # compute max width for alignment
    head_color = settings.MONTH_HEADER_COLOR
    print(f"\n{head_color}--- ROW {row[0]} DATA -------\033[0m")
    for attr, value in zip(attributes, row):
        if attr == "mese":
            continue
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
        print(f"{color}{attr.ljust(max_attr_len)} : {round(float(value),2)}\033[0m")
    print(f"{head_color}--------------------------------\033[0m\n")


def print_months_comparison(months_data, attributes):
    """
        Prints a comparison table of multiple months.

        :param months_data: dictionary with month names as keys and row tuples as values
        :param attributes: list of column names
    """
    if not months_data:
        print("[!] No data to compare.")
        return

    max_attr_len = max(len(attr) for attr in attributes)
    max_month_len = max(len(month) for month in months_data.keys())
    head_color = settings.MONTH_HEADER_COLOR
    
    # Print header
    print(f"\n{head_color}--- MONTHS COMPARISON -------\033[0m")
    print(f"\n{' ' * max_attr_len} | {' | '.join(month.ljust(12) for month in months_data.keys())}")
    print("-" * (max_attr_len + 5 + (15 * len(months_data))))
    
    # Print each attribute
    for attr_idx, attr in enumerate(attributes):
        if attr == "mese":
            continue
        
        # Determine color based on attribute type
        if attr == 'entrate':
            color = settings.ENTRATE_COLOR
        elif attr == 'uscite_variabili':
            color = settings.USCITE_VARIABILI_COLOR
        elif attr == 'uscite_fisse':
            color = settings.USCITE_FISSE_COLOR
        elif attr == 'uscite_totali':
            color = settings.USCITE_TOTALI_COLOR
        elif attr == 'delta':
            color = settings.DELTA_RED_COLOR
        else:
            color = "\033[0m"
        
        row_str = f"{color}{attr.ljust(max_attr_len)}\033[0m | "
        for month, data in months_data.items():
            if data:
                value = round(float(data[attr_idx]), 2)
                row_str += f"{str(value).ljust(12)} | "
        print(row_str.rstrip(" | "))
    
    print(f"{head_color}---------------------------------------------\033[0m\n")


def print_attribute_tracking(attribute, month_values):
    """
        Prints a tracking table for a single attribute across months.

        :param attribute: the attribute name being tracked
        :param month_values: dictionary with month names as keys and values
    """
    if not month_values:
        print("[!] No data to display.")
        return

    head_color = settings.MONTH_HEADER_COLOR
    print(f"\n{head_color}--- TRACKING: {attribute} -------\033[0m")
    
    # Determine color based on attribute type
    if attribute == 'entrate':
        color = settings.ENTRATE_COLOR
    elif attribute == 'uscite_variabili':
        color = settings.USCITE_VARIABILI_COLOR
    elif attribute == 'uscite_fisse':
        color = settings.USCITE_FISSE_COLOR
    elif attribute == 'uscite_totali':
        color = settings.USCITE_TOTALI_COLOR
    elif attribute == 'delta':
        color = settings.DELTA_RED_COLOR
    else:
        color = "\033[0m"
    
    print(f"\n{color}Month{''.ljust(15)}Value\033[0m")
    print("-" * 30)
    
    for month in sorted(month_values.keys()):
        value = month_values[month]
        print(f"{color}{month.ljust(20)}{value}\033[0m")
    
    print(f"{head_color}--------------------\033[0m\n")
