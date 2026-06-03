# Configuration Examples

Example configurations for different deployment scenarios.

## Production Configuration

For a production deployment with high reliability requirements:

```python
# config.py
CONFIG = {
    # MQTT Configuration
    "mqtt": {
        "broker": "mqtt.example.com",      # Production broker
        "port": 8883,                       # TLS port
        "client_id": "edge-iot-prod",
        "username": "prod_user",            # Use environment variables in production
        "password": "secure_password",
        "base_topic": "sensors/production",
        "keepalive": 120,
    },
    
    # Temperature thresholds
    "temperature": {
        "min_normal": 18.0,                 # Minimum safe temperature
        "max_normal": 28.0,                 # Maximum safe temperature
    },
    
    # Humidity thresholds
    "humidity": {
        "min_normal": 30.0,                 # Minimum safe humidity
        "max_normal": 70.0,                 # Maximum safe humidity
    },
    
    # Anomaly detection
    "anomaly": {
        "z_threshold": 2.5,                 # Stricter anomaly detection
        "min_history": 10,                  # Need more history
        "max_history": 100,                 # Keep longer history
    },
    
    # Device management
    "device": {
        "offline_timeout_seconds": 300,     # 5 minutes before offline
        "max_devices": 50,                  # Limit connected devices
    },
    
    # Logging
    "logging": {
        "level": "INFO",                    # Production level
        "file": "/var/log/edge-iot.log",   # System log directory
        "max_size_mb": 50,
        "backup_count": 5,
    },
}
```

## Development Configuration

For local testing and development:

```python
CONFIG = {
    "mqtt": {
        "broker": "test.mosquitto.org",     # Public test broker
        "port": 1883,
        "client_id": "edge-iot-dev",
        "base_topic": "sensors/test",
        "keepalive": 60,
    },
    
    "temperature": {
        "min_normal": 15.0,
        "max_normal": 35.0,
    },
    
    "humidity": {
        "min_normal": 20.0,
        "max_normal": 80.0,
    },
    
    "anomaly": {
        "z_threshold": 1.5,                 # Looser for testing
        "min_history": 3,                   # Quick to detect anomalies
        "max_history": 20,
    },
    
    "device": {
        "offline_timeout_seconds": 60,      # Quick timeout for testing
        "max_devices": 10,
    },
    
    "logging": {
        "level": "DEBUG",                   # Verbose for debugging
        "file": "./logs/edge-iot.log",
        "max_size_mb": 10,
        "backup_count": 3,
    },
}
```

## IoT Lab Configuration

For educational/lab environment:

```python
CONFIG = {
    "mqtt": {
        "broker": "localhost",              # Local Mosquitto
        "port": 1883,
        "client_id": "edge-iot-lab",
        "base_topic": "lab/sensors",
        "keepalive": 60,
    },
    
    "temperature": {
        "min_normal": 20.0,
        "max_normal": 30.0,
    },
    
    "humidity": {
        "min_normal": 30.0,
        "max_normal": 70.0,
    },
    
    "anomaly": {
        "z_threshold": 2.0,
        "min_history": 5,
        "max_history": 50,
    },
    
    "device": {
        "offline_timeout_seconds": 120,
        "max_devices": 20,
    },
    
    "logging": {
        "level": "INFO",
        "file": "./logs/lab.log",
        "max_size_mb": 20,
        "backup_count": 3,
    },
}
```

## Docker Configuration

For containerized deployment:

```python
import os

CONFIG = {
    "mqtt": {
        "broker": os.getenv("MQTT_BROKER", "mosquitto"),  # Use service name
        "port": int(os.getenv("MQTT_PORT", "1883")),
        "client_id": os.getenv("MQTT_CLIENT_ID", "edge-iot-docker"),
        "username": os.getenv("MQTT_USERNAME"),
        "password": os.getenv("MQTT_PASSWORD"),
        "base_topic": os.getenv("MQTT_BASE_TOPIC", "sensors"),
    },
    
    "temperature": {
        "min_normal": float(os.getenv("TEMP_MIN", "18.0")),
        "max_normal": float(os.getenv("TEMP_MAX", "28.0")),
    },
    
    "humidity": {
        "min_normal": float(os.getenv("HUM_MIN", "30.0")),
        "max_normal": float(os.getenv("HUM_MAX", "70.0")),
    },
    
    "anomaly": {
        "z_threshold": float(os.getenv("ANOMALY_THRESHOLD", "2.5")),
        "min_history": int(os.getenv("ANOMALY_MIN_HIST", "10")),
        "max_history": int(os.getenv("ANOMALY_MAX_HIST", "100")),
    },
    
    "device": {
        "offline_timeout_seconds": int(os.getenv("DEVICE_TIMEOUT", "300")),
        "max_devices": int(os.getenv("MAX_DEVICES", "50")),
    },
    
    "logging": {
        "level": os.getenv("LOG_LEVEL", "INFO"),
        "file": "/app/logs/edge-iot.log",
        "max_size_mb": int(os.getenv("LOG_SIZE_MB", "50")),
        "backup_count": int(os.getenv("LOG_BACKUPS", "5")),
    },
}
```

