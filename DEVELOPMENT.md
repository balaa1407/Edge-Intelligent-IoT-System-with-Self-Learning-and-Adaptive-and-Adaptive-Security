# Development Guide - Edge IoT System

This guide explains the architecture and how to contribute to the Edge IoT system.

## Architecture Overview

The system consists of three main components:

### 1. **bridge.py** - MQTT Data Bridge
- **Role**: Receives sensor data from ESP32 devices via MQTT
- **Responsibilities**:
  - Connects to MQTT broker (test.mosquitto.org)
  - Subscribes to device telemetry topics
  - Performs real-time anomaly detection (Z-score based)
  - Calculates multi-factor risk scores
  - Aggregates device data and writes to log.json

**Key Classes**:
- `DeviceState`: Manages per-device rolling history and anomaly detection
- Main processing functions: `process_messages()`, `aggregate_and_log()`

**Thread Safety**:
- Uses `threading.Lock` to protect `_devices` dict from concurrent access
- MQTT callbacks run on network thread, main thread processes aggregated data
- Message queue (`_message_queue`) safely passes messages between threads

### 2. **app.py** - Flask Web Dashboard
- **Role**: Serves the real-time monitoring dashboard
- **Responsibilities**:
  - Reads log.json (written by bridge.py)
  - Provides JSON data API for chart updates
  - Serves HTML dashboard UI
  - Implements health check endpoint

**Key Endpoints**:
- `GET /` - Serve dashboard HTML
- `GET /data` - Return latest sensor data and time-series arrays
- `GET /health` - Health check for monitoring systems

**Data Flow**:
1. Dashboard polls `/data` every 3 seconds
2. `/data` reads last 20 records from log.json
3. Returns time-series arrays for Chart.js visualization

### 3. **Sensor Firmware** - esp32_main.py / wokwi_corrected_code.py
- **Role**: Runs on ESP32 microcontroller
- **Responsibilities**:
  - Reads DHT sensor (temperature/humidity)
  - Publishes readings to MQTT
  - Implements Last Will Testament (LWT) for offline detection

## Data Flow

```
ESP32 Sensor
    ↓ (MQTT publish)
test.mosquitto.org (MQTT Broker)
    ↓ (MQTT subscribe)
bridge.py
    ├→ DeviceState (rolling history)
    ├→ Anomaly Detection (Z-score)
    ├→ Risk Scoring
    └→ log.json (append newline-delimited JSON)
         ↓ (read on each /data request)
      app.py
         ↓
      /data endpoint (JSON)
         ↓
      index.html (Chart.js visualization)
```

## Configuration

Configuration is defined in `bridge.py` as a `CONFIG` dictionary:

```python
CONFIG = {
    "mqtt": {
        "server": "test.mosquitto.org",      # MQTT broker
        "port": 1883,
        "base_topic": "edgeiot/balaa1407/#", # Topic filter
    },
    "thresholds": {
        "temp_critical_high": 45.0,  # Critical temperature
        "temp_high": 35.0,            # Warning temperature
        "temp_low": 10.0,             # Low warning
        "humi_high": 80.0,            # High humidity
        "humi_low": 20.0,             # Low humidity
    },
    "anomaly": {
        "min_history": 5,    # Readings before detection starts
        "max_history": 20,   # Rolling window size
        "z_threshold": 2.0,  # Standard deviations for anomaly
    },
    "log": {
        "file": "log.json",
        "max_bytes": 1_000_000,  # 1 MB max log size
        "backup_count": 3,        # Keep 3 backups
        "interval": 0.2,          # Update interval (seconds)
    },
}
```

## Risk Scoring Algorithm

The risk score (0-10) combines multiple factors:

| Factor | Score | Meaning |
|--------|-------|---------|
| Temp >= critical OR temp <= low | +5 | Extreme temperature |
| Temp >= high | +2 | Elevated temperature |
| Humidity out of bounds | +2 | Uncomfortable humidity |
| Device warning status | +2 | Device firmware warning |
| Temperature anomaly | +2 | Unusual temp pattern |
| Humidity anomaly | +1 | Unusual humidity pattern |

