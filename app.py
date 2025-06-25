# /path/to/your/proxy/project/app.py

#!/usr/bin/env python3
"""
Sunways API Proxy for Render.com
- Mimics a real browser to ensure a session cookie is issued.
- Forwards the session cookie back to Home Assistant.
- Handles gzip compression automatically.
"""

import os
import json
import urllib.request
import ssl
from http.server import BaseHTTPRequestHandler, HTTPServer
import logging
import gzip

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SunwaysProxyHandler(BaseHTTPRequestHandler):
    
    def _send_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Requested-With, ver, token')
        self.send_header('Access-Control-Allow-Credentials', 'true')
    
    def do_OPTIONS(self):
        self.send_response(204, "No Content")
        self._send_cors_headers()
        self.end_headers()
    
    def _proxy_request(self, method):
        try:
            target_url = f"https://api.sunways-portal.com{self.path}"
            
            post_data = b''
            if method == 'POST':
                content_length = int(self.headers.get('Content-Length', 0))
                if content_length > 0:
                    post_data = self.rfile.read(content_length)
            
            # --- START OF THE CRITICAL FIX ---
            # Hardcode headers to look exactly like a real browser request.
            # This is the key to getting the API to issue a Set-Cookie header.
            headers = {
                'Host': 'api.sunways-portal.com',
                'Connection': 'keep-alive',
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'Content-Type': 'application/json; charset=UTF-8',
                'X-Requested-With': 'XMLHttpRequest',
                'ver': 'pc',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Origin': 'https://www.sunways-portal.com',
                'Referer': 'https://www.sunways-portal.com/',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept-Language': 'en-US,en;q=0.9',
            }
            # --- END OF THE CRITICAL FIX ---

            # If the client (HA) sends a token header for subsequent requests, use it.
            if 'token' in self.headers:
                headers['Cookie'] = f"token={self.headers['token']}"

            ssl_context = ssl.create_default_context()
            req = urllib.request.Request(target_url, data=post_data, headers=headers, method=method)
            
            with urllib.request.urlopen(req, timeout=60, context=ssl_context) as response:
                response_data = response.read()
                
                if response.info().get('Content-Encoding') == 'gzip':
                    logger.info("Response is gzipped. Decompressing...")
                    response_data = gzip.decompress(response_data)

                self.send_response(response.getcode())
                
                # Forward necessary headers
                self.send_header('Content-Type', response.headers.get('Content-Type', 'application/json'))
                self._send_cors_headers()

                # Explicitly look for and forward the Set-Cookie header
                cookie_headers = response.headers.get_all('Set-Cookie')
                if cookie_headers:
                    for cookie in cookie_headers:
                        self.send_header('Set-Cookie', cookie)
                        logger.info(f"SUCCESS: Found and forwarded Set-Cookie header: {cookie.split(';')[0]}")
                
                self.end_headers()
                self.wfile.write(response_data)
                
        except Exception as e:
            logger.error(f"Unexpected error in proxy: {str(e)}", exc_info=True)
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Internal Proxy Error", "details": str(e)}).encode())

    def do_GET(self):
        self._proxy_request('GET')

    def do_POST(self):
        self._proxy_request('POST')

def run_server():
    port = int(os.environ.get('PORT', 8080))
    server_address = ('0.0.0.0', port)
    httpd = HTTPServer(server_address, SunwaysProxyHandler)
    
    logger.info(f"Starting Sunways Proxy Server on port {port}")
    httpd.serve_forever()

if __name__ == '__main__':
    run_server()
