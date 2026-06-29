import sqlite3, settings

class SQLManager:
    
    def __init__(self, database):
        self.conn = sqlite3.connect(database)
        self.cursor = self.conn.cursor()


    def _validate_attribute(self, attribute):
        if attribute not in settings.SQL_ATTRIBUTES_ALL:
            raise ValueError(f"Invalid column name: {attribute}")


    def get_data_by_month(self, month):
        data = self.cursor.execute("SELECT * FROM spese_mensili WHERE mese = ?", (month,)).fetchone()
        return data


    def get_value_by_attrANDmonth(self, month, attribute):
        self._validate_attribute(attribute)
        data = self.cursor.execute(f"SELECT {attribute} FROM spese_mensili WHERE mese = ?", (month,)).fetchone()[0]
        return round(float(data),2)


    def update_value_by_attrANDmonth(self, month, attribute, new_value):
        self._validate_attribute(attribute)
        self.cursor.execute(f"UPDATE spese_mensili SET {attribute} = ? WHERE mese = ?", (new_value, month))


    def insert_expense_in_registry(self, category, nota, amount):
        self.cursor.execute("INSERT INTO registro_spese (categoria, nota, importo) VALUES (?, ?, ?)", (category, nota, amount))


    def check_month_exists(self, month) -> bool:
        data = self.cursor.execute("SELECT COUNT(*) FROM spese_mensili WHERE mese = ?", (month,)).fetchone()[0]
        return data > 0
    

    def add_month_entry(self, month):
        columns_info = self.cursor.execute("PRAGMA table_info(spese_mensili)").fetchall()  
        columns = [col[1] for col in columns_info]  
        columns_str = ', '.join(columns)
        placeholders = ', '.join(['?'] * len(columns))
        values = (month,) + tuple([0] * (len(columns) - 1))
        query = f"INSERT INTO spese_mensili ({columns_str}) VALUES ({placeholders})"
        self.cursor.execute(query, values)
        self.commit()  


    def commit(self):
        self.conn.commit()
    

    def close(self):
        self.conn.close()


    def get_months_list(self, year=None):
        """Get list of all months available in database, optionally filtered by year, sorted temporally"""
        if year:
            data = self.cursor.execute("SELECT mese FROM spese_mensili WHERE mese LIKE ? ORDER BY mese", (f'{year}_%',)).fetchall()
        else:
            data = self.cursor.execute("SELECT mese FROM spese_mensili ORDER BY mese").fetchall()
        months = [month[0] for month in data]
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

    def get_months_data(self, months):
        """Get full row data for a list of months, returns {month: tuple}"""
        return {month: self.get_data_by_month(month) for month in months}


    def get_attribute_through_months(self, attribute, months):
        """Get a specific attribute value across multiple months"""
        self._validate_attribute(attribute)
        result = {}
        for month in months:
            if self.check_month_exists(month):
                value = self.get_value_by_attrANDmonth(month, attribute)
                result[month] = value
        return result

    
    def get_registro_entries(self, start_date=None, end_date=None):
        """Get entries from registro_spese filtered by optional date range (YYYY-MM-DD)"""
        query = "SELECT id, data, categoria, nota, importo FROM registro_spese"
        params = []
        conditions = []
        if start_date:
            conditions.append("date(data) >= ?")
            params.append(start_date)
        if end_date:
            conditions.append("date(data) <= ?")
            params.append(end_date)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY data"
        return self.cursor.execute(query, params).fetchall()


    def get_last_expense(self):
        """Get the last expense inserted"""
        data = self.cursor.execute("SELECT id, data, categoria, nota, importo FROM registro_spese ORDER BY id DESC LIMIT 1").fetchone()
        return data


    def delete_last_expense(self):
        """Delete the last expense and return its details"""
        last_expense = self.get_last_expense()
        if last_expense:
            expense_id, expense_data, category, nota, amount = last_expense
            self.cursor.execute("DELETE FROM registro_spese WHERE id = ?", (expense_id,))
            return last_expense
        return None


    def undo_last_expense(self, month):
        """Undo the last expense: remove it from registry and subtract from monthly total"""
        last_expense = self.get_last_expense()
        if last_expense:
            expense_id, expense_data, category, nota, amount = last_expense
            self.cursor.execute("DELETE FROM registro_spese WHERE id = ?", (expense_id,))
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
