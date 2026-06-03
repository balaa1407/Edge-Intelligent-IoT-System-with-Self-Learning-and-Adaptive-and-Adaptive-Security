# Extension Guide

How to extend the Edge IoT system with custom functionality.

## Adding New Sensor Types

### Step 1: Update Device State

```python
# In bridge.py, modify DeviceState class
class DeviceState:
    def __init__(self, device_id: str):
        # ... existing code ...
        self.pressure_hist = deque(maxlen=100)  # New sensor
        self.light_hist = deque(maxlen=100)     # New sensor
    
    def add_reading(self, data: Dict):
        # Process pressure
        if 'pressure' in data:
            self.pressure_hist.append(data['pressure'])
        
        # Process light
        if 'light' in data:
            self.light_hist.append(data['light'])
```

### Step 2: Add Anomaly Detection

```python
def check_pressure_anomaly(self) -> bool:
    """Detect pressure anomalies."""
    if len(self.pressure_hist) < 5:
        return False
    
    values = list(self.pressure_hist)
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    std_dev = variance ** 0.5
    
    if std_dev == 0:
        return False
    
    z_score = abs((values[-1] - mean) / std_dev)
    return z_score > 2.0
```

### Step 3: Update Risk Scoring

```python
def score_risk(device_state: DeviceState, config: Dict) -> int:
    """Calculate risk score with new sensors."""
    risk = 0
    
    # ... existing temperature/humidity checks ...
    
    # Check pressure
    if hasattr(device_state, 'pressure_hist') and device_state.pressure_hist:
        if device_state.check_pressure_anomaly():
            risk += 3
    
    # Check light
    if hasattr(device_state, 'light_hist') and device_state.light_hist:
        latest_light = device_state.light_hist[-1]
        if latest_light < 50:  # Too dark
            risk += 2
    
    return min(risk, 10)
```

### Step 4: Update Log Schema

```python
# In aggregate_and_log()
record = {
    "timestamp": timestamp,
    "temperature": avg_temp,
    "humidity": avg_humidity,
    "pressure": avg_pressure,      # New
    "light": avg_light,            # New
    "risk": risk_score,
    "mode": mode,
    "devices": device_summaries,
}
```

### Step 5: Update Dashboard

```javascript
// In index.html, add chart
<canvas id="pressureChart"></canvas>

// Update JavaScript
new Chart(document.getElementById('pressureChart'), {
    type: 'line',
    data: {
        labels: data.timestamps,
        datasets: [{
            label: 'Pressure (hPa)',
            data: data.pressure,
            borderColor: 'rgb(75, 192, 192)',
        }]
    }
});
```

---

## Adding Custom Alert Handlers

```python
# In bridge.py or custom module
from alerts import AlertManager, AlertLevel

# Create alert manager
alert_manager = AlertManager()

# Add custom handler
def sms_handler(alert: Alert) -> None:
    """Send SMS for critical alerts."""
    if alert.level == AlertLevel.CRITICAL:
        # Use Twilio, AWS SNS, etc.
        send_sms(phone_number, alert.message)

alert_manager.add_handler(sms_handler)

# Later in code
alert_manager.create_alert(
    AlertLevel.CRITICAL,
    "device-001",
    "Temperature critically high!",
    details={"temperature": 45.0}
)
```

---

## Custom Aggregation Functions

```python
# In data_aggregator.py or custom module
class CustomAggregator:
    """Custom aggregation logic."""
    
    @staticmethod
    def weighted_average(devices: Dict) -> float:
        """Calculate weighted average by device priority."""
        total_weight = 0
        weighted_sum = 0
        
        for device_id, state in devices.items():
            weight = get_device_priority(device_id)
            if state.latest.get('temperature'):
                weighted_sum += state.latest['temperature'] * weight
                total_weight += weight
        
        if total_weight == 0:
            return 0
        return weighted_sum / total_weight
    
    @staticmethod
    def percentile(devices: Dict, percentile: float = 0.95) -> float:
        """Get Nth percentile of temperatures."""
        values = [
            state.latest['temperature']
            for state in devices.values()
            if state.latest.get('temperature')
        ]
        
        if not values:
            return 0
        
        values.sort()
        index = int(len(values) * percentile)
        return values[index]
```

---

## Database Integration

Replace log.json with SQLite:

```python
import sqlite3

class DatabaseBackend:
    def __init__(self, db_path: str = 'edge_iot.db'):
        self.conn = sqlite3.connect(db_path)
        self._init_schema()
    
    def _init_schema(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS readings (
                id INTEGER PRIMARY KEY,
                timestamp TEXT NOT NULL,
                device_id TEXT NOT NULL,
                temperature REAL,
                humidity REAL,
                risk INTEGER,
                mode TEXT
            )
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_timestamp 
            ON readings(timestamp DESC)
        ''')
        self.conn.commit()
    
    def insert_reading(self, record: Dict):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO readings 
            (timestamp, device_id, temperature, humidity, risk, mode)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            record['timestamp'],
            record.get('device_id'),
            record.get('temperature'),
            record.get('humidity'),
            record.get('risk'),
            record.get('mode'),
        ))
        self.conn.commit()
    
    def get_recent(self, minutes: int = 60) -> List[Dict]:
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM readings
            WHERE datetime(timestamp) >= datetime('now', ?)
            ORDER BY timestamp DESC
        ''', (f'-{minutes} minutes',))
        return [dict(row) for row in cursor.fetchall()]
```

---

## Real-time WebSocket Support

