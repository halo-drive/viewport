# backend/auth_api.py

# Import current_app to access configuration
from flask import Blueprint, request, jsonify, session, current_app
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import os

auth_api_bp = Blueprint('auth_api', __name__)

# Redundant Database Initialization - app.py handles this
# -------------------------------------------------------------
# def init_auth_db():
#     db_path = current_app.config.get('DATABASE_PATH', 'users.db')
#     # Check relative to the instance folder or use an absolute path if configured
#     if not os.path.exists(db_path):
#         with sqlite3.connect(db_path) as conn:
#             c = conn.cursor()
#             c.execute('''
#             CREATE TABLE IF NOT EXISTS users (
#                 id INTEGER PRIMARY KEY AUTOINCREMENT,
#                 username TEXT NOT NULL,
#                 email TEXT UNIQUE NOT NULL,
#                 password TEXT NOT NULL,
#                 is_approved INTEGER NOT NULL DEFAULT 0
#             )
#             ''')
#             conn.commit()
#             print("Auth database initialized")
#     else:
#          print("Auth database already exists")


# init_auth_db() 
# -------------------------------------------------------------


@auth_api_bp.route('/api/auth/login', methods=['POST'])
def login_api():
    try:
        email = request.form['email']
        password = request.form['password']

        # Get admin credentials from config (loaded from .env)
        admin_user = current_app.config.get('ADMIN_USERNAME')
        admin_pass = current_app.config.get('ADMIN_PASSWORD')

        # Get database path from config
        db_path = current_app.config.get('DATABASE_PATH', 'users.db')

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
                session['email'] = email

                return jsonify({
                    "success": True,
                    "role": "admin",
                    "message": "Admin login successful."
                })
            else:
                # Fetch user by email
                c.execute('SELECT * FROM users WHERE email = ?', (email,))
                user = c.fetchone() # user[3] is password hash, user[4] is is_approved flag

                # Check password hash and approval status
                if user and check_password_hash(user[3], password) and user[4] == 1:
                    session['logged_in'] = True
                    session['role'] = 'user'
                    session['email'] = email

                    return jsonify({
                        "success": True,
                        "role": "user",
                        "message": "Login successful."
                    })
                else:
                    # Determine specific error message
                    if user and not check_password_hash(user[3], password):
                         message = "Invalid credentials."
                    elif user and user[4] == 0:
                        message = "Your account is pending approval."
                    else: # User not found or other issue
                        message = "Invalid credentials."

                    return jsonify({
                        "success": False,
                        "message": message
                    })
    except Exception as e:
        current_app.logger.error(f"Login error: {e}") # Use Flask logger
        return jsonify({"success": False, "message": "An unexpected error occurred during login."}), 500


@auth_api_bp.route('/api/auth/signup', methods=['POST'])
def signup_api():
    try:
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        password_hash = generate_password_hash(password)

        # Get database path from config
        db_path = current_app.config.get('DATABASE_PATH', 'users.db')

        with sqlite3.connect(db_path) as conn:
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
                # This error occurs if the email (UNIQUE column) already exists
                return jsonify({
                    "success": False,
                    "message": "Email already registered."
                }), 409 # 409 Conflict status code is appropriate here
    except Exception as e:
        current_app.logger.error(f"Signup error: {e}") # Use Flask logger
        return jsonify({"success": False, "message": "An unexpected error occurred during signup."}), 500


@auth_api_bp.route('/api/auth/logout', methods=['POST'])
def logout_api():
    session.pop('logged_in', None)
    session.pop('role', None)
    session.pop('email', None)
    # Consider clearing the whole session for a cleaner logout: session.clear()
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

# --- Admin Routes ---

def check_admin():
    """Helper function to check if user is admin"""
    if session.get('role') != 'admin':
        return False, jsonify({"success": False, "message": "Access denied."}), 403 # 403 Forbidden
    return True, None, None

