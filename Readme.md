# House Expenses Tracker

## Description
Web application per tracciare spese domestiche. Interfaccia Flask + SQLite, UI in italiano.

## Features
- **Add Expense** — Inserimento multiplo spese con attributo, importo, nota. Tabella riepilogativa mensile.
- **Data Analysis / Tracciamento** — Seleziona uno o più attributi, visualizza andamento su linea chart + tabella dati.
- **Data Analysis / Confronto** — Griglia mesi multi-selezione, statistiche riassuntive (entrate/uscite/delta), 4 tab: Tabella, Grafici (barre raggruppate/stacked/trend/donut), Analisi per mese, Variazione %.
- **Undo Expense** — Elimina una specifica spesa in un mese.
- **Show History** — Storico completo con filtri data, toggle visibilità colonne.
- **Change Year** — Cambia anno di lavoro.

## Requisiti
- Python 3.6+
- SQLite3
- Flask (unica dipendenza esterna)

## Setup
```bash
git clone <repository-url>
cd house_expenses_tracker
pip install -r requirements.txt
python main.py
```

Apri il browser su `http://localhost:5000` e registrati tramite l'interfaccia web.

**Nota:** `populate.sql` non è allineato allo schema corrente. Usalo solo come riferimento o inserisci dati manualmente dall'interfaccia Add Expense.

## Struttura
| File | Ruolo |
|---|---|
| `main.py` | Flask app — routes, request handling |
| `sqlManager.py` | Accesso dati SQLite |
| `utils.py` | Helper: formattazione date, colori |
| `settings.py` | Costanti: PORT, mesi, attributi |
| `templates/` | Jinja2 HTML templates |
| `static/style.css` | CSS |
| `init.sql` | Schema database |
| `user_data/` | Database per-utente (gitignored) |

## Porta
In `settings.py`: `PORT = 5000` (development senza sudo). Cambia a `443` per produzione.
