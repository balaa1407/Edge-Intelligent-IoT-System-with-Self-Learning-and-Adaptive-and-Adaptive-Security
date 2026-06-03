"""
Edge IoT — MQTT Bridge & Anomaly Processor
Python 3 | paho-mqtt

Subscribes to edgeiot/# and processes JSON telemetry published by the
upgraded ESP32 firmware. Handles multiple devices, per-device anomaly
detection, risk scoring, and structured log output compatible with the
Flask dashboard's log.json format.

Features:
  - Parses full JSON telemetry (temp, humidity, status, uptime, timestamp)
  - Per-device rolling history & Z-score anomaly detection
  - Multi-factor risk scoring (temp + humidity + device-reported status)
  - Handles LWT offline events
  - Graceful reconnect with exponential backoff
  - Thread-safe state with a queue
  - Rotating log file (max 1 MB, 3 backups)
  - Clean shutdown on Ctrl-C
"""

import time
import json
import queue
import signal
import logging
import logging.handlers
import threading
import uuid
import shutil
import os
from datetime import datetime, timezone
from collections import deque
import paho.mqtt.client as mqtt

# ── CONFIG ────────────────────────────────────────────────────────────────────
CONFIG = {
    "mqtt": {
        "server":      "test.mosquitto.org",  # PUBLIC broker
        "port":        1883,
        "client_id":   f"edge-bridge-{uuid.uuid4().hex[:8]}",  # Unique per instance
        "base_topic":  "edgeiot/balaa1407/#",
        "keepalive":   60,
        "reconnect_delay_min": 2,
        "reconnect_delay_max": 60,
    },
    "anomaly": {
        "min_history":    5,    # readings before detection kicks in
        "max_history":   20,    # rolling window size per device
        "z_threshold":  2.0,    # standard deviations for anomaly flag
    },
    "thresholds": {
        "temp_critical_high": 45.0,  # Critical high temperature
        "temp_high":          35.0,  # Warning temperature
        "temp_low":           10.0,  # Low temperature warning
        "humi_high":          80.0,  # High humidity warning
        "humi_low":           20.0,  # Low humidity warning
    },
    "log": {
        "file":         "log.json",
        "max_bytes":    1_000_000,   # 1 MB max file size
        "backup_count": 3,           # Keep 3 backup files
        "interval":     0.2,         # seconds between log writes
    },
}
# ── END CONFIG ────────────────────────────────────────────────────────────────

