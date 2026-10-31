# Receives episode files from the built-in browser (scripts/tiktok_batch.js) and saves them.
#
# Usage (plain Python, run it in the background; stop it with pkill -f receive.py when done):
#   python3 receive.py <inbox_dir>
#
# TikTok ties video links to the browser's own session and its page blocks fetch/XHR to other
# hosts, but not a plain form POST: the page fetches each episode, puts the files into a
# multipart form and submits it to http://127.0.0.1:8765/upload; this saves them into
# <inbox_dir>, prints "saved <file> <bytes> …" and redirects the browser back to the page.
import email.parser, email.policy, re, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
class H(BaseHTTPRequestHandler):
    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        msg = email.parser.BytesParser(policy=email.policy.HTTP).parsebytes(
            b"Content-Type: " + self.headers["Content-Type"].encode() + b"\r\n\r\n" + body)
        back, saved = "about:blank", []
        for part in msg.iter_parts():
            name, fn = part.get_param("name", header="content-disposition"), part.get_filename()
            data = part.get_payload(decode=True) or b""
            if fn:
                fn = re.sub(r"[^A-Za-z0-9_.-]", "_", fn); (out / fn).write_bytes(data); saved.append(f"{fn} {len(data)}")
            elif name == "back":
                back = data.decode()
        print("saved", *saved, flush=True)
        self.send_response(303); self.send_header("Location", back); self.end_headers()
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b"receiver ok")
    def log_message(self, *a): pass
ThreadingHTTPServer(("127.0.0.1", 8765), H).serve_forever()
