import json
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = 8000


class Handler(BaseHTTPRequestHandler):
    def send_json(self, status_code, body):
        data = json.dumps(body, separators=(",", ":")).encode()
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = self.path.split("?")[0]  # ignore any ?query=string
        if path == "/health":
            self.send_json(200, {"status": "ok", "version": "1.1.0"})
        else:
            self.send_json(404, {"error": "not found"})


if __name__ == "__main__":
    # 0.0.0.0 = listen on all network interfaces, required inside a container
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