# ── LOGGING SETUP ─────────────────────────────────────────────────────────────
# Configure logging for the bridge
logging.basicConfig(
    level=logging.INFO,  # Use DEBUG to see verbose messages
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("edge-bridge")

# Plain newline-delimited JSON log for Flask (no logging wrapper)
_log_lock = threading.Lock()

def write_json_log(record: dict) -> None:
    """
    Write a JSON record to the log file with automatic rotation.
    
    Args:
        record: Dictionary to serialize and write as JSON
        
    Safely handles concurrent writes and file rotation.
    """
    cfg = CONFIG["log"]
    line = json.dumps(record) + "\n"
    with _log_lock:
        try:
            # Rotate manually if needed
            if os.path.exists(cfg["file"]) and os.path.getsize(cfg["file"]) >= cfg["max_bytes"]:
                _rotate_log(cfg["file"], cfg["backup_count"])
            with open(cfg["file"], "a", encoding="utf-8") as f:
                f.write(line)
        except OSError as e:
            log.error(f"Log write failed: {e}")


def _rotate_log(path: str, backups: int) -> None:
    """
    Rotate log files manually.
    
    Renames existing backups and moves current log to .1 backup.
    
    Args:
        path: Path to the main log file
        backups: Number of backup files to maintain
    """
    for i in range(backups - 1, 0, -1):
        src = f"{path}.{i}"
        dst = f"{path}.{i+1}"
        if os.path.exists(src):
            shutil.move(src, dst)
    if os.path.exists(path):
        shutil.move(path, f"{path}.1")


# ── DEVICE STATE ──────────────────────────────────────────────────────────────
class DeviceState:
    """
    Holds rolling history and last telemetry for a single device.
    
    This class is used to track sensor readings over time and detect anomalies
    by comparing new readings to historical trends. We keep a rolling window of
    temperature and humidity values to calculate statistics for anomaly detection.
    """

    def __init__(self, device_id: str):
        """
        Initialize device state with empty history.
        
        Creates empty deques (circular buffers) for temperature and humidity
        that automatically maintain a fixed max size. When a new value is added
        and we exceed max_history, the oldest value is automatically dropped.
        """
        self.device_id = device_id
        # These deques act like a circular buffer - they keep the N most recent readings
        self.temp_hist = deque(maxlen=CONFIG["anomaly"]["max_history"])
        self.humi_hist = deque(maxlen=CONFIG["anomaly"]["max_history"])
        self.last_seen = None      # Track when we last received data from this device
        self.online    = True      # Device status (online/offline)
        self.latest    = {}        # Most recent sensor reading

    def update(self, payload: dict) -> None:
        """
        Update device with new telemetry reading.
        
        When a device sends new sensor data, we:
        1. Store it as the latest reading
        2. Record the current timestamp (when we received it)
        3. Add the values to our history deques for anomaly detection
        
        Args:
            payload: Dictionary with temperature and humidity data
        """
        self.latest    = payload
        self.last_seen = datetime.now(timezone.utc)  # Mark when we last heard from device
        self.online    = True
        
        # Safely extract and validate temperature
        # We try to convert to float, and silently skip if invalid (bad data)
        if "temperature" in payload:
            try:
                temp_val = float(payload["temperature"])
                self.temp_hist.append(temp_val)  # Add to rolling history
            except (ValueError, TypeError):
                pass  # Skip invalid values - don't crash, just log nothing
                
        # Safely extract and validate humidity
        # Same pattern as temperature - be defensive about bad data
        if "humidity" in payload:
            try:
                humi_val = float(payload["humidity"])
                self.humi_hist.append(humi_val)  # Add to rolling history
            except (ValueError, TypeError):
                pass  # Skip invalid values

    # ── Z-score helpers ──────────────────────────────────────────────────────
    @staticmethod
    def _z_score(history: deque, value: float) -> float | None:
        """
        Calculate Z-score for anomaly detection.
        
        Z-score tells us how many standard deviations away from the mean a value is.
        It's used to detect outliers: if a value is too far from normal, it's likely anomalous.
        
        Formula:
            Z = |value - mean| / std_deviation
        
        If we don't have enough history yet (less than min_history readings), 
        we return None to indicate we can't make a judgment yet.
        
        Args:
            history: Deque of historical values
            value: Current value to test
            
        Returns:
            Z-score if enough history data, None otherwise
        """
        if len(history) < CONFIG["anomaly"]["min_history"]:
            return None
        mean     = sum(history) / len(history)
        variance = sum((x - mean) ** 2 for x in history) / len(history)
        std      = variance ** 0.5
        if std < 0.001:
            return 0.0
        return abs((value - mean) / std)

    def is_temp_anomaly(self) -> bool:
        """
        Check if current temperature is anomalous.
        
        Compares the current temperature reading against the historical data.
        If the Z-score exceeds our threshold (default 2.0), we flag it as anomalous.
        This catches sudden spikes or drops that don't fit the normal pattern.
        """
        z = self._z_score(self.temp_hist, self.latest.get("temperature", 0))
        # Return True only if we have valid z-score AND it exceeds threshold
        return z is not None and z > CONFIG["anomaly"]["z_threshold"]

    def is_humi_anomaly(self) -> bool:
        """
        Check if current humidity is anomalous.
        
        Same logic as is_temp_anomaly but for humidity readings.
        Detects unusual humidity patterns compared to historical baseline.
        """
        z = self._z_score(self.humi_hist, self.latest.get("humidity", 0))
        # Return True only if we have valid z-score AND it exceeds threshold
        return z is not None and z > CONFIG["anomaly"]["z_threshold"]


# ── SHARED STATE ──────────────────────────────────────────────────────────────
# Global state shared across threads for all connected devices
_devices: dict[str, DeviceState] = {}  # Maps device_id -> DeviceState object
_devices_lock   = threading.Lock()     # Lock to safely access _devices from multiple threads
_message_queue: queue.Queue = queue.Queue()  # Thread-safe queue for incoming MQTT messages
_shutdown       = threading.Event()


# ── RISK SCORING ──────────────────────────────────────────────────────────────
def score_risk(device: DeviceState) -> dict:
    """
    Calculate risk score for a device based on multiple factors.
    
    This function implements a multi-factor risk scoring system that evaluates device
    health based on temperature, humidity, anomaly detection, and device status.
    
    Risk scoring rules:
    - Critical high or low temperature: +5  (immediate danger)
    - High temperature: +2                  (warning level)
    - Humidity out of bounds: +2            (comfort/safety issue)
    - Device status warning: +2             (device-reported issue)
    - Temperature anomaly: +2                (unusual pattern detected)
    - Humidity anomaly: +1                  (less critical anomaly)
    
    Final score is capped at 10 (max risk).
    
    Args:
        device: DeviceState instance to score
        
    Returns:
        Dictionary with:
        - score: 0-10 risk level
        - mode: "NORMAL" (0-3), "WARNING" (4-6), or "CRITICAL" (7-10)
        - status: Human-readable status ("Normal" or "Anomaly")
    """
    # Shorthand aliases for cleaner code
    t          = CONFIG["thresholds"]
    data       = device.latest
    temp       = data.get("temperature", 0)
    humi       = data.get("humidity",    0)
    dev_status = data.get("status", "OK").upper()  # Normalize to uppercase

    score = 0

    # ────────────────────────────────────────────────────────────────────────
    # STEP 1: Temperature-based scoring
    # We check both critical extremes and high warning level
    # ────────────────────────────────────────────────────────────────────────
    if temp >= t["temp_critical_high"] or temp <= t["temp_low"]:
        # Temperature is dangerously high OR dangerously low
        score += 5
    elif temp >= t["temp_high"]:
        # Temperature is elevated but not critical
        score += 2

    # ────────────────────────────────────────────────────────────────────────
    # STEP 2: Humidity-based scoring
    # Out of optimal range affects comfort and equipment lifespan
    # ────────────────────────────────────────────────────────────────────────
    if humi >= t["humi_high"] or humi <= t["humi_low"]:
        # Humidity is too high (mold risk) OR too low (drying/electrostatic)
        score += 2

    # ────────────────────────────────────────────────────────────────────────
    # STEP 3: Device-reported status
    # The device itself may flag issues
    # ────────────────────────────────────────────────────────────────────────
    if dev_status == "WARNING":
        # Device firmware reported a warning condition
        score += 2

    # ────────────────────────────────────────────────────────────────────────
    # STEP 4: Anomaly detection scoring
    # Flags unusual patterns that don't fit historical trends
    # ────────────────────────────────────────────────────────────────────────
    if device.is_temp_anomaly():
        # Temperature spike/drop detected that doesn't match trend
        score += 2
    if device.is_humi_anomaly():
        # Humidity anomaly detected (less critical than temp)
        score += 1

    # Cap the score at 10 (max risk level)
    score = min(score, 10)

    # ────────────────────────────────────────────────────────────────────────
    # STEP 5: Convert numerical score to operational mode and status
    # ────────────────────────────────────────────────────────────────────────
    if score >= 7:
        # High risk - immediate attention needed
        mode, status = "CRITICAL", "Anomaly"
    elif score >= 4:
        # Moderate risk - monitor and prepare response
        mode, status = "WARNING",  "Anomaly"
    else:
        # All good - normal operation
        mode, status = "NORMAL",   "Normal"

    return {"score": score, "mode": mode, "status": status}


# ── MQTT CALLBACKS ────────────────────────────────────────────────────────────
def on_connect(client, userdata, connect_flags, reason_code, properties):
    """
    MQTT on_connect callback handler.
    
    This function is called by the MQTT client library whenever the connection
    to the broker succeeds or fails. We use it to:
    1. Check if connection was successful
    2. Subscribe to the topics we care about (device telemetry)
    3. Log appropriate messages for debugging
    
    The reason_code parameter tells us what happened:
    - 0 = Success, we're connected!
    - 1-5 = Various failure reasons
    """
    # Map numeric reason codes to human-readable descriptions
    rc_map = {
        0: "OK",
        1: "Bad protocol",
        2: "ID rejected",
        3: "Server unavailable",
        4: "Bad credentials",
        5: "Not authorised"
    }
    if reason_code == 0:
        # ✓ Connection successful - now subscribe to device topics
        log.info(f"✓ MQTT connected → {CONFIG['mqtt']['server']}")
        # Subscribe to the base topic (e.g., "edgeiot/balaa1407/#")
        # The # wildcard means "all subtopics" (telemetry, status, etc)
        client.subscribe(CONFIG["mqtt"]["base_topic"])
        log.info(f"✓ Subscribed: {CONFIG['mqtt']['base_topic']}")
    else:
        # ✗ Connection failed - show user-friendly error message
        reason_text = rc_map.get(reason_code, f"Unknown ({reason_code})")
        log.error(f"✗ MQTT connect failed [{reason_code}]: {reason_text}")


def on_disconnect(client, userdata, disconnect_flags, reason_code, properties):
    """
    MQTT on_disconnect callback handler.
    
    Called whenever the connection to the broker is lost (intentional or crash).
    We log it for debugging, and the paho-mqtt library automatically handles
    reconnection attempts based on our reconnect_delay_set() configuration.
    
    Note: reason_code 0 means WE intentionally disconnected (clean shutdown)
    Non-zero means the broker kicked us off, so we'll auto-reconnect.
    """
    if reason_code != 0:
        # Unexpected disconnect - will auto-reconnect
        log.warning(f"⚠ MQTT disconnected (rc={reason_code}) - will attempt to reconnect automatically")
    else:
        # Clean intentional disconnect (e.g., during shutdown)
        log.info(f"MQTT disconnected cleanly")


def on_message(client, userdata, msg):
    """
    MQTT on_message callback handler.
    
    Called by the paho-mqtt library whenever a message arrives on a subscribed topic.
    We deserialize the JSON payload and queue it for processing.
    
    Why queue the messages?
    - The callback runs in the MQTT client's network thread
    - We don't want to block the network thread with heavy processing
    - Queuing allows us to process messages at our own pace on the main thread
    
    We're defensive about bad data:
    - Catch encoding errors (not UTF-8)
    - Catch JSON parse errors (malformed JSON)
    - Skip invalid messages without crashing
    """
    try:
        # Decode binary payload to UTF-8 string
        raw     = msg.payload.decode("utf-8")
        # Parse JSON string to Python dict
        payload = json.loads(raw)
    except UnicodeDecodeError as e:
        # Payload wasn't valid UTF-8 text
        log.warning(f"Bad payload encoding on {msg.topic}: {e}")
        return
    except json.JSONDecodeError as e:
        # Payload was text but not valid JSON
        log.warning(f"Bad JSON on {msg.topic}: {e}")
        return
    except Exception as e:
        # Some other unexpected error
        log.error(f"Unexpected error parsing message on {msg.topic}: {e}")
        return
    
    # All good - queue this for processing by main thread
    log.debug(f"📨 Message received on {msg.topic}")
    # Put (topic, parsed_json) tuple into the queue
    _message_queue.put((msg.topic, payload))


def build_mqtt_client() -> mqtt.Client:
    """
    Create and configure MQTT client instance.
    
    This factory function creates and configures a fresh MQTT client with all
    our callbacks attached and reconnection settings configured.
    
    Returns:
        Configured mqtt.Client object ready for connection
    """
    cfg    = CONFIG["mqtt"]
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=cfg["client_id"], clean_session=True)
    client.on_connect    = on_connect
    client.on_disconnect = on_disconnect
    client.on_message    = on_message
    client.reconnect_delay_set(
        min_delay=cfg["reconnect_delay_min"],
        max_delay=cfg["reconnect_delay_max"],
    )
    return client


