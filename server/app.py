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
    quantity = data.get("quantity")
    playlist = data.get("playlist", False)
    download_path = data.get("download_path") # Get download path
    if not url:
        return jsonify({"ok": False, "error": "url required"}), 400
    job_id = create_job(url, fmt, quantity, playlist, download_path) # Pass download_path
    return jsonify({"ok": True, "job_id": job_id})

@app.route("/api/jobs", methods=["GET"])
def api_jobs():
    return jsonify(list_jobs())

@app.route("/api/jobs/<job_id>/logs", methods=["GET"])
def api_job_logs(job_id):
    logs = get_job_logs(job_id)
    return jsonify({"logs": logs})

@app.route("/api/jobs/<job_id>/cancel", methods=["POST"])
def api_job_cancel(job_id):
    ok = cancel_job(job_id)
    return jsonify({"ok": ok})

@app.route("/api/folders", methods=["GET"])
def api_folders():
    return jsonify(list_download_folders())

@app.route("/api/folders/<folder_name>", methods=["DELETE"])
def api_delete_folder(folder_name):
    ok = delete_folder(folder_name)
    return jsonify({"ok": ok})

# serve downloads (unsafe, for local only)
@app.route("/downloads/<path:filename>")
def serve_downloads(filename):
    root = os.path.abspath(MAIN_DOWNLOADS_FOLDER)
    return send_from_directory(root, filename, as_attachment=True)

if __name__ == "__main__":
    # Run with: python server/app.py
    app.run(host="127.0.0.1", port=5000, debug=True)
