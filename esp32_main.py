"""
Edge IoT — ESP32 MQTT Publisher
MicroPython | umqtt.simple

Simulates two sensors (device1, device2) and publishes JSON telemetry
to the MQTT broker every 3 seconds.

In production: swap read_temperature() / read_humidity() for real
DHT22 / BME280 driver calls.

Topics published:
  edgeiot/<device_id>/telemetry  — JSON sensor payload
  edgeiot/<device_id>/status     — LWT "OFFLINE" on unexpected drop
"""

import network
import time
import json
import random
import machine
from umqtt.simple import MQTTClient

# ── CONFIG ────────────────────────────────────────────────────────────────────
CONFIG = {
    "wifi": {
        "ssid":     "Wokwi-GUEST",
        "password": "",
        "timeout":  20,
    },
    "mqtt": {
        "server":      "test.mosquitto.org",
        "port":        1883,
        "client_id":   "esp32-edge-01",
        "keepalive":   60,
        "base_topic":  "edgeiot",
        "qos":         0,
    },
    "devices": [
        {"id": "device1", "name": "Sensor A"},
        {"id": "device2", "name": "Sensor B"},
    ],
    "thresholds": {
        "temp_high": 40.0,
        "temp_low":  10.0,
        "humi_high": 80.0,
        "humi_low":  20.0,
    },
    "publish_interval": 3,
    "max_retries":       5,
    "backoff_base":      2,
}
# ── END CONFIG ────────────────────────────────────────────────────────────────

_start_ms = time.ticks_ms()


def uptime_s() -> float:
    return time.ticks_diff(time.ticks_ms(), _start_ms) / 1000.0


def log(level: str, msg: str) -> None:
    """
    Log a message with timestamp and level.
    
    Args:
        level: Log level (INFO, WARN, ERROR, DATA, etc.)
        msg: Message to log
    """
    print(f"[{uptime_s():8.1f}s] [{level:5}] {msg}")


# ── SENSOR SIMULATION ─────────────────────────────────────────────────────────
# Replace these functions with real sensor reads in production:
#
#   import dht
#   _sensor = dht.DHT22(machine.Pin(4))
#
#   def read_temperature(device_id):
#       _sensor.measure()
#       return round(_sensor.temperature(), 2)
#
#   def read_humidity(device_id):
#       _sensor.measure()
#       return round(_sensor.humidity(), 2)

def read_temperature(device_id: str) -> float:
    """
    Read temperature for a device.
    
    Currently simulates readings with occasional anomalies.
    Args:
        device_id: Device identifier string
        
    Returns:
        Temperature in Celsius (float)
    """
    base  = {"device1": 25.0, "device2": 27.0}.get(device_id, 25.0)
    spike = random.choice([0, 0, 0, 0, 18, -17])   # occasional anomaly
    noise = random.uniform(-0.5, 0.5)
    return round(base + spike + noise, 2)


def read_humidity(device_id: str) -> float:
    """
    Read humidity for a device.
    
    Currently simulates readings with noise.
    Args:
        device_id: Device identifier string
        
    Returns:
        Humidity as percentage (0-100)
    """
    base  = {"device1": 55.0, "device2": 60.0}.get(device_id, 55.0)
    noise = random.uniform(-2.0, 2.0)
    return round(max(0.0, min(100.0, base + noise)), 2)


def classify(temp: float, humi: float) -> str:
    """
    Classify sensor readings as WARNING or OK.
    
    Args:
        temp: Temperature in Celsius
        humi: Humidity as percentage
        
    Returns:
        "WARNING" if out of bounds, "OK" otherwise
    """
    t = CONFIG["thresholds"]
    if temp >= t["temp_high"] or temp <= t["temp_low"]:
        return "WARNING"
    if humi >= t["humi_high"] or humi <= t["humi_low"]:
        return "WARNING"
    return "OK"



# ── WIFI ──────────────────────────────────────────────────────────────────────
def connect_wifi() -> bool:
    """
    Connect ESP32 to WiFi network.
    
    Returns:
        True if successfully connected, False on timeout
    """
    cfg  = CONFIG["wifi"]
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if wlan.isconnected():
        return True

    log("INFO", f"Connecting to WiFi '{cfg['ssid']}'…")
    wlan.connect(cfg["ssid"], cfg["password"])

    deadline = time.time() + cfg["timeout"]
    while not wlan.isconnected():
        if time.time() > deadline:
            log("ERROR", "WiFi timeout")
            return False
        time.sleep(0.5)

    log("INFO", f"WiFi OK — IP: {wlan.ifconfig()[0]}")
    return True


