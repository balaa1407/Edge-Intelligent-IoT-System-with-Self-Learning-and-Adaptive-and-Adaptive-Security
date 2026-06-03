# Integration Testing Guide

Complete guide to testing the Edge IoT system with integrated components.

## Test Scenarios

### Scenario 1: Basic System Startup

```bash
# Terminal 1: Start bridge
python bridge.py
# Expected output:
# Connecting to MQTT broker...
# Connected to test.mosquitto.org
# Waiting for messages...

# Terminal 2: Start app
python app.py
# Expected output:
# * Serving Flask app
# * Running on http://127.0.0.1:5000

# Terminal 3: Test endpoints
curl http://localhost:5000/health
# Expected response:
# {"status": "ok", "timestamp": "...", "service": "..."}
```

### Scenario 2: End-to-End Data Flow

```bash
# Start system (terminals 1-2 above)

# Terminal 3: Publish test data
python cli.py publish device-001 --count 5 --interval 0.5

# Expected in bridge terminal:
# Received message: sensors/device-001/telemetry
# Temperature: 22.0°C, Humidity: 45.0%
# Processing...
# Writing to log

# Check dashboard: http://localhost:5000
# Should see chart data updating
```

### Scenario 3: Anomaly Detection

```bash
# Start system

# Terminal 3: Publish normal data
python cli.py publish device-002 --count 20

# Expected: All normal readings

# Terminal 3: Inject anomaly
mosquitto_pub -h test.mosquitto.org -t "sensors/device-002/telemetry" \
  -m '{"temperature": 99.9, "humidity": 5.0, "status": "OK"}'

# Expected in bridge:
# ANOMALY: device-002 temperature 99.9°C
# Risk score: 7 (CRITICAL)

# Dashboard should show alert
```

### Scenario 4: Multiple Devices

```bash
# Start system

# Terminal 3: Publish from 3 devices
python cli.py publish device-001 &
python cli.py publish device-002 &
python cli.py publish device-003 &

# Expected in log:
# - 3 devices active
# - System average temperature
# - System average humidity
```

### Scenario 5: Offline Device Detection

```bash
# Start system

# Terminal 3: Publish one message
mosquitto_pub -h test.mosquitto.org -t "sensors/device-001/telemetry" \
  -m '{"temperature": 25.0, "humidity": 50.0}'

# Wait 5 minutes (or adjust DEVICE_TIMEOUT in config)

# Expected in bridge:
# Device offline: device-001
# Setting status to OFFLINE
# Risk increases to 5

# Dashboard shows device as offline
```

## Automated Test Scripts

### test_mqtt_connection.py

```python
#!/usr/bin/env python3
"""Test MQTT connectivity."""

import paho.mqtt.client as mqtt
import time

def test_mqtt():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="test")
    
    try:
        client.connect("test.mosquitto.org", 1883, keepalive=5)
        client.loop_start()
        time.sleep(2)
        client.loop_stop()
        print("✓ MQTT connection test PASSED")
        return True
    except Exception as e:
        print(f"✗ MQTT connection test FAILED: {e}")
        return False

if __name__ == '__main__':
    exit(0 if test_mqtt() else 1)
```

### test_flask_api.py

```python
#!/usr/bin/env python3
"""Test Flask API endpoints."""

import requests
import json
import time

BASE_URL = "http://localhost:5000"

def test_health():
    """Test /health endpoint."""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'ok'
        print("✓ /health endpoint test PASSED")
        return True
    except Exception as e:
        print(f"✗ /health endpoint test FAILED: {e}")
        return False

def test_data():
    """Test /data endpoint."""
    try:
        response = requests.get(f"{BASE_URL}/data", timeout=5)
        assert response.status_code == 200
        data = response.json()
        assert 'temperature' in data
        assert 'humidity' in data
        assert 'latest' in data
        print("✓ /data endpoint test PASSED")
        return True
    except Exception as e:
        print(f"✗ /data endpoint test FAILED: {e}")
        return False

def test_root():
    """Test / endpoint."""
    try:
        response = requests.get(BASE_URL, timeout=5)
        assert response.status_code == 200
        assert 'text/html' in response.headers['Content-Type']
        print("✓ / endpoint test PASSED")
        return True
    except Exception as e:
        print(f"✗ / endpoint test FAILED: {e}")
        return False

if __name__ == '__main__':
    results = [
        test_health(),
        test_data(),
        test_root(),
    ]
    
    print(f"\n{sum(results)}/{len(results)} tests passed")
    exit(0 if all(results) else 1)
```

