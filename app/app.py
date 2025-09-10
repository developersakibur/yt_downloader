# server/app.py
from flask import Flask, request, jsonify, send_from_directory, render_template, Response
import os, json, re
from datetime import datetime

app = Flask(__name__, static_folder="../web", template_folder="../web", static_url_path="")

# allow simple CORS for extension/frontend
@app.after_request
def add_cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS"
    return resp

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/status")
def api_status():
    return jsonify({"ok": True})

def load_db():
    if not os.path.exists(DB_FILE):
        return {"tasks": []}

    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return {"tasks": []}  # blank file
            return json.loads(content)
    except (json.JSONDecodeError, FileNotFoundError):
        return {"tasks": []}


def save_db(db):
    if "tasks" not in db or not isinstance(db["tasks"], list):
        db["tasks"] = []
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2)
    print(f"[DB] Saved {len(db['tasks'])} tasks.")


DB_FILE = "app/database.json"

def create_session_folder(input_value, format_type):
    input_value = input_value.strip()
    format_type = format_type.upper()
    folder_name = ""

    # Try to get real metadata (playlist/channel titles)
    info = None
    try:
        info = _probe_info(input_value)
    except Exception as e:
        print(f"{now()} ⚠️ probe failed, fallback naming: {e}")

    if info and info.get("_type") == "playlist":
        playlist_name = sanitize_name(info.get("title", "Playlist"))
        folder_name = f"{playlist_name}_{format_type}_{now(date=True)}"
    elif "/results?search_query=" in input_value:
        keywords = sanitize_name(input_value.split("search_query=")[-1].replace("+", " "))
        folder_name = f"Search_{keywords}_{format_type}_{now(date=True)}"
    elif info and info.get("uploader"):
        channel_name = sanitize_name(info.get("uploader"))
        if "/shorts" in input_value:
            folder_name = f"{channel_name}_Shorts_{format_type}_{now(date=True)}"
        else:
            folder_name = f"{channel_name}_Videos_{format_type}_{now(date=True)}"
    elif "/shorts/" in input_value:
        folder_name = f"Short_{format_type}_{now(date=True)}"
    elif "watch?v=" in input_value:
        folder_name = f"Single_{format_type}_{now(date=True)}"
    else:
        folder_name = f"Unknown_{format_type}_{now(date=True)}"

    session_folder = os.path.join(main_downloads_folder, folder_name)
    os.makedirs(session_folder, exist_ok=True)
    print(f"✅ Session folder created: {session_folder}")
    return session_folder




def detect_type(url, playlist):
    url = url.strip()
    if ("watch?v=" in url or "youtu.be/" in url) and "list=" in url:
        return "playlist" if playlist else "long"
    if "watch?v=" in url or "youtu.be/" in url:
        return "long"
    if "shorts" in url:
        return "short"
    if "playlist" in url:
        return "playlist"
    if "youtube.com/results" in url:
        return "search"
    if re.match(r"https://www\.youtube\.com/@[^/]+/$", url):
        return "channel_full"
    if "/videos" in url:
        return "channel_longs"
    if "/shorts" in url:
        return "channel_shorts"
    return "unknown"

@app.route("/api/download", methods=["POST"])
def api_download():
    data = request.get_json(force=True)
    url = data.get("url", "").strip()
    format_type = data.get("format", "MP4").upper()
    quantity = data.get("quantity", 25)
    playlist = data.get("playlist", False).lower() == "true"

    if not url:
        return jsonify({"ok": False, "error": "url required"}), 400

    task_type = detect_type(url, playlist)
    task_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    session_folder = create_session_folder(task_type, format_type)

    task = {
        "id": task_id,
        "url": url,
        "type": task_type,
        "format": format_type,
        "quantity": quantity if task_type == "search" else "no",
        "playlist": "True" if playlist else "False",
        "index": "single" if task_type in ["long", "short"] else "multiple",
        "folderpath": f"downloads/{task_id}",
        "status": "pending",
        "files": []
    }

    db = load_db()
    if "tasks" not in db or not isinstance(db.get("tasks"), list):
        db["tasks"] = []
    db["tasks"].insert(0, task)
    save_db(db)

    return jsonify(task)

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=80)