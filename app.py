"""
Edge IoT — Flask Dashboard Server
Reads log.json written by bridge.py and serves the real-time dashboard.
"""

from flask import Flask, render_template, jsonify
import json
import os
from datetime import datetime, timezone

# Initialize Flask app
app = Flask(__name__)

# Configuration constants
LOG_FILE = "log.json"
MAX_RECORDS = 20

# ── cache control ─────────────────────────────────────────────────────────────

@app.after_request
def add_no_cache_headers(response):
    """
    Disable caching for all responses.
    
    Ensures dashboard always shows latest data from log.json.
    """
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# ── helpers ───────────────────────────────────────────────────────────────────

def parse_log(n: int = MAX_RECORDS) -> list[dict]:
    """
    Return the last n non-empty JSON lines from log.json.
    
    Args:
        n: Number of records to return
        
    Returns:
        List of parsed JSON objects from the log file
    """
    if not os.path.exists(LOG_FILE):
        return []
    records = []
    with open(LOG_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                # bridge.py wraps the JSON in a logging record; unwrap if needed
                if "message" in obj and obj.get("name") == "json-log":
                    obj = json.loads(obj["message"])
                records.append(obj)
            except (json.JSONDecodeError, KeyError):
                continue
    return records[-n:]


def iso_to_display(ts: str | None) -> str:
    """
    Convert ISO timestamp string to display format.
    
    Args:
        ts: ISO format timestamp string or None
        
    Returns:
        Formatted time string or "--" if invalid
    """
    if not ts:
        return "--"
    try:
        dt = datetime.fromisoformat(ts)
        return dt.astimezone().strftime("%H:%M:%S")
    except (ValueError, TypeError):
        return ts


# ── routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/data")
def data():
    """
    Serve the latest sensor data and chart information.
    
    Returns:
        JSON object with time-series data and latest readings
    """
    try:
        records = parse_log()
        if not records:
            return jsonify({
                "temperature": [], "humidity": [], "status": [],
                "timestamps": [], "modes": [], "risks": [],
                "latest": {}, "devices": {}, "alert": False,
            }), 200

        temps, humidity, status, timestamps, modes, risks = [], [], [], [], [], []
        for d in records:
            temps.append(d.get("temperature") or 0)
            humidity.append(d.get("humidity") or 0)
            status.append(d.get("status", "Normal"))
            timestamps.append(d.get("timestamp", datetime.now(timezone.utc).isoformat()))
            modes.append(d.get("mode", "NORMAL"))
            risks.append(d.get("risk", 0))

        latest   = records[-1] if records else {}
        lat_risk = latest.get("risk", 0)
        alert    = lat_risk >= 7

        # Per-device breakdown from latest record
        device_breakdown = latest.get("devices", {})

        return jsonify({
            # time-series arrays (for charts)
            "temperature": temps,
            "humidity":    humidity,
            "status":      status,
            "timestamps":  timestamps,
            "modes":       modes,
            "risks":       risks,
            # latest snapshot (for stat cards)
            "latest": {
                "temperature":  latest.get("temperature", "--"),
                "humidity":     latest.get("humidity", "--"),
                "status":       latest.get("status", "Normal"),
                "mode":         latest.get("mode", "NORMAL"),
                "risk":         lat_risk,
                "device_id":    latest.get("device_id", "EDGE-AGG"),
                "uptime":       latest.get("uptime", 0),
                "device_count": latest.get("device_count", 0),
            },
            "devices": device_breakdown,
            "alert":   alert,
        })

    except json.JSONDecodeError as e:
        app.logger.error(f"/data JSON error: {e}")
        return jsonify({
            "temperature": [], "humidity": [], "status": [],
            "timestamps": [], "modes": [], "risks": [],
            "latest": {}, "devices": {}, "alert": False,
        }), 400
    except IOError as e:
        app.logger.error(f"/data IO error: {e}")
        return jsonify({
            "temperature": [], "humidity": [], "status": [],
            "timestamps": [], "modes": [], "risks": [],
            "latest": {}, "devices": {}, "alert": False,
        }), 500
    except Exception as e:
        app.logger.error(f"/data error: {e}")
        return jsonify({
            "temperature": [], "humidity": [], "status": [],
            "timestamps": [], "modes": [], "risks": [],
            "latest": {}, "devices": {}, "alert": False,
        }), 500


@app.route("/health")
def health():
    """
    Health check endpoint.
    
    Returns:
        JSON object with status and current timestamp
    """
    return jsonify({"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
