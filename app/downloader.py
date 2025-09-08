# server/downloader.py

import os, subprocess, warnings, pytz, time, re, unicodedata, shutil
from datetime import datetime
from yt_dlp import YoutubeDL
from threading import Thread

warnings.filterwarnings("ignore")

# --------- CONFIG ---------
# set your cookies file path once (or via env var YTDLP_COOKIES_PATH)
COOKIES_PATH = os.environ.get("YTDLP_COOKIES_PATH", r"")  # e.g. r"D:\YTDLP\cookies.txt" or leave empty
USE_COOKIES = bool(COOKIES_PATH and os.path.exists(COOKIES_PATH))


current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
main_downloads_folder = os.path.join(parent_dir, "yt_downloads")
os.makedirs(main_downloads_folder, exist_ok=True)

MAIN_DOWNLOADS_FOLDER = main_downloads_folder

# --------- HELPERS ---------
def now(date=False):
    import pytz
    bd_tz = pytz.timezone("Asia/Dhaka")
    if date:
        return datetime.now(bd_tz).strftime("%Y-%m-%d_%H-%M-%S")
    return datetime.now(bd_tz).strftime("[%H-%M-%S]")

def sanitize_name(name: str):
    name = (name or "").strip().replace(" ", "-")
    return re.sub(r'[\\/*?:">|]', "", name)

class SilentLogger:
    def debug(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): print(msg)

def sanitize_filename(filename, index, max_length=30):
    sanitized = re.sub(r'[\\/*?:">|]', "", filename or "")
    sanitized = sanitized.replace(" ", "-").strip()
    sanitized = unicodedata.normalize('NFC', sanitized)
    base, ext = os.path.splitext(sanitized)
    if len(base) > max_length:
        base = base[:max_length]
    index_str = str(index).replace("/", "-")
    return f"{index_str}_{base}_Sakibur_{now(date=True)}{ext}"

def download_file(filepath):
    size_mb = os.path.getsize(filepath) / (1024*1024)
    print(f"{now()} 📥 Downloaded - ({size_mb:.2f} MiB) - {os.path.basename(filepath)}")

def create_progress_hook(message="⬇️ Downloading"):
    last_line_length = [0]
    def progress_hook(d):
        if d['status'] == 'downloading':
            downloaded = d.get('_downloaded_bytes_str') or f"{d['downloaded_bytes']/1024**2:.2f}MiB"
            total = d.get('_total_bytes_str') or (f"{d['total_bytes']/1024**2:.2f}MiB" if d.get('total_bytes') else '???')
            speed = d.get('_speed_str') or (f"{d['speed']/1024**2:.2f}MiB/s" if d.get('speed') else '??')
            eta = d.get('_eta_str') or time.strftime('%H:%M:%S', time.gmtime(d.get('eta',0)))
            progress = d.get('_percent_str') or (f"{(d['downloaded_bytes']/d['total_bytes']*100):.1f}%" if d.get('total_bytes') else '??%')
            line = f"{now()} {message} - {downloaded}/{total} - {progress} - {speed} - {eta}"
            print('\r' + ' '*last_line_length[0] + '\r' + line, end='', flush=True)
            last_line_length[0] = len(line)
        elif d['status'] == 'finished':
            print()
    return progress_hook

def ffmpeg_convert_with_progress(input_files, output_file, format_type, ffmpeg_args=None):
    if ffmpeg_args is None: ffmpeg_args = []
    max_size_mib = sum(os.path.getsize(f) for f in input_files)/(1024*1024)
    cmd = ["ffmpeg", "-y"] + sum([["-i", f] for f in input_files], []) + ffmpeg_args + [output_file]

    # Force UTF-8 text to avoid cp1252 decode errors on Windows
    process = subprocess.Popen(cmd, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")

    duration_pattern = re.compile(r"Duration: (\d+):(\d+):(\d+\.\d+)")
    time_pattern = re.compile(r"time=(\d+):(\d+):(\d+\.\d+)")
    duration_seconds = None
    last_percent = -1
    start_time = time.time()
    last_line_length = 0

    for line in process.stderr:
        line = line.strip()
        if duration_seconds is None:
            m = duration_pattern.search(line)
            if m:
                h, m_, s = m.groups()
                duration_seconds = int(h)*3600 + int(m_)*60 + float(s)
                continue
        m = time_pattern.search(line)
        if m and duration_seconds:
            h, m_, s = m.groups()
            current_seconds = int(h)*3600 + int(m_)*60 + float(s)
            percent = (current_seconds/duration_seconds)*100
            elapsed = time.time()-start_time
            speed = current_seconds/elapsed if elapsed>0 else 0
            eta_seconds = (duration_seconds-current_seconds)/speed if speed>0 else 0
            eta = time.strftime('%H:%M:%S', time.gmtime(eta_seconds))
            if int(percent)!=int(last_percent):
                now_str = time.strftime("[%H:%M:%S]")
                converted_mib = max_size_mib*(percent/100)
                line_out = f"{now_str} 🔄 Converting to {format_type} - {converted_mib:.2f}MiB/{max_size_mib:.2f}MiB - {percent:.1f}% - {speed:.2f}MiB/s - {eta}"
                print('\r'+' '*last_line_length+'\r'+line_out,end='',flush=True)
                last_line_length = len(line_out)
                last_percent = percent
    process.wait()
    print()

def _with_cookies(opts: dict):
    if USE_COOKIES:
        opts["cookiefile"] = "cookies/cookies.txt"
    return opts

def _probe_info(url):
    opts = _with_cookies({"quiet": True, "logger": SilentLogger()})
    with YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)

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