@auth_api_bp.route('/api/admin/pending-users', methods=['GET'])
def pending_users_api():
    is_admin, response, status_code = check_admin()
    if not is_admin:
        return response, status_code

    db_path = current_app.config.get('DATABASE_PATH', 'users.db')
    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row # Return rows as dict-like objects
            c = conn.cursor()
            c.execute('SELECT id, username, email FROM users WHERE is_approved = 0')
            pending_users = c.fetchall()

            # Convert Row objects to dictionaries
            users_list = [dict(user) for user in pending_users]

            return jsonify({
                "success": True,
                "pendingUsers": users_list
            })
    except Exception as e:
        current_app.logger.error(f"Pending users fetch error: {e}")
        return jsonify({"success": False, "message": "Error fetching pending users."}), 500


@auth_api_bp.route('/api/admin/approve-user', methods=['POST'])
def approve_user_api():
    is_admin, response, status_code = check_admin()
    if not is_admin:
        return response, status_code

    db_path = current_app.config.get('DATABASE_PATH', 'users.db')
    try:
        email = request.form['email']

        with sqlite3.connect(db_path) as conn:
            c = conn.cursor()
            c.execute('UPDATE users SET is_approved = 1 WHERE email = ? AND is_approved = 0', (email,))
            conn.commit()

            if c.rowcount > 0: # Check if any row was actually updated
                return jsonify({
                    "success": True,
                    "message": f"User {email} approved successfully."
                })
            else:
                # Check if user exists but was already approved or doesn't exist
                c.execute('SELECT COUNT(*) FROM users WHERE email = ?', (email,))
                user_exists = c.fetchone()[0] > 0
                message = "User not found or already approved." if user_exists else "User not found."
                return jsonify({
                    "success": False,
                    "message": message
                }), 404 # 404 Not Found is appropriate

    except KeyError:
         return jsonify({"success": False, "message": "Missing 'email' in request form."}), 400 # 400 Bad Request
    except Exception as e:
        current_app.logger.error(f"Approve user error: {e}")
        return jsonify({"success": False, "message": "An unexpected error occurred."}), 500


@auth_api_bp.route('/api/admin/delete-user', methods=['POST'])
def delete_user_api():
    is_admin, response, status_code = check_admin()
    if not is_admin:
        return response, status_code

    db_path = current_app.config.get('DATABASE_PATH', 'users.db')
    try:
        email = request.form['email']

        # Prevent admin from deleting themselves (optional safety check)
        admin_user_email = current_app.config.get('ADMIN_USERNAME') # Assuming admin logs in with email
        if email == admin_user_email or email == session.get('email'):
             return jsonify({"success": False, "message": "Admin cannot delete their own account."}), 403

        with sqlite3.connect(db_path) as conn:
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
                }), 404 # 404 Not Found

    except KeyError:
         return jsonify({"success": False, "message": "Missing 'email' in request form."}), 400
    except Exception as e:
        current_app.logger.error(f"Delete user error: {e}")
        return jsonify({"success": False, "message": "An unexpected error occurred."}), 500


@auth_api_bp.route('/api/admin/get-all-users', methods=['GET'])
def get_all_users_api():
    is_admin, response, status_code = check_admin()
    if not is_admin:
        return response, status_code

    db_path = current_app.config.get('DATABASE_PATH', 'users.db')
    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row # Return rows as dict-like objects
            c = conn.cursor()
            # Exclude admin user defined in config if desired? For now, get all.
            # Also exclude password hash from being sent to frontend
            c.execute('SELECT id, username, email, is_approved FROM users')
            all_users = c.fetchall()

            # Convert Row objects to dictionaries, converting is_approved to boolean
            users_list = [
                {"id": user["id"], "username": user["username"], "email": user["email"], "isApproved": bool(user["is_approved"])}
                for user in all_users
            ]

            return jsonify({
                "success": True,
                "users": users_list
            })
    except Exception as e:
        current_app.logger.error(f"Get all users error: {e}")
        return jsonify({"success": False, "message": "Error fetching users."}), 500