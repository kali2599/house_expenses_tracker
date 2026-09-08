import sqlite3
from config import settings
from datetime import datetime

class SQLManager:
    
    def __init__(self, database):
        self.conn = sqlite3.connect(database)
        self.cursor = self.conn.cursor()
        table = self.cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='registro_spese'"
        ).fetchone()
        if table:
            try:
                self.cursor.execute("ALTER TABLE registro_spese ADD COLUMN is_default INTEGER DEFAULT 0")
            except sqlite3.OperationalError:
                pass
            self.cursor.execute(
                "UPDATE registro_spese SET is_default = 1 WHERE nota = 'Default' AND is_default = 0"
            )
            self.conn.commit()


    def _validate_attribute(self, attribute):
        columns = self.get_column_names()
        if attribute not in columns:
            raise ValueError(f"Invalid column name: {attribute}")


    def get_column_names(self):
        """Return actual column names from spese_mensili table."""
        return [col[1] for col in self.cursor.execute("PRAGMA table_info(spese_mensili)").fetchall()]


    def get_user_attributes(self):
        """Return user's attribute classification."""
        columns = self.get_column_names()
        system = settings.SQL_SYSTEM_COLUMNS
        variabili = [c for c in columns if c not in system and c not in ('uscite_variabili', 'uscite_fisse')]
        editable = ['entrate'] + [c for c in columns if c not in system]
        return {
            'all': columns,
            'editable': editable,
            'variabili': [c for c in columns if c not in system and c not in settings.DEFAULT_FISSE and c != 'uscite_variabili' and c != 'uscite_fisse' and c != 'uscite_totali' and c != 'delta' and c != 'entrate'],
            'fisse': [c for c in columns if c not in system and c not in settings.DEFAULT_VARIABILI and c not in ('entrate', 'uscite_variabili', 'uscite_fisse', 'uscite_totali', 'delta')],
        }


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


    def insert_expense_in_registry(self, category, nota, amount, mese_data=None, is_default=0):
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.cursor.execute(
            "INSERT INTO registro_spese (timestamp, categoria, nota, importo, data, is_default) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (ts, category, nota, amount, mese_data, is_default))


    def check_month_exists(self, month) -> bool:
        data = self.cursor.execute("SELECT COUNT(*) FROM spese_mensili WHERE mese = ?", (month,)).fetchone()[0]
        return data > 0
    

    def add_month_entry(self, month, default_fisse=None, default_notes=None):
        columns_info = self.cursor.execute("PRAGMA table_info(spese_mensili)").fetchall()
        columns = [col[1] for col in columns_info]
        columns_str = ', '.join(columns)
        placeholders = ', '.join(['?'] * len(columns))
        default_fisse = default_fisse or {}
        default_notes = default_notes or {}
        values = [month]
        for col in columns[1:]:
            if col in default_fisse:
                try:
                    values.append(float(default_fisse[col]))
                except (TypeError, ValueError):
                    values.append(0.0)
            else:
                values.append(0)
        query = f"INSERT INTO spese_mensili ({columns_str}) VALUES ({placeholders})"
        self.cursor.execute(query, tuple(values))
        if default_fisse:
            year, month_name = month.split('_')
            month_num = self._get_month_number(month_name)
            mese_data = f"{month_num:02d}-{year}"
            for col, val in default_fisse.items():
                if val and float(val) != 0.0:
                    note = default_notes.get(col, 'Default')
                    self.insert_expense_in_registry(col, note, float(val), mese_data, is_default=1)
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
        """Get entries from registro_spese filtered by optional date range on `data` column (YYYY-MM-DD or YYYY-MM)"""
        query = "SELECT id, timestamp, categoria, nota, importo, data FROM registro_spese"
        params = []
        conditions = []
        if start_date:
            conditions.append("substr(data, 4, 4) || '-' || substr(data, 1, 2) >= ?")
            params.append(start_date[:7])
        if end_date:
            conditions.append("substr(data, 4, 4) || '-' || substr(data, 1, 2) <= ?")
            params.append(end_date[:7])
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY substr(data, 4, 4) || '-' || substr(data, 1, 2) DESC, timestamp DESC"
        return self.cursor.execute(query, params).fetchall()


    def get_last_expense(self):
        """Get the last expense inserted"""
        data = self.cursor.execute("SELECT id, timestamp, categoria, nota, importo, data FROM registro_spese ORDER BY id DESC LIMIT 1").fetchone()
        return data

    def get_last_expense_for_month(self, month_key):
        """Get the last expense for a specific month (month_key = YYYY_MESE)"""
        year, month_name = month_key.split('_')
        month_num = self._get_month_number(month_name)
        mese_data = f"{month_num:02d}-{year}"
        return self.cursor.execute(
            "SELECT id, timestamp, categoria, nota, importo, data "
            "FROM registro_spese WHERE data = ? ORDER BY id DESC LIMIT 1",
            (mese_data,)
        ).fetchone()

    def get_expenses_for_month(self, month_key):
        """Get all expenses for a specific month (month_key = YYYY_MESE), newest first"""
        year, month_name = month_key.split('_')
        month_num = self._get_month_number(month_name)
        mese_data = f"{month_num:02d}-{year}"
        return self.cursor.execute(
            "SELECT id, timestamp, categoria, nota, importo, data, is_default "
            "FROM registro_spese WHERE data = ? ORDER BY id DESC",
            (mese_data,)
        ).fetchall()


    def delete_last_expense(self):
        """Delete the last expense and return its details"""
        last_expense = self.get_last_expense()
        if last_expense:
            expense_id, expense_ts, category, nota, amount, expense_data = last_expense
            self.cursor.execute("DELETE FROM registro_spese WHERE id = ?", (expense_id,))
            return last_expense
        return None


    def undo_last_expense(self, month):
        """Undo the last expense: remove it from registry and subtract from monthly total"""
        last_expense = self.get_last_expense()
        if last_expense:
            expense_id, expense_ts, category, nota, amount, expense_data = last_expense
            self.cursor.execute("DELETE FROM registro_spese WHERE id = ?", (expense_id,))
            current_value = self.get_value_by_attrANDmonth(month, category)
            new_value = current_value - amount
            self.update_value_by_attrANDmonth(month, category, new_value)
            return last_expense
        return None


    def update_expense_in_registry(self, expense_id, new_nota, new_importo):
        """Update nota and importo of a registry expense. Returns (categoria, old_importo, data) or None."""
        row = self.cursor.execute(
            "SELECT categoria, importo, data FROM registro_spese WHERE id = ?",
            (expense_id,)
        ).fetchone()
        if not row:
            return None
        old_categoria, old_importo, data = row
        self.cursor.execute(
            "UPDATE registro_spese SET nota = ?, importo = ? WHERE id = ?",
            (new_nota, new_importo, expense_id)
        )
        return old_categoria, old_importo, data


    def _drop_all_triggers(self):
        """Drop all computed-column triggers for spese_mensili."""
        for name in ['update_uscite_variabili', 'update_uscite_fisse',
                     'update_uscite_totali', 'update_delta']:
            self.cursor.execute(f"DROP TRIGGER IF EXISTS {name}")


    def _recreate_triggers(self, variabili, fisse):
        """Recreate the computed-column triggers with the provided attribute lists."""
        self._drop_all_triggers()
        variabili_update = ' + '.join([f'(new."{v}" - old."{v}")' for v in variabili])
        fisse_update = ' + '.join([f'(new."{f}" - old."{f}")' for f in fisse])
        variabili_trigger_cols = ', '.join(variabili)
        fisse_trigger_cols = ', '.join(fisse)

        self.cursor.executescript(f"""
CREATE TRIGGER update_uscite_variabili AFTER UPDATE OF {variabili_trigger_cols}
ON spese_mensili
FOR EACH ROW
BEGIN
UPDATE spese_mensili
SET uscite_variabili = ROUND(uscite_variabili + {variabili_update}, 1)
WHERE mese = old.mese;
END;

CREATE TRIGGER update_uscite_fisse AFTER UPDATE OF {fisse_trigger_cols}
ON spese_mensili
FOR EACH ROW
BEGIN
UPDATE spese_mensili
SET uscite_fisse = ROUND(uscite_fisse + {fisse_update}, 1)
WHERE mese = old.mese;
END;

CREATE TRIGGER update_uscite_totali AFTER UPDATE OF uscite_variabili, uscite_fisse
ON spese_mensili
FOR EACH ROW
BEGIN
UPDATE spese_mensili
SET uscite_totali = ROUND(uscite_totali + (new.uscite_variabili - old.uscite_variabili) + (new.uscite_fisse - old.uscite_fisse), 1)
WHERE mese = old.mese;
END;

CREATE TRIGGER update_delta AFTER UPDATE OF uscite_totali, entrate
ON spese_mensili
FOR EACH ROW
BEGIN
UPDATE spese_mensili
SET delta = ROUND(entrate - uscite_totali, 1)
WHERE mese = old.mese;
END;
""")
        self.commit()


    def add_attribute(self, name, attr_type, variabili, fisse):
        """Add a new variabile or fisso column and recreate triggers."""
        name = name.strip()
        columns = self.get_column_names()
        system = set(['mese', 'entrate', 'uscite_variabili', 'uscite_fisse',
                      'uscite_totali', 'delta'])
        if not name:
            raise ValueError("Nome attributo vuoto.")
        if name in columns:
            raise ValueError(f"L'attributo '{name}' esiste già.")
        if name in system:
            raise ValueError(f"'{name}' è una colonna di sistema.")

        self.cursor.execute(f'ALTER TABLE spese_mensili ADD COLUMN "{name}" REAL DEFAULT 0')

        if attr_type == 'variabile':
            variabili.append(name)
        else:
            fisse.append(name)
        self._recreate_triggers(variabili, fisse)
        self.commit()


    def remove_attribute(self, name, from_month=None):
        """Deactivate a variabile or fisso column from a month onward.

        The column is never dropped (past data must be preserved). It is zeroed
        in every existing month >= from_month so trigger-maintained totals
        (uscite_fisse/variabili/totali/delta) remain consistent.
        """
        name = name.strip()
        columns = self.get_column_names()
        system = set(['mese', 'entrate', 'uscite_variabili', 'uscite_fisse',
                      'uscite_totali', 'delta'])
        if name in system:
            raise ValueError(f"'{name}' è una colonna di sistema e non può essere rimossa.")
        if name not in columns:
            raise ValueError(f"L'attributo '{name}' non esiste.")

        if from_month:
            affected = [m for m in self.get_all_months() if self._month_tuple(m) >= self._month_tuple(from_month)]
            if affected:
                placeholders = ', '.join(['?'] * len(affected))
                self.cursor.execute(
                    f'UPDATE spese_mensili SET "{name}" = 0 WHERE mese IN ({placeholders})',
                    tuple(affected)
                )
                self.commit()


    def get_all_months(self):
        """Return every month key present in spese_mensili, no ordering guarantee."""
        return [r[0] for r in self.cursor.execute("SELECT mese FROM spese_mensili").fetchall()]


    def month_is_pristine(self, month):
        """A month is pristine if its row is all zeros and no expenses were ever recorded for it."""
        row = self.get_data_by_month(month)
        if not row:
            return True
        columns = self.get_column_names()
        for col, val in zip(columns[1:], row[1:]):
            if val not in (None, 0, 0.0):
                return False
        year, month_name = month.split('_')
        month_num = self._get_month_number(month_name)
        mese_data = f"{month_num:02d}-{year}"
        count = self.cursor.execute(
            "SELECT COUNT(*) FROM registro_spese WHERE data = ?", (mese_data,)
        ).fetchone()[0]
        return count == 0


    @staticmethod
    def _month_tuple(key):
        """Convert a 'YYYY_MESE' month key into a sortable (year, month_number) tuple."""
        m = key.split('_')
        if len(m) != 2:
            return (0, 0)
        year, month_name = m
        months_map = {
            'GENNAIO': 1, 'FEBBRAIO': 2, 'MARZO': 3, 'APRILE': 4,
            'MAGGIO': 5, 'GIUGNO': 6, 'LUGLIO': 7, 'AGOSTO': 8,
            'SETTEMBRE': 9, 'OTTOBRE': 10, 'NOVEMBRE': 11, 'DICEMBRE': 12
        }
        return (int(year), months_map.get(month_name.upper(), 0))


def generate_user_db_sql(variabili, fisse):
    """Generate SQL to create a user's spese_mensili table with custom columns and triggers."""
    variabili_cols = ', '.join([f'"{v}" REAL' for v in variabili])
    fisse_cols = ', '.join([f'"{f}" REAL' for f in fisse])

    variabili_update = ' + '.join([f'(new."{v}" - old."{v}")' for v in variabili])
    fisse_update = ' + '.join([f'(new."{f}" - old."{f}")' for f in fisse])

    variabili_trigger_cols = ', '.join(variabili)
    fisse_trigger_cols = ', '.join(fisse)

    sql = f"""
CREATE TABLE registro_spese (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
    categoria TEXT,
    nota TEXT,
    importo REAL,
    data TEXT,
    is_default INTEGER DEFAULT 0
);

CREATE TABLE spese_mensili (
    mese TEXT PRIMARY KEY,
    entrate REAL,
    {variabili_cols},
    uscite_variabili REAL,
    {fisse_cols},
    uscite_fisse REAL,
    uscite_totali REAL,
    delta REAL
);

CREATE TRIGGER update_uscite_variabili AFTER UPDATE OF {variabili_trigger_cols}
ON spese_mensili
FOR EACH ROW
BEGIN
UPDATE spese_mensili
SET uscite_variabili = ROUND(uscite_variabili + {variabili_update}, 1)
WHERE mese = old.mese;
END;

CREATE TRIGGER update_uscite_fisse AFTER UPDATE OF {fisse_trigger_cols}
ON spese_mensili
FOR EACH ROW
BEGIN
UPDATE spese_mensili
SET uscite_fisse = ROUND(uscite_fisse + {fisse_update}, 1)
WHERE mese = old.mese;
END;

CREATE TRIGGER update_uscite_totali AFTER UPDATE OF uscite_variabili, uscite_fisse
ON spese_mensili
FOR EACH ROW
BEGIN
UPDATE spese_mensili
SET uscite_totali = ROUND(uscite_totali + (new.uscite_variabili - old.uscite_variabili) + (new.uscite_fisse - old.uscite_fisse), 1)
WHERE mese = old.mese;
END;

CREATE TRIGGER update_delta AFTER UPDATE OF uscite_totali, entrate
ON spese_mensili
FOR EACH ROW
BEGIN
UPDATE spese_mensili
SET delta = ROUND(entrate - uscite_totali, 1)
WHERE mese = old.mese;
END;
"""
    return sql
