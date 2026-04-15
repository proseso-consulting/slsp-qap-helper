"""eBIRForms local file-save agent.

Runs as a Windows tray icon, listens on localhost:5123.
Accepts POST /save with {path, content} and writes the file.
Only allows writes under C:\\eBIRForms\\.
"""

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ALLOWED_ROOT = Path(r"C:\eBIRForms")
PORT = 5123
CORS_ORIGIN = "*"


class SaveHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/save":
            self._respond(404, {"error": "not found"})
            return

        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))

        target = Path(body.get("path", ""))
        content = body.get("content", "")

        try:
            target.resolve().relative_to(ALLOWED_ROOT.resolve())
        except ValueError:
            self._respond(403, {"error": f"Path must be under {ALLOWED_ROOT}"})
            return

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        self._respond(200, {"status": "ok", "path": str(target)})

    def do_GET(self):
        if self.path == "/health":
            self._respond(200, {"status": "running", "version": "1.0.0"})
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


def main():
    try:
        import pystray
        from PIL import Image, ImageDraw

        img = Image.new("RGB", (64, 64), "white")
        draw = ImageDraw.Draw(img)
        draw.ellipse([8, 8, 56, 56], fill="green")

        def on_quit(icon, item):
            icon.stop()
            os._exit(0)

        icon = pystray.Icon(
            "ebirforms-agent",
            img,
            "eBIRForms Agent (localhost:5123)",
            menu=pystray.Menu(pystray.MenuItem("Quit", on_quit)),
        )

        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()

        icon.run()
    except ImportError:
        print(f"eBIRForms agent listening on localhost:{PORT}")
        run_server()


if __name__ == "__main__":
    main()
