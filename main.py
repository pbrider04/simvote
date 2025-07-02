from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import sqlite3
import os
import json
from datetime import datetime
import io
import csv

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

# Global variable for config
config = {}

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
            upvoter_data TEXT DEFAULT '[]'
        )
    ''')
    
    # ... Rest der init_db() Funktion bleibt gleich ...
    # Add upvoter_data column if it doesn't exist (for existing databases)
    try:
        cursor.execute("SELECT upvoter_data FROM feedback LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute("ALTER TABLE feedback ADD COLUMN upvoter_data TEXT DEFAULT '[]'")
    conn.commit()
    conn.close()

def load_config():
    global config
    config_path = os.path.join(BASE_DIR, "config.json")
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"Error: config.json not found at {config_path}. Using empty config.")
        config = {}
    except json.JSONDecodeError:
        print(f"Error: Could not decode config.json at {config_path}. Check JSON format.")
        config = {}


# Initialize the database and load config on startup
@app.on_event("startup")
def startup_event():
    init_db()
    load_config()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    conn = get_db_connection()
    feedbacks_raw = conn.execute('SELECT * FROM feedback ORDER BY votes DESC, timestamp DESC').fetchall()
    
    feedbacks = []
    for fb_row in feedbacks_raw:
        fb = dict(fb_row) # Convert Row object to dict for easier manipulation
        try:
            upvoter_list = json.loads(fb['upvoter_data'])
            # Extract names for display and count unique IDs for votes
            upvoter_names = [voter['name'] for voter in upvoter_list if 'name' in voter]
            
            fb['upvoter_names_list'] = upvoter_names # For display in template
            fb['votes'] = len(upvoter_list) # Votes are now derived from unique upvoter IDs
        except json.JSONDecodeError:
            # Handle cases where upvoter_data might be malformed or empty
            fb['upvoter_names_list'] = []
            fb['votes'] = 0
            # Potentially log this error or try to fix the data in DB

        feedbacks.append(fb)
    conn.close()
    
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "feedbacks": feedbacks, "url_for": request.url_for, "config": config}
    )

@app.post("/submit", response_class=RedirectResponse)
async def submit_feedback(
    question: str = Form(...),
    description: str = Form(""),
    name: str = Form(...)
):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO feedback (question, description, name, votes, upvoter_data) VALUES (?, ?, ?, 0, ?)',
        (question, description, name, '[]') # Initialize upvoter_data as empty JSON array
    )
    conn.commit()
    conn.close()
    return RedirectResponse(url="/", status_code=303)

@app.get("/vote/{fid}/{direction}/{upvoter_id_param}/{upvoter_name_param}", response_class=RedirectResponse)
async def vote_feedback(
    fid: int, 
    direction: str, 
    upvoter_id_param: str, 
    upvoter_name_param: str,
    request: Request # Request object needed for url_for in template
):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT upvoter_data FROM feedback WHERE id = ?', (fid,))
    result = cursor.fetchone()
    
    upvoter_data_json = result['upvoter_data'] if result and result['upvoter_data'] else '[]'
    upvoters = json.loads(upvoter_data_json)
    
    # Create a set of existing upvoter IDs for efficient lookup
    upvoter_ids_set = {voter['id'] for voter in upvoters if 'id' in voter}

    updated = False
    if direction == 'up':
        if upvoter_id_param not in upvoter_ids_set:
            upvoters.append({"id": upvoter_id_param, "name": upvoter_name_param})
            updated = True
    elif direction == 'down':
        # Remove the voter if they exist
        initial_len = len(upvoters)
        upvoters = [v for v in upvoters if v.get('id') != upvoter_id_param]
        if len(upvoters) < initial_len:
            updated = True
    
    if updated:
        new_votes = len(upvoters)
        new_upvoter_data_json = json.dumps(upvoters)
        cursor.execute('UPDATE feedback SET votes = ?, upvoter_data = ? WHERE id = ?',
                    (new_votes, new_upvoter_data_json, fid))
        conn.commit()
    
    conn.close()
    return RedirectResponse(url="/", status_code=303)

@app.get("/table", response_class=HTMLResponse)
async def show_table(request: Request):
    conn = get_db_connection()
    feedbacks_raw = conn.execute('SELECT * FROM feedback ORDER BY timestamp DESC').fetchall()
    conn.close()

    # Prepare data for display in the table, including processing upvoter_data
    feedbacks_for_table = []
    for fb_row in feedbacks_raw:
        fb = dict(fb_row)
        try:
            upvoter_list = json.loads(fb['upvoter_data'])
            # Display upvoter IDs as a comma-separated string for the table
            fb['upvoter_ids_display'] = ", ".join([voter['id'] for voter in upvoter_list if 'id' in voter])
            fb['upvoter_names_display'] = ", ".join([voter['name'] for voter in upvoter_list if 'name' in voter])
        except json.JSONDecodeError:
            fb['upvoter_ids_display'] = ""
            fb['upvoter_names_display'] = ""
        feedbacks_for_table.append(fb)

    return templates.TemplateResponse(
        "table.html",
        {"request": request, "feedbacks": feedbacks_for_table, "url_for": request.url_for, "config": config}
    )

@app.get("/export-csv")
async def export_csv():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, question, description, name, votes, timestamp, upvoter_data FROM feedback ORDER BY timestamp DESC')
    rows = cursor.fetchall()
    conn.close()

    # Get column names (excluding row_factory's automatic index, use actual column names)
    column_names = [description[0] for description in cursor.description]

    # Handle upvoter_data for CSV export (flatten it or make it readable)
    processed_rows = []
    for row in rows:
        row_dict = dict(row) # Convert Row to dict
        try:
            upvoter_list = json.loads(row_dict['upvoter_data'])
            upvoter_ids = "; ".join([voter['id'] for voter in upvoter_list if 'id' in voter])
            upvoter_names = "; ".join([voter['name'] for voter in upvoter_list if 'name' in voter])
            row_dict['upvoter_data_ids'] = upvoter_ids
            row_dict['upvoter_data_names'] = upvoter_names
        except json.JSONDecodeError:
            row_dict['upvoter_data_ids'] = ""
            row_dict['upvoter_data_names'] = ""
        
        # Select and reorder columns for CSV
        processed_rows.append([
            row_dict['id'],
            row_dict['question'],
            row_dict['description'],
            row_dict['name'],
            row_dict['votes'],
            row_dict['timestamp'],
            row_dict['upvoter_data_ids'], # New column
            row_dict['upvoter_data_names'] # New column
        ])
    
    # Update headers for CSV
    csv_headers = ['ID', 'Frage', 'Beschreibung', 'Name', 'Votes', 'Zeitstempel', 'Upvoter IDs', 'Upvoter Namen']

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(csv_headers)
    writer.writerows(processed_rows)

    response = Response(content=output.getvalue(), media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=feedback_export.csv"
    return response


# To run with uvicorn: uvicorn main:app --reload
if __name__ == '__main__':
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)