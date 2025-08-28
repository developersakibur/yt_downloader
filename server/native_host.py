import sys
import json
import struct
import subprocess
import os

# Get the directory of the native host script
script_dir = os.path.dirname(os.path.abspath(__file__))
# Construct the path to the app.py file
app_py_path = os.path.join(script_dir, 'app.py')

def get_message():
    raw_length = sys.stdin.buffer.read(4)
    if len(raw_length) == 0:
        sys.exit(0)
    message_length = struct.unpack('@I', raw_length)[0]
    message = sys.stdin.buffer.read(message_length).decode('utf-8')
    return json.loads(message)

def send_message(message):
    encoded_message = json.dumps(message).encode('utf-8')
    message_length = struct.pack('@I', len(encoded_message))
    sys.stdout.buffer.write(message_length)
    sys.stdout.buffer.write(encoded_message)
    sys.stdout.buffer.flush()

if __name__ == '__main__':
    try:
        message = get_message()
        if message.get('action') == 'start_server':
            # Start the Flask server as a detached process
            # This uses DETACHED_PROCESS flag for Windows
            subprocess.Popen([sys.executable, app_py_path], creationflags=subprocess.DETACHED_PROCESS)
            send_message({'status': 'ok', 'message': 'Server starting command sent.', 'server_url': 'http://yt_downloader.local/'})
        else:
            send_message({'status': 'error', 'message': 'Invalid action.'})
    except Exception as e:
        send_message({'status': 'error', 'message': str(e)})
