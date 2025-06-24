#!/usr/bin/env python3
"""
Sunways API Proxy for Render.com
Fixes SSL handshake issues by proxying requests to api.sunways-portal.com
"""

import os
import json
import urllib.request
import urllib.parse
import ssl
from http.server import BaseHTTPRequestHandler, HTTPServer
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SunwaysProxyHandler(BaseHTTPRequestHandler):
    """HTTP request handler that proxies requests to Sunways API"""
    
    def log_message(self, format, *args):
        """Override to use proper logging"""
        logger.info(f"{self.address_string()} - {format % args}")
    
    def _send_cors_headers(self):
        """Send CORS headers to allow cross-origin requests"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
    
    def do_OPTIONS(self):
        """Handle preflight CORS requests"""
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()
    
    def do_POST(self):
        """Handle POST requests to Sunways API"""
        try:
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length) if content_length > 0 else b''
            
            # Build target URL
            target_url = f"https://api.sunways-portal.com{self.path}"
            logger.info(f"Proxying POST request to: {target_url}")
            
            # Prepare headers for Sunways API
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json',
                'Origin': 'https://www.sunways-portal.com',
                'Referer': 'https://www.sunways-portal.com/',
            }
            
            # Copy Authorization header if present
            if 'Authorization' in self.headers:
                headers['Authorization'] = self.headers['Authorization']
            
            # Create SSL context
            ssl_context = ssl.create_default_context()
            
            # Make request to Sunways API
            req = urllib.request.Request(target_url, post_data, headers)
            
            with urllib.request.urlopen(req, timeout=60, context=ssl_context) as response:
                # Read response data
                response_data = response.read()
                response_code = response.getcode()
                
                logger.info(f"Sunways API responded with status: {response_code}")
                
                # Send response back to client
                self.send_response(response_code)
                self.send_header('Content-Type', 'application/json')
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(response_data)
                
        except urllib.error.HTTPError as e:
            logger.error(f"HTTP error from Sunways API: {e.code} - {e.reason}")
            try:
                error_data = e.read()
                self.send_response(e.code)
                self.send_header('Content-Type', 'application/json')
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(error_data)
            except:
                self._send_error_response(e.code, str(e.reason))
                
        except urllib.error.URLError as e:
            logger.error(f"Connection error to Sunways API: {e.reason}")
            self._send_error_response(503, f"Connection error: {e.reason}")
            
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            self._send_error_response(500, f"Internal proxy error: {str(e)}")
    
    def do_GET(self):
        """Handle GET requests to Sunways API"""
        try:
            # Build target URL
            target_url = f"https://api.sunways-portal.com{self.path}"
            logger.info(f"Proxying GET request to: {target_url}")
            
            # Prepare headers for Sunways API
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json',
                'Origin': 'https://www.sunways-portal.com',
                'Referer': 'https://www.sunways-portal.com/',
            }
            
            # Copy Authorization header if present
            if 'Authorization' in self.headers:
                headers['Authorization'] = self.headers['Authorization']
            
            # Create SSL context
            ssl_context = ssl.create_default_context()
            
            # Make request to Sunways API
            req = urllib.request.Request(target_url, headers=headers)
            
            with urllib.request.urlopen(req, timeout=60, context=ssl_context) as response:
                # Read response data
                response_data = response.read()
                response_code = response.getcode()
                
                logger.info(f"Sunways API responded with status: {response_code}")
                
                # Send response back to client
                self.send_response(response_code)
                self.send_header('Content-Type', 'application/json')
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(response_data)
                
        except urllib.error.HTTPError as e:
            logger.error(f"HTTP error from Sunways API: {e.code} - {e.reason}")
            try:
                error_data = e.read()
                self.send_response(e.code)
                self.send_header('Content-Type', 'application/json')
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(error_data)
            except:
                self._send_error_response(e.code, str(e.reason))
                
        except urllib.error.URLError as e:
            logger.error(f"Connection error to Sunways API: {e.reason}")
            self._send_error_response(503, f"Connection error: {e.reason}")
            
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            self._send_error_response(500, f"Internal proxy error: {str(e)}")
    
    def _send_error_response(self, status_code, message):
        """Send a JSON error response"""
        try:
            self.send_response(status_code)
            self.send_header('Content-Type', 'application/json')
            self._send_cors_headers()
            self.end_headers()
            
            error_data = {
                "error": message,
                "status": status_code
            }
            self.wfile.write(json.dumps(error_data).encode())
        except:
            pass

def run_server():
    """Start the proxy server"""
    # Get port from Render environment or default to 8080
    port = int(os.environ.get('PORT', 8080))
    
    server = HTTPServer(('0.0.0.0', port), SunwaysProxyHandler)
    
    logger.info(f"Starting Sunways Proxy Server on port {port}")
    logger.info(f"Proxying requests to: https://api.sunways-portal.com")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down server...")
        server.shutdown()

if __name__ == '__main__':
    run_server()
