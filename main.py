import sqlite3
import os
import json
import io # Import io for CSV export
import csv # Import csv for CSV export
from fastapi import FastAPI, Request, Form, Depends, HTTPException, UploadFile, File # Added UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse, FileResponse # Added FileResponse
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
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

# Database configuration
DATABASE_DIR = os.path.join(BASE_DIR, 'data') # NEW: Directory for the database
DATABASE_URL = os.path.join(DATABASE_DIR, 'feedback.db') # Updated DATABASE_URL

# Global variable to store configuration
app_config = {}

def get_db_connection():
    conn = sqlite3.connect(DATABASE_URL)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    # Ensure the database directory exists
    if not os.path.exists(DATABASE_DIR):
        os.makedirs(DATABASE_DIR)
        
    conn = sqlite3.connect(DATABASE_URL) # Connect after ensuring dir exists
    cursor = conn.cursor()
    
    # NEU: Feedback-Tabelle anpassen
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            description TEXT,
            name TEXT NOT NULL,
            votes INTEGER DEFAULT 0,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            browser_id TEXT, -- upvoter_id wird zu browser_id
            upvoters TEXT DEFAULT '' -- Speichert browser_ids als Komma-getrennte Liste
        )
    ''')
    
    # NEU: identities-Tabelle hinzufügen
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS identities (
            browser_id TEXT NOT NULL,
            name TEXT NOT NULL,
            UNIQUE(browser_id, name)
        )
    ''')

    # Spalten-Checks und Anpassungen für die Feedback-Tabelle (falls DB bereits existiert)
    cursor.execute("PRAGMA table_info(feedback)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'upvoter_id' in columns: # Alte Spalte entfernen (falls vorhanden)
        try:
            cursor.execute("ALTER TABLE feedback DROP COLUMN upvoter_id")
        except sqlite3.OperationalError:
            # Drop column might not be supported easily in older SQLite versions or if column is only one
            # For simplicity, we assume a fresh start or manual handling if this fails.
            pass # Keep it for now or handle manually if migration is complex
    
    if 'browser_id' not in columns: # Neue Spalte hinzufügen
        cursor.execute("ALTER TABLE feedback ADD COLUMN browser_id TEXT")
    
    if 'upvoters' not in columns: # Spalte hinzufügen, falls nicht vorhanden
        cursor.execute("ALTER TABLE feedback ADD COLUMN upvoters TEXT DEFAULT ''")

    conn.commit()
    conn.close()

# Load configuration on startup
def load_config():
    config_path = os.path.join(BASE_DIR, 'config.json')
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
            # Ensure app_maintainance_hint exists, set to empty string if not
            config_data.setdefault("app_maintainance_hint", "")
            return config_data
    return {
        "app_title": "Default App Title",
        "app_description": "Default App Description",
        "logo_path": "/static/default_logo.png",
        "app_maintainance_hint": "" # Default to empty string
    }

@app.on_event("startup")
async def startup_event():
    init_db()
    global app_config
    app_config = load_config()

# Hilfsfunktion, um Namen aus browser_ids zu holen
def get_names_for_browser_ids(browser_ids: List[str]) -> Dict[str, str]:
    if not browser_ids:
        return {}
    conn = get_db_connection()
    cursor = conn.cursor()
    # SQLITE_LIMIT_VARIABLE_NUMBER is 999. Use safe approach for many IDs.
    placeholders = ','.join('?' for _ in browser_ids)
    
    # Fetch all names for the given browser_ids
    cursor.execute(f"SELECT browser_id, name FROM identities WHERE browser_id IN ({placeholders})", browser_ids)
    name_map = {row['browser_id']: row['name'] for row in cursor.fetchall()}
    conn.close()
    return name_map


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    db = get_db_connection()
    feedbacks = db.execute('SELECT * FROM feedback ORDER BY votes DESC, timestamp DESC').fetchall()
    db.close()
    
    feedbacks_for_template = []
    all_browser_ids_to_fetch = set()

    for fb in feedbacks:
        fb_dict = dict(fb)
        # NEU: upvoters sind jetzt nur IDs
        if fb_dict['upvoters']:
            upvoter_ids = [entry.strip() for entry in fb_dict['upvoters'].split(',') if entry.strip()]
            all_browser_ids_to_fetch.update(upvoter_ids) # IDs für spätere Abfrage sammeln
            fb_dict['raw_upvoter_ids'] = upvoter_ids # Speichern der IDs zur späteren Verwendung
        else:
            fb_dict['raw_upvoter_ids'] = []
        feedbacks_for_template.append(fb_dict)

    # NEU: Namen für alle gesammelten Browser-IDs abrufen
    name_lookup = get_names_for_browser_ids(list(all_browser_ids_to_fetch))

    # upvoter_names_list befüllen
    for fb_dict in feedbacks_for_template:
        fb_dict['upvoter_names_list'] = [name_lookup.get(bid, 'Unbekannt') for bid in fb_dict['raw_upvoter_ids']]
        
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
    browser_id: str = Form(...), # upvoter_id wird zu browser_id
    feedback_id: Optional[int] = Form(None)
):
    conn = get_db_connection()
    cursor = conn.cursor()

    # NEU: Browser-ID und Name in identities-Tabelle speichern (falls nicht vorhanden)
    cursor.execute(
        'INSERT OR IGNORE INTO identities (browser_id, name) VALUES (?, ?)',
        (browser_id, name)
    )

    if feedback_id is not None:
        # NEU: Beim Editieren votes und upvoters unverändert lassen
        cursor.execute(
            'UPDATE feedback SET question = ?, description = ?, name = ?, browser_id = ? WHERE id = ?',
            (question, description, name, browser_id, feedback_id)
        )
    else:
        # NEU: Beim Einreichen einer neuen Frage
        # upvoters mit eigener ID initialisieren und votes auf 1 setzen
        initial_upvoters = browser_id
        initial_votes = 1
        cursor.execute(
            'INSERT INTO feedback (question, description, name, votes, browser_id, upvoters) VALUES (?, ?, ?, ?, ?, ?)',
            (question, description, name, initial_votes, browser_id, initial_upvoters)
        )
    conn.commit()
    conn.close()
    return RedirectResponse(url="/", status_code=303)

