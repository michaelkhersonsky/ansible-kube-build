
from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.parse

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/api/score"):
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)
            score = params.get("value", ["?"])[0]
            print(f"[SCORE] {self.client_address[0]} submitted score: {score}")
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Score received")
        else:
            self.send_response(404)
            self.end_headers()

HTTPServer(("", 5000), Handler).serve_forever()
