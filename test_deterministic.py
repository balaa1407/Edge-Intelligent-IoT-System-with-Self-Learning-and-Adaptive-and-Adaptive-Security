"""
Test simple random values for Wokwi
"""

import random

uptime_seconds = 0

print("\n" + "="*70)
print("RANDOM SENSOR VALUES - Each reading is different")
print("="*70)
print(f"{'#':<4} {'Time':<6} {'Temp °C':<10} {'Humidity %':<12}")
print("-"*70)

for i in range(30):
    temp = round(random.uniform(20.0, 35.0), 2)  # 20-35°C range
    humi = round(random.uniform(30.0, 70.0), 2)  # 30-70% humidity range
    
    print(f"{i+1:<4} {uptime_seconds:<6} {temp:<10.1f} {humi:<12.1f}")
    uptime_seconds += 1

print("-"*70)
print("✓ Different random values every second!")
print("✓ Temperature: 20-35°C (realistic)")  
print("✓ Humidity: 30-70% (realistic)")
print("="*70 + "\n")
