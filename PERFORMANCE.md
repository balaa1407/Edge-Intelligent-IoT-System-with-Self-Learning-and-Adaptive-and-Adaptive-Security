# Performance Tuning Guide

Optimize the Edge IoT system for your specific workload and environment.

## Quick Performance Checklist

- [ ] Monitor baseline metrics (memory, CPU, latency)
- [ ] Adjust anomaly detection threshold
- [ ] Configure history window sizes
- [ ] Set appropriate log rotation
- [ ] Enable caching where appropriate
- [ ] Optimize MQTT subscription pattern
- [ ] Test under load
- [ ] Monitor in production

---

## 1. Anomaly Detection Tuning

### Z-Score Threshold

The `z_threshold` parameter controls sensitivity. Adjust based on false positive rate.

```python
# In config
"anomaly": {
    "z_threshold": 2.0,  # Increase to reduce false positives
    "min_history": 10,   # Minimum samples before detection
    "max_history": 100,  # Window size
}
```

**Performance Impact**:
- Higher threshold: ✓ Fewer anomaly calculations, ✓ Faster processing
- Lower threshold: ✗ More false positives, ✗ Higher CPU

**Tuning Strategy**:

```python
# Monitor false positive rate
false_positives = anomaly_count / total_readings

if false_positive_rate > 0.05:  # >5%
    # Increase threshold
    z_threshold = 2.5
else:
    # Keep or decrease
    z_threshold = 1.5
```

### History Window Size

Larger window = better anomaly detection, but more memory.

```python
"anomaly": {
    "min_history": 10,   # ← Minimum before detecting
    "max_history": 100,  # ← Rolling window size
}
```

**Memory per Device**:
- 100 entries × 8 bytes (float) × 2 (temp + humidity) = 1.6 KB per device
- With 100 devices = 160 KB (negligible)

**Recommendation**:
- Small devices (< 10): min=5, max=50
- Medium devices (10-50): min=10, max=100
- Large deployments (> 50): min=15, max=200

---

## 2. Message Processing Tuning

### Queue Size and Timeout

```python
# In bridge.py main loop
message_queue = queue.Queue(maxsize=1000)

try:
    message = message_queue.get(timeout=1.0)
except queue.Empty:
    aggregate_and_log()
```

**Optimization**:
- Larger queue: Handles burst traffic, uses more memory
- Smaller queue: Tight control, may drop messages

```python
# For high-traffic systems
message_queue = queue.Queue(maxsize=5000)

# For low-traffic systems
message_queue = queue.Queue(maxsize=100)
```

### Aggregation Frequency

How often to write to log.json:

```python
# Option 1: Every N messages
message_count = 0
while running:
    message = message_queue.get()
    process_message(message)
    message_count += 1
    if message_count >= 100:  # ← Adjust this
        aggregate_and_log()
        message_count = 0

# Option 2: Every N seconds
last_aggregate = time.time()
while running:
    message = message_queue.get(timeout=0.5)
    process_message(message)
    if time.time() - last_aggregate >= 10:  # Every 10 seconds
        aggregate_and_log()
        last_aggregate = time.time()
```

**Performance Trade-off**:

| Frequency | Latency | Disk I/O | Disk Space |
|-----------|---------|----------|-----------|
| Every 10 msg | Low | High | Grows fast |
| Every 100 msg | Medium | Medium | Medium |
| Every 1000 msg | High | Low | Grows slow |
| Every 10 sec | Medium | Medium | Predictable |

**Recommendation**: Every 100-500 messages or 10-30 seconds

---

## 3. Log File Management

### Log Rotation

Prevent log.json from growing indefinitely:

