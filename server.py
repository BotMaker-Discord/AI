"""
Roblox Animation AI — Flask Proxy Server
=========================================
SETUP (local):
  1. pip install flask flask-cors requests
  2. set ANTHROPIC_API_KEY=sk-ant-...   (Windows)
     export ANTHROPIC_API_KEY=sk-ant-... (Mac/Linux)
  3. python server.py
  4. Open http://localhost:5000

DEPLOYING (Railway):
  - Push all files to GitHub
  - Connect repo on railway.app
  - Add ANTHROPIC_API_KEY in Railway Variables tab
  - Procfile should contain: web: gunicorn server:app --bind 0.0.0.0:$PORT
"""

import os
import time
import requests
from collections import defaultdict
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# Absolute path to the folder this file lives in — works on Railway and locally
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, static_folder=BASE_DIR)
CORS(app)

# ── API Key ────────────────────────────────────────────────────────────────
API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"

# ── Rate limiting ──────────────────────────────────────────────────────────
request_log = defaultdict(list)
RATE_LIMIT = 20
RATE_WINDOW = 3600

def is_rate_limited(ip):
    now = time.time()
    request_log[ip] = [t for t in request_log[ip] if now - t < RATE_WINDOW]
    if len(request_log[ip]) >= RATE_LIMIT:
        return True
    request_log[ip].append(now)
    return False

# ── Routes ─────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    """Serve the HTML frontend"""
    return send_from_directory(BASE_DIR, "index.html")

@app.route("/api/generate", methods=["POST"])
def generate():
    """Proxy — forwards requests to Anthropic with the server-side API key"""

    # Rate limit by IP
    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    if client_ip:
        client_ip = client_ip.split(",")[0].strip()
    if is_rate_limited(client_ip):
        return jsonify({"error": {"message": "Rate limit reached. Try again in an hour."}}), 429

    # Check key is configured
    if not API_KEY:
        return jsonify({"error": {"message": "Server API key not configured. Set ANTHROPIC_API_KEY environment variable."}}), 500

    # Parse body
    body = request.get_json()
    if not body:
        return jsonify({"error": {"message": "Invalid request body."}}), 400

    try:
        resp = requests.post(
            ANTHROPIC_URL,
            headers={
                "x-api-key": API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json=body,
            timeout=120,
        )
        return jsonify(resp.json()), resp.status_code

    except requests.exceptions.Timeout:
        return jsonify({"error": {"message": "Request timed out."}}), 504
    except Exception as e:
        return jsonify({"error": {"message": str(e)}}), 500


@app.route("/health")
def health():
    return jsonify({"status": "ok", "key_configured": bool(API_KEY)})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n🎮 Roblox Animation AI Server")
    print(f"   Running at: http://localhost:{port}")
    print(f"   API key:    {'✓ set' if API_KEY else '✗ NOT SET'}")
    print(f"   Rate limit: {RATE_LIMIT} requests / hour per IP\n")
    app.run(host="0.0.0.0", port=port, debug=False)
