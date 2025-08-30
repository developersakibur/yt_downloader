# server/app.py
from flask import Flask, request, jsonify, send_from_directory, render_template, Response
from threading import Thread
import os, time, json
from downloader import create_job, list_jobs, get_job_logs, cancel_job, delete_folder, list_download_folders, MAIN_DOWNLOADS_FOLDER

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

@app.route("/api/download", methods=["POST"])
def api_download():
    data = request.get_json(force=True)
    url = data.get("url")
    fmt = data.get("format", "MP4").upper()
    quantity = data.get("quantity", 25)
    playlist = data.get("playlist", False)
    if not url:
        return jsonify({"ok": False, "error": "url required"}), 400
    job_id = create_job(url, fmt, quantity, playlist) # Pass download_path
    return jsonify({"ok": True, "job_id": job_id})

@app.route("/api/downloads")
def api_downloads():
    folders = []
    for folder_name in os.listdir(MAIN_DOWNLOADS_FOLDER):
        if "MP3" in folder_name.upper() or "3GP" in folder_name.upper() or "MP4" in folder_name.upper():
            folder_path = os.path.join(MAIN_DOWNLOADS_FOLDER, folder_name)
            if os.path.isdir(folder_path):
                files = os.listdir(folder_path)
                folders.append({"name": folder_name, "files": files})
    return jsonify(folders)

# serve downloads (unsafe, for local only)

