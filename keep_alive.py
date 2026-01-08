"""
Minimal HTTP health check server to keep Render web service awake.
Runs alongside the main bot in a separate thread.
"""
import os
from flask import Flask, jsonify, render_template
from threading import Thread

app = Flask(__name__)


@app.route("/")
def home():
    """Landing page with bot information"""
    try:
        return render_template("index.html")
    except Exception:
        # Fallback if template not found
        return jsonify({"status": "alive", "service": "RoboVAI Bot"})


@app.route("/health")
def health():
    return jsonify({"status": "healthy", "bot": "running"})


@app.route("/api/status")
def api_status():
    """API endpoint for monitoring"""
    return jsonify({
        "status": "alive",
        "service": "RoboVAI Bot",
        "version": "2.0",
        "features": ["telegram", "multi-platform", "ai-powered", "og-images"]
    })


def run():
    """Run Flask server in background thread"""
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)


def keep_alive():
    """Start the web server in a background thread"""
    t = Thread(target=run, daemon=True)
    t.start()
    print(f"✅ Keep-alive server started on port {os.getenv('PORT', 8080)}")
