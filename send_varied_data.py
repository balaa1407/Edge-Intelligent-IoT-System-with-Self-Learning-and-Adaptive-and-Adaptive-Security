"""
Direct publisher - Send varied readings to the bridge
Shows what Wokwi will send
"""

import paho.mqtt.client as mqtt
import json
import time
import random

broker = "test.mosquitto.org"
port = 1883
device_id = "wokwi-dht22"
base_topic = "edgeiot"

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="test-publisher-varied", clean_session=True)

def on_connect(client, userdata, connect_flags, reason_code, properties):
    if reason_code == 0:
        print(f"✓ Connected to {broker}:{port}\n")
    else:
        print(f"✗ Connection failed: {reason_code}")

client.on_connect = on_connect

try:
    print(f"Connecting to {broker}:{port}...")
    client.connect(broker, port, 60)
    client.loop_start()
    time.sleep(1)
    
    uptime_seconds = 0
    base_temp = 24.0
    base_humi = 40.0
    
    def get_temperature():
        cycle = (uptime_seconds % 20) * 0.3
        variation = random.uniform(-1.5, 1.5)
        spike = 0
        if uptime_seconds % 15 == 0:
            spike = random.choice([0, 0, 0, 10, 15, 18])
        temp = base_temp + cycle + variation + spike
        return round(max(15.0, min(50.0, temp)), 2)
    
    def get_humidity():
        cycle = ((uptime_seconds + 5) % 25) * 0.4
        variation = random.uniform(-3.0, 3.0)
        spike = 0
        if uptime_seconds % 18 == 0:
            spike = random.choice([0, 0, 0, 15, 25])
        humi = base_humi + cycle + variation + spike
        return round(max(10.0, min(95.0, humi)), 2)
    
    print(f"{'#':<4} {'Time':<8} {'Temp °C':<10} {'Humidity %':<12} Status")
    print("-" * 50)
    
    for i in range(40):
        temp = get_temperature()
        humi = get_humidity()
        
        payload = {
            "device_id": device_id,
            "temperature": temp,
            "humidity": humi,
            "status": "OK",
            "uptime": uptime_seconds,
            "timestamp": int(time.time())
        }
        
        topic = f"{base_topic}/{device_id}/telemetry"
        msg = json.dumps(payload)
        
        result = client.publish(topic, msg, qos=1)
        status = "✓" if result.rc == 0 else "✗"
        
        print(f"{i+1:<4} {uptime_seconds:<8} {temp:<10.1f} {humi:<12.1f} {status}")
        
        uptime_seconds += 1
        time.sleep(1)
    
    client.loop_stop()
    client.disconnect()
    print("\n✓ Sending complete! Check bridge output for anomaly detection.")
    
except Exception as e:
    print(f"Error: {e}")
