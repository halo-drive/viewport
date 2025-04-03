from flask import Blueprint, request, jsonify, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import os

auth_api_bp = Blueprint('auth_api', __name__)

# Initialize the SQLite database
def init_auth_db():
    if not os.path.exists('users.db'):
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
            print("Auth database initialized")
    else:
        print("Auth database already exists")

# Initialize the database when the blueprint is registered
init_auth_db()

@auth_api_bp.route('/api/auth/login', methods=['POST'])
def login_api():
    try:
        email = request.form['email']
        password = request.form['password']
        
        with sqlite3.connect('users.db') as conn:
            c = conn.cursor()
            # Check if admin
            if (email == 'admin' and password == 'halodrive') or (email == 'terry.s' and password == 'avenuep3m3robotics!!'):
                session['logged_in'] = True
                session['role'] = 'admin'
                session['email'] = email
                
                return jsonify({
                    "success": True,
                    "role": "admin",
                    "message": "Admin login successful."
                })
            else:
                # Fetch user by email
                c.execute('SELECT * FROM users WHERE email = ?', (email,))
                user = c.fetchone()
                if user and check_password_hash(user[3], password) and user[4] == 1:  # Match hashed password and check approval
                    session['logged_in'] = True
                    session['role'] = 'user'
                    session['email'] = email
                    
                    return jsonify({
                        "success": True,
                        "role": "user",
                        "message": "Login successful."
                    })
                else:
                    if user and user[4] == 0:
                        message = "Your account is pending approval."
                    else:
                        message = "Invalid credentials."
                    
                    return jsonify({
                        "success": False,
                        "message": message
                    })
    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({"success": False, "message": str(e)})

@auth_api_bp.route('/api/auth/signup', methods=['POST'])
def signup_api():
    try:
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        password_hash = generate_password_hash(password)
        
        with sqlite3.connect('users.db') as conn:
            c = conn.cursor()
            try:
                c.execute('INSERT INTO users (username, email, password) VALUES (?, ?, ?)', 
                         (username, email, password_hash))
                conn.commit()
                return jsonify({
                    "success": True,
                    "message": "Signup successful! Awaiting admin approval."
                })
            except sqlite3.IntegrityError:
                return jsonify({
                    "success": False,
                    "message": "Email already registered."
                })
    except Exception as e:
        print(f"Signup error: {e}")
        return jsonify({"success": False, "message": str(e)})

@auth_api_bp.route('/api/auth/logout', methods=['POST'])
def logout_api():
    session.pop('logged_in', None)
    session.pop('role', None)
    session.pop('email', None)
    return jsonify({"success": True, "message": "Logged out successfully."})

@auth_api_bp.route('/api/auth/status', methods=['GET'])
def status_api():
    if session.get('logged_in'):
        return jsonify({
            "loggedIn": True,
            "role": session.get('role'),
            "email": session.get('email')
        })
    else:
        return jsonify({
            "loggedIn": False
        })

@auth_api_bp.route('/api/admin/pending-users', methods=['GET'])
def pending_users_api():
    if session.get('role') != 'admin':
        return jsonify({"success": False, "message": "Access denied."})
    
    with sqlite3.connect('users.db') as conn:
        c = conn.cursor()
        c.execute('SELECT id, username, email FROM users WHERE is_approved = 0')
        pending_users = c.fetchall()
        
        users_list = []
        for user in pending_users:
            users_list.append({
                "id": user[0],
                "username": user[1],
                "email": user[2]
            })
        
        return jsonify({
            "success": True,
            "pendingUsers": users_list
        })

@auth_api_bp.route('/api/admin/approve-user', methods=['POST'])
def approve_user_api():
    if session.get('role') != 'admin':
        return jsonify({"success": False, "message": "Access denied."})
    
    try:
        email = request.form['email']
        
        with sqlite3.connect('users.db') as conn:
            c = conn.cursor()
            c.execute('UPDATE users SET is_approved = 1 WHERE email = ?', (email,))
            conn.commit()
            
            if c.rowcount > 0:
                return jsonify({
                    "success": True,
                    "message": f"User {email} approved successfully."
                })
            else:
                return jsonify({
                    "success": False,
                    "message": "User not found."
                })
    except Exception as e:
        print(f"Approve user error: {e}")
        return jsonify({"success": False, "message": str(e)})
    
@auth_api_bp.route('/api/admin/delete-user', methods=['POST'])
def delete_user_api():
    if session.get('role') != 'admin':
        return jsonify({"success": False, "message": "Access denied."})
    
    try:
        email = request.form['email']
        
        with sqlite3.connect('users.db') as conn:
            c = conn.cursor()
            c.execute('DELETE FROM users WHERE email = ?', (email,))
            conn.commit()
            
            if c.rowcount > 0:
                return jsonify({
                    "success": True,
                    "message": f"User {email} deleted successfully."
                })
            else:
                return jsonify({
                    "success": False,
                    "message": "User not found."
                })
    except Exception as e:
        print(f"Delete user error: {e}")
        return jsonify({"success": False, "message": str(e)})

@auth_api_bp.route('/api/admin/get-all-users', methods=['GET'])
def get_all_users_api():
    if session.get('role') != 'admin':
        return jsonify({"success": False, "message": "Access denied."})
    
    with sqlite3.connect('users.db') as conn:
        c = conn.cursor()
        c.execute('SELECT id, username, email, is_approved FROM users')
        all_users = c.fetchall()
        
        users_list = []
        for user in all_users:
            users_list.append({
                "id": user[0],
                "username": user[1],
                "email": user[2],
                "isApproved": bool(user[3])
            })
        
        return jsonify({
            "success": True,
            "users": users_list
        })