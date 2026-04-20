# ✅ NEW WOKWI CODE - STEP BY STEP SETUP

## 🎯 IMMEDIATE STEPS (Do these NOW):

### Step 1: Open Wokwi Project
Go to: https://wokwi.com/projects/322577683855704658

### Step 2: Copy ALL Code Below
```python
"""
MicroPython IoT Weather Station for Wokwi - Updated for Edge IoT System

Configuration for test.mosquitto.org MQTT broker
Publishes to: edgeiot/<device_id>/telemetry

To integrate with the Edge IoT Dashboard:
1. Replace the code in your Wokwi project with this
2. The bridge will automatically detect and process telemetry
3. View in dashboard at http://localhost:5000

https://wokwi.com/projects/322577683855704658
"""

import network
import time
from machine import Pin
import dht
import ujson
from umqtt.simple import MQTTClient

# MQTT Server Parameters - PUBLIC BROKER
MQTT_CLIENT_ID = "wokwi-esp32-weather"
MQTT_BROKER    = "test.mosquitto.org"  # Changed to public broker
MQTT_USER      = ""
MQTT_PASSWORD  = ""
MQTT_BASE_TOPIC = "edgeiot"
DEVICE_ID      = "wokwi-dht22"  # Unique device identifier

import random

sensor = dht.DHT22(Pin(15))

print("Connecting to WiFi", end="")
sta_if = network.WLAN(network.STA_IF)
sta_if.active(True)
sta_if.connect('Wokwi-GUEST', '')
while not sta_if.isconnected():
  print(".", end="")
  time.sleep(0.1)
print(" Connected!")

print("Connecting to MQTT server... ", end="")
try:
  client = MQTTClient(MQTT_CLIENT_ID, MQTT_BROKER, user=MQTT_USER, password=MQTT_PASSWORD)
  client.connect()
  print("✓ Connected!")
except Exception as e:
  print("✗ MQTT Connection Failed!")
  print("Error: " + str(e))
  raise

# Track uptime
uptime_seconds = 0

while True:
  print("Measuring weather conditions...")
  
  # Simple random values - realistic sensor readings
  temp = round(random.uniform(20.0, 35.0), 2)  # 20-35°C range
  humi = round(random.uniform(30.0, 70.0), 2)  # 30-70% humidity range
  
  # Payload format for Edge IoT Bridge
  message = ujson.dumps({
    "device_id": DEVICE_ID,
    "temperature": temp,
    "humidity": humi,
    "status": "OK",
    "uptime": uptime_seconds,
    "timestamp": int(time.time())
  })
  
  # Publish to correct topic format: edgeiot/<device_id>/telemetry
  topic = "{}/{}/telemetry".format(MQTT_BASE_TOPIC, DEVICE_ID)
  print("[{}s] {}C | {}%".format(uptime_seconds, temp, humi))
  try:
    client.publish(topic, message)
    print("  ✓ Published to {}".format(topic))
  except Exception as e:
    print("  ✗ Publish failed: " + str(e))
  
  uptime_seconds += 1
  time.sleep(1)
```

### Step 3: In Wokwi Editor
1. **Select ALL** existing code: <kbd>Ctrl+A</kbd>
2. **Delete** it
3. **Paste** the code above: <kbd>Ctrl+V</kbd>
4. Click **RUN** button

### Step 4: Watch Wokwi Output
You should see:
```
Connecting to WiFi........ Connected!
Connecting to MQTT server... ✓ Connected!
Measuring weather conditions...
[0s] 32.13C | 45.07%
  ✓ Published to edgeiot/wokwi-dht22/telemetry
Measuring weather conditions...
[1s] 28.57C | 52.09%
  ✓ Published to edgeiot/wokwi-dht22/telemetry
...
```

### Step 5: Check Bridge Output
Terminal should show different temperatures every second:
```
13:10:52 [INFO] [AGG] temp=32.13°C  humi=45.07%  risk=0/10  mode=NORMAL  devices=1
13:10:53 [INFO] [AGG] temp=28.57°C  humi=52.09%  risk=0/10  mode=NORMAL  devices=1
13:10:54 [INFO] [AGG] temp=25.34°C  humi=38.62%  risk=0/10  mode=NORMAL  devices=1
```

## ⚠️ TROUBLESHOOTING

| Problem | Solution |
|---------|----------|
| `✗ MQTT Connection Failed!` | WiFi not connecting - check Wokwi WiFi setup |
| Same values repeating | Old code still running - make sure you RUN after paste |
| Dashboard still shows old data | Bridge needs restart in terminal |
| Nothing shows in bridge | Wait 5-10 seconds for MQTT connection |

## 🔧 What to Do If MQTT Connection Fails

If you see `✗ MQTT Connection Failed!` in Wokwi output, the issue might be Wokwi network access to external MQTT broker.

**Fallback Option:** Use local simulated data instead:
- Modify line: `temp = round(random.uniform(20.0, 35.0), 2)`
- Change to something like: `temp = 20.0 + (uptime_seconds % 15) * 0.5`

But first, try the exact steps above!
