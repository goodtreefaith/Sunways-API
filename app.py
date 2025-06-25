# app.py for Render.com (with robust error handling)
import os
import requests
from flask import Flask, request, Response, jsonify
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

TARGET_BASE_URL = "https://api.sunways-portal.com"

@app.route('/<path:subpath>', methods=['GET', 'POST'])
def proxy(subpath):
    """A robust proxy that forwards requests and handles upstream errors."""
    
    url = f"{TARGET_BASE_URL}/{subpath}"
    headers = {key: value for (key, value) in request.headers if key.lower() != 'host'}
    data = request.get_data()
    
    logger.info(f"Proxying {request.method} request for path: {subpath}")

    try:
        resp = requests.request(
            method=request.method,
            url=url,
            headers=headers,
            data=data,
            params=request.args,
            timeout=30
        )

        # --- START OF ROBUST ERROR HANDLING ---
        # Check if the response from Sunways is successful
        if resp.status_code != 200:
            logger.error(f"Upstream API returned an error. Status: {resp.status_code}, Body: {resp.text[:500]}")
            # Return a proper JSON error to Home Assistant
            return jsonify({
                "error": "Upstream API Error",
                "status_code": resp.status_code,
                "details": resp.text[:500] # Return first 500 chars of the error
            }), resp.status_code

        # Check if the response is actually JSON
        if 'application/json' not in resp.headers.get('Content-Type', ''):
            logger.error(f"Upstream API did not return JSON. Content-Type: {resp.headers.get('Content-Type')}, Body: {resp.text[:500]}")
            return jsonify({
                "error": "Upstream API did not return JSON",
                "content_type": resp.headers.get('Content-Type'),
                "details": resp.text[:500]
            }), 502 # 502 Bad Gateway is appropriate here

        # --- END OF ROBUST ERROR HANDLING ---

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
