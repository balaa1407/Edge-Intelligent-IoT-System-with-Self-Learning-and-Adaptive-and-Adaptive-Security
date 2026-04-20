"""
Test publisher — simulates ESP32 publishing telemetry to public MQTT broker
"""

import paho.mqtt.client as mqtt
import json
import time
from datetime import datetime, timezone

# Use public test broker (test.mosquitto.org) for consistency
broker = "test.mosquitto.org"
port = 1883

device_id = "wokwi-device1"
base_topic = "edgeiot"

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="test-publisher", clean_session=True)

def on_connect(client, userdata, connect_flags, reason_code, properties):
    if reason_code == 0:
        print(f"✓ Connected to broker at {broker}:{port}")
    else:
        print(f"✗ Connection failed with code {reason_code}")

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
    print("\n⚠ Failed to connect to test.mosquitto.org")
    print("Make sure you have internet connection and the public MQTT broker is accessible.")
