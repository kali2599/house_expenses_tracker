#DATABASE = "data.db"

MONTHS_INDEX = {1:"GENNAIO", 2:"FEBBRAIO", 3:"MARZO", 4:"APRILE", 5:"MAGGIO", 6:"GIUGNO", 7:"LUGLIO", 8:"AGOSTO", 9:"SETTEMBRE", 10:"OTTOBRE", 11:"NOVEMBRE", 12:"DICEMBRE"}

MONTH_HEADER_COLOR = "\033[96m"
ENTRATE_COLOR = "\033[94m"
USCITE_VARIABILI_COLOR = "\033[93m"
USCITE_FISSE_COLOR = "\033[93m"
USCITE_TOTALI_COLOR = "\033[91m"
DELTA_RED_COLOR = "\033[91m"
DELTA_GREEN_COLOR = "\033[92m"


### SQL attributes
SQL_ATTRIBUTES_ALL = ['mese', 'entrate', 'spesa', 'pasti_fuori', 'svago', 'shopping', 'inaspettate', 'varie', 'salute', 'vacanze', 'uscite_variabili', 'abbonamenti', 'investimenti', 'assicurazioni', 'condominio', 'luce', 'gas', 'mutuo', 'lenti', 'telefonia', 'parrucchiere', 'palestra', 'uscite_fisse', 'uscite_totali', 'delta']
SQL_ATTRIBUTES_NOT_EDITABLE = ['mese', 'uscite_variabili', 'uscite_fisse[]', 'uscite_totali', 'delta']
SQL_ATTRIBUTES_EDITABLE = ['entrate', 'spesa', 'pasti_fuori', 'svago', 'shopping', 'inaspettate', 'varie', 'salute', 'vacanze', 'abbonamenti','investimenti', 'assicurazioni', 'condominio', 'luce', 'gas', 'mutuo', 'lenti', 'telefonia', 'parrucchiere', 'palestra']