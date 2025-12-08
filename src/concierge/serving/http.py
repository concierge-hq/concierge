"""
HTTP Transport - Wraps SessionManager to expose it over HTTP.
This is just a thin adapter that handles HTTP protocol details.
"""

import asyncio
import json
from http.server import BaseHTTPRequestHandler
from http.server import HTTPServer as BaseHTTPServer

from concierge.serving.manager import SessionManager


class HTTPRequestHandler(BaseHTTPRequestHandler):
    """Minimal HTTP handler - one endpoint, sends message, gets response."""

    def do_POST(self):
        """
        POST / - Send message
        Body: {"action": "...", ...}
        Session ID via X-Session-Id header (MCP pattern)
        Returns session_id in X-Session-Id header
        """
        length = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(length)
        body = json.loads(body_bytes.decode())

        print("\n" + "=" * 80)
        print("INCOMING REQUEST:")
        print(json.dumps(body, indent=2))
        print("=" * 80)

        session_id = self.headers.get("X-Session-Id")

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            response = loop.run_until_complete(self.server.session_manager.handle_request(session_id, body))
            loop.close()

            # Log outgoing response
            print("\nOUTGOING RESPONSE:")
            print(f"Session: {session_id}")
            print(f"Length: {len(response)} chars")
            print(response[:300] + "..." if len(response) > 300 else response)
            print("=" * 80 + "\n")

            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.send_header("X-Session-Id", session_id)
            self.end_headers()
            self.wfile.write(response.encode())
        except Exception as e:
            print(f"\n[ERROR] {e}")
            print("=" * 80 + "\n")

            self.send_response(500)
            self.send_header("Content-type", "text/plain")
            if session_id:
                self.send_header("X-Session-Id", session_id)
            self.end_headers()
            self.wfile.write(str(e).encode())

    def log_message(self, format, *args):
        """Minimal logging"""
        print(f"[{self.log_date_time_string()}] {format % args}")


class HTTPServer:
    """
    HTTP Server - Transport adapter that exposes SessionManager over HTTP.

    This is just plumbing - it knows about HTTP but not about workflows,
    stages, tasks, etc. All business logic is in SessionManager.
    """

    def __init__(self, session_manager: SessionManager, host: str = "0.0.0.0", port: int = 8080):
        """
        Initialize HTTP server with a SessionManager.

        Args:
            session_manager: The core SessionManager instance to expose
            host: Host to bind to
            port: Port to bind to
        """
        self.session_manager = session_manager
        self.host = host
        self.port = port

    def run(self):
        """Start the HTTP server"""
        httpd = BaseHTTPServer((self.host, self.port), HTTPRequestHandler)
        httpd.session_manager = self.session_manager

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            httpd.shutdown()


if __name__ == "__main__":
    from examples.simple_stock import StockWorkflow

    from concierge.serving.manager import SessionManager

    wf = StockWorkflow._workflow
    print("Listening on port 8081")
    print(f"Workflow: {wf.name} | Stages: {', '.join(wf.stages.keys())}")

    session_manager = SessionManager(wf)
    HTTPServer(session_manager, port=8081).run()
