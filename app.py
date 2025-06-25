# app.py for Render.com (Final version with correct header filtering)
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
    A deliberate proxy that explicitly constructs headers and filters response headers
    to prevent content encoding mismatches.
    """
    url = f"{TARGET_BASE_URL}/{subpath}"
    logger.info(f"Proxying {request.method} for path: {subpath}")

    upstream_headers = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest',
        'ver': 'pc'
    }

    if 'token' in request.headers:
        upstream_headers['token'] = request.headers['token']
        logger.info("Added 'token' header to upstream request.")
    
    if 'Content-Type' in request.headers:
        upstream_headers['Content-Type'] = request.headers['Content-Type']
    
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
        
        # --- START OF THE FINAL FIX ---
        # These headers are managed by the connection and can cause issues if forwarded.
        # Crucially, we remove 'Content-Encoding' because `requests` automatically decompresses the body.
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers_to_forward = []
        for name, value in resp.headers.items():
            if name.lower() not in excluded_headers:
                headers_to_forward.append((name, value))
        # --- END OF THE FINAL FIX ---
        
        # Create and return the response with the decompressed content and clean headers.
        response = Response(resp.content, resp.status_code, headers_to_forward)
        return response

    except requests.exceptions.RequestException as e:
        logger.error(f"Proxy request to Sunways failed: {e}")
        return Response(f"Proxy Error: {e}", status=502)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
