import calendar
from config import settings


def get_color_for_attribute(attribute, value=None):
    if attribute == 'entrate':
        return "entrate"
    elif attribute in ('uscite_variabili', 'uscite_fisse'):
        return "uscite"
    elif attribute == 'uscite_totali':
        return "uscite-totali"
    elif attribute == 'delta':
        if value is not None:
            return "delta-positivo" if value >= 0 else "delta-negativo"
        return ""
    else:
        return ""


def parse_date_bound(raw, bound):
    if not raw:
        return None

    parts = raw.split("-")
    if len(parts) == 1:
        year = parts[0]
        if len(year) != 4 or not year.isdigit():
            return None
        if bound == "start":
            return f"{year}-01-01"
        else:
            return f"{year}-12-31"

    if len(parts) == 2:
        year, month = parts
        if len(year) != 4 or not year.isdigit() or not month.isdigit():
            return None
        month = int(month)
        if month < 1 or month > 12:
            return None
        if bound == "start":
            return f"{year}-{month:02d}-01"
        else:
            last = calendar.monthrange(int(year), month)[1]
            return f"{year}-{month:02d}-{last:02d}"

    if len(parts) == 3:
        year, month, day = parts
        if not year.isdigit() or not month.isdigit() or not day.isdigit():
            return None
        year, month, day = int(year), int(month), int(day)
        if month < 1 or month > 12 or day < 1 or day > 31:
            return None
        return f"{year:04d}-{month:02d}-{day:02d}"

    return None
