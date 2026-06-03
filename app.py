"""
Edge IoT — Flask Dashboard Server

This Flask web server serves the real-time IoT monitoring dashboard.
It reads the log.json file written by bridge.py and provides JSON data
endpoints for the web frontend to render charts and statistics.

Architecture:
- /         → Serve index.html (the dashboard UI)
- /data     → JSON endpoint with latest sensor data, time-series arrays, alerts
- /health   → Simple health check endpoint (for monitoring)

The dashboard updates every 3 seconds by polling /data endpoint.
"""

from flask import Flask, render_template, jsonify
import json
import os
from datetime import datetime, timezone

# Initialize Flask app
app = Flask(__name__)

# Configuration constants
LOG_FILE = "log.json"         # File where bridge.py writes sensor data
MAX_RECORDS = 20              # Number of historical records to serve to dashboard

# ── cache control ─────────────────────────────────────────────────────────────
# IMPORTANT: We disable browser caching so the dashboard always fetches fresh data

@app.after_request
def add_no_cache_headers(response):
    """
    Disable caching for all responses.
    
    This is crucial for real-time dashboards. If the browser caches responses,
    the user won't see new data - they'll see stale cached data.
    
    By disabling caching, we force the browser to always fetch fresh data
    from the server.
    """
    # Tell browser, proxies, and CDNs not to cache
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"  # For HTTP/1.0 compatibility
    response.headers["Expires"] = "0"        # For very old clients
    return response

# ── helpers ───────────────────────────────────────────────────────────────────
# Utility functions for log file parsing and data validation

def is_valid_record(record: dict) -> bool:
    """
    Validate that a record has required fields.
    
    We only display records that have all required sensor fields.
    Records without these fields are incomplete and shouldn't be shown.
    
    Args:
        record: JSON object to validate
        
    Returns:
        True if record has ALL minimum required fields, False otherwise
    """
    required_fields = ["timestamp", "temperature", "humidity"]
    return all(field in record for field in required_fields)


