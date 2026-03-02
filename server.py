"""
Roblox Animation AI — Flask Proxy Server
=========================================
This server holds your Anthropic API key and proxies requests from the
frontend so users never see your key.

SETUP:
  1. pip install flask flask-cors requests
  2. Set your API key:
       Windows:  set ANTHROPIC_API_KEY=sk-ant-...
       Mac/Linux: export ANTHROPIC_API_KEY=sk-ant-...
     OR just paste it directly into API_KEY below (not recommended for public servers)
  3. python server.py
  4. Open http://localhost:5000 in your browser

DEPLOYING FOR OTHER USERS:
  - Railway.app  → push to GitHub, connect repo, set ANTHROPIC_API_KEY env var
  - Render.com   → same, free tier available
  - Heroku       → heroku config:set ANTHROPIC_API_KEY=sk-ant-...
  - Any VPS      → run with gunicorn: pip install gunicorn && gunicorn server:app
"""

import os
import requests
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder=".")
CORS(app)  # Allow the HTML frontend to call this server

# ── API Key ────────────────────────────────────────────────────────────────
# Reads from environment variable (recommended) or falls back to hardcoded
API_KEY = os.environ.get("ANTHROPIC_API_KEY", "PASTE_YOUR_KEY_HERE")

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"

# ── Rate limiting (optional but recommended) ───────────────────────────────
from collections import defaultdict
import time

request_log = defaultdict(list)
RATE_LIMIT = 20       # max requests
RATE_WINDOW = 3600    # per hour (seconds)

def is_rate_limited(ip):
    now = time.time()
    timestamps = request_log[ip]
    # Remove old entries outside the window
    request_log[ip] = [t for t in timestamps if now - t < RATE_WINDOW]
    if len(request_log[ip]) >= RATE_LIMIT:
        return True
    request_log[ip].append(now)
    return False

# ── Routes ─────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    """Serve the HTML frontend"""
    return send_from_directory(".", "index.html")

@app.route("/api/generate", methods=["POST"])
def generate():
    """Proxy route — receives request from frontend, forwards to Anthropic"""

    # Rate limiting by IP
    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    if is_rate_limited(client_ip):
        return jsonify({"error": {"message": "Rate limit reached. Try again in an hour."}}), 429

    # Validate key is set
    if not API_KEY or API_KEY == "PASTE_YOUR_KEY_HERE":
        return jsonify({"error": {"message": "Server API key not configured. Set ANTHROPIC_API_KEY."}}), 500

    # Forward request body to Anthropic
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
    key_set = bool(API_KEY and API_KEY != "PASTE_YOUR_KEY_HERE")
    return jsonify({"status": "ok", "key_configured": key_set})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    key_set = bool(API_KEY and API_KEY != "PASTE_YOUR_KEY_HERE")
    print(f"\n🎮 Roblox Animation AI Server")
    print(f"   Running at: http://localhost:{port}")
    print(f"   API key:    {'✓ set' if key_set else '✗ NOT SET — set ANTHROPIC_API_KEY env var'}")
    print(f"   Rate limit: {RATE_LIMIT} requests / hour per IP\n")
    app.run(host="0.0.0.0", port=port, debug=False)
