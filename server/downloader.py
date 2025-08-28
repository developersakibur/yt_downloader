# server/downloader.py
import os, subprocess, threading, time, re, unicodedata, shutil
from datetime import datetime
from yt_dlp import YoutubeDL

# --------- CONFIG ---------
COOKIES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.txt")
USE_COOKIES = bool(COOKIES_PATH and os.path.exists(COOKIES_PATH))

# base downloads directory: one level up from this file
MAIN_DOWNLOADS_FOLDER = "D:\\Downloads"
os.makedirs(MAIN_DOWNLOADS_FOLDER, exist_ok=True)

# simple in-memory job store (not persistent)
_jobs = {}
_jobs_lock = threading.Lock()


def now(date=False):
    import pytz
    bd_tz = pytz.timezone("Asia/Dhaka")
    if date:
        return datetime.now(bd_tz).strftime("%Y-%m-%d_%H-%M-%S")
    return datetime.now(bd_tz).strftime("[%H:%M:%S]")


def sanitize_name(name):
    name = (name or "").strip().replace(" ", "-")
    return re.sub(r'[\\/*?:"<>|]', "", name)


class SilentLogger:
    def debug(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): print(msg)


def _with_cookies(opts: dict):
    if USE_COOKIES:
        opts["cookiefile"] = COOKIES_PATH
    return opts


def probe_info(url):
    # Handle YouTube search URLs
    if "youtube.com/results?search_query=" in url:
        query = url.split("search_query=")[-1].replace("+", " ")
        url = f"ytsearch:{query}"

    opts = _with_cookies({"quiet": True, "logger": SilentLogger()})
    with YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)


def _make_session_folder(name, fmt, base_folder):
    safe = sanitize_name(name)
    folder_name = f"{safe}_{fmt}_{now(date=True)}"
    dest = os.path.join(base_folder, folder_name)
    os.makedirs(dest, exist_ok=True)
    return dest


def _sanitize_filename(filename, index, max_length=40):
    sanitized = re.sub(r'[\\/*?:"<>|]', "", filename or "")
    sanitized = sanitized.replace(" ", "-").strip()
    sanitized = unicodedata.normalize('NFC', sanitized)
    base, ext = os.path.splitext(sanitized)
    if len(base) > max_length:
        base = base[:max_length]
    index_str = str(index).replace("/", "-")
    return f"{index_str}_{base}_Sakibur_{now(date=True)}{ext}"


