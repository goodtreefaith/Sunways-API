# app.py for Render.com (with token-to-cookie translation)
import os
import requests
from flask import Flask, request, Response, jsonify
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

TARGET_BASE_URL = "https://api.sunways-portal.com"

@app.route('/<path:subpath>', methods=['GET', 'POST'])
def proxy(subpath):
    """A robust proxy that translates the token header to a cookie."""
    
    url = f"{TARGET_BASE_URL}/{subpath}"
    headers = {key: value for (key, value) in request.headers if key.lower() != 'host'}
    data = request.get_data()
    
    logger.info(f"Proxying {request.method} for path: {subpath}")

    # --- START OF THE FINAL FIX ---
    # The Sunways API expects the token back as a cookie, not a header.
    # We must translate the 'token' header from HA into a 'Cookie' header for Sunways.
    if 'token' in headers:
        token_value = headers['token']
        headers['Cookie'] = f'token={token_value}'
        # Remove the original token header to avoid any confusion
        del headers['token']
        logger.info("Translated 'token' header to 'Cookie' header for upstream request.")
    # --- END OF THE FINAL FIX ---

    try:
        resp = requests.request(
            method=request.method,
            url=url,
            headers=headers,
            data=data,
            params=request.args,
            timeout=30
        )

        if resp.status_code != 200:
            logger.error(f"Upstream API Error. Status: {resp.status_code}, Body: {resp.text[:500]}")
            return jsonify({"error": "Upstream API Error", "status_code": resp.status_code, "details": resp.text[:500]}), resp.status_code

        if 'application/json' not in resp.headers.get('Content-Type', ''):
            logger.error(f"Upstream API did not return JSON. Body: {resp.text[:500]}")
            return jsonify({"error": "Upstream API did not return JSON", "details": resp.text[:500]}), 502

        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers_to_forward = [(name, value) for (name, value) in resp.raw.headers.items() if name.lower() not in excluded_headers]
        
        response = Response(resp.content, resp.status_code, headers_to_forward)
        return response

    except requests.exceptions.RequestException as e:
        logger.error(f"Proxy request to Sunways failed: {e}")
        return jsonify({"error": "Proxy request failed", "details": str(e)}), 502

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
