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
from datetime import datetime, timezone
from collections import deque
import paho.mqtt.client as mqtt

# ── CONFIG ────────────────────────────────────────────────────────────────────
CONFIG = {
    "mqtt": {
        "server":      "test.mosquitto.org",  # PUBLIC broker
        "port":        1883,
        "client_id":   "edge-bridge-01",
        "base_topic":  "edgeiot/#",
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
        "temp_critical_high": 45.0,
        "temp_high":          35.0,
        "temp_low":           10.0,
        "humi_high":          80.0,
        "humi_low":           20.0,
    },
    "log": {
        "file":         "log.json",
        "max_bytes":    1_000_000,   # 1 MB
        "backup_count": 3,
        "interval":     1,           # seconds between log writes
    },
}
# ── END CONFIG ────────────────────────────────────────────────────────────────

# ── LOGGING SETUP ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG to see all messages
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("edge-bridge")

# Plain newline-delimited JSON log for Flask (no logging wrapper)
_log_lock = threading.Lock()


def write_json_log(record: dict) -> None:
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
    import os, shutil
    for i in range(backups - 1, 0, -1):
        src = f"{path}.{i}"
        dst = f"{path}.{i+1}"
        if os.path.exists(src):
            shutil.move(src, dst)
    if os.path.exists(path):
        shutil.move(path, f"{path}.1")


import os  # needed for write_json_log

# ── DEVICE STATE ──────────────────────────────────────────────────────────────
class DeviceState:
    """Holds rolling history and last telemetry for a single device."""

    def __init__(self, device_id: str):
        self.device_id = device_id
        self.temp_hist = deque(maxlen=CONFIG["anomaly"]["max_history"])
        self.humi_hist = deque(maxlen=CONFIG["anomaly"]["max_history"])
        self.last_seen = None
        self.online    = True
        self.latest    = {}

    def update(self, payload: dict) -> None:
        self.latest    = payload
        self.last_seen = datetime.now(timezone.utc)
        self.online    = True
        if "temperature" in payload:
            self.temp_hist.append(float(payload["temperature"]))
        if "humidity" in payload:
            self.humi_hist.append(float(payload["humidity"]))

    # ── Z-score helpers ──────────────────────────────────────────────────────
    @staticmethod
    def _z_score(history: deque, value: float) -> float | None:
        if len(history) < CONFIG["anomaly"]["min_history"]:
            return None
        mean     = sum(history) / len(history)
        variance = sum((x - mean) ** 2 for x in history) / len(history)
        std      = variance ** 0.5
        if std < 0.001:
            return 0.0
        return abs((value - mean) / std)

    def is_temp_anomaly(self) -> bool:
        z = self._z_score(self.temp_hist, self.latest.get("temperature", 0))
        return z is not None and z > CONFIG["anomaly"]["z_threshold"]

    def is_humi_anomaly(self) -> bool:
        z = self._z_score(self.humi_hist, self.latest.get("humidity", 0))
        return z is not None and z > CONFIG["anomaly"]["z_threshold"]


# ── SHARED STATE ──────────────────────────────────────────────────────────────
_devices: dict[str, DeviceState] = {}
_devices_lock   = threading.Lock()
_message_queue: queue.Queue = queue.Queue()
_shutdown       = threading.Event()


# ── RISK SCORING ──────────────────────────────────────────────────────────────
def score_risk(device: DeviceState) -> dict:
    t          = CONFIG["thresholds"]
    data       = device.latest
    temp       = data.get("temperature", 0)
    humi       = data.get("humidity",    0)
    dev_status = data.get("status", "OK").upper()

    score = 0

    if temp >= t["temp_critical_high"] or temp <= t["temp_low"]:
        score += 5
    elif temp >= t["temp_high"]:
        score += 2

    if humi >= t["humi_high"] or humi <= t["humi_low"]:
        score += 2

    if dev_status == "WARNING":
        score += 2

    if device.is_temp_anomaly():
        score += 2
    if device.is_humi_anomaly():
        score += 1

    score = min(score, 10)

    if score >= 7:
        mode, status = "CRITICAL", "Anomaly"
    elif score >= 4:
        mode, status = "WARNING",  "Anomaly"
    else:
        mode, status = "NORMAL",   "Normal"

    return {"score": score, "mode": mode, "status": status}