## Performance Test

```python
#!/usr/bin/env python3
"""Performance test - measure latency."""

import time
import json
import paho.mqtt.client as mqtt
from datetime import datetime, timezone

class PerformanceTest:
    def __init__(self):
        self.latencies = []
        self.received = False
    
    def on_message(self, client, userdata, msg):
        receive_time = time.time()
        payload = json.loads(msg.payload)
        
        publish_time = datetime.fromisoformat(payload['timestamp']).timestamp()
        latency_ms = (receive_time - publish_time) * 1000
        
        self.latencies.append(latency_ms)
        self.received = True
    
    def run(self, message_count=100):
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        client.on_message = self.on_message
        client.connect("test.mosquitto.org", 1883)
        client.subscribe("sensors/perf-test/#")
        client.loop_start()
        
        # Publish test messages
        for i in range(message_count):
            payload = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'temperature': 20 + i % 10,
            }
            client.publish('sensors/perf-test/telemetry', json.dumps(payload))
            time.sleep(0.01)
        
        time.sleep(2)
        client.loop_stop()
        
        if self.latencies:
            avg_latency = sum(self.latencies) / len(self.latencies)
            max_latency = max(self.latencies)
            min_latency = min(self.latencies)
            
            print(f"Performance Test Results:")
            print(f"  Messages: {len(self.latencies)}/{message_count}")
            print(f"  Avg Latency: {avg_latency:.1f}ms")
            print(f"  Min Latency: {min_latency:.1f}ms")
            print(f"  Max Latency: {max_latency:.1f}ms")

if __name__ == '__main__':
    test = PerformanceTest()
    test.run()
```

## Load Test

```bash
#!/bin/bash
# Load test with multiple devices

echo "Starting load test with 10 devices..."

for i in {1..10}; do
    (python cli.py publish "device-$i" --count 100 &)
done

wait

echo "Load test complete"
```

## Test Results Template

```
┌─────────────────────────────────────┐
│ Edge IoT System Test Results        │
├─────────────────────────────────────┤
│ MQTT Connectivity ................. PASS
│ Bridge Processing ................ PASS
│ Flask /health endpoint ........... PASS
│ Flask /data endpoint ............. PASS
│ Dashboard Loading ................ PASS
│ Anomaly Detection ................ PASS
│ Risk Scoring ..................... PASS
│ Log File Writing ................. PASS
│ Multiple Devices ................. PASS
│ Performance (latency < 100ms) .... PASS
│ Memory Usage (<500MB) ............ PASS
├─────────────────────────────────────┤
│ Overall Status: ✓ PASS              │
│ Date: 2024-01-15 14:30:00           │
│ Tester: [Your Name]                 │
└─────────────────────────────────────┘
```

## Debugging Tests

If tests fail:

```bash
# 1. Check MQTT broker
mosquitto_sub -h test.mosquitto.org -t "test" &

# 2. Check bridge output
tail -f logs/bridge.log | grep ERROR

# 3. Check app output
# Look at Flask terminal output

# 4. Check log file
tail -f log.json | python -m json.tool

# 5. Validate JSON
python cli.py validate

# 6. Check system resources
ps aux | grep python
free -h
```

## Test Checklist

- [ ] MQTT broker is reachable
- [ ] Bridge starts without errors
- [ ] App starts without errors
- [ ] /health endpoint responds
- [ ] /data endpoint returns data
- [ ] Dashboard HTML loads
- [ ] Charts display data
- [ ] Anomaly detection works
- [ ] Risk scoring works
- [ ] Alerts appear when needed
- [ ] Multiple devices handled
- [ ] Offline detection works
- [ ] Performance acceptable
- [ ] No memory leaks
- [ ] Log file clean and consistent
