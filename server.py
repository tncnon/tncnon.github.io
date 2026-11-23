"""
Portfolio admin server (local only).

  python server.py         -> http://localhost:5500        (website)
                              http://localhost:5500/admin/ (backend)

Endpoints:
  GET  /api/data            -> data.json
  POST /api/data            -> save data.json (old version backed up to backups/)
  POST /api/upload          -> {folder, name, data(base64)} -> saves into assets/<folder>/
  GET  /api/oembed?url=...  -> YouTube title lookup
"""
import base64, datetime, http.server, json, os, re, shutil, socketserver, sys, urllib.parse, urllib.request, webbrowser

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data.json")
BACKUPS = os.path.join(ROOT, "backups")
FOLDERS = {"works", "thumbs", "logos", "videos"}
MAX_BODY = 40 * 1024 * 1024
PORT = int(os.environ.get("PORT", 5500))


def safe_name(name):
    base, ext = os.path.splitext(os.path.basename(name))
    base = re.sub(r"[^A-Za-z0-9_-]+", "-", base).strip("-")[:60] or "file"
    ext = ext.lower() if ext.lower() in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"} else ".jpg"
    return base + ext


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def end_headers(self):
        if self.path.split("?")[0].endswith((".json", ".html", "/")):
            self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        n = int(self.headers.get("Content-Length", 0))
        if n > MAX_BODY:
            raise ValueError("ไฟล์ใหญ่เกินไป")
        return json.loads(self.rfile.read(n) or b"{}")

    def _same_origin(self):
        origin = self.headers.get("Origin")
        return origin is None or urllib.parse.urlparse(origin).hostname in ("localhost", "127.0.0.1")

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        if u.path == "/api/data":
            with open(DATA, encoding="utf-8") as f:
                return self._json(json.load(f))
        if u.path == "/api/oembed":
            url = urllib.parse.parse_qs(u.query).get("url", [""])[0]
            try:
                q = "https://www.youtube.com/oembed?format=json&url=" + urllib.parse.quote(url, safe="")
                with urllib.request.urlopen(q, timeout=8) as r:
                    return self._json(json.load(r))
            except Exception as e:
                return self._json({"error": str(e)}, 502)
        return super().do_GET()

    def do_POST(self):
        if not self._same_origin():
            return self._json({"error": "forbidden"}, 403)
        try:
            if self.path == "/api/data":
                data = self._body()
                if not isinstance(data, dict) or "profile" not in data:
                    return self._json({"error": "ข้อมูลไม่ถูกต้อง"}, 400)
                os.makedirs(BACKUPS, exist_ok=True)
                stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
                if os.path.exists(DATA):
                    shutil.copy2(DATA, os.path.join(BACKUPS, f"data-{stamp}.json"))
                tmp = DATA + ".tmp"
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                os.replace(tmp, DATA)
                return self._json({"ok": True, "backup": f"backups/data-{stamp}.json"})

            if self.path == "/api/upload":
                b = self._body()
                folder = b.get("folder")
                if folder not in FOLDERS:
                    return self._json({"error": "bad folder"}, 400)
                raw = b.get("data", "")
                raw = raw.split(",", 1)[1] if raw.startswith("data:") else raw
                blob = base64.b64decode(raw)
                d = os.path.join(ROOT, "assets", folder)
                os.makedirs(d, exist_ok=True)
                name = safe_name(b.get("name", "file.jpg"))
                stem, ext = os.path.splitext(name)
                i = 1
                while os.path.exists(os.path.join(d, name)):
                    i += 1
                    name = f"{stem}-{i}{ext}"
                with open(os.path.join(d, name), "wb") as f:
                    f.write(blob)
                return self._json({"ok": True, "path": f"assets/{folder}/{name}"})
        except Exception as e:
            return self._json({"error": str(e)}, 400)
        return self._json({"error": "not found"}, 404)


class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


if __name__ == "__main__":
    srv = Server(("127.0.0.1", PORT), Handler)
    print(f"\n  Website : http://localhost:{PORT}/\n  Admin   : http://localhost:{PORT}/admin/\n  (ปิดหน้าต่างนี้เพื่อหยุด server)\n")
    if "--open" in sys.argv:
        webbrowser.open(f"http://localhost:{PORT}/admin/")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