```python
from flask import Flask
from flask_socketio import SocketIO, emit

app = Flask(__name__)
socketio = SocketIO(app)

@socketio.on('connect')
def handle_connect():
    emit('response', {'data': 'Connected'})

# In bridge.py
def aggregate_and_log():
    # ... existing code ...
    
    # Broadcast to connected clients
    socketio.emit('update', record, broadcast=True)

# In client JavaScript
const socket = io();
socket.on('update', (data) => {
    updateCharts(data);
});
```

---

## Machine Learning Integration

```python
# Using scikit-learn for prediction
from sklearn.ensemble import IsolationForest
import numpy as np

class MLAnomalyDetector:
    def __init__(self):
        self.model = IsolationForest(contamination=0.1)
        self.training_data = []
    
    def train(self, readings: List[float]):
        """Train anomaly detector."""
        X = np.array(readings).reshape(-1, 1)
        self.model.fit(X)
    
    def predict(self, reading: float) -> bool:
        """Predict if reading is anomaly."""
        prediction = self.model.predict([[reading]])
        return prediction[0] == -1  # -1 = anomaly
```

---

## Integration with External APIs

```python
import requests

class WeatherIntegration:
    """Integrate weather data."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.openweathermap.org"
    
    def get_outdoor_temp(self, lat: float, lon: float) -> float:
        """Get outdoor temperature."""
        response = requests.get(
            f"{self.base_url}/data/2.5/weather",
            params={
                'lat': lat,
                'lon': lon,
                'appid': self.api_key,
            }
        )
        return response.json()['main']['temp']
    
    def compare_with_outdoor(self, indoor: float, lat: float, lon: float):
        """Compare indoor vs outdoor."""
        outdoor = self.get_outdoor_temp(lat, lon)
        diff = abs(indoor - outdoor)
        
        if diff > 10:
            # Alert if difference is large
            return f"Indoor/outdoor difference: {diff}°C"
```

---

## Performance Monitoring

```python
from metrics import MetricsCollector

collector = MetricsCollector()

def process_with_metrics():
    with PerformanceTimer('process_message', collector):
        # Process code here
        pass
    
    with PerformanceTimer('aggregate_and_log', collector):
        # Aggregation code here
        pass

# Report metrics
def report_metrics():
    for metric_name in collector.metrics:
        summary = collector.get_summary(metric_name)
        print(f"{metric_name}: {summary['avg']:.2f}ms avg")
```

---

## Custom Configuration Schema

```python
from pydantic import BaseModel, validator

class DeviceConfig(BaseModel):
    """Configuration for a device."""
    device_id: str
    location: str
    sensor_types: List[str]
    thresholds: Dict[str, tuple]
    
    @validator('device_id')
    def validate_device_id(cls, v):
        if not v:
            raise ValueError('Device ID required')
        return v

# Usage
config = DeviceConfig(
    device_id='device-001',
    location='living-room',
    sensor_types=['temperature', 'humidity', 'pressure'],
    thresholds={'temperature': (18, 28)}
)
```

---

## Testing Custom Code

```python
import unittest

class TestCustomFeatures(unittest.TestCase):
    def test_pressure_anomaly(self):
        state = DeviceState('test')
        state.pressure_hist = deque([1013, 1013, 1014, 1013, 50])  # Anomaly
        
        self.assertTrue(state.check_pressure_anomaly())
    
    def test_custom_aggregation(self):
        devices = {
            'device-1': MockDeviceState(temp=20),
            'device-2': MockDeviceState(temp=25),
        }
        
        avg = CustomAggregator.weighted_average(devices)
        self.assertGreater(avg, 0)
    
    def test_ml_detector(self):
        detector = MLAnomalyDetector()
        detector.train([20, 21, 22, 21, 20, 21])
        
        self.assertFalse(detector.predict(21))  # Normal
        self.assertTrue(detector.predict(100))   # Anomaly
```

---

## Deployment Patterns

### A/B Testing

```python
# Run two versions in parallel
if use_new_algorithm:
    risk = new_risk_scoring(device_state)
else:
    risk = old_risk_scoring(device_state)

# Log both for comparison
metrics.record_metric('old_risk', old_risk, tags={'version': 'v1'})
metrics.record_metric('new_risk', new_risk, tags={'version': 'v2'})
```

### Feature Flags

```python
FEATURE_FLAGS = {
    'ml_anomaly_detection': False,
    'slack_alerts': False,
    'database_backend': False,
}

# Use in code
if FEATURE_FLAGS['ml_anomaly_detection']:
    is_anomaly = ml_detector.predict(reading)
else:
    is_anomaly = zscore_detector.predict(reading)
```

---

## Documentation for Custom Code

Always document your extensions:

```python
def my_custom_function(param1: str, param2: int) -> bool:
    """
    Brief description of what this does.
    
    Detailed explanation of the algorithm or logic.
    
    Args:
        param1: Description of param1
        param2: Description of param2
    
    Returns:
        Description of return value
    
    Examples:
        >>> my_custom_function("test", 10)
        True
    
    Raises:
        ValueError: When param1 is empty
    """
    # Implementation
```

---

## Contributing Guidelines

When extending the system:

1. **Write tests first**: TDD approach
2. **Document thoroughly**: Docstrings and examples
3. **Follow patterns**: Consistent with existing code
4. **Consider performance**: Measure before optimizing
5. **Add to guides**: Update ARCHITECTURE, DEVELOPMENT
6. **Get feedback**: Code review with team

For production extensions, submit PR with:
- [ ] Unit tests
- [ ] Integration tests
- [ ] Documentation
- [ ] Performance benchmarks
- [ ] Deployment notes
