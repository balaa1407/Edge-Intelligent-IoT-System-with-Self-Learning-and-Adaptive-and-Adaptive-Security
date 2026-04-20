"""
Test publisher — simulates ESP32 publishing telemetry to local MQTT broker
"""

import paho.mqtt.client as mqtt
import json
import time
from datetime import datetime, timezone

# Try to publish to broker (if available locally)
broker = "127.0.0.1"  # Local broker instead of test.mosquitto.org
port = 1883

device_id = "wokwi-device1"
base_topic = "edgeiot"

client = mqtt.Client(client_id="test-publisher", clean_session=True)

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"✓ Connected to broker at {broker}:{port}")
    else:
        print(f"✗ Connection failed with code {rc}")

client.on_connect = on_connect

try:
    print(f"Connecting to {broker}:{port}...")
    client.connect(broker, port, 60)
    client.loop_start()
    
    # Wait for connection
    time.sleep(1)
    
    # Publish sample telemetry
    for i in range(10):
        payload = {
            "device_id": device_id,
            "temperature": 22.5 + (i * 0.5),  # Incrementing temp
            "humidity": 50.0 + (i * 1.5),      # Incrementing humidity
            "status": "OK",
            "uptime": int(time.time()),
            "timestamp": int(time.time())
        }
        
        topic = f"{base_topic}/{device_id}/telemetry"
        msg = json.dumps(payload)
        
        result = client.publish(topic, msg, qos=1)
        status = "✓" if result.rc == 0 else "✗"
        print(f"{status} Published: {topic}")
        print(f"   Temp: {payload['temperature']}°C, Humidity: {payload['humidity']}%")
        
        time.sleep(2)
    
    client.loop_stop()
    client.disconnect()
    print("Done!")
    
except Exception as e:
    print(f"Error: {e}")
    print("\n⚠ No local MQTT broker found.")
    print("To use this test, start a local broker first:")
    print("  docker run -d -p 1883:1883 eclipse-mosquitto")
    print("  OR install: apt-get install mosquitto")
