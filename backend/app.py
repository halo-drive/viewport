# backend/app.py

import os
import sqlite3
import logging # Import logging
from flask import (
    Flask, Blueprint, render_template, request, session,
    redirect, url_for, flash, jsonify
)
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

# --- Project Imports ---
from config import Config
# Import your blueprints
from diesel_api import diesel_api_bp
from hydrogen_api import hydrogen_api_bp
from weather_test import weather_test_bp
from auth_api import auth_api_bp
from tracking import tracking_bp
from hydrogen import hydrogen_bp
from routemap import routemap_bp
# -----------------------

# --- Flask App Initialization ---
app = Flask(__name__)
app.config.from_object(Config)  # Load config from Config class (reads .env via Config)

# --- Logging Setup ---
# Configure logging (adjust level and format as needed for production)
logging.basicConfig(level=logging.INFO, # Use INFO or WARNING for production
                    format='%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s')
# ---------------------

# --- CORS Configuration ---
# NOTE: For production, you might need to adjust origins.
# If Nginx serves both frontend and proxies backend on the same domain/IP,
# CORS might not be strictly necessary, but 'supports_credentials=True' IS
# still essential for session cookies to work correctly via the proxy.
CORS(app, supports_credentials=True, resources={
    r"/api/*": {"origins": "*"}, # Allow API calls from anywhere for now (adjust later)
    # Or be more specific if needed, e.g., allow your EC2 IP/domain
    # r"/*": {"origins": ["http://<your_ec2_ip>", "http://<your_domain>"]}
})
# ------------------------

# --- Database Initialization ---
# Initialize the SQLite database and create the 'users' table if it doesn't exist
def init_db():
    # Use DATABASE_PATH from config
    db_path = app.config.get('DATABASE_PATH', 'users.db')
    try:
        with sqlite3.connect(db_path) as conn:
            c = conn.cursor()
            # Create a table for users if it doesn't exist
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
    init_db() # Initialize DB within application context
# ---------------------------

# --- Register Blueprints ---
app.register_blueprint(tracking_bp)
app.register_blueprint(hydrogen_bp)
app.register_blueprint(routemap_bp)
app.register_blueprint(diesel_api_bp)
app.register_blueprint(hydrogen_api_bp)
app.register_blueprint(weather_test_bp)
app.register_blueprint(auth_api_bp) # Contains /api/auth routes
# ---------------------------

# --- Error Handlers ---
@app.errorhandler(404)
def not_found(e):
    # Check if the request expects JSON
    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return jsonify({"error": "Not Found", "message": str(e)}), 404
    # Otherwise, return HTML (or redirect)
    return render_template('404.html'), 404 # Assuming you have a 404.html template

@app.errorhandler(405)
def method_not_allowed(e):
     if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return jsonify({"error": "Method Not Allowed", "message": str(e)}), 405
     return render_template('405.html'), 405 # Assuming you have a 405.html template

# Consider adding a generic 500 error handler too
@app.errorhandler(Exception)
def handle_exception(e):
    # Log the error
    app.logger.error(f"Unhandled exception: {e}", exc_info=True)
    # Return JSON response for API requests or generic error page
    if request.path.startswith('/api/'):
         return jsonify(error="Internal Server Error", message="An unexpected error occurred."), 500
    # You might want a user-friendly HTML error page here
    return "<h1>Internal Server Error</h1>", 500
# ----------------------


# === Server-Rendered Routes (Consider if needed alongside SPA + API) ===
# NOTE: These routes seem to handle login/signup via server-rendered pages.
# If your frontend is a Single Page Application (SPA) handling all user
# interaction and calling the '/api/auth/...' routes from auth_api.py,
# these routes might be redundant or only needed for specific admin pages.

# Admin login route (Server-rendered)
@app.route('/login', methods=['GET', 'POST'])
def login():
    # Redirect if already logged in
    if session.get('logged_in'):
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Get admin credentials from config
        admin_user = app.config.get('ADMIN_USERNAME')
        admin_pass = app.config.get('ADMIN_PASSWORD')
        db_path = app.config.get('DATABASE_PATH', 'users.db')

        with sqlite3.connect(db_path) as conn:
            c = conn.cursor()

            # --- CHANGE: Use configured admin credentials ---
            is_admin_login = False
            if admin_user and admin_pass: # Check if admin creds are configured
                if email == admin_user and password == admin_pass:
                    is_admin_login = True

            if is_admin_login:
            # --- End CHANGE ---
                session['logged_in'] = True
                session['role'] = 'admin'
                session['email'] = email # Store email in session
                app.logger.info(f"Admin login successful for {email}")
                return redirect(url_for('admin_dashboard')) # Redirect admin here
            else:
                # Check regular user
                c.execute('SELECT * FROM users WHERE email = ?', (email,))
                user = c.fetchone()
                if user and check_password_hash(user[3], password) and user[4] == 1:
                    session['logged_in'] = True
                    session['role'] = 'user'
                    session['email'] = email # Store email in session
                    app.logger.info(f"User login successful for {email}")
                    return redirect(url_for('index')) # Redirect regular user here
                else:
                    app.logger.warning(f"Failed login attempt for {email}")
                    if user and user[4] == 0:
                        flash('Your account is pending approval.')
                    else:
                        flash('Invalid credentials.')
                    # No redirect here, stay on login page to show flash message

    # For GET request or failed POST, render the login template
    return render_template('login.html')