def parse_log(n: int = MAX_RECORDS) -> list[dict]:
    """
    Return the last n non-empty JSON lines from log.json.
    
    This function reads the log file line-by-line and parses newline-delimited JSON.
    It's robust to:
    - Missing or empty lines
    - Malformed JSON (skips those lines)
    - Wrapped logging records (unwraps them)
    
    We return only the LAST n records because:
    1. The dashboard only shows recent history (not all historical data)
    2. The log file can grow large, so we limit memory usage
    
    Args:
        n: Number of records to return (default 20)
        
    Returns:
        List of parsed JSON objects from the log file (last n records)
        Returns empty list if log file doesn't exist
    """
    # If log file doesn't exist yet, return empty (no data)
    if not os.path.exists(LOG_FILE):
        return []
    
    records = []
    # Read log file line-by-line (streaming approach, memory efficient)
    with open(LOG_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # Skip empty lines
            if not line:
                continue
            try:
                obj = json.loads(line)
                # bridge.py may wrap JSON in a logging record format
                # If we detect that format, unwrap it to get the actual data
                if "message" in obj and obj.get("name") == "json-log":
                    # Extract the actual JSON from the logging wrapper
                    obj = json.loads(obj["message"])
                # Only include valid records (have required fields)
                if is_valid_record(obj):
                    records.append(obj)
            except (json.JSONDecodeError, KeyError, ValueError):
                # Malformed line - skip it and continue
                # This makes the system resilient to corruption
                continue
    
    # Return ONLY the last n records
    # This keeps memory usage bounded and returns fresh data
    return records[-n:]


def iso_to_display(ts: str | None) -> str:
    """
    Convert ISO timestamp string to display format.
    
    Converts from ISO format (e.g., "2024-01-15T10:30:45+00:00")
    to user-friendly time display (e.g., "10:30:45")
    
    This is used in the dashboard to show readable timestamps.
    
    Args:
        ts: ISO format timestamp string or None
        
    Returns:
        Formatted time string (e.g., "14:23:15") or "--" if invalid
    """
    if not ts:
        return "--"  # Missing data
    try:
        dt = datetime.fromisoformat(ts)
        return dt.astimezone().strftime("%H:%M:%S")
    except (ValueError, TypeError):
        # Parsing failed - return the original timestamp
        return ts


def safe_get(obj: dict, key: str, default=None):
    """
    Safely get a value from a dictionary with type checking.
    
    This defensive function prevents KeyError and TypeError exceptions
    when accessing nested data structures. It's especially useful when
    working with partially-complete JSON records.
    
    Args:
        obj: Dictionary to access (or None)
        key: Key to retrieve
        default: Default value if key not found or obj is None
        
    Returns:
        Value at key, or default if missing or obj is not a dict
    """
    # Type check first - only dicts support .get()
    if not isinstance(obj, dict):
        return default
    return obj.get(key, default)


# ── routes ────────────────────────────────────────────────────────────────────
# Flask HTTP endpoints that serve the web dashboard

@app.route("/")
def index():
    """
    Serve the main dashboard HTML page.
    
    Returns:
        The index.html template (rendered with no dynamic content)
    """
    return render_template("index.html")


@app.route("/data")
def data():
    """
    Serve the latest sensor data and chart information.
    
    This is the main data API endpoint called by the dashboard every 3 seconds.
    It returns:
    1. Time-series arrays for charts (temperatures, humidity, etc.)
    2. Latest readings for stat cards
    3. Per-device breakdown (individual device stats)
    4. Alert status (whether risk is critical)
    
    Returns:
        JSON object with time-series data and latest readings
        Status codes:
        - 200: Success (includes data)
        - 400: JSON parsing error in log file
        - 500: File I/O error
    """
    try:
        records = parse_log()
        if not records:
            # No data available yet - return empty template with default values
            return jsonify({
                "temperature": [], "humidity": [], "status": [],
                "timestamps": [], "modes": [], "risks": [],
                "latest": {}, "devices": {}, "alert": False,
            }), 200

        # ────────────────────────────────────────────────────────────────────
        # Build time-series arrays for Chart.js line charts
        # Each element at index i corresponds to one historical reading
        # ────────────────────────────────────────────────────────────────────
        temps, humidity, status, timestamps, modes, risks = [], [], [], [], [], []
        for d in records:
            # Extract values with safe defaults (0 for numbers, defaults for strings)
            temps.append(d.get("temperature") or 0)
            humidity.append(d.get("humidity") or 0)
            status.append(d.get("status", "Normal"))
            timestamps.append(d.get("timestamp", datetime.now(timezone.utc).isoformat()))
            modes.append(d.get("mode", "NORMAL"))  # NORMAL | WARNING | CRITICAL
            risks.append(d.get("risk", 0))

        # ────────────────────────────────────────────────────────────────────
        # Extract latest reading (for stat cards and alerts)
        # ────────────────────────────────────────────────────────────────────
        latest   = records[-1] if records else {}  # Last record is most recent
        lat_risk = latest.get("risk", 0)
        # Alert triggered if risk is critical (>= 7)
        alert    = lat_risk >= 7  # Alert threshold is risk >= 7

        # Per-device breakdown from latest record (individual device stats)
        device_breakdown = latest.get("devices", {})

        # Return complete data structure for dashboard
        return jsonify({
            # ── TIME-SERIES ARRAYS (for Chart.js line charts) ──
            "temperature": temps,   # Array of temp readings over time
            "humidity":    humidity,   # Array of humidity readings over time
            "status":      status,   # Array of status labels
            "timestamps":  timestamps,  # Array of timestamps (for X-axis)
            "modes":       modes,   # Array of system modes (color coding)
            "risks":       risks,   # Array of risk scores (for coloring bars)
            
            # ── LATEST SNAPSHOT (for stat cards) ──
            "latest": {
                "temperature":  latest.get("temperature", "--"),
                "humidity":     latest.get("humidity", "--"),
                "status":       latest.get("status", "Normal"),
                "mode":         latest.get("mode", "NORMAL"),
                "risk":         lat_risk,
                "device_id":    latest.get("device_id", "EDGE-AGG"),  # Usually aggregate
                "uptime":       latest.get("uptime", 0),
                "device_count": latest.get("device_count", 0),  # How many devices online
            },
            
            # ── PER-DEVICE BREAKDOWN ──
            "devices": device_breakdown,  # Individual stats for each connected device
            
            # ── ALERT STATUS ──
            "alert":   alert,  # True if system risk is critical
        })

    except json.JSONDecodeError as e:
        # Error parsing JSON from log file
        app.logger.error(f"/data JSON error: {e}")
        return jsonify({
            "temperature": [], "humidity": [], "status": [],
            "timestamps": [], "modes": [], "risks": [],
            "latest": {}, "devices": {}, "alert": False,
        }), 400
    except IOError as e:
        # Error reading log file (permissions, missing file, etc.)
        app.logger.error(f"/data IO error: {e}")
        return jsonify({
            "temperature": [], "humidity": [], "status": [],
            "timestamps": [], "modes": [], "risks": [],
            "latest": {}, "devices": {}, "alert": False,
        }), 500
    except Exception as e:
        # Unexpected error - return empty response
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