## Kubernetes Configuration (ConfigMap)

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: edge-iot-config
  namespace: default
data:
  MQTT_BROKER: "mosquitto.default.svc.cluster.local"
  MQTT_PORT: "1883"
  MQTT_BASE_TOPIC: "sensors/k8s"
  TEMP_MIN: "18.0"
  TEMP_MAX: "28.0"
  HUM_MIN: "30.0"
  HUM_MAX: "70.0"
  ANOMALY_THRESHOLD: "2.5"
  DEVICE_TIMEOUT: "300"
  LOG_LEVEL: "INFO"
```

---

## Configuration Validation

Always validate configuration on startup:

```python
from config_validator import ConfigValidator

validator = ConfigValidator(CONFIG)
is_valid, errors, warnings = validator.validate_all()

if not is_valid:
    print("Configuration errors:")
    for error in errors:
        print(f"  - {error}")
    exit(1)

if warnings:
    print("Configuration warnings:")
    for warning in warnings:
        print(f"  - {warning}")
```

---

## Environment-Specific Usage

Load configuration based on environment:

```python
import os

ENV = os.getenv("ENVIRONMENT", "development")

if ENV == "production":
    from configs.production import CONFIG
elif ENV == "docker":
    from configs.docker import CONFIG
else:
    from configs.development import CONFIG
```

---

## Adjusting Anomaly Detection

The `z_threshold` parameter controls anomaly sensitivity:

| Value | Sensitivity | Use Case |
|-------|-------------|----------|
| 1.0 | Very High | Lab/test - catches minor variations |
| 1.5 | High | Development - catches moderate anomalies |
| 2.0 | Medium | Balanced - catches real anomalies |
| 2.5 | Low | Production - only catches major anomalies |
| 3.0+ | Very Low | Noisy environments - only extreme values |

Adjust based on your sensor noise characteristics.

---

## Temperature Thresholds

Set thresholds based on your application:

```python
# Comfortable office environment
"temperature": {
    "min_normal": 20.0,  # °C
    "max_normal": 25.0,
},

# Warehouse/storage
"temperature": {
    "min_normal": 15.0,  # °C
    "max_normal": 25.0,
},

# Cold storage
"temperature": {
    "min_normal": -20.0,  # °C
    "max_normal": -15.0,
},

# Server room (tight tolerance)
"temperature": {
    "min_normal": 18.0,  # °C
    "max_normal": 24.0,
},
```

---

## Quick Start

1. Copy configuration example matching your use case
2. Update values for your environment
3. Run config validation: `python -c "from config import CONFIG; from config_validator import ConfigValidator; print(ConfigValidator(CONFIG).validate_all())"`
4. Start system: `python bridge.py` and `python app.py`

---

## Troubleshooting Configuration

**Problem**: "MQTT connection timeout"
- Solution: Verify `broker` hostname/IP is correct
- Solution: Check firewall allows port 1883 (or custom port)
- Solution: Verify MQTT server is running

**Problem**: "Too many anomalies detected"
- Solution: Increase `z_threshold` (e.g., 1.5 → 2.5)
- Solution: Increase `min_history` for more samples

**Problem**: "Devices going offline too quickly"
- Solution: Increase `offline_timeout_seconds`
- Solution: Check device MQTT connection stability

---

## Performance Tuning

For systems with many devices:

```python
CONFIG = {
    # ... other settings ...
    
    "device": {
        "offline_timeout_seconds": 600,  # 10 minutes - longer to avoid churn
        "max_devices": 1000,             # Handle many devices
    },
    
    "anomaly": {
        "max_history": 200,  # Keep more history for better detection
        "z_threshold": 3.0,  # Higher threshold to reduce false positives
    },
    
    "logging": {
        "max_size_mb": 100,   # Larger log files
        "backup_count": 10,   # Keep more backups
    },
}
```