@app.get("/vote/{fid}/{direction}/{browser_id_param}/{name_param}", response_class=RedirectResponse) # upvoter_id_param wird zu browser_id_param
async def vote_feedback(fid: int, direction: str, browser_id_param: str, name_param: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    # NEU: Browser-ID und Name in identities-Tabelle speichern (falls nicht vorhanden)
    cursor.execute(
        'INSERT OR IGNORE INTO identities (browser_id, name) VALUES (?, ?)',
        (browser_id_param, name_param)
    )

    cursor.execute('SELECT upvoters FROM feedback WHERE id = ?', (fid,))
    current_upvoters_raw = cursor.fetchone()
    
    current_upvoters_str = current_upvoters_raw['upvoters'] if current_upvoters_raw and current_upvoters_raw['upvoters'] else ""
    current_upvoters_list = [u.strip() for u in current_upvoters_str.split(',') if u.strip()] # Liste der IDs

    updated_upvoters_list = list(current_upvoters_list) # Kopie erstellen

    if direction == 'up':
        if browser_id_param not in updated_upvoters_list:
            updated_upvoters_list.append(browser_id_param)
    elif direction == 'down':
        if browser_id_param in updated_upvoters_list:
            updated_upvoters_list.remove(browser_id_param)
    
    # NEU: Votes aus der Anzahl der Upvoter ermitteln
    new_votes = len(updated_upvoters_list)
    new_upvoters_str = ','.join(updated_upvoters_list)

    cursor.execute(
        'UPDATE feedback SET votes = ?, upvoters = ? WHERE id = ?',
        (new_votes, new_upvoters_str, fid)
    )
    
    conn.commit()
    conn.close()
    return RedirectResponse(url="/", status_code=303)

@app.get("/table", response_class=HTMLResponse)
async def show_table(request: Request):
    conn = get_db_connection()
    feedbacks = conn.execute('SELECT * FROM feedback ORDER BY timestamp DESC').fetchall()
    conn.close()
    
    feedbacks_for_template = []
    all_browser_ids_to_fetch = set()

    for fb in feedbacks:
        fb_dict = dict(fb)
        # NEU: upvoters sind jetzt nur IDs
        if fb_dict['upvoters']:
            upvoter_ids = [entry.strip() for entry in fb_dict['upvoters'].split(',') if entry.strip()]
            all_browser_ids_to_fetch.update(upvoter_ids) # IDs für spätere Abfrage sammeln
            fb_dict['raw_upvoter_ids'] = upvoter_ids # Speichern der IDs zur späteren Verwendung
        else:
            fb_dict['raw_upvoter_ids'] = []
        feedbacks_for_template.append(fb_dict)

    # NEU: Namen für alle gesammelten Browser-IDs abrufen
    name_lookup = get_names_for_browser_ids(list(all_browser_ids_to_fetch))

    # upvoter_names_list befüllen
    for fb_dict in feedbacks_for_template:
        fb_dict['upvoter_names_list'] = [name_lookup.get(bid, 'Unbekannt') for bid in fb_dict['raw_upvoter_ids']]


    return templates.TemplateResponse(
        "table.html",
        {"request": request, "feedbacks": feedbacks_for_template, "url_for": request.url_for, "config": app_config}
    )

@app.get("/export/csv")
async def export_feedback_csv():
    conn = get_db_connection()
    cursor = conn.cursor()
    # NEU: browser_id statt upvoter_id abfragen
    cursor.execute('SELECT id, question, description, name, votes, timestamp, browser_id, upvoters FROM feedback')
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

@app.get("/download_db")
async def download_db():
    """Endpoint to download the feedback.db file."""
    if not os.path.exists(DATABASE_URL):
        raise HTTPException(status_code=404, detail="Database file not found.")
    
    return FileResponse(
        path=DATABASE_URL,
        media_type="application/octet-stream", # Generic binary file
        filename="feedback.db",
        headers={"Content-Disposition": "attachment; filename=feedback.db"}
    )

@app.post("/upload_db", response_class=RedirectResponse)
async def upload_db(db_file: UploadFile = File(...)):
    """Endpoint to upload and replace the feedback.db file."""
    if db_file.filename != "feedback.db":
        raise HTTPException(status_code=400, detail="Only 'feedback.db' files are accepted.")

    try:
        # Ensure the database directory exists
        if not os.path.exists(DATABASE_DIR):
            os.makedirs(DATABASE_DIR)

        # IMPORTANT: Close all existing DB connections before replacing the file
        # This is a critical step to prevent database locking issues.
        # In a real application, you might need a more robust connection management.
        # For this simple example, we assume no active connections during upload.

        # Save the uploaded file, overwriting the old one
        with open(DATABASE_URL, "wb") as buffer:
            while True:
                chunk = await db_file.read(1024) # Read in chunks
                if not chunk:
                    break
                buffer.write(chunk)
        
        # Re-initialize the database schema if the new DB is empty or lacks tables
        # This ensures the table structure exists after an upload,
        # but won't alter existing data in an already structured DB.
        init_db()

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading database file: {e}")
    
    return RedirectResponse(url="/", status_code=303) # Redirect to home after upload


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)