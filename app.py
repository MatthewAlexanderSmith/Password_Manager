"""
CogniVault — Desktop Application Launcher
Bridges the HTML/JS frontend with the FastAPI backend using pywebview.

Architecture:
  1. FastAPI (feature/backend-api) runs on a background thread at localhost:8000
  2. pywebview opens a native OS window that loads the frontend HTML file
  3. The JS in index.html communicates with FastAPI via fetch() to 127.0.0.1:8000
  4. Zero external network exposure — all IPC is local

Usage:
  pip install pywebview uvicorn fastapi
  python app.py
"""

import json
import threading
import time
import os
import sys
import urllib.error
import urllib.request
import webview
import uvicorn

# ─── PATH SETUP ─────────────────────────────────────────────────────────────
# Add the backend folder to import path so `from main import app` works when
# main.py lives inside `backend-api/`.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(BASE_DIR, "backend-api")
FRONTEND_HTML = os.path.join(BASE_DIR, "frontend", "index.html")

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

APP_TITLE = "CogniVault"
APP_WIDTH = 1200
APP_HEIGHT = 760
APP_MIN_WIDTH = 900
APP_MIN_HEIGHT = 600

# ─── BACKEND CONFIG ──────────────────────────────────────────────────────────
BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 8000


# ─── FASTAPI SERVER THREAD ───────────────────────────────────────────────────
def run_backend():
    """
    Runs the FastAPI app via uvicorn in a daemon thread.
    Import is done here so that sys.path adjustments take effect first.
    """
    try:
        # If running from repo root after merging branches:
        from main import app  # noqa: F401
        uvicorn.run(
            app,
            host=BACKEND_HOST,
            port=BACKEND_PORT,
            log_level="warning",   # Keep console clean in production
            access_log=False,
        )
    except ImportError as e:
        print(f"[CogniVault] Could not import FastAPI app: {e}")
        print("[CogniVault] Ensure feature/backend-api is merged and main.py is present.")
        sys.exit(1)


def wait_for_backend(timeout: float = 10.0) -> bool:
    """
    Polls the backend health endpoint until it's ready or times out.
    Returns True if the backend came up, False on timeout.
    """
    import urllib.request
    import urllib.error

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            try:
                urllib.request.urlopen(
                    f"http://{BACKEND_HOST}:{BACKEND_PORT}/docs",
                    timeout=1
                )
            except Exception:
                urllib.request.urlopen(
                    f"http://{BACKEND_HOST}:{BACKEND_PORT}/vault/status",
                    timeout=1
                )
            return True
        except Exception:
            time.sleep(0.15)
    return False


# ─── PYWEBVIEW API ───────────────────────────────────────────────────────────
class CogniVaultAPI:
    """
    Optional pywebview JS API layer.
    Currently unused (all communication goes through fetch → FastAPI),
    but this class is here for future native OS integrations like:
      - System tray support
      - Native file save/open dialogs
      - Clipboard access
    """

    def open_file_dialog(self):
        """Opens a native file picker and returns the selected path."""
        result = webview.windows[0].create_file_dialog(
            webview.OPEN_DIALOG,
            allow_multiple=False,
        )
        return result[0] if result else None

    def save_file_dialog(self, suggested_name: str = "vault_export.enc"):
        """Opens a native save dialog and returns the chosen path."""
        result = webview.windows[0].create_file_dialog(
            webview.SAVE_DIALOG,
            save_filename=suggested_name,
        )
        return result if result else None


    def request(self, method: str, path: str, body=None):
        url = f"http://{BACKEND_HOST}:{BACKEND_PORT}{path}"
        data = None
        headers = {"Content-Type": "application/json"}

        if body is not None:
            data = json.dumps(body).encode("utf-8")

        req = urllib.request.Request(
            url=url,
            data=data,
            headers=headers,
            method=method.upper(),
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = resp.read().decode("utf-8")
                if not raw:
                    return {}
                try:
                    return json.loads(raw)
                except json.JSONDecodeError:
                    return {"raw": raw}
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", errors="replace")
            try:
                payload = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                payload = {"detail": raw}
            message = payload.get("detail") or payload.get("message") or f"HTTP {e.code}"
            raise Exception(message)
        except Exception as e:
            raise Exception(str(e))

    def get_app_version(self):
        return "1.0.0-pqc"


# ─── MAIN ────────────────────────────────────────────────────────────────────
def main():
    print("╔══════════════════════════════════════╗")
    print("║         CogniVault  v1.0.0           ║")
    print("║  Local · AI-Enhanced · Quantum-Safe  ║")
    print("╚══════════════════════════════════════╝")

    # 1. Validate frontend file exists
    if not os.path.isfile(FRONTEND_HTML):
        print(f"[ERROR] Frontend not found at: {FRONTEND_HTML}")
        sys.exit(1)

    # 2. Start FastAPI backend in a daemon thread
    backend_thread = threading.Thread(target=run_backend, daemon=True)
    backend_thread.start()
    print(f"[CogniVault] Backend starting on http://{BACKEND_HOST}:{BACKEND_PORT} …")

    # 3. Wait for backend to become healthy
    if wait_for_backend(timeout=12.0):
        print("[CogniVault] Backend ready.")
    else:
        print("[CogniVault] Warning: backend did not respond in time. Continuing anyway.")

    # 4. Open pywebview native window pointing to the local HTML file
    frontend_url = f"file:///{os.path.abspath(FRONTEND_HTML).replace(os.sep, '/')}"
    print(f"[CogniVault] Loading frontend: {frontend_url}")

    api = CogniVaultAPI()

    window = webview.create_window(
        title=APP_TITLE,
        url=frontend_url,
        js_api=api,
        width=APP_WIDTH,
        height=APP_HEIGHT,
        min_size=(APP_MIN_WIDTH, APP_MIN_HEIGHT),
        resizable=True,
        # Frameless look (optional — set False if you prefer the OS titlebar)
        frameless=False,
        # Prevent the window from exposing the URL bar
        easy_drag=False,
        # Allow fetch() calls to localhost to work from file:// origin
        # This is safe because the server explicitly allows 127.0.0.1 in CORS
        text_select=False,
    )

    webview.start(
        debug=False,        # Set True during development to open DevTools
        http_server=False,  # We use our own FastAPI server
    )

    print("[CogniVault] Window closed. Goodbye.")


if __name__ == "__main__":
    main()
