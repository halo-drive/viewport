from flask import Flask
from flask_cors import CORS
from config import Config
import os
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify
from diesel_api import diesel_api_bp
from hydrogen_api import hydrogen_api_bp
from weather_test import weather_test_bp
from auth_api import auth_api_bp
from tracking import tracking_bp
from hydrogen import hydrogen_bp
from routemap import routemap_bp

app = Flask(__name__)
app.config.from_object(Config)  # Load config from Config class

# Set the secret key from config
app.secret_key = Config.SECRET_KEY

CORS(app, supports_credentials=True, resources={r"/*": {"origins": "http://localhost:5173"}})

# Register blueprints
app.register_blueprint(tracking_bp)
app.register_blueprint(hydrogen_bp)
app.register_blueprint(routemap_bp)
app.register_blueprint(diesel_api_bp)
app.register_blueprint(hydrogen_api_bp)
app.register_blueprint(weather_test_bp)
app.register_blueprint(auth_api_bp)

@app.errorhandler(404)
def not_found(e):
  return '<h1>Error 404!</h1>', 404

@app.errorhandler(405)
def method_not_allowed(e):
    return '<h1>Error 405 - Method Not Allowed</h1>', 405

# Initialize the SQLite database and create the 'users' table if it doesn't exist
def init_db():
    with sqlite3.connect('users.db') as conn:
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

init_db()

# Admin login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        with sqlite3.connect('users.db') as conn:
            c = conn.cursor()
            # Check if admin
            if email == 'terry.s' and password == 'avenuep3m3robotics!!':
                session['logged_in'] = True
                session['role'] = 'admin'
                return redirect(url_for('admin_dashboard'))
            else:
                # Fetch user by email
                c.execute('SELECT * FROM users WHERE email = ?', (email,))
                user = c.fetchone()
                if user and check_password_hash(user[3], password) and user[4] == 1:  # Match hashed password and check approval
                    session['logged_in'] = True
                    session['role'] = 'user'
                    return redirect(url_for('index'))
                else:
                    flash('Invalid credentials or account not approved yet.')
    
    return render_template('login.html')

# User signup route
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        password_hash = generate_password_hash(password)  # Hash the password

        with sqlite3.connect('users.db') as conn:
            c = conn.cursor()
            try:
                c.execute('INSERT INTO users (username, email, password) VALUES (?, ?, ?)', 
                          (username, email, password_hash))  # Save hashed password
                conn.commit()
                flash('Signup successful! Awaiting admin approval.')
                return redirect(url_for('login'))
            except sqlite3.IntegrityError:
                flash('Email already registered.')
    
    return render_template('signup.html')

# Admin dashboard to approve users
@app.route('/admin_dashboard')
def admin_dashboard():
    if session.get('role') != 'admin':
        flash('Access denied.')
        return redirect(url_for('login'))
    
    with sqlite3.connect('users.db') as conn:
        c = conn.cursor()
        c.execute('SELECT username, email FROM users WHERE is_approved = 0')
        pending_users = c.fetchall()  # Fetch pending users

    return render_template('admin_dashboard.html', pending_users=pending_users)

# Approve user route (accessible by admin only)
@app.route('/approve/<string:email>')
def approve_user(email):
    if session.get('role') != 'admin':
        flash('Access denied.')
        return redirect(url_for('login'))
    
    with sqlite3.connect('users.db') as conn:
        c = conn.cursor()
        c.execute('UPDATE users SET is_approved = 1 WHERE email = ?', (email,))
        conn.commit()
    
    return redirect(url_for('admin_dashboard'))

# User index route
@app.route('/index')
@app.route('/')
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    if session.get('role') == 'admin':
        return redirect(url_for('admin_dashboard'))
    
    return render_template('index.html')

# Logout route
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('role', None)
    return redirect(url_for('login'))

# Add API status route for frontend to test connectivity
@app.route('/api/status')
def api_status():
    return jsonify({"status": "OK", "message": "API is running"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=443, debug=True)