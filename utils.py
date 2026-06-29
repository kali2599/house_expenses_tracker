import calendar
import settings
from argparse import ArgumentParser
from datetime import datetime


##########################################
#### UTILITY FUNCTIONS FOR USER INPUT ####
##########################################

def select_year() -> int:
    """
        Prompts the user to select a year.

        :return: selected year as integer
    """
    year_input = input("> Insert year (e.g., 2024): ")
    try:
        year = int(year_input)
    except:
        print("[!] Invalid year. Using current year.")
    print()

    return year


def select_year_and_month(sql_manager, year):
    """Allow user to select a month for the given year"""
    print_months()
    month_id = ""
    while not (month_id.isdigit() and 1 <= int(month_id) <= 12):
        month_id = input(f"> Select a month (1-12): ")
    month_name = settings.MONTHS_INDEX[int(month_id)]
    month = f"{year}_{month_name}"
    
    if not sql_manager.check_month_exists(month):
        print("[+] Month non present in the database.")
        print("[+] Adding month entry...")
        try:
            sql_manager.add_month_entry(month)
            print("[+] Month entry added successfully.")
        except Exception as e:
            print(f"[!] Error adding month entry: {e}")
    
    return month



############################
##### GETTER FUNCTIONS #####
############################

def get_color_for_attribute(attribute, value=None):
    """
        Get the appropriate color for an attribute.
        
        :param attribute: the attribute name
        :param value: the value of the attribute (optional, needed for delta)
        :return: ANSI color code
    """
    if attribute == 'entrate':
        return settings.ENTRATE_COLOR
    elif attribute == 'uscite_variabili':
        return settings.USCITE_VARIABILI_COLOR
    elif attribute == 'uscite_fisse':
        return settings.USCITE_FISSE_COLOR
    elif attribute == 'uscite_totali':
        return settings.USCITE_TOTALI_COLOR
    elif attribute == 'delta':
        if value is not None:
            return settings.DELTA_RED_COLOR if value < 0 else settings.DELTA_GREEN_COLOR
        return ""
    else:
        return "\033[0m" # No color




