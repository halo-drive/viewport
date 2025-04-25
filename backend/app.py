import os
import sqlite3
import logging 
from flask import (
    Flask, Blueprint, render_template, request, session,
    redirect, url_for, flash, jsonify
)
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from electric_api import electric_api_bp
from config import Config
from diesel_api import diesel_api_bp
from hydrogen_api import hydrogen_api_bp
from auth_api import auth_api_bp

app = Flask(__name__)
app.config.from_object(Config)  

app.config['SESSION_COOKIE_NAME'] = 'viewport_session'
app.config['SESSION_COOKIE_PATH'] = '/'  # Only accessible at root path

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s')

# for dev only
# !!!!!IMPORTANT!!!!!!!!
# comment this out while pushing to github and production
# CORS(app, supports_credentials=True, resources={r"/api/*": {"origins": "http://localhost:5173"}})
# !!!!IMPORTANT!!!!!!!

def init_db():
    db_path = app.config.get('DATABASE_PATH', 'users.db')
    try:
        with sqlite3.connect(db_path) as conn:
            c = conn.cursor()
            c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                is_approved INTEGER NOT NULL DEFAULT 0
            )
            ''')
            conn.commit()
            app.logger.info(f"Database initialized successfully at {db_path}")
    except sqlite3.Error as e:
        app.logger.error(f"Database initialization error at {db_path}: {e}")
    except Exception as e:
        app.logger.error(f"An unexpected error occurred during DB init: {e}")

with app.app_context():
    init_db() 

app.register_blueprint(diesel_api_bp)
app.register_blueprint(hydrogen_api_bp)
app.register_blueprint(auth_api_bp) 
app.register_blueprint(electric_api_bp)
  

@app.errorhandler(404)
def not_found(e):
    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return jsonify({"error": "Not Found", "message": str(e)}), 404
    return "<h1>404 - Not Found</h1>", 404 

@app.errorhandler(405)
def method_not_allowed(e):
     if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return jsonify({"error": "Method Not Allowed", "message": str(e)}), 405
     return "<h1>405 - Method Not Allowed</h1>", 405 

@app.errorhandler(Exception)
def handle_exception(e):
    app.logger.error(f"Unhandled exception: {e}", exc_info=True)
    if request.path.startswith('/api/'):
         return jsonify(error="Internal Server Error", message="An unexpected error occurred."), 500
    return "<h1>Internal Server Error</h1>", 500


# --- API Status Route ---
# Simple health check endpoint for the frontend or monitoring
@app.route('/api/status')
def api_status():
    return jsonify({"status": "OK", "message": "API is running"})
# ------------------------

# for dev only
# !!!!!IMPORTANT!!!!!!!!
# comment this out while pushing to github and production
# if __name__ == '__main__':
#     app.run(host='0.0.0.0', port=443, debug=True)
# !!!!!IMPORTANT!!!!!!!!
