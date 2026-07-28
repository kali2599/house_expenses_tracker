from flask import Flask
import os, argparse

from config.settings import PORT, HOST
from init_app import init_app
from routes import register_routes
from utils import get_color_for_attribute
from config.settings import MONTHS_INDEX, DEFAULT_VARIABILI, DEFAULT_FISSE


# --- Initialize directories and databases
init_app()


# --- Create Flask app
app = Flask(__name__)

KEY_FILE = 'flask_secret.key'
if os.path.exists(KEY_FILE):
    with open(KEY_FILE, 'rb') as f:
        app.secret_key = f.read()
else:
    app.secret_key = os.urandom(24)
    with open(KEY_FILE, 'wb') as f:
        f.write(app.secret_key)

app.jinja_env.globals.update(zip=zip)
app.jinja_env.globals.update(get_color_for_attribute=get_color_for_attribute)
app.jinja_env.globals.update(MONTHS_INDEX=MONTHS_INDEX)
app.jinja_env.globals.update(DEFAULT_VARIABILI=DEFAULT_VARIABILI)
app.jinja_env.globals.update(DEFAULT_FISSE=DEFAULT_FISSE)


# --- Register all routes
register_routes(app)


# --- Run
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="House Expenses Tracker")
    parser.add_argument("--host", default=HOST, help="Host to bind to (default: {HOST})")
    parser.add_argument("--port", type=int, default=PORT, help=f"Port to listen on (default: {PORT})")
    parser.add_argument("--debug", dest="debug", action="store_true", default=True, help="Enable debug mode")
    parser.add_argument("--no-debug", dest="debug", action="store_false", help="Disable debug mode")
    args = parser.parse_args()

    app.run(host=args.host, port=args.port, debug=args.debug)
