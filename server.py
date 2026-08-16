#!/usr/bin/env python3
"""FREEZE FREEKS — tiny stdlib-only site + email-list backend.

Run:  python3 server.py
Site: http://localhost:8787   Admin: http://localhost:8787/admin
Signups persist in signups.json next to this file.
"""
import json
import os
import re
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get("PORT", "8787"))
ROOT = os.path.dirname(os.path.abspath(__file__))
PUBLIC = os.path.join(ROOT, "public")
DB = os.path.join(ROOT, "signups.json")
MSG_DB = os.path.join(ROOT, "messages.json")

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
LOCK = threading.Lock()

MIME = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css",
    ".js": "text/javascript",
    ".json": "application/json",
    ".ttf": "font/ttf",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
}


def load_signups():
    try:
        with open(DB, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_signups(signups):
    with open(DB, "w", encoding="utf-8") as f:
        json.dump(signups, f, indent=2)


def load_messages():
    try:
        with open(MSG_DB, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_messages(messages):
    with open(MSG_DB, "w", encoding="utf-8") as f:
        json.dump(messages, f, indent=2)


class Handler(BaseHTTPRequestHandler):
    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length > 10_000:
            return None
        try:
            return json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            return None

    def do_POST(self):
        if self.path == "/api/contact":
            return self._contact()
        if self.path != "/api/signup":
            return self._json(404, {"error": "Not found."})
        data = self._read_body()
        if data is None:
            return self._json(400, {"error": "Bad request."})
        email = str(data.get("email", "")).strip().lower()
        if not EMAIL_RE.match(email):
            return self._json(400, {"error": "That email doesn’t look right."})
        source = str(data.get("source", "site"))[:40]
        with LOCK:
            signups = load_signups()
            if any(s["email"] == email for s in signups):
                return self._json(200, {"ok": True, "duplicate": True})
            signups.append({
                "email": email,
                "ts": datetime.now(timezone.utc).isoformat(),
                "source": source,
            })
            save_signups(signups)
        print(f"[signup] {email} ({len(signups)} total)")
        return self._json(201, {"ok": True})

    def _contact(self):
        data = self._read_body()
        if data is None:
            return self._json(400, {"error": "Bad request."})
        name = str(data.get("name", "")).strip()[:80]
        email = str(data.get("email", "")).strip().lower()
        flavor = str(data.get("flavor", "")).strip()[:60]
        msg = str(data.get("msg", "")).strip()[:2000]
        if not name:
            return self._json(400, {"error": "Tell us your name."})
        if not EMAIL_RE.match(email):
            return self._json(400, {"error": "That email doesn’t look right."})
        with LOCK:
            messages = load_messages()
            entry = {
                "id": f"m{len(messages) + 1}-{int(datetime.now(timezone.utc).timestamp() * 1000)}",
                "name": name,
                "email": email,
                "flavor": flavor,
                "msg": msg,
                "ts": datetime.now(timezone.utc).isoformat(),
            }
            messages.append(entry)
            save_messages(messages)
        print(f"[contact] {name} <{email}> — {flavor}")
        return self._json(201, {"ok": True})

    def do_DELETE(self):
        from urllib.parse import unquote
        mm = re.match(r"^/api/messages/(.+)$", self.path)
        if mm:
            mid = unquote(mm.group(1))
            with LOCK:
                messages = load_messages()
                remaining = [x for x in messages if x.get("id") != mid]
                if len(remaining) == len(messages):
                    return self._json(404, {"error": "Not found."})
                save_messages(remaining)
            return self._json(200, {"ok": True})
        m = re.match(r"^/api/signups/(.+)$", self.path)
        if not m:
            return self._json(404, {"error": "Not found."})
        email = unquote(m.group(1)).lower()
        with LOCK:
            signups = load_signups()
            remaining = [s for s in signups if s["email"] != email]
            if len(remaining) == len(signups):
                return self._json(404, {"error": "Not found."})
            save_signups(remaining)
        print(f"[remove] {email} ({len(remaining)} total)")
        return self._json(200, {"ok": True})

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/api/signups":
            return self._json(200, list(reversed(load_signups())))  # newest first
        if path == "/api/messages":
            return self._json(200, list(reversed(load_messages())))  # newest first
        file = {"/": "/index.html", "/admin": "/admin.html"}.get(path, path)
        full = os.path.normpath(os.path.join(PUBLIC, file.lstrip("/")))
        if not full.startswith(PUBLIC):
            return self._json(403, {"error": "Forbidden."})
        try:
            with open(full, "rb") as f:
                buf = f.read()
        except OSError:
            return self._json(404, {"error": "Not found."})
        ext = os.path.splitext(full)[1]
        self.send_response(200)
        self.send_header("Content-Type", MIME.get(ext, "application/octet-stream"))
        self.send_header("Content-Length", str(len(buf)))
        self.end_headers()
        self.wfile.write(buf)

    def log_message(self, *args):  # quiet the default per-request noise
        pass


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"FREEZE FREEKS running → http://localhost:{PORT}  (admin: http://localhost:{PORT}/admin)", flush=True)
    server.serve_forever()
