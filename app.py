# /path/to/your/proxy/project/app.py

#!/usr/bin/env python3
"""
Sunways API Proxy for Render.com with Session Management
Fixes SSL handshake issues and properly forwards authentication sessions
"""

import os
import json
import urllib.request
import urllib.parse
import ssl
from http.server import BaseHTTPRequestHandler, HTTPServer
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SunwaysProxyHandler(BaseHTTPRequestHandler):
    """HTTP request handler that proxies requests to Sunways API with session management"""
    
    def log_message(self, format, *args):
        """Override to use proper logging"""
        logger.info(f"{self.address_string()} - {format % args}")
    
    def _send_cors_headers(self):
        """Send CORS headers to allow cross-origin requests"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, Cookie, X-Requested-With, ver')
        self.send_header('Access-Control-Allow-Credentials', 'true')
    
    def do_OPTIONS(self):
        """Handle preflight CORS requests"""
        self.send_response(204, "No Content")
        self._send_cors_headers()
        self.end_headers()
    
    def _proxy_request(self, method):
        """Generic proxy handler for GET and POST"""
        try:
            target_url = f"https://api.sunways-portal.com{self.path}"
            logger.info(f"Proxying {method} request to: {target_url}")
            
            post_data = b''
            if method == 'POST':
                content_length = int(self.headers.get('Content-Length', 0))
                if content_length > 0:
                    post_data = self.rfile.read(content_length)
            
            # Prepare headers for Sunways API, forwarding from client
            headers = {key: value for key, value in self.headers.items() if key.lower() not in ['host', 'connection']}
            headers['Host'] = 'api.sunways-portal.com'

            ssl_context = ssl.create_default_context()
            req = urllib.request.Request(target_url, data=post_data, headers=headers, method=method)
            
            with urllib.request.urlopen(req, timeout=60, context=ssl_context) as response:
                response_data = response.read()
                response_code = response.getcode()
                
                logger.info(f"Sunways API responded with status: {response_code}")
                
                self.send_response(response_code)
                
                # Forward all headers from API to client, especially Content-Type
                for header_name, header_value in response.headers.items():
                    if header_name.lower() not in ['set-cookie', 'transfer-encoding', 'connection', 'content-encoding']:
                        self.send_header(header_name, header_value)

                # --- START OF THE CRITICAL FIX ---
                # Use get_all() to reliably get all Set-Cookie headers
                cookie_headers = response.headers.get_all('Set-Cookie')
                if cookie_headers:
                    for cookie in cookie_headers:
                        self.send_header('Set-Cookie', cookie)
                        logger.info(f"SUCCESS: Forwarding Set-Cookie header: {cookie}")
                else:
                    logger.warning("WARNING: No Set-Cookie header found in response from Sunways API.")
                # --- END OF THE CRITICAL FIX ---
                
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(response_data)
                
        except urllib.error.HTTPError as e:
            logger.error(f"HTTP error from Sunways API: {e.code} - {e.reason}")
            error_data = e.read()
            self.send_response(e.code)
            self.send_header('Content-Type', 'application/json')
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(error_data)
        except Exception as e:
            logger.error(f"Unexpected error in proxy: {str(e)}", exc_info=True)
            self._send_error_response(500, f"Internal proxy error: {str(e)}")

    def do_GET(self):
        self._proxy_request('GET')

    def do_POST(self):
        self._proxy_request('POST')

    def _send_error_response(self, status_code, message):
        """Send a JSON error response"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self._send_cors_headers()
        self.end_headers()
        error_data = {"error": message, "status": status_code}
        self.wfile.write(json.dumps(error_data).encode())

def run_server():
    """Start the proxy server"""
    port = int(os.environ.get('PORT', 8080))
    server_address = ('0.0.0.0', port)
    httpd = HTTPServer(server_address, SunwaysProxyHandler)
    
    logger.info(f"Starting Sunways Proxy Server on port {port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    logger.info("Server stopped.")

if __name__ == '__main__':
    run_server()
