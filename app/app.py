from flask import Flask, request, render_template, redirect
import sqlite3
import os
from datetime import datetime

app = Flask(__name__, template_folder='templates', static_folder='static')

DB_FILE = 'feedback.db'

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    if not os.path.exists(DB_FILE):
        db = get_db()
        db.execute('''
            CREATE TABLE feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL,
                description TEXT,
                name TEXT NOT NULL,
                votes INTEGER DEFAULT 0,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        db.commit()

@app.route('/')
def index():
    db = get_db()
    feedbacks = db.execute('SELECT * FROM feedback ORDER BY votes DESC, timestamp DESC').fetchall()
    return render_template('index.html', feedbacks=feedbacks)

@app.route('/submit', methods=['POST'])
def submit():
    question = request.form['question']
    description = request.form['description']
    name = request.form['name']
    db = get_db()
    db.execute('INSERT INTO feedback (question, description, name, votes) VALUES (?, ?, ?, 0)',
               (question, description, name))
    db.commit()
    return redirect('/')

@app.route('/vote/<int:fid>/<direction>')
def vote(fid, direction):
    db = get_db()
    if direction == 'up':
        db.execute('UPDATE feedback SET votes = votes + 1 WHERE id = ?', (fid,))
    elif direction == 'down':
        db.execute('UPDATE feedback SET votes = votes - 1 WHERE id = ?', (fid,))
    db.commit()
    return redirect('/')

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)