# ── MESSAGE PROCESSOR ─────────────────────────────────────────────────────────
def process_messages() -> None:
    """
    Process all messages in the queue.
    
    This is the main message processor that runs on the main thread.
    It drains the message queue (which is filled by MQTT callbacks) and:
    1. Parses MQTT topic structure to extract device_id and subtopic
    2. Auto-registers new devices (DeviceState instance)
    3. Handles different message types (telemetry vs status)
    4. Updates device state and calculates risk scores
    
    Topic format: edgeiot/{device_id}/{subtopic}
    Example: edgeiot/balaa1407/telemetry
    """
    message_count = 0
    # Drain the queue - process ALL messages that have accumulated
    while not _message_queue.empty():
        try:
            topic, payload = _message_queue.get_nowait()
        except queue.Empty:
            # Queue is now empty
            break

        message_count += 1
        
        # ────────────────────────────────────────────────────────────────────
        # STEP 1: Parse the MQTT topic to get device_id and subtopic
        # Topic format: "edgeiot/balaa1407/telemetry"
        # ────────────────────────────────────────────────────────────────────
        parts     = topic.split("/")
        device_id = parts[1] if len(parts) >= 2 else "unknown"
        subtopic  = parts[2] if len(parts) >= 3 else ""

        # ────────────────────────────────────────────────────────────────────
        # STEP 2: Get or create DeviceState for this device
        # We use a lock to ensure thread-safe access to the _devices dict
        # ────────────────────────────────────────────────────────────────────
        with _devices_lock:
            if device_id not in _devices:
                # First time seeing this device - create state for it
                _devices[device_id] = DeviceState(device_id)
                log.info(f"✓ New device: {device_id}")
            device = _devices[device_id]

        # ────────────────────────────────────────────────────────────────────
        # STEP 3: Handle different message types
        # ────────────────────────────────────────────────────────────────────
        
        # Last Will and Testament (LWT) - device went offline
        if subtopic == "status" and payload.get("status") == "OFFLINE":
            log.warning(f"[{device_id}] OFFLINE (LWT)")
            device.online = False  # Mark device as offline
            continue

        # Telemetry data - actual sensor readings
        if subtopic == "telemetry":
            # Update device with new sensor readings
            device.update(payload)
            # Calculate risk score based on new data
            risk = score_risk(device)
            # Log the received data with emoji for visual scanning
            log.info(
                f"[{device_id}] "
                f"🌡️ {payload.get('temperature')}°C | "
                f"💧 {payload.get('humidity')}% | "
                f"⚠️  risk={risk['score']}/10"
            )
    
    # Log summary if we processed anything
    if message_count > 0:
        log.debug(f"📦 Processed {message_count} message(s) from queue")


