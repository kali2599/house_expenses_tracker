# House Expenses Tracker

## Description
The House Expenses Tracker is a Python-based web application designed to help you manage and track your household expenses efficiently. It uses SQLite as the database to store expense data and flask to serve the backend.

## Features
- Add, update, and delete expenses.
- View expense summaries.
- Lightweight and easy to use.

## Prerequisites
- Python 3.6 or higher
- SQLite3

## Setup
1. Clone the repository:
   ```bash
   git clone <repository-url>
   ```
2. Navigate to the project directory:
   ```bash
   cd house_expenses_tracker
   ```
3. Initialize the database:
   ```bash
   sqlite3 data.db < init.sql
   ```
4. Populate the database:
      ```bash
   sqlite3 data.db < populate.sql
   ```
   (NOTE: populate.sql script has fake data. Fix it with your real data)
5. Install required Python packages (if any):
   ```bash
   pip install -r requirements.txt
   ```

## Usage
Run the application:
```bash
python app.py
```

### Inserting new expense
To insert a new expense, you can use the `/update` endpoint. This endpoint accepts the following query parameters:
- `category` (mandatory): The category of the expense (e.g., "food", "transport").
- `month` (mandatory): The month for the expense (e.g., "October").
- `amount` (mandatory): The amount of the expense (must be numeric).
- `note` (optional): A note or description for the expense.

Example `curl` command:
```bash
curl "http://localhost:8080/update?category=svago&month=ottobre&amount=200&note=compleanno"
```

If the request is successful, the server will respond with a confirmation message and the database will be updated coherently.

If any mandatory parameter is missing or invalid, the server will return an error message.

## File Structure
- `app.py`: Entry point of the web application.
- `settings.py`: Configuration settings for the application.
- `sqlManager.py`: Handles database operations.
- `utils.py`: Utility functions used across the application.
- `init.sql`: SQL script to initialize the database schema.
- `populate.sql`: SQL script to populate the 'spese_mensili' table.


## Contributing
Contributions are welcome! Feel free to open issues or submit pull requests.