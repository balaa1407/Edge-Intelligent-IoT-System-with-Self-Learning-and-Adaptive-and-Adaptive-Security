# System Architecture Overview

Deep dive into the Edge IoT system architecture, design decisions, and component interactions.

## Table of Contents

1. [System Overview](#system-overview)
2. [Component Architecture](#component-architecture)
3. [Data Flow](#data-flow)
4. [Design Patterns](#design-patterns)
5. [Thread Model](#thread-model)
6. [Scalability](#scalability)
7. [Extension Points](#extension-points)

---

## System Overview

The Edge IoT system is a real-time sensor monitoring platform that:

- **Collects** temperature and humidity data from distributed IoT devices via MQTT
- **Analyzes** sensor readings for anomalies using statistical methods
- **Aggregates** data across devices to compute system-wide statistics
- **Visualizes** trends and alerts through a web dashboard
- **Stores** historical data for analysis and auditing

### Key Characteristics

| Aspect | Details |
|--------|---------|
| Protocol | MQTT pub/sub for device-to-broker communication |
| Data Store | Newline-delimited JSON (log.json) for streaming efficiency |
| Web Framework | Flask with Chart.js for real-time visualization |
| Processing | Single-threaded bridge process with async MQTT callbacks |
| Scalability | Supports 10s of devices on single machine |
| Deployment | Standalone Python application, Docker-compatible |

---

## Component Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         IoT Devices                         │
│                (ESP32, Sensors, Gateways)                   │
└─────────────────────────┬──────────────────────────────────┘
                          │ MQTT (JSON)
                          ▼
         ┌────────────────────────────────────┐
         │   MQTT Broker (test.mosquitto.org) │
         └────────────────────────────────────┘
                          │
         ┌────────────────┴──────────────────┐
         │                                   │
         ▼                                   ▼
  ┌─────────────┐                   ┌─────────────┐
  │  bridge.py  │                   │   app.py    │
  │(Subscriber) │                   │  (Dashboard)│
  └─────────────┘                   └─────────────┘
         │                                   │
         │ log.json                          │ Read
         ▼                                   ▼
  ┌──────────────────────────────────────────────┐
  │          Data Persistence Layer              │
  │  - log.json (newline-delimited JSON)        │
  │  - config files                             │
  │  - logs directory                           │
  └──────────────────────────────────────────────┘
         │
         └─────────────────────────────────┐
                                           │
         ┌─────────────────────────────────┼──────────┐
         │                                 │          │
         ▼                                 ▼          ▼
    ┌─────────┐                     ┌──────────┐  ┌──────────┐
    │ Analysis│                     │ Export   │  │ Alerting │
    │ Tools   │                     │ Tools    │  │ System   │
    └─────────┘                     └──────────┘  └──────────┘
```

### Core Components

#### 1. **bridge.py** - MQTT Subscriber & Processor

```python
Purpose:
  - Subscribe to device telemetry topics
  - Parse and validate sensor readings
  - Detect anomalies using z-score method
  - Calculate risk scores
  - Aggregate data across devices
  - Persist data to log.json

Key Classes:
  - DeviceState: Per-device history and anomaly detection
  - Callbacks: on_connect, on_disconnect, on_message
  - Main thread: Queue processor and logger

Threading:
  - MQTT callbacks run in paho client thread
  - Messages queued in thread-safe queue
  - Main thread processes queue and aggregates
```

#### 2. **app.py** - Flask Web Server

```python
Purpose:
  - Serve dashboard HTML
  - Provide /data API for real-time updates
  - Provide /health endpoint for monitoring
  - Cache-control for fresh data

Routes:
  - GET /: Serve index.html
  - GET /data: Return time-series JSON for charts
  - GET /health: Return service status

Data Pipeline:
  1. Read log.json
  2. Parse newline-delimited JSON
  3. Extract latest N records
  4. Format for Chart.js
  5. Return as JSON response
```

#### 3. **Supporting Modules** - Utilities & Helpers

```
utils.py
├── Validation functions
├── Math utilities (mean, std_dev)
├── Safe division with error handling
└── Formatting utilities

config_validator.py
├── Validate MQTT settings
├── Validate thresholds
├── Validate anomaly parameters
└── Return validation report

logger_setup.py
├── Configure logging handlers
├── Rotating file handler
├── Console output
└── Log formatting

device_manager.py
├── Track device health
├── Detect offline devices
├── Report uptime
└── Manage device lifecycle

data_aggregator.py
├── Calculate system averages
├── Find min/max readings
├── Count anomalies
└── Generate summary records

api_response.py
├── Standardize API responses
├── Dashboard data formatting
├── Health check responses
└── Response validation

metrics.py
├── Track performance metrics
├── Calculate health scores
├── Monitor error rates
└── Performance timing

data_tools.py
├── Export to CSV/JSON/JSONL
├── Statistical analysis
├── Data validation
└── Data cleaning

exceptions.py
├── Custom exception hierarchy
├── Domain-specific errors
├── Error context preservation
└── Exception logging helpers

test_utils.py
├── Test data generation
├── Mock device state
├── Assertion helpers
└── Pre-built test datasets

mqtt_utils.py
├── MQTT client wrapper
├── Topic builder
├── Payload validation
└── Safe JSON extraction
```

---

## Data Flow

### Real-Time Sensor Reading

```
1. ESP32 Device publishes:
   Topic: sensors/device-001/telemetry
   Payload: {"temperature": 23.5, "humidity": 45.0, ...}

2. MQTT Broker receives and routes message

3. bridge.py on_message callback:
   - Decode JSON
   - Validate fields
   - Queue for processing

4. Main thread processes queue:
   - Retrieve DeviceState for device
   - Add to rolling history (deque)
   - Check for anomalies (z-score)
   - Update device status

5. Every N seconds, aggregate_and_log():
   - Calculate system averages
   - Build summary record
   - Calculate risk score
   - Append to log.json

6. log.json gets new line:
   {
     "timestamp": "2024-01-15T14:30:45.123Z",
     "temperature": 23.2,
     "humidity": 45.3,
     "risk": 2,
     "mode": "NORMAL",
     "device_count": 3,
     "devices": {...}
   }

7. Flask app.py reads log.json:
   - Parse JSON lines
   - Extract last 20 entries
   - Build Chart.js data arrays
   - Return as /data endpoint response

8. Browser dashboard fetches /data every 3 seconds:
   - Updates temperature chart
   - Updates humidity chart
   - Shows latest readings
   - Displays alerts if risk > 7
```

### Anomaly Detection Path

```
Reading arrives → DeviceState.add_reading()
    ↓
Check if enough history (min_history threshold)
    ↓
Calculate mean of history
    ↓
Calculate standard deviation
    ↓
Calculate z-score: |reading - mean| / std_dev
    ↓
Compare with z_threshold (default 2.0)
    ↓
If z_score > threshold:
    ├─ Mark as anomaly in DeviceState
    ├─ Increase risk score by 4 points
    └─ Log warning message
    ↓
Store result in log.json
    ↓
Dashboard shows in alerts
```

### Risk Scoring Path

```
For each reading:

1. Start with risk_score = 0

2. Check temperature bounds:
   - If temp < min_normal or > max_normal: +3 points

3. Check humidity bounds:
   - If humidity < min_normal or > max_normal: +2 points

4. Check for anomaly:
   - If z_score > threshold: +4 points

5. Device offline:
   - If last_seen > timeout: +5 points

6. Clamp to 0-10 range

7. Determine mode:
   - NORMAL: risk 0-3
   - WARNING: risk 4-6
   - CRITICAL: risk 7-10

8. Trigger alerts if CRITICAL
```

---

## Design Patterns

### 1. Producer-Consumer Pattern

```python
# MQTT Callbacks (Producer)
def on_message(client, userdata, msg):
    payload = json.loads(msg.payload)
    message_queue.put(payload)  # Non-blocking

# Main Thread (Consumer)
while running:
    try:
        message = message_queue.get(timeout=1.0)
        process_message(message)
    except queue.Empty:
        aggregate_and_log()  # Periodic task
```

**Benefits**:
- Decouples MQTT callbacks from processing
- MQTT thread not blocked by slow processing
- Graceful handling of burst messages
- Periodic aggregation between messages

### 2. Thread-Safe Shared State

```python
# DeviceState class holds per-device data
devices = {}  # {device_id: DeviceState}
device_lock = threading.Lock()

# Protection pattern
with device_lock:
    if device_id not in devices:
        devices[device_id] = DeviceState(device_id)
    devices[device_id].add_reading(temp, humidity)
```

**Benefits**:
- Safe access from multiple threads
- MQTT callbacks can read/update safely
- Main thread doesn't block callbacks
- Predictable synchronization

### 3. Stateful Processing

```python
# DeviceState maintains rolling window of history
class DeviceState:
    def __init__(self, device_id):
        self.temp_hist = deque(maxlen=100)  # Auto-rotate
        self.humi_hist = deque(maxlen=100)
        self.latest = {}
        self.last_seen = datetime.now()
    
    def add_reading(self, temp, humidity):
        self.temp_hist.append(temp)  # Auto-pops old values
        self.humi_hist.append(humidity)
        self.latest = {"temp": temp, "humidity": humidity}
```

**Benefits**:
- Automatic history window management
- No manual cleanup needed
- Efficient memory usage
- O(1) append operation

### 4. Configuration Validation

```python
# Validate on startup
validator = ConfigValidator(CONFIG)
is_valid, errors, warnings = validator.validate_all()

if not is_valid:
    for error in errors:
        print(f"FATAL: {error}")
    exit(1)

if warnings:
    for warning in warnings:
        print(f"WARNING: {warning}")
```

**Benefits**:
- Catch configuration issues early
- Fail fast before processing
- User-friendly error messages
- Optional warnings for best practices

### 5. Newline-Delimited JSON

```python
# Writing (append mode, stream-friendly)
with open('log.json', 'a') as f:
    f.write(json.dumps(record) + '\n')

# Reading (line-by-line, memory efficient)
with open('log.json', 'r') as f:
    for line in f:
        record = json.loads(line)
        process(record)
```

**Benefits**:
- Efficient for large files (no full parse)
- Stream-friendly (can append indefinitely)
- Each line is independent
- Easy to tail/follow in real-time

---

## Thread Model

```
Main Process
│
├─ MQTT Client Thread (paho-mqtt internal)
│  └─ on_connect() callback
│  └─ on_disconnect() callback
│  └─ on_message() callback → queue.put()
│
├─ Main Application Thread
│  ├─ Loop every 1 second:
│  │  ├─ Drain message queue
│  │  ├─ Process each message
│  │  │  └─ Update DeviceState
│  │  │  └─ Check anomalies
│  │  │  └─ Calculate risk
│  │  │
│  │  └─ Every N messages:
│  │     ├─ aggregate_and_log()
│  │     ├─ Calculate averages
│  │     ├─ Check offline devices
│  │     └─ Write to log.json
│  │
│  └─ On shutdown: cleanup & disconnect
│
└─ Flask Thread (on demand)
   └─ /data route
   └─ /health route
   └─ Static file serving
```

### Thread Safety

| Resource | Protection | Method |
|----------|-----------|--------|
| `devices` dict | Lock | threading.Lock() |
| `message_queue` | Atomic | queue.Queue() |
| `log.json` | Exclusive | Single writer |
| Flask routes | None needed | Read-only access |

### Concurrency Implications

- **MQTT callbacks never block**: Messages queued immediately
- **Main thread cannot block Flask**: Routes run in separate thread
- **Multiple devices safe**: DeviceState protected per-device
- **Log file atomic writes**: Single writer, no corruption
- **Dashboard reads fresh data**: No caching, always current

---

## Scalability

### Vertical Scaling (Single Machine)

| Factor | Limit | Mitigation |
|--------|-------|-----------|
| Memory | ~1GB log file | Rotate log files daily |
| CPU | 100% on anomaly detection | Increase z_threshold |
| Devices | 50-100 per machine | Partition by device group |
| Message rate | 1000 msg/sec | Batch aggregation |

### Horizontal Scaling

For 100+ devices, consider:

```
Architecture:
  ┌─────────────────────────────────┐
  │   MQTT Broker (Central)         │
  └─────────────────────────────────┘
   ├── bridge-group1.py ──┐
   ├── bridge-group2.py ──┼─ App Load Balancer ─ Flask instances
   └── bridge-group3.py ──┘

Each bridge subscribes to subset of topics:
  - bridge-group1: sensors/floor-1/#
  - bridge-group2: sensors/floor-2/#
  - bridge-group3: sensors/floor-3/#

Shared database (optional):
  - PostgreSQL for log storage
  - Redis for shared cache
  - InfluxDB for time-series
```

---

## Extension Points

### 1. Adding New Sensor Types

```python
# In bridge.py
if device_data.get('pressure'):  # New sensor
    device_state.pressure_hist.append(device_data['pressure'])
    check_pressure_anomaly()
```

### 2. Custom Alert Handlers

```python
# In aggregate_and_log()
if risk_score >= 7:
    send_email_alert(device_id, risk_score)
    send_slack_notification(risk_score)
    trigger_siren()
```

### 3. Different Anomaly Methods

```python
# Instead of z-score, use:
from scipy import stats

# Isolation Forest
from sklearn.ensemble import IsolationForest
```

### 4. Database Integration

```python
# Instead of log.json:
import sqlite3

conn = sqlite3.connect('edge_iot.db')
cursor = conn.cursor()
cursor.execute('''
    INSERT INTO readings
    VALUES (?, ?, ?, ?, ?, ?)
''', (timestamp, device_id, temp, humidity, risk, mode))
```

### 5. Cloud Integration

```python
# Send data to cloud
import requests

def send_to_cloud(record):
    requests.post(
        'https://api.example.com/readings',
        json=record,
        timeout=5
    )
```

---

## Performance Characteristics

### Message Processing Latency

```
Message published ─┐
                   │ ~1-2ms (MQTT broker)
Message received ──┤
                   │ ~0.1-0.5ms (callback queue)
Queued ────────────┤
                   │ ~1-5ms (processing)
Processed ─────────┤
                   │ ~5-10ms (JSON serialization)
Written to disk ───┘

Total: ~7-18ms from publish to persistent storage
```

### Memory Usage

```
Base application: ~50 MB
Per device: ~2-5 MB (1000 history entries)
Log file: 1000 entries ≈ 100 KB

Example:
  - 10 devices + base = 70-80 MB
  - 1 month of logs = 10 MB
  - Growing slowly with data
```

### CPU Usage

```
Idle: <1% CPU
At 10 msg/sec: ~5% CPU
At 100 msg/sec: ~20% CPU
At 1000 msg/sec: ~80% CPU

Anomaly detection adds ~10% per 1000 entries
```

---

## Failure Modes

| Failure | Impact | Recovery |
|---------|--------|----------|
| MQTT broker down | No new data | Auto-reconnect |
| Device offline | Missing readings | Timeout detection |
| log.json corruption | Data loss | Rotate and restart |
| Out of memory | Process crash | Restart with cleanup |
| Flask crash | No dashboard | Restart Flask only |

---

## Best Practices

1. **Validate all inputs**: Never trust MQTT data
2. **Use configuration validation**: Catch errors early
3. **Monitor system health**: Track metrics
4. **Log everything**: Essential for debugging
5. **Test with anomalies**: Ensure detection works
6. **Rotate logs regularly**: Prevent disk fill
7. **Set reasonable thresholds**: Domain-specific
8. **Document custom code**: For maintenance