# ── AGGREGATE & LOG ───────────────────────────────────────────────────────────
def aggregate_and_log() -> None:
    """
    Aggregate data from all online devices and write to log file.
    
    This function is called periodically (every 0.2s) to:
    1. Collect all online devices that have sent telemetry
    2. Calculate system-wide averages (avg temperature, humidity)
    3. Determine overall system risk (highest risk device determines system risk)
    4. Write a structured JSON record to log.json for the Flask dashboard
    
    The log file format is newline-delimited JSON (one record per line)
    which is easy to parse and stream.
    """
    # Take a snapshot of all online devices with data
    # We use a lock to safely read the _devices dict
    with _devices_lock:
        snapshot = {k: v for k, v in _devices.items() if v.online and v.latest}

    if not snapshot:
        log.warning("⏳ Waiting for device data…")
        return

    # Safely collect all temperature and humidity readings
    all_temps = [d.latest["temperature"] for d in snapshot.values() if "temperature" in d.latest]
    all_humis = [d.latest["humidity"]    for d in snapshot.values() if "humidity"    in d.latest]

    # Calculate averages safely - avoid division by zero
    if all_temps:
        avg_temp = round(sum(all_temps) / len(all_temps), 2)
    else:
        avg_temp = None
        
    if all_humis:
        avg_humi = round(sum(all_humis) / len(all_humis), 2)
    else:
        avg_humi = None

    # Build per-device records
    device_records = {}
    for dev_id, device in snapshot.items():
        risk = score_risk(device)
        device_records[dev_id] = {
            "device_id":   dev_id,
            "temperature": device.latest.get("temperature"),
            "humidity":    device.latest.get("humidity"),
            "status":      risk["status"],
            "mode":        risk["mode"],
            "risk":        risk["score"],
            "uptime":      device.latest.get("uptime"),
            "last_seen":   device.last_seen.isoformat() if device.last_seen else None,
        }

    # Calculate overall system risk
    top_risk   = max((score_risk(d)["score"] for d in snapshot.values()), default=0)
    top_mode   = "CRITICAL" if top_risk >= 7 else ("WARNING" if top_risk >= 4 else "NORMAL")
    top_status = "Anomaly" if top_risk >= 4 else "Normal"

    # Build aggregated record
    record = {
        "timestamp":    datetime.now(timezone.utc).isoformat(),
        "temperature":  avg_temp,
        "humidity":     avg_humi,
        "status":       top_status,
        "mode":         top_mode,
        "risk":         top_risk,
        "device_count": len(snapshot),
        "devices":      device_records,
        "device_id":    "EDGE-AGG",
        "uptime":       int(time.monotonic()),
    }

    write_json_log(record)
    log.info(
        f"[AGG] 🌡️  {avg_temp}°C | 💧 {avg_humi}% | "
        f"⚠️  {top_risk}/10 | {len(snapshot)} device(s)"
    )


