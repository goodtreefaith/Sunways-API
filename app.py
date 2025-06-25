# app.py for Render.com
import os
import requests
from flask import Flask, request, Response

app = Flask(__name__)

TARGET_BASE_URL = "https://api.sunways-portal.com"

@app.route('/<path:subpath>', methods=['GET', 'POST'])
def proxy(subpath):
    """A simple proxy that forwards requests and responses."""
    
    # Build the target URL
    url = f"{TARGET_BASE_URL}/{subpath}"
    
    # Copy headers from the incoming request
    headers = {key: value for (key, value) in request.headers if key != 'Host'}
    
    # Get the body from the incoming request
    data = request.get_data()
    
    try:
        # Make the request to the real Sunways API
        resp = requests.request(
            method=request.method,
            url=url,
            headers=headers,
            data=data,
            params=request.args,
            timeout=30
        )
        
        # Exclude problematic headers from the response
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers_to_forward = [(name, value) for (name, value) in resp.raw.headers.items() if name.lower() not in excluded_headers]
        
        # Create and return the response to Home Assistant
        response = Response(resp.content, resp.status_code, headers_to_forward)
        return response

    except requests.exceptions.RequestException as e:
        return Response(f"Proxy Error: {e}", status=502)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
