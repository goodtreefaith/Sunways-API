# /path/to/your/proxy/project/app.py

import os
import requests
from http.server import BaseHTTPRequestHandler, HTTPServer
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# The real Sunways API endpoint
TARGET_BASE_URL = "https://api.sunways-portal.com"

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
        # Create a new session for each request to keep things clean
        session = requests.Session()

        # These headers make the request look like it's from a real browser
        session.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'X-Requested-With': 'XMLHttpRequest',
            'ver': 'pc',
            'Origin': 'https://www.sunways-portal.com',
            'Referer': 'https://www.sunways-portal.com/',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache',
        }
        
        url = f"{TARGET_BASE_URL}{self.path}"
        
        # Get body from the original request
        data = None
        if method == 'POST':
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                data = self.rfile.read(content_length)
        
        # Forward the 'Content-Type' header from the client (HA)
        if 'Content-Type' in self.headers:
            session.headers['Content-Type'] = self.headers['Content-Type']
        
        # If HA sends a token, the API expects it as a 'token' header, not a cookie
        if 'token' in self.headers:
            session.headers['token'] = self.headers['token']

        try:
            # Make the request to the target server
            response = session.request(method, url, data=data, timeout=20)
            
            # Send response back to the client
            self.send_response(response.status_code)
            
            # Forward headers from the target's response
            for name, value in response.headers.items():
                # Skip headers that will be handled by the server or are problematic
                if name.lower() in ['content-encoding', 'content-length', 'transfer-encoding', 'connection']:
                    continue
                self.send_header(name, value)
                if name.lower() == 'set-cookie':
                    logger.info(f"SUCCESS: Found and forwarding Set-Cookie: {value.split(';')[0]}")

            self._send_cors_headers()
            self.end_headers()
            
            # Write the response content
            self.wfile.write(response.content)

        except requests.exceptions.RequestException as e:
            logger.error(f"Proxy request failed: {e}")
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
    logger.info(f"Starting robust proxy on port {port}...")
    httpd.serve_forever()

if __name__ == '__main__':
    run()
