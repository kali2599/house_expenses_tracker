# House Expenses Tracker

## Description
Web application per tracciare spese domestiche. Interfaccia Flask + SQLite, UI in italiano.

## Features
- **Add Expense** — Inserimento multiplo spese con attributo, importo, nota. Tabella riepilogativa mensile.
- **Data Analysis / Tracciamento** — Seleziona uno o piu attributi, visualizza andamento su linea chart + tabella dati.
- **Data Analysis / Confronto** — Griglia mesi multi-selezione, statistiche riassuntive (entrate/uscite/delta), 4 tab: Tabella, Grafici, Analisi per mese, Variazione %.
- **Data Analysis / Storico** — Storico completo con filtri data, modifica ed eliminazione spese.
- **Change Year** — Cambia anno di lavoro.

## Requisiti
- Python 3.6+
- SQLite3
- Flask (unica dipendenza esterna)
- Docker (opzionale, per containerizzazione)

## Setup (senza Docker)
```bash
git clone <repository-url>
cd house_expenses_tracker
pip install -r requirements.txt
python3 main.py
```

Apri il browser su `http://localhost:8080` e registrati tramite l'interfaccia web.

## Setup con Docker

### Build
```bash
docker build -t house-expenses .
```

### Run — bind su tutte le interfacce (default)
```bash
docker run -d -p 8080:8080 -v house_data:/app/data --name house-expenses house-expenses
```
L'app e' accessibile da:
- `http://127.0.0.1:8080` (localhost)
- `http://<IP_RETE>:8080` (qualsiasi interfaccia di rete dell'host)

### Run — bind su un singolo indirizzo IP
```bash
docker run -d -p 127.0.0.1:8080:8080 -v house_data:/app/data --name house-expenses house-expenses
```
L'app e' accessibile solo da `http://127.0.0.1:8080` (localhost). Nessun accesso dalla rete.

Esempio con IP di rete specifico:
```bash
docker run -d -p 192.168.1.4:8080:8080 -v house_data:/app/data --name house-expenses house-expenses
```
L'app e' accessibile solo da `http://192.168.1.4:8080`.

### Gestione container
```bash
docker logs house-expenses        # log
docker stop house-expenses        # ferma
docker start house-expenses       # riavvia
docker rm -f house-expenses       # rimuovi
```

Il volume Docker `house_data` preserva database e foto profilo tra i restart.

## Struttura
| File | Ruolo |
|---|---|
| `main.py` | Entry point Flask — app creation, secret key, CLI args |
| `routes.py` | Routes, decorators, permission helpers, context processor |
| `config/settings.py` | Costanti: PORT, HOST, MONTHS_INDEX, attributi, paths |
| `db/sql_manager.py` | SQLManager + generate_user_db_sql() — accesso dati SQLite |
| `db/init.sql` | Schema database legacy (default attributes) |
| `utils.py` | Helper: formattazione date, colori |
| `init_app.py` | Inizializzazione — crea dirs, users.db, flask_secret.key |
| `templates/` | Jinja2 HTML templates |
| `static/css/style.css` | CSS |
| `data/` | Database utente e upload (gitignored) |
| `Dockerfile` | Containerizzazione Docker |
