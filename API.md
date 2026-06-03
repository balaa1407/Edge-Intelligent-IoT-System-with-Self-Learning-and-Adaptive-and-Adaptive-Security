# API Documentation

Complete API reference for the Edge IoT Flask dashboard endpoints.

## Base URL

```
http://localhost:5000
```

## Endpoints

### 1. GET /

Serves the dashboard HTML page.

**Response**: HTML document (index.html)

**Example**:
```bash
curl http://localhost:5000/
```

---

### 2. GET /data

Returns latest sensor data and time-series arrays for chart visualization.

**Purpose**: Main endpoint for dashboard updates. Called every 3 seconds by the frontend.

**Response**: JSON object

```json
{
  "success": true,
  "temperature": [23.1, 24.5, 22.8, 25.0],           # Array for line chart
  "humidity": [45.2, 48.5, 42.1, 50.0],              # Array for line chart
  "status": ["Normal", "Normal", "Normal", "Anomaly"], # Status labels
  "timestamps": ["14:30:15", "14:30:45", "14:31:15", "14:31:45"], # X-axis labels
  "modes": ["NORMAL", "NORMAL", "NORMAL", "WARNING"],  # Color coding
  "risks": [1, 2, 1, 5],                              # Risk scores 0-10
  "latest": {
    "temperature": 25.0,
    "humidity": 50.0,
    "status": "Anomaly",
    "mode": "WARNING",
    "risk": 5,
    "device_id": "EDGE-AGG",
    "uptime": 3456,
    "device_count": 2
  },
  "devices": {
    "balaa1407": {
      "device_id": "balaa1407",
      "temperature": 24.5,
      "humidity": 48.5,
      "status": "Normal",
      "mode": "NORMAL",
      "risk": 0,
      "uptime": 1800,
      "last_seen": "2024-01-15T14:31:45.123456+00:00"
    }
  },
  "alert": false
}
```

**Error Responses**:

- **400 Bad Request** - JSON parsing error in log file
  ```json
  {
    "temperature": [],
    "humidity": [],
    "status": [],
    "timestamps": [],
    "modes": [],
    "risks": [],
    "latest": {},
    "devices": {},
    "alert": false
  }
  ```

- **500 Internal Server Error** - File I/O error reading log.json
  ```json
  {
    "temperature": [],
    "humidity": [],
    ...
  }
  ```

**Example**:
```bash
curl http://localhost:5000/data | python -m json.tool
```

**Response Time**: Should be < 100ms under normal conditions

---

### 3. GET /health

Health check endpoint for monitoring systems.

**Purpose**: Simple status check for uptime monitoring, load balancers.

**Response**: JSON object

```json
{
  "status": "ok",
  "timestamp": "2024-01-15T14:31:45.123456+00:00",
  "service": "Edge IoT Dashboard"
}
```

**HTTP Status**: 200 (OK)

**Example**:
```bash
curl http://localhost:5000/health
# Response time: < 10ms
```

**Use Cases**:
- Kubernetes liveness probe
- Uptime monitoring services
- Load balancer health check
- System status dashboard

---

## Data Structure Reference

### Sensor Reading Object

```json
{
  "timestamp": "2024-01-15T14:30:45.123456+00:00",  # ISO format UTC
  "temperature": 25.3,                                # Celsius, float
  "humidity": 48.5,                                   # Percent, float
  "status": "OK" | "WARNING" | "OFFLINE",             # Device status
  "mode": "NORMAL" | "WARNING" | "CRITICAL",          # System mode
  "risk": 5,                                          # 0-10 score
  "device_id": "balaa1407",                           # Device identifier
  "device_count": 2,                                  # Number of online devices
  "uptime": 3600                                      # Seconds
}
```

### Device Summary Object

```json
{
  "device_id": "balaa1407",
  "temperature": 24.5,
  "humidity": 48.5,
  "status": "Normal",
  "mode": "NORMAL",
  "risk": 0,
  "uptime": 1800,
  "last_seen": "2024-01-15T14:31:45.123456+00:00"
}
```

### Risk Score Meanings

| Score | Mode | Meaning |
|-------|------|---------|
| 0-3 | NORMAL | Everything is fine |
| 4-6 | WARNING | Monitor closely, possible issues |
| 7-10 | CRITICAL | Immediate attention needed |

### System Modes

- **NORMAL**: No issues detected, temperatures and humidity within thresholds
- **WARNING**: One or more sensors outside normal range, or anomalies detected
- **CRITICAL**: Critical condition, system risk score >= 7

---

## Examples

### Python Client

```python
import requests
import json

# Fetch latest data
response = requests.get('http://localhost:5000/data')
data = response.json()

# Process temperature array
temps = data['temperature']
avg_temp = sum(temps) / len(temps) if temps else 0

# Check alert
if data['alert']:
    print(f"⚠️  ALERT: System at critical risk!")

print(f"Latest: {data['latest']['temperature']}°C")
```

### JavaScript (Dashboard Frontend)

```javascript
// Fetch data every 3 seconds
async function updateDashboard() {
  const response = await fetch('/data');
  const data = await response.json();
  
  // Update Chart.js charts
  chart.data.labels = data.timestamps;
  chart.data.datasets[0].data = data.temperature;
  chart.update();
  
  // Update stat cards
  document.getElementById('temp').textContent = data.latest.temperature;
  document.getElementById('humidity').textContent = data.latest.humidity;
  
  // Show alert if needed
  if (data.alert) {
    document.getElementById('alert-banner').style.display = 'flex';
  }
}

setInterval(updateDashboard, 3000);
```

### Bash / cURL

```bash
# Health check
curl -i http://localhost:5000/health

# Get latest data
curl http://localhost:5000/data | jq '.latest'

# Extract just temperatures
curl http://localhost:5000/data | jq '.temperature'

# Check if alert is active
curl http://localhost:5000/data | jq '.alert'
```

---

## Performance Notes

- **Data endpoint**: Returns last 20 records from log.json
- **Response size**: Typically < 5KB
- **Polling frequency**: Dashboard polls every 3 seconds (configurable in HTML)
- **Caching**: Disabled - all responses are fresh

## Rate Limiting

Currently no rate limiting implemented. For production, consider:

```python
from flask_limiter import Limiter
limiter = Limiter(app, key_func=lambda: request.remote_addr)
@app.route('/data')
@limiter.limit("30/minute")
def data():
    # Implementation
```

## CORS

Currently no CORS headers. For cross-origin requests:

```python
from flask_cors import CORS
CORS(app)
```

## Error Codes

The system uses HTTP status codes:

| Code | Meaning |
|------|---------|
| 200 | Success - data returned normally |
| 400 | Bad Request - malformed data |
| 500 | Internal Server Error - server error |

---

## Monitoring Integration

### Prometheus Metrics

Could be added to expose metrics like:

```
edge_iot_device_count{status="online"} 2
edge_iot_temperature_celsius{device="balaa1407"} 25.3
edge_iot_humidity_percent{device="balaa1407"} 48.5
edge_iot_risk_score{device="balaa1407"} 0
```

### Grafana Dashboard

Could visualize the time-series data directly from /data endpoint.

---

## Changelog

### Version 1.0
- Initial implementation
- Three endpoints: /, /data, /health
- Real-time sensor data streaming
- Risk scoring and anomaly detection
