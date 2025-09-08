import sys, json, struct, subprocess, os

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
app_py_path = os.path.join(project_root, 'app', 'app.py')

def get_message():
    raw_length = sys.stdin.buffer.read(4)
    if not raw_length:
        sys.exit(0)
    message_length = struct.unpack('@I', raw_length)[0]
    return json.loads(sys.stdin.buffer.read(message_length).decode('utf-8'))

def send_message(message):
    encoded = json.dumps(message).encode('utf-8')
    sys.stdout.buffer.write(struct.pack('@I', len(encoded)))
    sys.stdout.buffer.write(encoded)
    sys.stdout.buffer.flush()

if __name__ == '__main__':
    try:
        msg = get_message()
        if msg.get('action') == 'start_server':
            command = [sys.executable, app_py_path]
            subprocess.Popen(
                command,
                cwd=project_root,
                creationflags=subprocess.DETACHED_PROCESS,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            send_message({'status': 'ok', 'message': 'Server starting.'})
        else:
            send_message({'status': 'error', 'message': 'Invalid action.'})
    except Exception as e:
        send_message({'status': 'error', 'message': str(e)})