# app.py for Render.com (Final "Less is More" Version)
import os
import requests
from flask import Flask, request, Response
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
TARGET_BASE_URL = "https://api.sunways-portal.com"

@app.route('/<path:subpath>', methods=['GET', 'POST'])
def proxy(subpath):
    """
    A minimal proxy that only forwards the essential headers required by the API,
    avoiding any extra headers that might confuse it.
    """
    url = f"{TARGET_BASE_URL}/{subpath}"
    logger.info(f"--- New Request ---")
    logger.info(f"Proxying {request.method} for path: {subpath}")

    # Create a minimal set of headers for the upstream request.
    upstream_headers = {}

    # The API requires Content-Type for POST login requests.
    if 'Content-Type' in request.headers:
        upstream_headers['Content-Type'] = request.headers['Content-Type']
    
    # The API requires the token for data requests.
    if 'token' in request.headers:
        upstream_headers['token'] = request.headers['token']
        logger.info("Forwarding essential 'token' header.")
    
    data = request.get_data()
    
    try:
        resp = requests.request(
            method=request.method,
            url=url,
            headers=upstream_headers,
            data=data,
            params=request.args,
            timeout=30
        )
        
        logger.info(f"--- Response from Sunways API ---")
        logger.info(f"  Status Code: {resp.status_code}")
        logger.info(f"  Content-Type: {resp.headers.get('Content-Type')}")
        
        # Forward the response back to Home Assistant
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers_to_forward = [(name, value) for (name, value) in resp.headers.items() if name.lower() not in excluded_headers]
        
        response = Response(resp.content, resp.status_code, headers_to_forward)
        return response

    except requests.exceptions.RequestException as e:
        logger.error(f"Proxy request to Sunways failed: {e}")
        return Response(f"Proxy Error: {e}", status=502)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
