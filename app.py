# app.py for Render.com (Maximum Debugging Version)
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
    url = f"{TARGET_BASE_URL}/{subpath}"
    logger.info(f"--- New Request ---")
    logger.info(f"Proxying {request.method} for path: {subpath}")

    upstream_headers = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest',
        'ver': 'pc',
        'Origin': 'https://www.sunways-portal.com',
        'Referer': 'https://www.sunways-portal.com/',
    }

    if 'token' in request.headers:
        upstream_headers['token'] = request.headers['token']
        logger.info(f"Forwarding token: ...{request.headers['token'][-10:]}")
    
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
        
        # --- MAXIMUM DEBUGGING ---
        logger.info(f"--- Response from Sunways API ---")
        logger.info(f"  Status Code: {resp.status_code}")
        logger.info(f"  Headers: {resp.headers}")
        # Try to decode the content, but don't fail if it's not text
        try:
            body_preview = resp.content.decode('utf-8', errors='replace')
        except:
            body_preview = str(resp.content)
        logger.info(f"  Full Body: {body_preview}")
        # --- END DEBUGGING ---

        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers_to_forward = []
        for name, value in resp.headers.items():
            if name.lower() not in excluded_headers:
                headers_to_forward.append((name, value))
        
        response = Response(resp.content, resp.status_code, headers_to_forward)
        return response

    except requests.exceptions.RequestException as e:
        logger.error(f"Proxy request to Sunways failed: {e}")
        return Response(f"Proxy Error: {e}", status=502)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
