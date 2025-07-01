from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import sqlite3
import os
from datetime import datetime
import json

app = FastAPI()

templates = Jinja2Templates(directory="templates")

def from_json_filter(value):
    if value:
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return []
    return []

templates.env.filters["from_json"] = from_json_filter

app.mount("/static", StaticFiles(directory="static"), name="static")

DATABASE_URL = 'feedback.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE_URL)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            description TEXT,
            name TEXT NOT NULL,
            votes INTEGER DEFAULT 0,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            upvoters TEXT DEFAULT '[]'
        )
    ''')
    conn.commit()
    conn.close()

@app.on_event("startup")
async def startup_event():
    init_db()

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    db = get_db_connection()
    # Sortierung wie bisher: nach Votes (die jetzt direkt den Upvotern entsprechen)
    feedbacks = db.execute('SELECT * FROM feedback ORDER BY votes DESC, timestamp DESC').fetchall()
    db.close()
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "feedbacks": feedbacks, "current_user": None}
    )

@app.post("/submit", response_class=RedirectResponse)
async def submit_feedback(
    question: str = Form(...),
    description: str = Form(""),
    name: str = Form(...)
):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Der Ersteller ist automatisch der erste Upvoter
    upvoters_list = [name]
    initial_votes = 1 # Startet mit einer Stimme vom Ersteller
    upvoters_json = json.dumps(upvoters_list)

    cursor.execute(
        'INSERT INTO feedback (question, description, name, votes, upvoters) VALUES (?, ?, ?, ?, ?)',
        (question, description, name, initial_votes, upvoters_json)
    )
    conn.commit()
    conn.close()
    return RedirectResponse(url="/", status_code=303)

@app.get("/vote/{fid}/{direction}/{voter_name}", response_class=RedirectResponse)
async def vote_feedback(fid: int, direction: str, voter_name: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    feedback_row = conn.execute('SELECT votes, upvoters FROM feedback WHERE id = ?', (fid,)).fetchone()
    if not feedback_row:
        raise HTTPException(status_code=404, detail="Feedback not found")

    current_upvoters = json.loads(feedback_row['upvoters'])

    if direction == 'up':
        if voter_name not in current_upvoters:
            current_upvoters.append(voter_name)
    elif direction == 'down':
        # Nur downvoten, wenn der Nutzer zuvor upgevoted hat
        if voter_name in current_upvoters:
            current_upvoters.remove(voter_name)
        else:
            # Wenn der Nutzer nicht in der Liste ist, passiert nichts oder eine Nachricht
            print(f"User {voter_name} cannot downvote feedback {fid} as they haven't upvoted it.")
            conn.close()
            return RedirectResponse(url="/", status_code=303)
    else:
        raise HTTPException(status_code=400, detail="Invalid vote direction")

    # Anzahl der Votes entspricht immer der Anzahl der Upvoter
    updated_votes = len(current_upvoters)
    updated_upvoters_json = json.dumps(current_upvoters)

    cursor.execute(
        'UPDATE feedback SET votes = ?, upvoters = ? WHERE id = ?',
        (updated_votes, updated_upvoters_json, fid)
    )
    conn.commit()
    conn.close()
    return RedirectResponse(url="/", status_code=303)