# ── ENTRY POINT ───────────────────────────────────────────────────────────────
def run() -> None:
    """
    Main entry point for the Edge IoT MQTT bridge.
    
    This is where the bridge application starts. It:
    1. Initializes the MQTT client
    2. Connects to the MQTT broker (with retry logic)
    3. Sets up signal handlers for graceful shutdown
    4. Runs the main event loop (process messages, aggregate, log)
    5. Cleans up on shutdown (disconnect MQTT, flush logs)
    
    The flow:
    - MQTT network thread runs in background (client.loop_start())
    - Main thread processes messages and aggregates data every 0.2s
    - Ctrl+C or kill signal triggers graceful shutdown
    """
    log.info("🚀 Edge IoT bridge starting…")

    # Create and configure MQTT client
    client = build_mqtt_client()
    cfg    = CONFIG["mqtt"]

    # ────────────────────────────────────────────────────────────────────────
    # STEP 1: Connect to MQTT broker with exponential backoff retry
    # ────────────────────────────────────────────────────────────────────────
    # If broker is temporarily unavailable, we retry with increasing delays
    # Delays: 2s, 4s, 8s, 16s before finally giving up
    max_retries = 5
    for attempt in range(1, max_retries + 1):
        try:
            log.info(f"Connecting to MQTT (attempt {attempt}/{max_retries})…")
            client.connect(cfg["server"], cfg["port"], cfg["keepalive"])
            log.info("✓ MQTT initial connection successful")
            break
        except OSError as e:
            log.warning(f"⚠ Connection attempt {attempt} failed: {e}")
            if attempt < max_retries:
                # Exponential backoff: wait longer each attempt
                # 2^1=2s, 2^2=4s, 2^3=8s, 2^4=16s
                time.sleep(2 ** attempt)
            else:
                log.error(f"✗ Failed to connect after {max_retries} attempts")
                raise

    # Start the MQTT network thread (runs in background)
    # This thread handles all MQTT communication and invokes our callbacks
    client.loop_start()

    # ────────────────────────────────────────────────────────────────────────
    # STEP 2: Register signal handlers for graceful shutdown
    # ────────────────────────────────────────────────────────────────────────
    # When user presses Ctrl+C or process receives kill signal,
    # we set _shutdown event which breaks the main loop
    def _handle_signal(sig, frame):
        """Handle shutdown signals gracefully."""
        sig_name = signal.Signals(sig).name
        log.info(f"🛑 Received {sig_name} signal — shutting down gracefully…")
        # Signal the main loop to exit
        _shutdown.set()

    signal.signal(signal.SIGINT,  _handle_signal)   # Ctrl+C in terminal
    signal.signal(signal.SIGTERM, _handle_signal)   # 'kill' command from OS

    # ────────────────────────────────────────────────────────────────────────
    # STEP 3: Main event loop - runs until shutdown signal received
    # ────────────────────────────────────────────────────────────────────────
    # This loop:
    # 1. Processes all MQTT messages queued since last iteration
    # 2. Aggregates data from all devices and writes to log.json
    # 3. Sleeps for a short interval (0.2s) before repeating
    # 
    # The MQTT network thread runs concurrently in background,
    # continuously receiving messages and queueing them for us.
    # ────────────────────────────────────────────────────────────────────────
    interval = CONFIG["log"]["interval"]
    log.info(f"✓ Loop started — updating every {interval}s\n")

    try:
        # Main loop - run until we receive a shutdown signal (Ctrl+C or kill)
        while not _shutdown.is_set():
            # Process all MQTT messages that arrived since last iteration
            process_messages()
            # Aggregate data and write to log file
            aggregate_and_log()
            # Sleep before next iteration
            time.sleep(interval)
    finally:
        # ────────────────────────────────────────────────────────────────────
        # STEP 4: Graceful shutdown cleanup
        # The finally block ensures cleanup happens even if exception occurs
        # ────────────────────────────────────────────────────────────────────
        log.info("🛑 Stopping MQTT loop…")
        client.loop_stop()      # Stop the background network thread
        client.disconnect()     # Disconnect from broker cleanly
        log.info("Bridge stopped.")


if __name__ == "__main__":
    # ── MAIN ENTRY POINT ──────────────────────────────────────────────────
    # This script is meant to be run directly:
    #   python bridge.py
    # It starts the MQTT bridge server that connects to the broker,
    # receives sensor data, performs anomaly detection, and logs results.
    # ──────────────────────────────────────────────────────────────────────
    run()
