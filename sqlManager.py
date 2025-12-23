import sqlite3

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

    def commit(self):
        self.conn.commit()
    
    def close(self):
        self.conn.close()
