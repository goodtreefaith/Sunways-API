# app.py for Render.com (Final, Deliberate Version)
import os
import requests
from flask import Flask, request, Response
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
TARGET_BASE_URL = "https://api.sunways-portal.com"

@app.route('/<path:subpath>', methods=['GET', 'POST'])
def proxy(subpath):
    """
    A deliberate proxy that explicitly constructs headers for the upstream request,
    ensuring the 'token' is handled correctly.
    """
    url = f"{TARGET_BASE_URL}/{subpath}"
    logger.info(f"Proxying {request.method} for path: {subpath}")

    # --- START OF THE FINAL FIX ---
    # Create a fresh, clean dictionary for the headers to be sent to Sunways.
    upstream_headers = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest',
        'ver': 'pc'
    }

    # Explicitly check for the 'token' and 'Content-Type' headers from the incoming
    # request from Home Assistant and add them to our clean dictionary.
    if 'token' in request.headers:
        upstream_headers['token'] = request.headers['token']
        logger.info("Found and added 'token' header to upstream request.")
    
    if 'Content-Type' in request.headers:
        upstream_headers['Content-Type'] = request.headers['Content-Type']
    # --- END OF THE FINAL FIX ---
    
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
        
        # Forward the entire response from Sunways back to Home Assistant
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers_to_forward = [(name, value) for (name, value) in resp.raw.headers.items() if name.lower() not in excluded_headers]
        
        response = Response(resp.content, resp.status_code, headers_to_forward)
        return response

    except requests.exceptions.RequestException as e:
        logger.error(f"Proxy request to Sunways failed: {e}")
        return Response(f"Proxy Error: {e}", status=502)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