def download_job(job_id, url, fmt, session_folder, quantity=None, playlist=False, progress_callback=None, log_callback=None):
    """Execute a download job. progress_callback(log_line) called with text lines."""
    print(f"Starting download_job for job {job_id}")
    print(f"URL: {url}")
    print(f"Format: {fmt}")
    print(f"Quantity: {quantity}")

    original_url = url # Store original URL for logging

    # Handle YouTube search URLs
    if "youtube.com/results?search_query=" in url:
        query = url.split("search_query=")[-1].replace("+", " ")
        if quantity:
            url = f"ytsearch{quantity}:{query}"
        else:
            url = f"ytsearch:{query}"
        print(f"Converted search URL to: {url}")

    try:
        info = probe_info(original_url) # Use original_url for probing to get proper title
        title = info.get("title", "video")
    except Exception as e:
        if log_callback:
            log_callback(f"Failed probe: {e}\n")
        with _jobs_lock:
            _jobs[job_id]["status"] = "failed"
            _jobs[job_id]["error"] = str(e)
        return

    with _jobs_lock:
        _jobs[job_id].update({"title": title, "status": "running"})

    # support playlist or single
    ydl_opts = {"quiet": True, "logger": SilentLogger()}
    if not playlist:
        ydl_opts['noplaylist'] = True
    if quantity:
        ydl_opts['playlist_items'] = f'1-{quantity}'
    
    print(f"YDL opts: {ydl_opts}")

    with YoutubeDL(_with_cookies(ydl_opts)) as ydl:
        info = ydl.extract_info(url, download=False)
        entries = info.get("entries") or [info]
    
    print(f"Found {len(entries)} entries.")

    total = len(entries)
    for idx, entry in enumerate(entries, 1):
        if _jobs[job_id].get("cancelled"):
            if log_callback:
                log_callback("Job cancelled by user\n")
            with _jobs_lock:
                _jobs[job_id]["status"] = "cancelled"
            return

        index_tag = f"{str(idx).zfill(2)}/{str(total).zfill(2)}" if total > 1 else "(Single)"
        fname = entry.get("title", "video")
        safe_filename = _sanitize_filename(fname, index_tag)

        if fmt == "MP3":
            audio_path = os.path.join(session_folder, f"{safe_filename}.webm")
            mp3_path = os.path.join(session_folder, f"{safe_filename}.mp3")
            ydl_opts_mp3 = _with_cookies({
                "outtmpl": audio_path,
                "format": "bestaudio",
                "quiet": True,
                "logger": SilentLogger(),
            })
            if log_callback:
                log_callback(f"Downloading audio for {fname}\n")
            with YoutubeDL(ydl_opts_mp3) as ydl:
                ydl.download([entry.get("webpage_url") or entry.get("url")])
            # convert via ffmpeg
            cmd = ["ffmpeg", "-y", "-i", audio_path, mp3_path]
            proc = subprocess.Popen(cmd, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
            for line in proc.stderr:
                if log_callback:
                    log_callback(line)
            proc.wait()
            try:
                os.remove(audio_path)
            except:
                pass
            if log_callback:
                log_callback(f"Saved {mp3_path}\n")

        elif fmt == "3GP":
            mp4_path = os.path.join(session_folder, f"{safe_filename}.mp4")
            gp_path = os.path.join(session_folder, f"{safe_filename}.3gp")
            ydl_opts_3gp = _with_cookies({
                "outtmpl": mp4_path,
                "format": "18",
                "quiet": True,
                "logger": SilentLogger(),
            })
            if log_callback:
                log_callback(f"Downloading video for {fname}\n")
            with YoutubeDL(ydl_opts_3gp) as ydl:
                ydl.download([entry.get("webpage_url") or entry.get("url")])
            cmd = [
                "ffmpeg", "-y", "-i", mp4_path,
                "-s", "320x240", "-c:v", "mpeg4", "-b:v", "200k", "-c:a", "aac", "-ac", "1",
                gp_path
            ]
            proc = subprocess.Popen(cmd, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
            for line in proc.stderr:
                if log_callback:
                    log_callback(line)
            proc.wait()
            try:
                os.remove(mp4_path)
            except:
                pass
            if log_callback:
                log_callback(f"Saved {gp_path}\n")

        else:  # MP4
            video_file = os.path.join(session_folder, f"{safe_filename}.video.mp4")
            audio_file = os.path.join(session_folder, f"{safe_filename}.audio.m4a")
            output_file = os.path.join(session_folder, f"{safe_filename}.mp4")
            video_opts = _with_cookies({
                "outtmpl": video_file,
                "format": "bestvideo[ext=mp4][height<=1080]",
                "quiet": True,
                "logger": SilentLogger()
            })
            audio_opts = _with_cookies({
                "outtmpl": audio_file,
                "format": "bestaudio",
                "quiet": True,
                "logger": SilentLogger()
            })
            if log_callback:
                log_callback(f"Downloading video + audio for {fname}\n")
            with YoutubeDL(video_opts) as ydl:
                ydl.download([entry.get("webpage_url") or entry.get("url")])
            with YoutubeDL(audio_opts) as ydl:
                ydl.download([entry.get("webpage_url") or entry.get("url")])
            # ffmpeg merge
            cmd = ["ffmpeg", "-y", "-i", video_file, "-i", audio_file, "-c", "copy", output_file]
            proc = subprocess.Popen(cmd, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
            for line in proc.stderr:
                if log_callback:
                    log_callback(line)
            proc.wait()
            try:
                os.remove(video_file)
                os.remove(audio_file)
            except:
                pass
            if log_callback:
                log_callback(f"Saved {output_file}\n")

    with _jobs_lock:
        _jobs[job_id]["status"] = "completed"
    if log_callback:
        log_callback("Job completed\n")




def create_job(url, fmt, quantity=None, playlist=False, download_path=None):
    # create session folder name using probe if possible
    session_title = "session"
    try:
        if "youtube.com/results?search_query=" in url:
            query = url.split("search_query=")[-1].replace("+", " ")
            session_title = f"Search_{query}"
        elif "youtube.com/playlist?list=" in url or playlist:
            info = probe_info(url)
            playlist_title = info.get("title") or "Playlist"
            session_title = f"Playlist_{playlist_title}"
        else:
            info = probe_info(url)
            session_title = info.get("title") or info.get("uploader") or "session"
    except Exception:
        session_title = "session"

    base_download_folder = download_path if download_path and os.path.isdir(download_path) else MAIN_DOWNLOADS_FOLDER
    session_folder = _make_session_folder(session_title, fmt, base_download_folder)
    job_id = str(int(time.time() * 1000))
    job = {
        "id": job_id,
        "url": url,
        "format": fmt,
        "quantity": quantity,
        "playlist": playlist,
        "status": "queued",
        "title": title,
        "session_folder": session_folder,
        "created_at": now(date=True),
        "cancelled": False
    }
    with _jobs_lock:
        _jobs[job_id] = job
    # run in background thread
    t = threading.Thread(
        target=download_job,
        args=(job_id, url, fmt, session_folder, quantity, playlist, None, lambda ln: _append_log(job_id, ln)),
        daemon=True
    )
    with _jobs_lock:
        _jobs[job_id]["thread"] = t
        _jobs[job_id]["status"] = "running"
    t.start()
    return job_id


def _append_log(job_id, line):
    with _jobs_lock:
        job = _jobs.get(job_id)
        if not job:
            return
        logs = job.get("logs", [])
        logs.append(line)
        # keep limited logs
        if len(logs) > 1000:
            logs = logs[-1000:]
        job["logs"] = logs


def list_jobs():
    with _jobs_lock:
        return {k: {kk: v for kk, v in job.items() if kk != "thread"} for k, job in _jobs.items()}


def get_job_logs(job_id):
    with _jobs_lock:
        job = _jobs.get(job_id)
        if not job:
            return []
        return job.get("logs", [])


def cancel_job(job_id):
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job:
            job["cancelled"] = True
            job["status"] = "cancelled"
            return True
    return False


def delete_folder(folder_name):
    path = os.path.join(MAIN_DOWNLOADS_FOLDER, folder_name)
    if os.path.exists(path) and os.path.isdir(path):
        shutil.rmtree(path)
        return True
    return False


def list_download_folders():
    out = []
    for name in os.listdir(MAIN_DOWNLOADS_FOLDER):
        p = os.path.join(MAIN_DOWNLOADS_FOLDER, name)
        if os.path.isdir(p):
            files = os.listdir(p)
            out.append({"name": name, "files": files, "path": p})
    return out
