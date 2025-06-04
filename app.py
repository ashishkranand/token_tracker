import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_socketio import SocketIO
import mysql.connector
from datetime import date

app = Flask(__name__)
app.secret_key = "your_secret_key"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

db_config = {
    'host': os.environ.get("DB_HOST"),
    'user': os.environ.get("DB_USER"),
    'password': os.environ.get("DB_PASSWORD"),
    'database': os.environ.get("DB_NAME"),
    'port': os.environ.get("DB_PORT")
}

def get_db_connection():
    return mysql.connector.connect(**db_config)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()

        if not username or not password:
            return render_template('register.html', error="Username and password are required.")

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM users WHERE username=%s", (username,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return render_template('register.html', error="Username already exists.")

        cursor.execute("INSERT INTO users (username, password, is_admin) VALUES (%s, %s, %s)",
                       (username, password, 0))
        conn.commit()
        cursor.close()
        conn.close()

        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, password, is_admin FROM users WHERE username=%s", (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        if user and user[1] == password:
            session['user_id'] = user[0]
            session['username'] = username
            session['is_admin'] = bool(user[2])
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error="Invalid username or password")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/', methods=['GET', 'POST'])
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    today = date.today()
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM tokens WHERE created_date=%s", (today,))
    token_count = cursor.fetchone()[0]

    if request.method == 'POST':
        if token_count > 0:
            cursor.close()
            conn.close()
            return "Tokens already created for today."

        try:
            num_tokens = int(request.form['num_tokens'])
            for i in range(1, num_tokens + 1):
                cursor.execute(
                    "INSERT INTO tokens (token_number, status, created_date) VALUES (%s, %s, %s)",
                    (i, 'pending', today)
                )
            conn.commit()
        except Exception as e:
            cursor.close()
            conn.close()
            return f"Error: {e}"
        return redirect(url_for('index'))

    if session.get('is_admin'):
        cursor.execute(
            "SELECT id, token_number, status FROM tokens WHERE created_date=%s ORDER BY token_number",
            (today,)
        )
    else:
        cursor.execute(
            "SELECT id, token_number, status FROM tokens WHERE created_date=%s AND status != %s ORDER BY token_number",
            (today, 'counselling complete')
        )

    tokens = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('index.html', tokens=tokens, token_count=token_count)

@app.route('/students', methods=['GET'])
def students():
    today = date.today()
    conn = get_db_connection()
    cursor = conn.cursor()

    if session.get('is_admin'):
        cursor.execute(
            "SELECT token_number, status FROM tokens WHERE created_date=%s ORDER BY token_number",
            (today,)
        )
    else:
        cursor.execute(
            "SELECT token_number, status FROM tokens WHERE created_date=%s AND status != %s ORDER BY token_number",
            (today, 'counselling complete')
        )

    tokens = cursor.fetchall()
    cursor.close()
    conn.close()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify(tokens=[{'number': t[0], 'status': t[1]} for t in tokens])

    return render_template('students.html', tokens=tokens)

@app.route('/update_status', methods=['POST'])
def update_status():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    data = request.get_json()
    token_id = data.get('id')
    status = data.get('status')

    if status not in ['sm verified', 'counselling complete', 'pending']:
        return jsonify({'success': False, 'error': 'Invalid status'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE tokens SET status=%s WHERE id=%s", (status, token_id))
    conn.commit()

    cursor.execute("SELECT token_number, status FROM tokens WHERE id=%s", (token_id,))
    updated_token = cursor.fetchone()

    cursor.close()
    conn.close()

    socketio.emit('status_update', {
        'number': updated_token[0],
        'status': updated_token[1]
    })

    return jsonify({'success': True})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