```python
import os

def rotate_log_if_needed(filename='log.json', max_size_mb=50):
    """Rotate log file if it exceeds size limit."""
    try:
        size_mb = os.path.getsize(filename) / (1024 * 1024)
        if size_mb > max_size_mb:
            # Backup current log
            import shutil
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup = f"log_{timestamp}.json"
            shutil.copy(filename, backup)
            
            # Remove old backups (keep 5)
            logs = sorted(glob.glob('log_*.json'))
            for old_log in logs[:-5]:
                os.remove(old_log)
            
            # Start fresh
            open(filename, 'w').close()
    except Exception as e:
        logger.error(f"Log rotation failed: {e}")

# Call in main loop
rotate_log_if_needed()
```

**Configuration**:

```python
{
    "logging": {
        "max_size_mb": 50,      # Size threshold
        "backup_count": 5,      # Keep N backups
        "retention_days": 30,   # Delete after N days
    }
}
```

### Compression

For archival, compress old logs:

```python
import gzip

def compress_old_logs(days=7):
    """Compress logs older than N days."""
    cutoff = time.time() - (days * 86400)
    for log_file in glob.glob('log_*.json'):
        if os.stat(log_file).st_mtime < cutoff:
            with open(log_file, 'rb') as f_in:
                with gzip.open(f'{log_file}.gz', 'wb') as f_out:
                    f_out.writelines(f_in)
            os.remove(log_file)
```

---

## 4. Flask Dashboard Optimization

### Caching Strategy

```python
# In app.py
from flask_caching import Cache

cache = Cache(app, config={'CACHE_TYPE': 'simple'})

@app.route('/data')
@cache.cached(timeout=1)  # Cache for 1 second
def data():
    return process_log()
```

**Benefits**:
- ✓ Reduces disk I/O
- ✓ Faster responses for multiple concurrent requests
- ✓ Reduces CPU on parsing

**Trade-off**:
- Data may be 1 second old

### Limiting Response Size

```python
def parse_log(max_entries=20):
    """Parse log, limiting to last N entries."""
    with open('log.json', 'r') as f:
        lines = f.readlines()
    
    # Only process last max_entries
    entries = []
    for line in lines[-max_entries:]:
        entries.append(json.loads(line))
    
    return entries
```

**Benefits**:
- ✓ Smaller JSON responses (< 10 KB)
- ✓ Faster serialization
- ✓ Lower bandwidth

### Compression

```python
from flask_compress import Compress

Compress(app)  # Auto-compress responses
```

**Results**:
- 10 KB JSON → 2 KB gzip
- Network: ~80% bandwidth reduction
- Browser decompresses automatically

---

## 5. MQTT Optimization

### Subscription Pattern

```python
# Broad subscription
client.subscribe('sensors/#')  # Matches all devices

# Specific subscriptions
client.subscribe([
    ('sensors/floor-1/#', 1),  # QoS 1
    ('sensors/floor-2/#', 1),
])
```

**Trade-off**:
- Broad: Simple, but processes all messages
- Specific: More control, multiple subscriptions

### Message Filtering

```python
def on_message(client, userdata, msg):
    # Ignore certain topics
    if 'debug' in msg.topic or 'test' in msg.topic:
        return  # Skip processing
    
    # Only process telemetry
    if 'telemetry' not in msg.topic:
        return
    
    # Process message
    process_message(msg)
```

**Benefits**:
- Reduces processing load
- Cleaner data

### QoS (Quality of Service)

```python
# QoS 0: Fire and forget (fastest, least reliable)
client.subscribe('sensors/#', qos=0)

# QoS 1: At least once (balanced)
client.subscribe('sensors/#', qos=1)

# QoS 2: Exactly once (slowest, most reliable)
client.subscribe('sensors/#', qos=2)
```

**Recommendation**: Use QoS 1 for IoT sensors (balance speed and reliability)

---

## 6. System Resource Monitoring

### Memory Usage

```python
import psutil

def check_memory():
    """Monitor memory usage."""
    process = psutil.Process()
    mem_info = process.memory_info()
    mem_percent = process.memory_percent()
    
    print(f"Memory: {mem_info.rss / 1024 / 1024:.1f} MB ({mem_percent:.1f}%)")
    
    if mem_percent > 80:
        logger.warning("High memory usage!")
        # Trigger cleanup
        cleanup_old_data()

# Check periodically
threading.Timer(60, check_memory).start()
```

