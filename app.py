from flask import Flask, jsonify, request, g
from flask_cors import CORS
import sqlite3
import hashlib
import secrets

app = Flask(__name__)
CORS(app)  # This enables CORS for all routes

DATABASE = "todos.db"

# Simple in-memory session store: token -> user_id
sessions = {}

def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()

# Initialize the database with users and todos tables
# Todos table now has a user_id foreign key

def init_db():
    with app.app_context():
        db = get_db()
        db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        db.execute('''
            CREATE TABLE IF NOT EXISTS todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                completed BOOLEAN NOT NULL DEFAULT 0,
                user_id INTEGER NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        db.commit()

# Helper to get user_id from session token

def get_user_id_from_token():
    token = request.headers.get('Authorization')
    return sessions.get(token)

@app.route("/")
def home():
    return "Hello, World!"

# --- AUTHENTICATION ENDPOINTS ---

# Register a new user
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    db = get_db()
    try:
        db.execute('INSERT INTO users (username, password) VALUES (?, ?)', 
                   (username, hashlib.sha256(password.encode()).hexdigest()))
        db.commit()
        return jsonify({'message': 'User registered successfully'})
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Username already exists'}), 409

# Login and get a session token
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    db = get_db()
    cur = db.execute('SELECT id, password FROM users WHERE username = ?', (username,))
    user = cur.fetchone()
    if user and user['password'] == hashlib.sha256(password.encode()).hexdigest():
        token = secrets.token_hex(16)
        sessions[token] = user['id']
        return jsonify({'token': token})
    return jsonify({'error': 'Invalid credentials'}), 401

# --- TODOS ENDPOINTS (ALL REQUIRE AUTH) ---

@app.route('/todos', methods=['GET'])
def get_todos():
    user_id = get_user_id_from_token()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    db = get_db()
    cur = db.execute("SELECT id, text, completed FROM todos WHERE user_id = ?", (user_id,))
    todos = [dict(row) for row in cur.fetchall()]
    return jsonify(todos)

@app.route('/todos', methods=['POST'])
def add_todo():
    user_id = get_user_id_from_token()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    db = get_db()
    cur = db.execute(
        'INSERT INTO todos (text, completed, user_id) VALUES (?, ?, ?)',
        (data.get('text', ''), data.get('completed', False), user_id)
    )
    db.commit()
    new_id = cur.lastrowid
    cur = db.execute('SELECT id, text, completed FROM todos WHERE id = ?', (new_id,))
    new_todo = dict(cur.fetchone())
    return jsonify(new_todo), 201

@app.route('/todos/<int:todo_id>', methods=['DELETE'])
def delete_todo(todo_id):
    user_id = get_user_id_from_token()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    db = get_db()
    db.execute('DELETE FROM todos WHERE id = ? AND user_id = ?', (todo_id, user_id))
    db.commit()
    return '', 204

@app.route('/todos/<int:todo_id>', methods=['PATCH'])
def update_todo(todo_id):
    user_id = get_user_id_from_token()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    db = get_db()
    if 'text' in data:
        db.execute('UPDATE todos SET text = ? WHERE id = ? AND user_id = ?', (data['text'], todo_id, user_id))
    if 'completed' in data:
        db.execute('UPDATE todos SET completed = ? WHERE id = ? AND user_id = ?', (data['completed'], todo_id, user_id))
    db.commit()
    cur = db.execute('SELECT id, text, completed FROM todos WHERE id = ? AND user_id = ?', (todo_id, user_id))
    todo = cur.fetchone()
    if todo:
        return jsonify(dict(todo))
    else:
        return jsonify({'error': 'Todo not found'}), 404

@app.route('/todos/clear_completed', methods=['POST'])
def clear_completed():
    user_id = get_user_id_from_token()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    db = get_db()
    db.execute('DELETE FROM todos WHERE completed = 1 AND user_id = ?', (user_id,))
    db.commit()
    return '', 204

init_db()

if __name__ == "__main__":
    app.run(debug=True)
