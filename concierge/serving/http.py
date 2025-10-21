"""
HTTP Transport - Wraps SessionManager to expose it over HTTP.
This is just a thin adapter that handles HTTP protocol details.
"""
from http.server import HTTPServer as BaseHTTPServer, BaseHTTPRequestHandler
import json
import asyncio
from urllib.parse import urlparse
from concierge.serving.manager import SessionManager


class HTTPRequestHandler(BaseHTTPRequestHandler):
    """Minimal HTTP handler - one endpoint, sends message, gets response."""
    
    def do_POST(self):
        """
        POST / - Send message
        Body: {"session_id": "...", "action": "...", ...}
        Returns session_id in X-Session-Id header
        """
        length = int(self.headers.get('Content-Length', 0))
        body_bytes = self.rfile.read(length)
        body = json.loads(body_bytes.decode())
        
        # Log incoming request
        print("\n" + "="*80)
        print("INCOMING REQUEST:")
        print(json.dumps(body, indent=2))
        print("="*80)
        
        session_id = body.pop('session_id', None)
        if not session_id:
            session_id = self.server.session_manager.create_session()
            print(f"[NEW] Created session: {session_id}")
        else:
            print(f"[EXISTING] Using session: {session_id}")
        
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            response = loop.run_until_complete(
                self.server.session_manager.handle_request(session_id, body)
            )
            loop.close()
            
            # Log outgoing response
            print("\nOUTGOING RESPONSE:")
            print(f"Session: {session_id}")
            print(f"Length: {len(response)} chars")
            print(response[:300] + "..." if len(response) > 300 else response)
            print("="*80 + "\n")
            
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.send_header('X-Session-Id', session_id)  # Return session_id!
            self.end_headers()
            self.wfile.write(response.encode())
        except Exception as e:
            print(f"\n[ERROR] {e}")
            print("="*80 + "\n")
            
            self.send_response(500)
            self.send_header('Content-type', 'text/plain')
            if session_id:
                self.send_header('X-Session-Id', session_id)
            self.end_headers()
            self.wfile.write(str(e).encode())
    
    def log_message(self, format, *args):
        """Minimal logging"""
        print(f"[{self.log_date_time_string()}] {format % args}")


class HTTPServer:
    """
    HTTP Server - Transport adapter that exposes SessionManager over HTTP.
    
    This is just plumbing - it knows about HTTP but not about workflows,
    stages, tools, etc. All business logic is in SessionManager.
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
    from concierge.serving.manager import SessionManager
    from examples.simple_stock import StockWorkflow
    
    wf = StockWorkflow._workflow
    print(f"Listening on port 8081")
    print(f"Workflow: {wf.name} | Stages: {', '.join(wf.stages.keys())}")
    
    session_manager = SessionManager(wf)
    HTTPServer(session_manager, port=8081).run()

