#! Test if Wokwi messages are hitting the broker
import paho.mqtt.client as mqtt
import json

messages_received = 0

def on_message(client, userdata, msg):
    global messages_received
    messages_received += 1
    try:
        data = json.loads(msg.payload)
        print(f"[{messages_received}] {msg.topic}: {data['temperature']}°C | {data['humidity']}%")
    except:
        print(f"[{messages_received}] {msg.topic}: {msg.payload}")

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="test-monitor")
client.on_message = on_message
client.connect("test.mosquitto.org")
client.subscribe("edgeiot/wokwi-dht22/telemetry")

print("Listening for Wokwi messages for 20 seconds...")
print("=" * 60)

import time
client.loop_start()
time.sleep(20)
client.loop_stop()

print("=" * 60)
print(f"Total messages received: {messages_received}")
if messages_received > 5:
    print("✅ Wokwi IS publishing continuously")
else:
    print(f"⚠️  Only {messages_received} messages (Wokwi might have stopped)")
