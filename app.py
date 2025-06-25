# /path/to/your/proxy/project/app.py

import os
import requests
from http.server import BaseHTTPRequestHandler, HTTPServer
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ProxyHandler(BaseHTTPRequestHandler):
    
    def _send_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Requested-With, ver, token')
        self.send_header('Access-Control-Allow-Credentials', 'true')

    def do_OPTIONS(self):
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    def _proxy_request(self, method):
        session = requests.Session()

        # Use the essential headers that the HA integration expects
        session.headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
            "ver": "pc",
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
            ),
            "Origin": "https://www.sunways-portal.com",
            "Referer": "https://www.sunways-portal.com/",
        }

        target_url = f"https://api.sunways-portal.com{self.path}"
        
        post_data = None
        if method == 'POST':
            session.headers['Content-Type'] = self.headers.get('Content-Type', 'application/json; charset=UTF-8')
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                post_data = self.rfile.read(content_length)
        
        # For data requests (not login), HA will send a token. The API expects this
        # as a 'token' header. We must forward it.
        if 'token' in self.headers:
            session.headers['token'] = self.headers['token']

        try:
            # --- TWO-STEP AUTHENTICATION MIMICRY ---
            # If this is a login request, first "prime" the session.
            if self.path == '/monitor/auth/login':
                logger.info("Login request detected. Priming session by visiting main portal...")
                try:
                    # Step 1: Visit the main portal to get any initial session cookies.
                    session.get("https://www.sunways-portal.com/", timeout=10)
                    logger.info("Session primed. Acquired cookies: %s", session.cookies.get_dict())
                except requests.exceptions.RequestException as e:
                    logger.warning("Failed to prime session, but continuing anyway: %s", e)
            # --- END OF TWO-STEP LOGIC ---

            # Step 2: Make the actual request (login or data fetch)
            logger.info("Proxying %s to %s", method, target_url)
            response = session.request(method, target_url, data=post_data, timeout=20)
            
            self.send_response(response.status_code)
            
            for name, value in response.headers.items():
                if name.lower() not in ['content-encoding', 'content-length', 'transfer-encoding', 'connection']:
                    self.send_header(name, value)
                if name.lower() == 'set-cookie':
                    logger.info("SUCCESS: Found and forwarding Set-Cookie: %s", value.split(';')[0])

            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(response.content)

        except requests.exceptions.RequestException as e:
            logger.error("Proxy request failed: %s", e)
            self.send_response(502)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"error": "Proxy request failed"}')

    def do_GET(self):
        self._proxy_request('GET')

    def do_POST(self):
        self._proxy_request('POST')

def run(server_class=HTTPServer, handler_class=ProxyHandler, port=8080):
    port = int(os.environ.get('PORT', 8080))
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    logger.info(f"Starting two-step auth proxy on port {port}...")
    httpd.serve_forever()

if __name__ == '__main__':
    run()
