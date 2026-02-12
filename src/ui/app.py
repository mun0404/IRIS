from __future__ import annotations

import json
from pathlib import Path
from flask import Flask, jsonify, render_template, send_from_directory

app = Flask(__name__)

# Resolve project root regardless of where you run python from
ROOT = Path(__file__).resolve().parents[2]          # .../IRIS_Final
OUT = ROOT / "outputs" / "current"
LATEST = OUT / "latest.json"
IMAGES = OUT / "images"

@app.get("/")
def home():
    return render_template("dashboard.html")

@app.get("/api/latest")
def api_latest():
    if not LATEST.exists():
        return jsonify({})
    return jsonify(json.loads(LATEST.read_text() or "{}"))

@app.get("/images/<path:name>")
def images(name: str):
    return send_from_directory(IMAGES, name)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)