### CPU Usage

```python
def check_cpu():
    """Monitor CPU usage."""
    cpu_percent = psutil.Process().cpu_percent(interval=1)
    
    print(f"CPU: {cpu_percent:.1f}%")
    
    if cpu_percent > 80:
        logger.warning("High CPU usage!")
        # Reduce processing frequency
        AGGREGATION_INTERVAL = 30  # Increase from 10
```

### Disk Usage

```python
def check_disk():
    """Monitor disk space."""
    disk = psutil.disk_usage('.')
    usage_percent = disk.percent
    
    print(f"Disk: {usage_percent:.1f}%")
    
    if usage_percent > 80:
        logger.warning("Low disk space!")
        rotate_log_if_needed()
```

---

## 7. Load Testing

### Simple Load Test

```python
import concurrent.futures
import time

def publish_test_data(device_id, count=100, interval=0.1):
    """Publish test messages."""
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.connect('test.mosquitto.org', 1883)
    client.loop_start()
    
    for i in range(count):
        payload = {
            'temperature': 20 + (i % 10),
            'humidity': 45 + (i % 20),
        }
        client.publish(f'sensors/{device_id}/telemetry', json.dumps(payload))
        time.sleep(interval)
    
    client.loop_stop()

# Test with 10 devices
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    for device_id in [f'device-{i}' for i in range(10)]:
        executor.submit(publish_test_data, device_id)
```

### Measure Performance

```python
import time

start = time.time()
# Run system under load
time.sleep(60)
elapsed = time.time() - start

# Measure
with open('log.json') as f:
    entries = len(f.readlines())

throughput = entries / elapsed
print(f"Throughput: {throughput:.1f} entries/sec")
```

---

## 8. Production Deployment Checklist

```
PERFORMANCE
- [ ] Anomaly threshold tuned (test for false positives)
- [ ] History window optimized for memory
- [ ] Log rotation configured
- [ ] Caching enabled for Flask
- [ ] MQTT QoS set to 1

MONITORING
- [ ] CPU usage < 50% under normal load
- [ ] Memory usage < 500 MB
- [ ] Disk usage growing < 100 MB/day
- [ ] Message latency < 100 ms
- [ ] Error rate < 1%

SCALABILITY
- [ ] Can handle 2x current load
- [ ] Log rotation prevents disk fill
- [ ] Old data archived to external storage
- [ ] Can add devices without restart

RELIABILITY
- [ ] MQTT reconnection tested
- [ ] Log file corruption recovery tested
- [ ] Process restart tested
- [ ] Backup strategy in place
```

---

## Benchmarks

### Baseline (Reference System)

```
Hardware: Intel Core i7, 8GB RAM
Network: 10Mbps Ethernet
MQTT Broker: test.mosquitto.org

Metrics:
- Message latency: 15-25 ms
- Processing rate: 500-1000 msg/sec
- Memory usage: 150-200 MB
- CPU usage: 20-30%
- Log size: 1 GB per month
```

### Bottlenecks

| Factor | Limit | Mitigation |
|--------|-------|-----------|
| Message rate | 1000/sec | Increase aggregation interval |
| Memory | 1 GB | Reduce history window |
| Disk I/O | 100 MB/min | Batch writes, compression |
| Anomaly detection | 10000 entries | Increase z_threshold |

---

## Performance Tips

1. **Profile before optimizing**: Measure, don't guess
2. **Start with defaults**: Then tune for your workload
3. **Monitor continuously**: In production
4. **Document changes**: Keep notes on tuning
5. **Test under load**: Know your limits
6. **Plan for growth**: 2-3x headroom
7. **Use appropriate tools**: psutil, cProfile, flamegraph
8. **Balance trade-offs**: No free lunch - choose wisely

