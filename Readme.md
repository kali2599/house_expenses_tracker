# House Expenses Tracker

## Description
The House Expenses Tracker is a Python-based application designed to help you manage and track your household expenses efficiently. It uses SQLite as the database to store expense data.

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
4. Install required Python packages (if any):
   ```bash
   pip install -r requirements.txt
   ```

## Usage
Run the application:
```bash
python main.py
```

## File Structure
- `main.py`: Entry point of the application.
- `settings.py`: Configuration settings for the application.
- `sqlManager.py`: Handles database operations.
- `utils.py`: Utility functions used across the application.
- `init.sql`: SQL script to initialize the database schema.


## Contributing
Contributions are welcome! Feel free to open issues or submit pull requests.