def download_single_video(url, format_type, session_folder, index="(Single)"):
    format_type = format_type.upper()
    info = _probe_info(url)
    title = info.get("title","video")
    print(f"{now()} 🔷 {index} - {title}")
    title = sanitize_filename(title,index)

    if format_type == "MP3":
        audio_path = os.path.join(session_folder,f"{title}.webm")
        mp3_path = os.path.join(session_folder,f"{title}.mp3")
        ydl_opts = _with_cookies({
            "outtmpl": audio_path,
            "format": "bestaudio",
            "quiet": True,
            "progress_hooks": [create_progress_hook("🎧 Downloading Audio")],
            "logger": SilentLogger()
        })
        with YoutubeDL(ydl_opts) as ydl: ydl.download([url])
        ffmpeg_convert_with_progress([audio_path], mp3_path,"MP3")
        os.remove(audio_path)
        download_file(mp3_path)

    elif format_type == "3GP":
        mp4_path = os.path.join(session_folder,f"{title}.mp4")
        gp_path = os.path.join(session_folder,f"{title}.3gp")
        ydl_opts = _with_cookies({
            "outtmpl": mp4_path,
            "format": "18",
            "quiet": True,
            "progress_hooks": [create_progress_hook("🎥 Downloading Video")],
            "logger": SilentLogger()
        })
        with YoutubeDL(ydl_opts) as ydl: ydl.download([url])
        ffmpeg_convert_with_progress([mp4_path], gp_path,"3GP",["-s","320x240","-c:v","mpeg4","-b:v","200k","-c:a","aac","-ac","1"])
        os.remove(mp4_path)
        download_file(gp_path)

    elif format_type == "MP4":
        video_file = os.path.join(session_folder,f"{title}.video.mp4")
        audio_file = os.path.join(session_folder,f"{title}.audio.m4a")
        output_file = os.path.join(session_folder,f"{title}.mp4")
        video_opts = _with_cookies({
            "outtmpl": video_file,
            "format": "bestvideo[ext=mp4][height<=1080]",
            "quiet": True,
            "progress_hooks": [create_progress_hook("🎥 Downloading Video")],
            "logger": SilentLogger()
        })
        audio_opts = _with_cookies({
            "outtmpl": audio_file,
            "format": "bestaudio",
            "quiet": True,
            "progress_hooks": [create_progress_hook("🎧 Downloading Audio")],
            "logger": SilentLogger()
        })
        with YoutubeDL(video_opts) as ydl: ydl.download([url])
        with YoutubeDL(audio_opts) as ydl: ydl.download([url])
        ffmpeg_convert_with_progress([video_file, audio_file], output_file,"MP4",["-c","copy"])
        os.remove(video_file); os.remove(audio_file)
        download_file(output_file)

    else:
        print(f"{now()} ❌ Unknown format: {format_type}")

def process_and_download(input_value, format_type):
    format_type = format_type.upper()
    session_folder = create_session_folder(input_value, format_type)
    if not session_folder:
        return
    # Collect IDs (playlist/channel/search vs single)
    with YoutubeDL(_with_cookies({"quiet":True,'logger':SilentLogger()})) as ydl:
        info = ydl.extract_info(input_value, download=False)
        if info.get("entries"):
            video_ids = [e['id'] for e in info['entries']]
        else:
            video_ids = [input_value.split("watch?v=")[-1].split("&")[0]]
    total = len(video_ids)
    for idx, vid in enumerate(video_ids, 1):
        index_tag = f"{str(idx).zfill(2)}/{str(total).zfill(2)}" if total>1 else "(Single)"
        video_url = f"https://youtu.be/{vid}"
        print("----------")
        download_single_video(video_url, format_type, session_folder, index_tag)


