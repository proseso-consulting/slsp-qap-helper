"""eBIRForms local file-save agent.

Runs as a Windows tray icon, listens on localhost:5123.
Accepts POST /save with {path, content} and writes the file.
Only allows writes under the detected eBIRForms directory.

Distributed as a standalone .exe via PyInstaller.
On first run, registers itself in Windows Startup so it runs on boot.
"""

import json
import os
import sys
import threading
import winreg
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from tkinter import Tk, filedialog, messagebox

PORT = 5123
CORS_ORIGIN = "*"
APP_NAME = "eBIRForms Agent"
VERSION = "1.1.0"

# Resolved at startup
EBIRFORMS_ROOT: Path = Path(r"C:\eBIRForms")

# Common install locations
_SEARCH_PATHS = [
    Path(r"C:\eBIRForms"),
    Path(r"D:\eBIRForms"),
    Path(r"C:\Program Files\eBIRForms"),
    Path(r"C:\Program Files (x86)\eBIRForms"),
]


def _config_path() -> Path:
    """Config file lives next to the exe (or script)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / "ebirforms_agent.json"
    return Path(__file__).parent / "ebirforms_agent.json"


def _load_config() -> dict:
    p = _config_path()
    if p.exists():
        return json.loads(p.read_text())
    return {}


def _save_config(cfg: dict):
    _config_path().write_text(json.dumps(cfg, indent=2))


def _detect_ebirforms() -> Path | None:
    """Find eBIRForms install by looking for BIRForms.exe."""
    # Check saved config first
    cfg = _load_config()
    saved = cfg.get("ebirforms_path")
    if saved and Path(saved).exists():
        return Path(saved)

    # Search common paths
    for p in _SEARCH_PATHS:
        if (p / "BIRForms.exe").exists() or (p / "savefile").exists():
            return p

    return None


def _ask_user_for_path() -> Path | None:
    """Show a folder picker if eBIRForms can't be found."""
    root = Tk()
    root.withdraw()
    messagebox.showinfo(
        APP_NAME,
        "Could not find eBIRForms installation.\n\n"
        "Please select the folder where eBIRForms is installed\n"
        "(the folder containing BIRForms.exe).",
    )
    folder = filedialog.askdirectory(title="Select eBIRForms folder")
    root.destroy()
    if folder:
        return Path(folder)
    return None


def resolve_ebirforms_root() -> Path:
    """Detect or ask for the eBIRForms directory. Saves to config."""
    found = _detect_ebirforms()
    if found:
        _save_config({"ebirforms_path": str(found)})
        return found

    picked = _ask_user_for_path()
    if picked:
        _save_config({"ebirforms_path": str(picked)})
        return picked

    # Last resort: default
    return Path(r"C:\eBIRForms")


class SaveHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/save":
            self._respond(404, {"error": "not found"})
            return

        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))

        target = Path(body.get("path", ""))
        content = body.get("content", "")

        # Rewrite path prefix to match actual install location
        # The server always sends C:\eBIRForms\..., remap to real path
        try:
            relative = target.relative_to(Path(r"C:\eBIRForms"))
            target = EBIRFORMS_ROOT / relative
        except ValueError:
            pass

        try:
            target.resolve().relative_to(EBIRFORMS_ROOT.resolve())
        except ValueError:
            self._respond(403, {"error": f"Path must be under {EBIRFORMS_ROOT}"})
            return

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        self._respond(200, {"status": "ok", "path": str(target)})

    def do_GET(self):
        if self.path == "/health":
            self._respond(200, {
                "status": "running",
                "version": VERSION,
                "ebirforms_path": str(EBIRFORMS_ROOT),
            })
        else:
            self._respond(404, {"error": "not found"})

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors_headers()
        self.end_headers()

    def _respond(self, code, data):
        self.send_response(code)
        self._cors_headers()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", CORS_ORIGIN)
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, format, *args):
        pass


def run_server():
    server = HTTPServer(("127.0.0.1", PORT), SaveHandler)
    server.serve_forever()


def register_startup():
    """Add this exe to Windows Startup (current user) so it runs on login."""
    exe_path = sys.executable if getattr(sys, "frozen", False) else None
    if not exe_path:
        return
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE,
        )
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, f'"{exe_path}"')
        winreg.CloseKey(key)
    except OSError:
        pass


def main():
    global EBIRFORMS_ROOT
    EBIRFORMS_ROOT = resolve_ebirforms_root()
    EBIRFORMS_ROOT.mkdir(parents=True, exist_ok=True)

    register_startup()

    import pystray
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (64, 64), "white")
    draw = ImageDraw.Draw(img)
    draw.ellipse([8, 8, 56, 56], fill="#28a745")

    def on_change_folder(icon, item):
        picked = _ask_user_for_path()
        if picked:
            global EBIRFORMS_ROOT
            EBIRFORMS_ROOT = picked
            _save_config({"ebirforms_path": str(picked)})
            icon.title = f"{APP_NAME} - {picked}"

    def on_quit(icon, item):
        icon.stop()
        os._exit(0)

    icon = pystray.Icon(
        "ebirforms-agent",
        img,
        f"{APP_NAME} - {EBIRFORMS_ROOT}",
        menu=pystray.Menu(
            pystray.MenuItem(f"v{VERSION} (localhost:{PORT})", lambda *a: None, enabled=False),
            pystray.MenuItem("Change eBIRForms folder...", on_change_folder),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", on_quit),
        ),
    )

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    icon.run()


if __name__ == "__main__":
    main()
