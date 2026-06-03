# Project Setup and Installation Guide

Quick start guide for setting up and running the Edge IoT system.

## System Requirements

- Python 3.9 or higher
- pip (Python package manager)
- MQTT broker access (defaults to test.mosquitto.org)
- ~50 MB disk space for logs and cache

## Installation Steps

### 1. Clone the Repository
```bash
git clone <repository-url>
cd Edge-Intelligent-IoT-System
```

### 2. Create Virtual Environment
```bash
# On Linux/Mac:
python3 -m venv venv
source venv/bin/activate

# On Windows:
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

Check installed packages:
```bash
pip list
```

Should show:
- flask >= 3.0.0
- paho-mqtt >= 2.0.0

### 4. Validate Configuration
```bash
python -c "
from config_validator import ConfigValidator
from bridge import CONFIG
validator = ConfigValidator()
valid, errors, warnings = validator.validate_all(CONFIG)
if valid:
    print('✓ Configuration is valid')
else:
    print('✗ Configuration errors:')
    for e in errors:
        print(f'  - {e}')
"
```

## Running the System

### Terminal 1: Start the MQTT Bridge
```bash
python bridge.py
```

Expected output:
```
2024-01-15 14:30:45 [INFO] 🚀 Edge IoT bridge starting…
2024-01-15 14:30:45 [INFO] Connecting to MQTT (attempt 1/5)…
2024-01-15 14:30:46 [INFO] ✓ MQTT connected → test.mosquitto.org
2024-01-15 14:30:46 [INFO] ✓ Subscribed: edgeiot/balaa1407/#
2024-01-15 14:30:46 [INFO] ✓ Loop started — updating every 0.2s
```

The bridge will now:
- Subscribe to MQTT topics
- Wait for sensor data
- Process messages in real-time
- Write to log.json every 0.2 seconds

### Terminal 2: Start the Flask Dashboard
```bash
python app.py
```

Expected output:
```
 * Running on http://0.0.0.0:5000
 * Debug mode: off
WARNING: This is a development server. Do not use it in production.
```

Now open your browser to: **http://localhost:5000**

### Terminal 3: Simulate Sensor Data (Optional)

For testing without physical ESP32:

```bash
python send_varied_data.py
```

This will publish random sensor readings to MQTT.

## Project Structure

```
edge-iot/
├── bridge.py                 # MQTT subscriber + anomaly detection
├── app.py                    # Flask web server
├── esp32_main.py            # ESP32 firmware (physical device)
├── wokwi_corrected_code.py  # Wokwi simulator code
├── templates/
│   └── index.html           # Dashboard UI
├── utils.py                 # Utility functions
├── config_validator.py      # Configuration validation
├── logger_setup.py          # Logging configuration
├── data_aggregator.py       # Data aggregation utilities
├── device_manager.py        # Device management
├── api_response.py          # API response builders
├── requirements.txt         # Python dependencies
├── log.json                 # Auto-generated sensor log
└── README.md                # Main documentation
```

## Configuration

Edit the `CONFIG` dictionary in `bridge.py` to customize:

### MQTT Settings
```python
"mqtt": {
    "server": "test.mosquitto.org",      # MQTT broker address
    "port": 1883,                         # MQTT port
    "base_topic": "edgeiot/balaa1407/#",  # Topic to subscribe
}
```

### Sensor Thresholds
```python
"thresholds": {
    "temp_critical_high": 45.0,  # Critical temperature
    "temp_high": 35.0,            # Warning temperature
    "temp_low": 10.0,             # Low warning
    "humi_high": 80.0,            # High humidity
    "humi_low": 20.0,             # Low humidity
}
```

### Anomaly Detection
```python
"anomaly": {
    "min_history": 5,    # Readings before detection
    "max_history": 20,   # Rolling window size
    "z_threshold": 2.0,  # Std devs for anomaly
}
```

## Troubleshooting

### "Connection refused" Error
```
✗ Connection attempt 1 failed: Connection refused
```
**Solution**: Ensure mosquitto broker is running and accessible
```bash
# Check if broker is reachable
nc -zv test.mosquitto.org 1883
```

### "No module named 'paho'" Error
```
ModuleNotFoundError: No module named 'paho'
```
**Solution**: Install missing package
```bash
pip install paho-mqtt
```

### "Permission denied" on log.json
```
PermissionError: [Errno 13] Permission denied: 'log.json'
```
**Solution**: Change log file location or permissions
```bash
# Make log directory writable
chmod 755 .

# Or change log location in CONFIG:
"file": "/tmp/log.json"
```

### Dashboard shows "No Data"
1. Verify bridge.py is running (check for errors)
2. Verify a sensor device is publishing (check bridge logs)
3. Check that log.json was created and has content:
   ```bash
   tail -n 5 log.json
   ```
4. Clear browser cache (press F5 or Ctrl+Shift+Delete)

### High CPU Usage
- Reduce logging verbosity: Change `level=logging.DEBUG` to `logging.INFO`
- Increase aggregation interval: Change `CONFIG["log"]["interval"]` from 0.2 to 1.0

## Testing

### Test MQTT Publishing
```bash
# Install mosquitto client tools:
apt install mosquitto-clients  # Linux
brew install mosquitto        # Mac

# Publish test message:
mosquitto_pub -h test.mosquitto.org -t edgeiot/test/telemetry \
  -m '{"temperature": 25.5, "humidity": 45.2}'

# Subscribe to verify:
mosquitto_sub -h test.mosquitto.org -t "edgeiot/#"
```

### Test Flask Endpoint
```bash
# Health check:
curl http://localhost:5000/health | python -m json.tool

# Get latest data:
curl http://localhost:5000/data | python -m json.tool
```

### Verify Configuration
```bash
python -c "from bridge import CONFIG; import json; print(json.dumps(CONFIG, indent=2))"
```

## Performance Tips

1. **Reduce Message Frequency**: Lower ESP32 publish rate to save bandwidth
2. **Increase Aggregation Interval**: Change from 0.2s to 1.0s if not latency-critical
3. **Limit History Size**: Reduce `max_history` if memory is constrained
4. **Disable Debug Logging**: Set `logging.INFO` instead of `logging.DEBUG`

## Deployment

For production deployment:

1. Use a real MQTT broker instead of test.mosquitto.org
2. Enable SSL/TLS for MQTT and Flask
3. Use a production WSGI server (e.g., gunicorn):
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 app:app
   ```
4. Run as systemd service with auto-restart
5. Configure log rotation
6. Set up monitoring and alerting

## Support

For issues or questions:
1. Check DEVELOPMENT.md for architecture details
2. Review log files for error messages
3. Verify configuration with config_validator.py
4. Test MQTT connectivity with mosquitto tools
