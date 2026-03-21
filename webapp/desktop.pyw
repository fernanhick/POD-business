import os, sys, threading, time, urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR / "backend"
WORKSPACE_DIR = SCRIPT_DIR.parent / "workspace"

# Load workspace .env before importing the app
from dotenv import load_dotenv
load_dotenv(WORKSPACE_DIR / ".env")

# Make backend importable
sys.path.insert(0, str(BACKEND_DIR))
os.chdir(str(BACKEND_DIR))

import uvicorn
import webview

server_instance = None

def run_server():
    global server_instance
    config = uvicorn.Config("app.main:app", host="127.0.0.1", port=8000, log_level="warning")
    server_instance = uvicorn.Server(config)
    server_instance.run()

# Start server in background thread
server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()

# Wait for server ready (up to 10s)
for _ in range(100):
    try:
        urllib.request.urlopen("http://127.0.0.1:8000/api/health")
        break
    except Exception:
        time.sleep(0.1)

# Open desktop window
window = webview.create_window(
    "POD Business Control Center",
    "http://127.0.0.1:8000",
    width=1400,
    height=900,
    min_size=(1024, 700),
)
webview.start()  # Blocks until window is closed

# Graceful shutdown
if server_instance:
    server_instance.should_exit = True
    server_thread.join(timeout=5)