################################
###### PRINTING FUNCTIONS ######
################################

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
        Prints a comparison table of multiple months with proper colors.
        Months are sorted and each value is colored according to its attribute type.

        :param months_data: dictionary with month names as keys and row tuples as values
        :param attributes: list of column names
    """
    if not months_data:
        print("[!] No data to compare.")
        return

    max_attr_len = max(len(attr) for attr in attributes)
    head_color = settings.MONTH_HEADER_COLOR
    sorted_months = months_data.keys()
    
    # Print header
    col_width = 14
    print(f"\n{head_color}--- MONTHS COMPARISON -------\033[0m")
    print(f"\n{' ' * max_attr_len} | {' | '.join(month.ljust(col_width) for month in sorted_months)} | {'Mean'.ljust(col_width)}")
    len_border = max_attr_len + 5 + (15 * len(months_data)) + 15
    print("-" * len_border)
    
    # Print each attribute
    for attr_idx, attr in enumerate(attributes):
        if attr == "mese":
            continue
        
        # Get color for attribute
        color = get_color_for_attribute(attr)
        
        row_str = f"{color}{attr.ljust(max_attr_len)}\033[0m | "
        values = []
        for month in sorted_months:
            data = months_data[month]
            if data:
                value = round(float(data[attr_idx]), 2)
                values.append(value)
                cell_color = get_color_for_attribute(attr, value)
                row_str += f"{cell_color}{str(value).ljust(col_width)}\033[0m | "
        mean = round(sum(values) / len(values), 2) if values else 0
        cell_color = get_color_for_attribute(attr, mean)
        row_str += f"{cell_color}{str(mean).ljust(col_width)}\033[0m"
        print(row_str)
    
    print(f"{head_color}{ '-' * len_border }\033[0m\n")


def print_registro_entries(entries):
    """
        Prints registro_spese entries in a table.
        
        :param entries: list of tuples (id, data, categoria, nota, importo)
    """
    if not entries:
        print("[!] No entries found.")
        return

    note_lens = [len(e[3]) for e in entries]
    max_nota_len = max(max(note_lens), 20)

    print(f"\n{'ID'.ljust(4)} | {'Date'.ljust(20)} | {'Category'.ljust(16)} | {'Note'.ljust(max_nota_len)} | {'Amount'.rjust(8)}")
    print("-" * (4 + 3 + 20 + 3 + 16 + 3 + max_nota_len + 3 + 8))
    head_color = settings.MONTH_HEADER_COLOR
    month_counts = {}
    for entry in entries:
        m = entry[1][:7]
        month_counts[m] = month_counts.get(m, 0) + 1
    prev_month = None
    for entry in entries:
        eid, data, categoria, nota, importo = entry
        cur_month = data[:7]
        if cur_month != prev_month:
            year = int(data[:4])
            month_num = int(data[5:7])
            month_name = settings.MONTHS_INDEX[month_num]
            count = month_counts[cur_month]
            print(f"{head_color}--- {year} {month_name} ({count}) ---\033[0m")
            prev_month = cur_month
        importo = round(float(importo), 2)
        print(f"{str(eid).ljust(4)} | {data.ljust(20)} | {categoria.ljust(16)} | {nota.ljust(max_nota_len)} | {str(importo).rjust(8)}")
    print()


def print_attribute_tracking(attribute, month_values):
    """
        Prints a tracking table for a single attribute across months with colors.
        - Red color for highest value
        - Green color for lowest value
        - Months are sorted

        :param attribute: the attribute name being tracked
        :param month_values: dictionary with month names as keys and values
    """
    if not month_values:
        print("[!] No data to display.")
        return

    # Find max and min values
    max_value = max(month_values.values())
    min_value = min(month_values.values())

    head_color = settings.MONTH_HEADER_COLOR
    print(f"\n{head_color}--- TRACKING: {attribute} -------\033[0m")
    
    print(f"\n{head_color}Month{''.ljust(15)}Value\033[0m")
    print("-" * 30)
    
    for month in month_values.keys():
        value = month_values[month]
        
        # Color based on highest/lowest
        if value == max_value:
            color = settings.DELTA_RED_COLOR  # Red for highest
        elif value == min_value:
            color = settings.DELTA_GREEN_COLOR  # Green for lowest
        else:
            color = "\033[0m"  # Default
        
        print(f"{color}{month.ljust(20)}{value}\033[0m")
    
    print(f"{head_color}--------------------\033[0m\n")



#################################
#### MISCELLANEOUS FUNCTIONS ####
#################################

def parse_date_bound(raw, bound):
    """
        Parse a relaxed date input into YYYY-MM-DD or None.
        - ""          -> None
        - "2026"       -> "2026-01-01" (start) / "2026-12-31" (end)
        - "2026-3"     -> "2026-03-01" (start) / last day of March (end)
        - "2026-03-15" -> as-is
    """
    if not raw:
        return None

    parts = raw.split("-")
    if len(parts) == 1:
        year = parts[0]
        if len(year) != 4 or not year.isdigit():
            print(f"[!] Invalid year: {year}")
            return None
        if bound == "start":
            return f"{year}-01-01"
        else:
            return f"{year}-12-31"

    if len(parts) == 2:
        year, month = parts
        if len(year) != 4 or not year.isdigit() or not month.isdigit():
            print(f"[!] Invalid date: {raw}")
            return None
        month = int(month)
        if month < 1 or month > 12:
            print(f"[!] Invalid month: {month}")
            return None
        if bound == "start":
            return f"{year}-{month:02d}-01"
        else:
            last = calendar.monthrange(int(year), month)[1]
            return f"{year}-{month:02d}-{last:02d}"

    if len(parts) == 3:
        year, month, day = parts
        if not year.isdigit() or not month.isdigit() or not day.isdigit():
            print(f"[!] Invalid date: {raw}")
            return None
        year, month, day = int(year), int(month), int(day)
        if month < 1 or month > 12:
            print(f"[!] Invalid month: {month}")
            return None
        if day < 1 or day > 31:
            print(f"[!] Invalid day: {day}")
            return None
        return f"{year:04d}-{month:02d}-{day:02d}"

    print(f"[!] Invalid date format: {raw}")
    return None


def handle_args():
    """
        handle command-line arguments

        :return: parsed arguments
    """
    parser = ArgumentParser(description="House expenses tracker")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose mode")
    args = parser.parse_args()
    return args