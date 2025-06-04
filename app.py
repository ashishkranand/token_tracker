import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import mysql.connector
from datetime import date

app = Flask(__name__)
app.secret_key = "your_secret_key"

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

        # Check if user already exists
        cursor.execute("SELECT id FROM users WHERE username=%s", (username,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return render_template('register.html', error="Username already exists.")

        # Register user (default is_admin=0 for regular user)
        cursor.execute("INSERT INTO users (username, password, is_admin) VALUES (%s, %s, %s)",
                       (username, password, 0))
        conn.commit()
        cursor.close()
        conn.close()

        return redirect(url_for('login'))

    return render_template('register.html')

# Login route
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

# Admin and normal user dashboard (for token creation and update)
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

    # Admin sees all tokens; normal users only those NOT counselling complete
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


@app.route('/students')
def students():
    today = date.today()
    conn = get_db_connection()
    cursor = conn.cursor()

    # Students see only tokens NOT counselling complete; admin sees all
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

    return render_template('students.html', tokens=tokens)


# Update token status (admin and normal users allowed)
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
    cursor.close()
    conn.close()
    return jsonify({'success': True})




if __name__ == '__main__':
    app.run(debug=True)

