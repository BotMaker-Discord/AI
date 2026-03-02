import os
import sys
import json
import base64
import logging

from flask import Flask, request, jsonify, Response
from flask_cors import CORS

# --- Logging setup (critical for Railway debugging) ---
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# --- App creation at module level (gunicorn imports this) ---
app = Flask(__name__)
CORS(app)

# --- Your base64-encoded HTML ---
# Paste your actual base64 string here
INDEX_HTML_B64 = "PUT_YOUR_BASE64_HTML_HERE"

try:
    INDEX_HTML = base64.b64decode(INDEX_HTML_B64).decode("utf-8")
    logger.info("HTML template decoded successfully (%d bytes)", len(INDEX_HTML))
except Exception as e:
    logger.error("Failed to decode HTML template: %s", e)
    INDEX_HTML = "<h1>App loaded but HTML template failed to decode</h1>"

# --- Validate required env vars at import time (--preload surfaces this) ---
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    logger.warning("ANTHROPIC_API_KEY is not set — /api/generate will fail")


@app.route("/")
def index():
    return Response(INDEX_HTML, mimetype="text/html")


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/api/generate", methods=["POST"])
def generate():
    if not ANTHROPIC_API_KEY:
        return jsonify({"error": "ANTHROPIC_API_KEY not configured"}), 500

    import requests as req  # local import to keep startup fast

    try:
        body = request.get_json(force=True)
        logger.info("/api/generate called with model=%s", body.get("model", "unknown"))

        resp = req.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json=body,
            timeout=90,
        )

        return Response(
            resp.content,
            status=resp.status_code,
            content_type=resp.headers.get("content-type", "application/json"),
        )

    except req.exceptions.Timeout:
        logger.error("Upstream Anthropic API timed out")
        return jsonify({"error": "Upstream API timeout"}), 504
    except Exception as e:
        logger.exception("Error in /api/generate")
        return jsonify({"error": str(e)}), 500


# --- Only used for local dev (gunicorn ignores this) ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    logger.info("Starting dev server on port %d", port)
    app.run(host="0.0.0.0", port=port, debug=True)
