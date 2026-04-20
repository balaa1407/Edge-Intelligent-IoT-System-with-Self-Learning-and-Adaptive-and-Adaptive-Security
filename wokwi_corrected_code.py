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
client = MQTTClient(MQTT_CLIENT_ID, MQTT_BROKER, user=MQTT_USER, password=MQTT_PASSWORD)
client.connect()

print("Connected!")

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
  client.publish(topic, message)
  
  uptime_seconds += 1
  time.sleep(1)