# User signup route (Server-rendered)
@app.route('/signup', methods=['GET', 'POST'])
def signup():
     # Redirect if already logged in
    if session.get('logged_in'):
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        password_hash = generate_password_hash(password)
        db_path = app.config.get('DATABASE_PATH', 'users.db')

        with sqlite3.connect(db_path) as conn:
            c = conn.cursor()
            try:
                c.execute('INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
                          (username, email, password_hash))
                conn.commit()
                flash('Signup successful! Awaiting admin approval.')
                app.logger.info(f"New user signup: {email}")
                return redirect(url_for('login'))
            except sqlite3.IntegrityError:
                flash('Email already registered.')
                app.logger.warning(f"Signup failed (email exists): {email}")
            except Exception as e:
                 app.logger.error(f"Signup error for {email}: {e}")
                 flash('An error occurred during signup.')

    return render_template('signup.html')


# Admin dashboard (Server-rendered)
@app.route('/admin_dashboard')
def admin_dashboard():
    if session.get('role') != 'admin':
        flash('Access denied.')
        return redirect(url_for('login'))

    db_path = app.config.get('DATABASE_PATH', 'users.db')
    pending_users = []
    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row # Access columns by name
            c = conn.cursor()
            # Fetch details needed for the dashboard template
            c.execute('SELECT id, username, email FROM users WHERE is_approved = 0')
            pending_users = c.fetchall()
    except Exception as e:
        app.logger.error(f"Error fetching pending users for admin dashboard: {e}")
        flash("Error loading pending users.")

    # Render the admin dashboard template, passing the list of users
    return render_template('admin_dashboard.html', pending_users=pending_users)


# Approve user route (Server-rendered)
@app.route('/approve/<string:email>')
def approve_user(email):
    if session.get('role') != 'admin':
        flash('Access denied.')
        return redirect(url_for('login'))

    db_path = app.config.get('DATABASE_PATH', 'users.db')
    try:
        with sqlite3.connect(db_path) as conn:
            c = conn.cursor()
            c.execute('UPDATE users SET is_approved = 1 WHERE email = ? AND is_approved = 0', (email,))
            conn.commit()
            if c.rowcount > 0:
                 flash(f'User {email} approved.')
                 app.logger.info(f"Admin approved user: {email}")
            else:
                 flash(f'User {email} not found or already approved.')
    except Exception as e:
         app.logger.error(f"Error approving user {email}: {e}")
         flash("An error occurred while approving the user.")

    return redirect(url_for('admin_dashboard'))


# User index route (Server-rendered entry point for logged-in users)
@app.route('/')
@app.route('/index')
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    if session.get('role') == 'admin':
        # Maybe admins have a specific index or just go to dashboard?
        return redirect(url_for('admin_dashboard'))

    # Render the main user page (could be index.html or another template)
    # This template might be the one that loads your SPA frontend assets
    return render_template('index.html')


# Logout route (Server-rendered)
@app.route('/logout')
def logout():
    # Use the API logout logic for consistency if possible,
    # but popping session here also works for server-rendered flow.
    user_email = session.get('email', 'unknown user') # Log who logged out
    session.pop('logged_in', None)
    session.pop('role', None)
    session.pop('email', None)
    # session.clear() # Optionally clear everything
    flash('You have been logged out.')
    app.logger.info(f"User logged out: {user_email}")
    return redirect(url_for('login'))

# =======================================================================

# --- API Status Route ---
# Simple health check endpoint for the frontend or monitoring
@app.route('/api/status')
def api_status():
    return jsonify({"status": "OK", "message": "API is running"})
# ------------------------


# --- Remove Development Server Execution ---
# if __name__ == '__main__':
#    # DO NOT use app.run() in production! Use Gunicorn via systemd.
#    # app.run(host='0.0.0.0', port=443, debug=True) # <-- COMMENTED OUT / DELETED
#    pass # Keep the block empty or remove it entirely
# -----------------------------------------