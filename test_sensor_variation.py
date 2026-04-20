"""
Local test - Show realistic sensor variation before deploying to Wokwi
Run this to see what real data will look like
"""

import random
import time

uptime_seconds = 0
base_temp = 24.0
base_humi = 40.0
counter = 0

def get_temperature():
  # Time-based variation + random component + cycle pattern
  cycle = (uptime_seconds % 20) * 0.3  # cycles 0-6°C every 20 seconds
  variation = random.uniform(-1.5, 1.5)  # ±1.5°C random
  spike = 0
  if uptime_seconds % 15 == 0:  # spike every 15 seconds
    spike = random.choice([0, 0, 0, 10, 15, 18])
  
  temp = base_temp + cycle + variation + spike
  return round(max(15.0, min(50.0, temp)), 2)

def get_humidity():
  # Different cycle from temp
  cycle = ((uptime_seconds + 5) % 25) * 0.4  # offset cycle
  variation = random.uniform(-3.0, 3.0)  # ±3% random
  spike = 0
  if uptime_seconds % 18 == 0:  # spike at different interval
    spike = random.choice([0, 0, 0, 15, 25])
  
  humi = base_humi + cycle + variation + spike
  return round(max(10.0, min(95.0, humi)), 2)

print("\n" + "="*60)
print("REALISTIC SENSOR SIMULATION - Real-time readings")
print("="*60)
print(f"{'Time':<8} {'Temp °C':<10} {'Humidity %':<12}")
print("-"*60)

for i in range(30):  # Show 30 seconds of data
  temp = get_temperature()
  humi = get_humidity()
  print(f"{uptime_seconds:<8} {temp:<10.1f} {humi:<12.1f}")
  uptime_seconds += 1
  time.sleep(0.5)  # Demo at 0.5s per reading

print("-"*60)
print("✓ System will detect anomalies in the spikes!")
print("="*60 + "\n")
