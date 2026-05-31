# tests/mock_server.py
import json
import threading
import time
import socketserver
import http.server
import logging
import websockets.sync.server as ws_sync
from typing import Dict, List

logger = logging.getLogger(__name__)

class MockAPIServer:
    """Simulatore API thread-safe per test isolati."""
    def __init__(self, host="127.0.0.1", http_port=0, ws_port=0):
        self.host = host
        self.http_port = http_port
        self.ws_port = ws_port
        self.http_url = ""
        self.ws_url = ""
        self._stop = threading.Event()
        self.tokens: Dict[str, dict] = {}
        self.ws_clients: List = []
        self._clients_lock = threading.Lock()

    def start(self):
        # HTTP
        class H(http.server.BaseHTTPRequestHandler):
            def do_POST(s):
                if s.path == "/auth/login":
                    l = int(s.headers.get("Content-Length", 0))
                    b = json.loads(s.rfile.read(l).decode())
                    t = f"mock_{b.get('username', 'guest')}"
                    mock_srv.tokens[t] = {"user": b.get("username")}
                    s._resp(200, {"token": t})
                else: s._resp(404, {"error": "not_found"})
            def do_GET(s):
                if s.path == "/api/status":
                    if "mock_" in s.headers.get("Authorization", ""):
                        s._resp(200, {"status": "ok"})
                    else: s._resp(401, {"error": "unauthorized"})
                else: s._resp(404, {"error": "not_found"})
            def _resp(s, code, data):
                s.send_response(code); s.send_header("Content-Type", "application/json"); s.end_headers()
                s.wfile.write(json.dumps(data).encode())
            def log_message(s, *a): pass
        mock_srv = self
        self._http = socketserver.TCPServer((self.host, self.http_port), H)
        self.http_port = self._http.server_address[1]
        self.http_url = f"http://{self.host}:{self.http_port}"
        threading.Thread(target=self._http.serve_forever, daemon=True).start()

        # WS
        def ws_handler(conn):
            with self._clients_lock: self.ws_clients.append(conn)
            try:
                while not self._stop.is_set():
                    msg = conn.recv()
                    conn.send(json.dumps({"echo": msg}))
            except: pass
            finally:
                with self._clients_lock:
                    if conn in self.ws_clients: self.ws_clients.remove(conn)
                conn.close()
        self._ws = ws_sync.serve(ws_handler, self.host, self.ws_port)
        self.ws_port = self._ws.socket.getsockname()[1]
        self.ws_url = f"ws://{self.host}:{self.ws_port}"
        threading.Thread(target=self._ws.serve_forever, daemon=True).start()
        time.sleep(0.3)  # Wait for bind

    def stop(self):
        self._stop.set()
        if hasattr(self, "_http"): self._http.shutdown()
        if hasattr(self, "_ws"): self._ws.shutdown()
        logger.info("Mock server stopped.")