**Modes**:
- `NORMAL` (0-3): Everything fine
- `WARNING` (4-6): Monitor closely
- `CRITICAL` (7-10): Immediate attention

## Anomaly Detection

Uses Z-score method to detect outliers:

```
Z-score = |value - mean| / std_deviation
```

- Requires minimum 5 historical readings before detection
- Maintains rolling window of last 20 readings
- Threshold: 2.0 standard deviations = anomaly
- Useful for catching sensor spikes or failures

## Thread Model

```
Main Thread                    Network Thread (MQTT)
────────────────────────────   ─────────────────────
while not shutdown:            on_message()
  process_messages()  ←→ queue → client.loop_start()
  aggregate_and_log()
  sleep(0.2s)
  
cleanup()
```

**Why queue-based?**
- MQTT callbacks must return quickly (they run on network thread)
- Processing sensor data could block MQTT reception
- Queue decouples network I/O from data processing

## Logging

Two log destinations:

1. **Console Logs**: Real-time feedback while running
   ```
   [INFO] [AGG] 🌡️  25.3°C | 💧 45.2% | ⚠️  2/10
   ```

2. **log.json**: Newline-delimited JSON for dashboard
   ```json
   {"timestamp": "2024-01-15T14:30:45.123456+00:00", "temperature": 25.3, ...}
   ```

## Testing & Validation

### Configuration Validation
```python
from config_validator import ConfigValidator

validator = ConfigValidator()
valid, errors, warnings = validator.validate_all(CONFIG)
```

### Utility Functions
```python
from utils import sanitize_device_id, calculate_std_dev, safe_divide

# Safe math operations
std_dev = calculate_std_dev([23.1, 24.5, 22.8])
ratio = safe_divide(temp, humidity, default=1.0)

# Safe device ID handling
clean_id = sanitize_device_id(raw_mqtt_topic)
```

## Common Development Tasks

### Adding a New Threshold
1. Add to CONFIG["thresholds"] in bridge.py
2. Update ConfigValidator.validate_thresholds()
3. Update risk scoring logic if needed
4. Test with test devices

### Adding a New Sensor Type
1. Update DeviceState class to track new sensor type
2. Add parsing logic to process_messages()
3. Update risk_scoring() to consider new sensor
4. Update HTML dashboard to display new metric

### Changing Log File Format
1. Update write_json_log() in bridge.py if needed
2. Update parse_log() in app.py to handle new format
3. Ensure backwards compatibility with old logs
4. Update dashboard to display new fields

## Performance Considerations

- **Message Queue**: Non-blocking, bounded (prevents memory explosion)
- **File I/O**: Rotating log files (max 1 MB, 3 backups)
- **Device State**: Limited to last 20 readings per device per metric
- **Dashboard**: Returns only last 20 records to browser
- **Aggregation**: Runs every 0.2 seconds regardless of message count

## Deployment Checklist

- [ ] Validate CONFIG with ConfigValidator
- [ ] Test MQTT connection with credentials
- [ ] Verify log.json location is writable
- [ ] Check Flask runs on correct host/port
- [ ] Verify SSL/TLS certificates if using secure MQTT
- [ ] Set appropriate logging levels for production
- [ ] Monitor disk space for rotating logs
- [ ] Set up monitoring/alerting for bridge.py process
- [ ] Backup log files periodically

## Troubleshooting

**"Failed to connect to MQTT"**
- Check broker URL and port
- Verify network connectivity
- Check firewall rules
- Ensure mosquitto service is running

**"No data in dashboard"**
- Verify bridge.py is running
- Check device is publishing to correct topic
- Check log.json exists and has recent entries
- Monitor bridge.py logs for errors

**"Risk score always 0"**
- Verify min_history threshold is met (needs 5+ readings)
- Check that device is sending valid temp/humidity
- Review thresholds - may be too lenient

## Resources

- MQTT Protocol: https://mqtt.org/
- Chart.js: https://www.chartjs.org/
- Flask: https://flask.palletsprojects.com/
- paho-mqtt Python: https://eclipse.org/paho/clients/python/
