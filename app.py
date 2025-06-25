# Updated app.py for Render.com with better header forwarding
import os
import requests
from flask import Flask, request, Response, make_response
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
TARGET_BASE_URL = "https://api.sunways-portal.com"

@app.route('/<path:subpath>', methods=['GET', 'POST'])
def proxy(subpath):
    """
    Enhanced proxy that forwards all headers including cookies
    """
    url = f"{TARGET_BASE_URL}/{subpath}"
    logger.info(f"--- New Request ---")
    logger.info(f"Proxying {request.method} for path: {subpath}")

    # Forward all headers from the client request
    upstream_headers = {}
    for header, value in request.headers:
        # Skip headers that requests library handles
        if header.lower() not in ['host', 'content-length']:
            upstream_headers[header] = value
    
    # Log if token is being forwarded
    if 'token' in upstream_headers:
        logger.info("Forwarding 'token' header")
    
    # Forward cookies
    if request.cookies:
        cookie_string = '; '.join([f"{k}={v}" for k, v in request.cookies.items()])
        upstream_headers['Cookie'] = cookie_string
        logger.info(f"Forwarding cookies: {list(request.cookies.keys())}")
    
    data = request.get_data()
    
    try:
        resp = requests.request(
            method=request.method,
            url=url,
            headers=upstream_headers,
            data=data,
            params=request.args,
            timeout=30,
            allow_redirects=False
        )
        
        logger.info(f"--- Response from Sunways API ---")
        logger.info(f"  Status Code: {resp.status_code}")
        logger.info(f"  Content-Type: {resp.headers.get('Content-Type')}")
        
        # Create response
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers_to_forward = [(name, value) for (name, value) in resp.headers.items() 
                              if name.lower() not in excluded_headers]
        
        response = Response(resp.content, resp.status_code, headers_to_forward)
        
        # Forward any cookies from the API
        if 'Set-Cookie' in resp.headers:
            response.headers['Set-Cookie'] = resp.headers['Set-Cookie']
            
        return response

    except requests.exceptions.RequestException as e:
        logger.error(f"Proxy request to Sunways failed: {e}")
        return Response(f"Proxy Error: {e}", status=502)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
