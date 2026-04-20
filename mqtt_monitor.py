#!/usr/bin/env python3
"""
Quick MQTT broker monitor - shows all messages on edgeiot/#
"""
import paho.mqtt.client as mqtt
import json

def on_connect(client, userdata, connect_flags, reason_code, properties):
    if reason_code == 0:
        print("✓ Connected to broker")
        client.subscribe("edgeiot/#")
        print("Listening on edgeiot/#...\n")
    else:
        print(f"✗ Connection failed: {reason_code}")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        print(f"Topic: {msg.topic}")
        print(f"  → {json.dumps(payload, indent=2)}\n")
    except:
        print(f"Topic: {msg.topic}")
        print(f"  → {msg.payload.decode()}\n")

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="mqtt-monitor")
client.on_connect = on_connect
client.on_message = on_message

print("Connecting to test.mosquitto.org...")
client.connect("test.mosquitto.org", 1883, 60)
client.loop_forever()
