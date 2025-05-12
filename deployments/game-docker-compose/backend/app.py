from http.server import BaseHTTPRequestHandler, HTTPServer

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        print(f"GET {self.path} from {self.client_address[0]}")
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Backend response OK")

HTTPServer(("", 5000), Handler).serve_forever()

