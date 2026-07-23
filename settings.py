
### MISCELLANEOUS
MONTHS_INDEX = {1:"GENNAIO", 2:"FEBBRAIO", 3:"MARZO", 4:"APRILE", 5:"MAGGIO", 6:"GIUGNO", 7:"LUGLIO", 8:"AGOSTO", 9:"SETTEMBRE", 10:"OTTOBRE", 11:"NOVEMBRE", 12:"DICEMBRE"}

### COLORS
MONTH_HEADER_COLOR = "\033[96m"
ENTRATE_COLOR = "\033[94m"
USCITE_VARIABILI_COLOR = "\033[93m"
USCITE_FISSE_COLOR = "\033[93m"
USCITE_TOTALI_COLOR = "\033[91m"
DELTA_RED_COLOR = "\033[91m"
DELTA_GREEN_COLOR = "\033[92m"

### SQL attributes — system (always present, not editable by user)
SQL_SYSTEM_COLUMNS = ['mese', 'entrate', 'uscite_variabili', 'uscite_fisse', 'uscite_totali', 'delta']

### SQL attributes — user defaults (used at signup)
DEFAULT_VARIABILI = ['spesa', 'pasti_fuori', 'svago', 'shopping', 'inaspettate', 'varie', 'salute', 'vacanze']
DEFAULT_FISSE = ['abbonamenti', 'investimenti', 'assicurazioni', 'condominio', 'luce', 'gas', 'mutuo', 'lenti', 'telefonia', 'parrucchiere', 'palestra']

### SQL attributes — legacy fallback (kept for backward compat)
SQL_ATTRIBUTES_ALL = ['mese', 'entrate'] + DEFAULT_VARIABILI + ['uscite_variabili'] + DEFAULT_FISSE + ['uscite_fisse', 'uscite_totali', 'delta']
SQL_ATTRIBUTES_NOT_EDITABLE = ['mese', 'uscite_variabili', 'uscite_fisse', 'uscite_totali', 'delta']
SQL_ATTRIBUTES_EDITABLE = ['entrate'] + DEFAULT_VARIABILI + DEFAULT_FISSE

### WEB PARAMETERS
PORT = 5000

### PATHS
DATA_DIR = "data"
USER_DB_DIR = "data/user_data"
USERS_DB = "data/users.db"