# ── MQTT CALLBACKS ────────────────────────────────────────────────────────────
def on_connect(client, userdata, connect_flags, reason_code, properties):
    rc_map = {0:"OK",1:"Bad protocol",2:"ID rejected",3:"Server unavailable",
              4:"Bad credentials",5:"Not authorised"}
    if reason_code == 0:
        log.info(f"✓ MQTT connected → {CONFIG['mqtt']['server']}")
        client.subscribe(CONFIG["mqtt"]["base_topic"])
        log.info(f"✓ Subscribed: {CONFIG['mqtt']['base_topic']}")
    else:
        log.error(f"✗ MQTT connect failed [{reason_code}]: {rc_map.get(reason_code, reason_code)}")


def on_disconnect(client, userdata, disconnect_flags, reason_code, properties):
    if reason_code != 0:
        log.warning(f"⚠ MQTT disconnected (rc={reason_code}) - will attempt to reconnect automatically")
    else:
        log.info(f"MQTT disconnected cleanly")


def on_message(client, userdata, msg):
    try:
        raw     = msg.payload.decode("utf-8")
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        log.warning(f"Bad payload on {msg.topic}: {e}")
        return
    
    # Debug: Log every message received
    log.debug(f"📨 Message received on {msg.topic}")
    _message_queue.put((msg.topic, payload))


def build_mqtt_client() -> mqtt.Client:
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
    message_count = 0
    while not _message_queue.empty():
        try:
            topic, payload = _message_queue.get_nowait()
        except queue.Empty:
            break

        message_count += 1
        parts     = topic.split("/")
        device_id = parts[1] if len(parts) >= 2 else "unknown"
        subtopic  = parts[2] if len(parts) >= 3 else ""

        with _devices_lock:
            if device_id not in _devices:
                _devices[device_id] = DeviceState(device_id)
                log.info(f"✓ New device: {device_id}")
            device = _devices[device_id]

        if subtopic == "status" and payload.get("status") == "OFFLINE":
            log.warning(f"[{device_id}] OFFLINE (LWT)")
            device.online = False
            continue

        if subtopic == "telemetry":
            device.update(payload)
            risk = score_risk(device)
            log.info(
                f"[{device_id}] "
                f"🌡️ {payload.get('temperature')}°C | "
                f"💧 {payload.get('humidity')}% | "
                f"⚠️  risk={risk['score']}/10"
            )
    
    if message_count > 0:
        log.debug(f"📦 Processed {message_count} message(s) from queue")


# ── AGGREGATE & LOG ───────────────────────────────────────────────────────────
def aggregate_and_log() -> None:
    with _devices_lock:
        snapshot = {k: v for k, v in _devices.items() if v.online and v.latest}

    if not snapshot:
        log.warning("⏳ Waiting for device data…")
        return

    all_temps = [d.latest["temperature"] for d in snapshot.values() if "temperature" in d.latest]
    all_humis = [d.latest["humidity"]    for d in snapshot.values() if "humidity"    in d.latest]

    avg_temp = round(sum(all_temps) / len(all_temps), 2) if all_temps else None
    avg_humi = round(sum(all_humis) / len(all_humis), 2) if all_humis else None

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

    top_risk   = max((score_risk(d)["score"] for d in snapshot.values()), default=0)
    top_mode   = "CRITICAL" if top_risk >= 7 else ("WARNING" if top_risk >= 4 else "NORMAL")
    top_status = "Anomaly" if top_risk >= 4 else "Normal"

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
    log.info("🚀 Edge IoT bridge starting…")

    client = build_mqtt_client()
    cfg    = CONFIG["mqtt"]

    # Try initial connection with retries
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
                time.sleep(2 ** attempt)  # exponential backoff: 2s, 4s, 8s, 16s
            else:
                log.error(f"✗ Failed to connect after {max_retries} attempts")
                raise

    client.loop_start()

    def _handle_signal(sig, frame):
        log.info("🛑 Shutdown signal received…")
        _shutdown.set()

    signal.signal(signal.SIGINT,  _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    interval = CONFIG["log"]["interval"]
    log.info(f"✓ Loop started — updating every {interval}s\n")

    try:
        while not _shutdown.is_set():
            process_messages()
            aggregate_and_log()
            time.sleep(interval)
    finally:
        log.info("🛑 Stopping MQTT loop…")
        client.loop_stop()
        client.disconnect()
        log.info("Bridge stopped.")


if __name__ == "__main__":
    run()
