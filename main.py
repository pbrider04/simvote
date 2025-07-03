import sqlite3
import os
import json
import io # Import io for CSV export
import csv # Import csv for CSV export
from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse # Import StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from typing import List, Dict, Optional
from datetime import datetime
import uuid
import uvicorn # Import uvicorn

app = FastAPI()

# Get the directory of the current file (main.py)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Configure Jinja2 templates relative to BASE_DIR
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# Mount static files correctly, giving it a 'name'
# Passen Sie diesen Pfad an, falls sich Ihr 'static' Ordner relativ zu main.py geändert hat.
# Basierend auf früheren Beispielen war er direkt neben main.py, also ist BASE_DIR ausreichend.
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

# Database configuration
# Der Pfad zur Datenbankdatei ist jetzt im gemounteten 'data'-Verzeichnis
DATABASE_URL = os.path.join(BASE_DIR, 'data', 'feedback.db') # <-- NEU

# Global variable to store configuration
app_config = {}

def get_db_connection():
    conn = sqlite3.connect(DATABASE_URL)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Stellen Sie sicher, dass das Verzeichnis existiert, bevor Sie versuchen, die DB zu erstellen
    db_dir = os.path.dirname(DATABASE_URL)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir) # Erstellt das Verzeichnis, falls es nicht existiert (im Container)
        
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            description TEXT,
            name TEXT NOT NULL,
            votes INTEGER DEFAULT 0,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            upvoter_id TEXT,
            upvoters TEXT DEFAULT ''
        )
    ''')
    
    cursor.execute("PRAGMA table_info(feedback)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'upvoter_id' not in columns:
        cursor.execute("ALTER TABLE feedback ADD COLUMN upvoter_id TEXT")
    if 'upvoters' not in columns:
        cursor.execute("ALTER TABLE feedback ADD COLUMN upvoters TEXT DEFAULT ''")

    conn.commit()
    conn.close()

# Load configuration on startup
def load_config():
    config_path = os.path.join(BASE_DIR, 'config.json')
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "app_title": "Default App Title",
        "app_description": "Default App Description",
        "logo_path": "/static/default_logo.png"
    }

@app.on_event("startup")
async def startup_event():
    init_db()
    global app_config
    app_config = load_config()

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    db = get_db_connection()
    feedbacks = db.execute('SELECT * FROM feedback ORDER BY votes DESC, timestamp DESC').fetchall()
    
    feedbacks_for_template = []
    for fb in feedbacks:
        fb_dict = dict(fb)
        if fb_dict['upvoters']:
            upvoter_entries = [entry.strip() for entry in fb_dict['upvoters'].split(',') if entry.strip()]
            fb_dict['upvoter_names_list'] = [entry.split(':', 1)[1] for entry in upvoter_entries if ':' in entry]
        else:
            fb_dict['upvoter_names_list'] = []
        feedbacks_for_template.append(fb_dict)

    db.close()
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "feedbacks": feedbacks_for_template, "url_for": request.url_for, "config": app_config}
    )

@app.post("/submit", response_class=RedirectResponse)
async def submit_feedback(
    request: Request,
    question: str = Form(...),
    description: str = Form(""),
    name: str = Form(...),
    upvoter_id: str = Form(...),
    feedback_id: Optional[int] = Form(None)
):
    conn = get_db_connection()
    cursor = conn.cursor()

    if feedback_id is not None:
        cursor.execute(
            'UPDATE feedback SET question = ?, description = ?, name = ? WHERE id = ? AND upvoter_id = ?',
            (question, description, name, feedback_id, upvoter_id)
        )
    else:
        cursor.execute(
            'INSERT INTO feedback (question, description, name, votes, upvoter_id, upvoters) VALUES (?, ?, ?, 0, ?, "")',
            (question, description, name, upvoter_id)
        )
    conn.commit()
    conn.close()
    return RedirectResponse(url="/", status_code=303)

@app.get("/vote/{fid}/{direction}/{upvoter_id_param}/{upvoter_name_param}", response_class=RedirectResponse)
async def vote_feedback(fid: int, direction: str, upvoter_id_param: str, upvoter_name_param: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT upvoters FROM feedback WHERE id = ?', (fid,))
    current_upvoters_raw = cursor.fetchone()
    
    current_upvoters_str = current_upvoters_raw['upvoters'] if current_upvoters_raw and current_upvoters_raw['upvoters'] else ""
    current_upvoters_list = [u.strip() for u in current_upvoters_str.split(',') if u.strip()]
    
    current_upvoter_ids_only = [u.split(':', 1)[0] for u in current_upvoters_list if ':' in u]

    if direction == 'up':
        if upvoter_id_param not in current_upvoter_ids_only:
            cursor.execute('UPDATE feedback SET votes = votes + 1 WHERE id = ?', (fid,))
            new_upvoter_entry = f"{upvoter_id_param}:{upvoter_name_param}"
            updated_upvoters_list = current_upvoters_list + [new_upvoter_entry]
            cursor.execute('UPDATE feedback SET upvoters = ? WHERE id = ?', (','.join(updated_upvoters_list), fid))
    elif direction == 'down':
        if upvoter_id_param in current_upvoter_ids_only:
            cursor.execute('UPDATE feedback SET votes = votes - 1 WHERE id = ?', (fid,))
            updated_upvoters_list = [u for u in current_upvoters_list if not u.startswith(f"{upvoter_id_param}:")]
            cursor.execute('UPDATE feedback SET upvoters = ? WHERE id = ?', (','.join(updated_upvoters_list), fid))
    
    conn.commit()
    conn.close()
    return RedirectResponse(url="/", status_code=303)

@app.get("/table", response_class=HTMLResponse)
async def show_table(request: Request):
    conn = get_db_connection()
    feedbacks = conn.execute('SELECT * FROM feedback ORDER BY timestamp DESC').fetchall()
    conn.close()
    
    feedbacks_for_template = []
    for fb in feedbacks:
        fb_dict = dict(fb)
        if fb_dict['upvoters']:
            upvoter_entries = [entry.strip() for entry in fb_dict['upvoters'].split(',') if entry.strip()]
            fb_dict['upvoter_names_list'] = [entry.split(':', 1)[1] for entry in upvoter_entries if ':' in entry]
        else:
            fb_dict['upvoter_names_list'] = []
        feedbacks_for_template.append(fb_dict)

    return templates.TemplateResponse(
        "table.html",
        {"request": request, "feedbacks": feedbacks_for_template, "url_for": request.url_for, "config": app_config}
    )

@app.get("/export/csv")
async def export_feedback_csv():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, question, description, name, votes, timestamp, upvoter_id, upvoters FROM feedback')
    rows = cursor.fetchall()
    conn.close()

    # Get column names from the cursor description
    column_names = [description[0] for description in cursor.description]

    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow(column_names)

    # Write data rows
    for row in rows:
        writer.writerow(list(row))

    output.seek(0)
    
    headers = {
        "Content-Disposition": "attachment; filename=feedback_export.csv",
        "Content-Type": "text/csv; charset=utf-8"
    }
    return StreamingResponse(output, headers=headers, media_type="text/csv")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)