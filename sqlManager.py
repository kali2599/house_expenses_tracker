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
        return data

    def update_value_by_attrANDmonth(self, month, attribute, new_value):
        self.cursor.execute(f"UPDATE spese_mensili SET {attribute} =  {new_value} WHERE mese = '{month}'")

    def insert_expense_in_registry(self, category, nota, amount):
        self.cursor.execute(f"INSERT INTO registro_spese (categoria, nota, importo) VALUES ('{category}', '{nota}', {amount})")

    def check_month_exists(self, month) -> bool:
        data = self.cursor.execute(f"SELECT COUNT(*) FROM spese_mensili WHERE mese = '{month}'").fetchone()[0]
        return data > 0
    
    def add_month_entry(self, month):
        columns_info = self.cursor.execute("PRAGMA table_info(spese_mensili)").fetchall()  # Get column names from the table schema
        columns = [col[1] for col in columns_info]  
        columns_str = ', '.join(columns)
        values_str = ', '.join(['0'] * len(columns))
        values_str = f"'{month}', " + values_str
        query = f"INSERT INTO spese_mensili ({columns_str}) VALUES ({values_str})"
        self.cursor.execute(query)
        self.commit()  

    def commit(self):
        self.conn.commit()
    
    def close(self):
        self.conn.close()


if __name__ == "__main__":
    db = open("./database_path", "r").read().strip()
    sql_manager = SQLManager(db)
    sql_manager.add_month_entry("2026_APRILE")
    sql_manager.close()