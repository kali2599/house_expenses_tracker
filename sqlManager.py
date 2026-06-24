import sqlite3, settings

class SQLManager:
    def __init__(self, database):
        self.conn = sqlite3.connect(database)
        self.cursor = self.conn.cursor()

    def get_data_by_month(self, month):
        data = self.cursor.execute(f"SELECT * FROM spese_mensili WHERE mese = '{month}'").fetchall()[0]
        return data

    def get_value_by_attrANDmonth(self, month, attribute):
        data = self.cursor.execute(f"SELECT {attribute} FROM spese_mensili WHERE mese = '{month}'").fetchone()[0]
        return round(float(data),2)

    def update_value_by_attrANDmonth(self, month, attribute, new_value):
        self.cursor.execute(f"UPDATE spese_mensili SET {attribute} =  {new_value} WHERE mese = '{month}'")

    def insert_expense_in_registry(self, category, nota, amount):
        self.cursor.execute(f"INSERT INTO registro_spese (categoria, nota, importo) VALUES ('{category}', '{nota}', {amount})")

    def check_month_exists(self, month) -> bool:
        data = self.cursor.execute(f"SELECT COUNT(*) FROM spese_mensili WHERE mese = '{month}'").fetchone()[0]
        return data > 0
    
    def add_month_entry(self, month):
        columns_info = self.cursor.execute("PRAGMA table_info(spese_mensili)").fetchall()  
        # Get column names from the table schema
        columns = [col[1] for col in columns_info]  
        #print(f"[DEBUG] Columns in spese_mensili: {columns}")  # Debug print to check column names
        columns_str = ', '.join(columns)
        values_str = ', '.join(['0'] * (len(columns) - 1)) # -1 to excluding the 'month' column
        values_str = f"'{month}', " + values_str
        query = f"INSERT INTO spese_mensili ({columns_str}) VALUES ({values_str})"
        self.cursor.execute(query)
        self.commit()  

    def commit(self):
        self.conn.commit()
    
    def close(self):
        self.conn.close()

    # FEATURE 1: Compare different months
    def get_months_list(self, year=None):
        """Get list of all months available in database, optionally filtered by year, sorted temporally"""
        if year:
            query = f"SELECT mese FROM spese_mensili WHERE mese LIKE '{year}_%' ORDER BY mese"
        else:
            query = "SELECT mese FROM spese_mensili ORDER BY mese"
        data = self.cursor.execute(query).fetchall()
        months = [month[0] for month in data]
        # Sort temporally: extract year and month, then sort
        months_sorted = sorted(months, key=lambda x: (int(x.split('_')[0]), self._get_month_number(x.split('_')[1])))
        return months_sorted

    def _get_month_number(self, month_name):
        """Convert Italian month name to number for proper sorting"""
        months_map = {
            'GENNAIO': 1, 'FEBBRAIO': 2, 'MARZO': 3, 'APRILE': 4,
            'MAGGIO': 5, 'GIUGNO': 6, 'LUGLIO': 7, 'AGOSTO': 8,
            'SETTEMBRE': 9, 'OTTOBRE': 10, 'NOVEMBRE': 11, 'DICEMBRE': 12
        }
        return months_map.get(month_name, 0)

    def compare_months(self, month1, month2):
        """Compare two months and return their values for all attributes"""
        data1 = self.get_data_by_month(month1)
        data2 = self.get_data_by_month(month2)
        return data1, data2

    # FEATURE 2: Track single attribute through several months
    def get_attribute_through_months(self, attribute, months):
        """Get a specific attribute value across multiple months"""
        result = {}
        for month in months:
            if self.check_month_exists(month):
                value = self.get_value_by_attrANDmonth(month, attribute)
                result[month] = value
        return result

    # FEATURE 3: Undo functionality
    def get_last_expense(self):
        """Get the last expense inserted"""
        data = self.cursor.execute("SELECT id, categoria, nota, importo FROM registro_spese ORDER BY id DESC LIMIT 1").fetchone()
        return data

    def delete_last_expense(self):
        """Delete the last expense and return its details"""
        last_expense = self.get_last_expense()
        if last_expense:
            expense_id, category, nota, amount = last_expense
            self.cursor.execute(f"DELETE FROM registro_spese WHERE id = {expense_id}")
            return last_expense
        return None

    def undo_last_expense(self, month):
        """Undo the last expense: remove it from registry and subtract from monthly total"""
        last_expense = self.get_last_expense()
        if last_expense:
            expense_id, category, nota, amount = last_expense
            # Delete from registry
            self.cursor.execute(f"DELETE FROM registro_spese WHERE id = {expense_id}")
            # Subtract from monthly total
            current_value = self.get_value_by_attrANDmonth(month, category)
            new_value = current_value - amount
            self.update_value_by_attrANDmonth(month, category, new_value)
            return last_expense
        return None


if __name__ == "__main__":
    db = open("./database_path", "r").read().strip()
    sql_manager = SQLManager(db)
    sql_manager.add_month_entry("2026_APRILE")
    sql_manager.close()