def ensure_wifi() -> bool:
    """
    Ensure WiFi connection is active, reconnect if needed.
    
    Returns:
        True if connected, False if connection failed
    """
    if network.WLAN(network.STA_IF).isconnected():
        return True
    log("WARN", "WiFi lost — reconnecting…")
    return connect_wifi()


# ── MQTT ──────────────────────────────────────────────────────────────────────
_mqtt_client = None


def _lwt_topic(device_id: str) -> bytes:
    """
    Construct Last Will Testament topic for a device.
    
    Args:
        device_id: Device identifier
        
    Returns:
        Topic path as bytes
    """
    return f"{CONFIG['mqtt']['base_topic']}/{device_id}/status".encode()


def connect_mqtt() -> bool:
    """
    Connect ESP32 MQTT client to broker.
    
    Returns:
        True if successfully connected, False otherwise
    """
    global _mqtt_client
    cfg = CONFIG["mqtt"]

    lwt_dev     = CONFIG["devices"][0]["id"]
    lwt_payload = json.dumps({"status": "OFFLINE", "device_id": lwt_dev})

    try:
        c = MQTTClient(
            client_id = cfg["client_id"],
            server    = cfg["server"],
            port      = cfg["port"],
            keepalive = cfg["keepalive"],
        )
        c.set_last_will(_lwt_topic(lwt_dev), lwt_payload.encode(), retain=True, qos=0)
        c.connect()
        _mqtt_client = c
        log("INFO", f"MQTT OK → {cfg['server']}:{cfg['port']}")
        return True
    except Exception as exc:
        log("ERROR", f"MQTT connect failed: {exc}")
        _mqtt_client = None
        return False


def ensure_mqtt() -> bool:
    if _mqtt_client is not None:
        return True
    log("WARN", "MQTT gone — reconnecting…")
    return connect_mqtt()


def publish_payload(topic: str, payload: dict) -> bool:
    global _mqtt_client
    if _mqtt_client is None:
        return False
    try:
        _mqtt_client.publish(
            topic.encode(),
            json.dumps(payload).encode(),
            qos=CONFIG["mqtt"]["qos"],
        )
        return True
    except Exception as exc:
        log("ERROR", f"Publish failed ({topic}): {exc}")
        _mqtt_client = None
        return False


# ── TELEMETRY ─────────────────────────────────────────────────────────────────
def publish_telemetry() -> int:
    """Publish all devices. Returns number of failures."""
    base     = CONFIG["mqtt"]["base_topic"]
    failures = 0

    for device in CONFIG["devices"]:
        dev_id = device["id"]
        temp   = read_temperature(dev_id)
        humi   = read_humidity(dev_id)
        status = classify(temp, humi)

        payload = {
            "device_id":   dev_id,
            "temperature": temp,
            "humidity":    humi,
            "status":      status,
            "uptime":      round(uptime_s()),
            "timestamp":   time.time(),
        }

        topic = f"{base}/{dev_id}/telemetry"
        ok    = publish_payload(topic, payload)

        if ok:
            tag = "⚠ WARN" if status == "WARNING" else "OK   "
            log("DATA", f"{dev_id} | {temp:5.1f}°C | {humi:4.1f}% RH | {tag}")
        else:
            log("WARN", f"Publish failed: {dev_id}")
            failures += 1

    return failures


# ── MAIN ──────────────────────────────────────────────────────────────────────
def run() -> None:
    log("INFO", "Edge IoT ESP32 publisher starting…")
    delay = CONFIG["backoff_base"]

    # Initial connection with backoff
    for attempt in range(1, CONFIG["max_retries"] + 1):
        if connect_wifi() and connect_mqtt():
            break
        log("WARN", f"Attempt {attempt}/{CONFIG['max_retries']} failed — retry in {delay}s")
        time.sleep(delay)
        delay = min(delay * 2, 60)
    else:
        log("ERROR", "Max retries reached — resetting")
        machine.reset()

    log("INFO", "Publish loop started")
    consecutive_fails = 0

    while True:
        try:
            if not ensure_wifi() or not ensure_mqtt():
                time.sleep(CONFIG["backoff_base"])
                continue

            fails = publish_telemetry()
            if fails:
                consecutive_fails += fails
                if consecutive_fails >= 10:
                    log("ERROR", "Too many failures — resetting")
                    machine.reset()
            else:
                consecutive_fails = 0

            time.sleep(CONFIG["publish_interval"])

        except KeyboardInterrupt:
            log("INFO", "Stopped by user")
            if _mqtt_client:
                try:
                    _mqtt_client.disconnect()
                except Exception:
                    pass
            break
        except Exception as exc:
            log("ERROR", f"Unexpected: {exc}")
            time.sleep(CONFIG["backoff_base"])


run()
