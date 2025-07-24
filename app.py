import os
import psycopg2
from flask import Flask, jsonify, request, g
from flask_cors import CORS
import hashlib
import secrets

app = Flask(__name__)
CORS(app)

# Use PostgreSQL connection from environment variable
DATABASE_URL = os.environ.get('DATABASE_URL')

# Simple in-memory session store: token -> user_id
sessions = {}

def get_db():
    if 'db' not in g:
        g.db = psycopg2.connect(DATABASE_URL, sslmode='require')
    return g.db

@app.teardown_appcontext
def close_connection(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()

# Initialize the database with users and todos tables
# Todos table now has a user_id foreign key
def init_db():
    with app.app_context():
        db = get_db()
        cur = db.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS todos (
                id SERIAL PRIMARY KEY,
                text TEXT NOT NULL,
                completed BOOLEAN NOT NULL DEFAULT FALSE,
                user_id INTEGER NOT NULL REFERENCES users(id)
            )
        ''')
        db.commit()
        cur.close()

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
    cur = db.cursor()
    try:
        cur.execute('INSERT INTO users (username, password) VALUES (%s, %s)', 
                    (username, hashlib.sha256(password.encode()).hexdigest()))
        db.commit()
        cur.close()
        return jsonify({'message': 'User registered successfully'})
    except psycopg2.errors.UniqueViolation:
        db.rollback()
        cur.close()
        return jsonify({'error': 'Username already exists'}), 409
    except Exception as e:
        db.rollback()
        cur.close()
        return jsonify({'error': str(e)}), 500

# Login and get a session token
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    db = get_db()
    cur = db.cursor()
    cur.execute('SELECT id, password FROM users WHERE username = %s', (username,))
    user = cur.fetchone()
    cur.close()
    if user and user[1] == hashlib.sha256(password.encode()).hexdigest():
        token = secrets.token_hex(16)
        sessions[token] = user[0]
        return jsonify({'token': token})
    return jsonify({'error': 'Invalid credentials'}), 401

# --- TODOS ENDPOINTS (ALL REQUIRE AUTH) ---

@app.route('/todos', methods=['GET'])
def get_todos():
    user_id = get_user_id_from_token()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    db = get_db()
    cur = db.cursor()
    cur.execute('SELECT id, text, completed FROM todos WHERE user_id = %s', (user_id,))
    todos = [dict(id=row[0], text=row[1], completed=row[2]) for row in cur.fetchall()]
    cur.close()
    return jsonify(todos)

@app.route('/todos', methods=['POST'])
def add_todo():
    user_id = get_user_id_from_token()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    db = get_db()
    cur = db.cursor()
    cur.execute(
        'INSERT INTO todos (text, completed, user_id) VALUES (%s, %s, %s) RETURNING id',
        (data.get('text', ''), data.get('completed', False), user_id)
    )
    new_id = cur.fetchone()[0]
    db.commit()
    cur.execute('SELECT id, text, completed FROM todos WHERE id = %s', (new_id,))
    new_todo = cur.fetchone()
    cur.close()
    return jsonify(dict(id=new_todo[0], text=new_todo[1], completed=new_todo[2])), 201

@app.route('/todos/<int:todo_id>', methods=['DELETE'])
def delete_todo(todo_id):
    user_id = get_user_id_from_token()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    db = get_db()
    cur = db.cursor()
    cur.execute('DELETE FROM todos WHERE id = %s AND user_id = %s', (todo_id, user_id))
    db.commit()
    cur.close()
    return '', 204

@app.route('/todos/<int:todo_id>', methods=['PATCH'])
def update_todo(todo_id):
    user_id = get_user_id_from_token()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    db = get_db()
    cur = db.cursor()
    if 'text' in data:
        cur.execute('UPDATE todos SET text = %s WHERE id = %s AND user_id = %s', (data['text'], todo_id, user_id))
    if 'completed' in data:
        cur.execute('UPDATE todos SET completed = %s WHERE id = %s AND user_id = %s', (data['completed'], todo_id, user_id))
    db.commit()
    cur.execute('SELECT id, text, completed FROM todos WHERE id = %s AND user_id = %s', (todo_id, user_id))
    todo = cur.fetchone()
    cur.close()
    if todo:
        return jsonify(dict(id=todo[0], text=todo[1], completed=todo[2]))
    else:
        return jsonify({'error': 'Todo not found'}), 404

@app.route('/todos/clear_completed', methods=['POST'])
def clear_completed():
    user_id = get_user_id_from_token()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    db = get_db()
    cur = db.cursor()
    cur.execute('DELETE FROM todos WHERE completed = TRUE AND user_id = %s', (user_id,))
    db.commit()
    cur.close()
    return '', 204

# Always initialize the database (for Render and local)
init_db()

if __name__ == "__main__":
    app.run(debug=True)
