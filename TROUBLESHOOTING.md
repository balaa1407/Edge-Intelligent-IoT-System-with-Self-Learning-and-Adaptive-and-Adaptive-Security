# Troubleshooting Guide

Common issues and solutions for the Edge IoT system.

## MQTT Connection Issues

### Problem: "Connection refused" when starting bridge.py

**Symptoms**:
```
Error: [Errno 111] Connection refused
Failed to connect to MQTT broker
```

**Causes**:
- MQTT broker not running
- Broker on different host/port than configured
- Firewall blocking connection
- Network connectivity issue

**Solutions**:

1. **Check if MQTT broker is running**:
   ```bash
   # Check if mosquitto is running
   ps aux | grep mosquitto
   
   # Or test connection
   mosquitto_sub -h test.mosquitto.org -t "test" -C 1
   ```

2. **Verify broker address in config**:
   ```python
   # Check bridge.py or config
   MQTT_BROKER = "test.mosquitto.org"  # Should be correct
   MQTT_PORT = 1883                     # Default is 1883
   ```

3. **Check network connectivity**:
   ```bash
   # Test if broker is reachable
   ping test.mosquitto.org
   telnet test.mosquitto.org 1883
   ```

4. **Start local Mosquitto broker** (if testing locally):
   ```bash
   # Install Mosquitto
   sudo apt-get install mosquitto
   
   # Start the broker
   sudo systemctl start mosquitto
   sudo systemctl status mosquitto
   ```

5. **Check firewall**:
   ```bash
   # Allow MQTT port
   sudo ufw allow 1883/tcp
   ```

---

## No Data Appearing in Dashboard

### Problem: Dashboard shows empty charts

**Symptoms**:
- Flask app starts successfully
- Dashboard loads but no data displayed
- /data endpoint returns empty arrays

**Causes**:
- No devices sending MQTT messages
- Bridge process not running
- log.json not being created/updated
- MQTT connection issues (see above)

**Solutions**:

1. **Verify bridge.py is running**:
   ```bash
   # Check if process is running
   ps aux | grep bridge.py
   
   # Or check logs
   tail -f logs/bridge.log
   ```

2. **Start bridge.py**:
   ```bash
   python bridge.py
   ```

3. **Verify log.json exists**:
   ```bash
   # Check if log file is being written
   ls -lh log.json
   
   # Watch for updates
   tail -f log.json
   ```

4. **Test with sample data**:
   ```bash
   # Publish test message
   python send_varied_data.py
   
   # Or manually with mosquitto_pub
   mosquitto_pub -h test.mosquitto.org -t "sensors/device1/telemetry" \
     -m '{"temperature": 23.5, "humidity": 45.0, "status": "OK"}'
   ```

5. **Check MQTT subscription**:
   ```bash
   # Monitor MQTT messages
   mosquitto_sub -h test.mosquitto.org -t "sensors/#"
   ```

---

## High Memory Usage

### Problem: Bridge process using excessive memory

**Symptoms**:
- Memory usage increases over time
- System becomes slow
- Process crashes with out of memory

**Causes**:
- Too many devices without cleanup
- History buffers growing without limit
- Log file getting too large

**Solutions**:

1. **Check memory usage**:
   ```bash
   # Monitor process memory
   watch -n 1 'ps aux | grep bridge.py'
   
   # Or use top
   top -p $(pgrep -f bridge.py)
   ```

2. **Reduce history size in config**:
   ```python
   "anomaly": {
       "max_history": 50,  # Reduce from 100
   }
   ```

3. **Rotate log files**:
   ```bash
   # Check log size
   ls -lh log.json*
   
   # Or restart bridge to create fresh log
   kill $(pgrep -f bridge.py)
   sleep 1
   python bridge.py &
   ```

4. **Limit number of devices**:
   ```python
   "device": {
       "max_devices": 20,  # Restrict connected devices
       "offline_timeout_seconds": 300,  # Remove idle devices
   }
   ```

5. **Implement log cleanup**:
   ```python
   # Add to bridge.py
   import os
   if os.path.getsize("log.json") > 50_000_000:  # 50 MB
       os.remove("log.json")  # Start fresh
   ```

---

## Anomalies Detected Too Frequently

### Problem: Too many false positive anomalies

**Symptoms**:
- Alert shown constantly
- Risk score always high
- Mode always WARNING or CRITICAL

**Causes**:
- Anomaly threshold too sensitive (z_threshold too low)
- Sensors are naturally noisy
- Not enough historical data

**Solutions**:

1. **Increase anomaly threshold**:
   ```python
   "anomaly": {
       "z_threshold": 3.0,  # Increase from 2.0
   }
   ```

   | Threshold | Sensitivity | Use Case |
   |-----------|------------|----------|
   | 1.0 | Very high | Lab/controlled |
   | 1.5 | High | Development |
   | 2.0 | Medium | Normal |
   | 2.5 | Low | Production |
   | 3.0+ | Very low | Noisy sensors |

2. **Increase minimum history**:
   ```python
   "anomaly": {
       "min_history": 15,  # Increase from 5
       "max_history": 100,
   }
   ```

3. **Check sensor quality**:
   ```bash
   # View raw sensor data
   mosquitto_sub -h test.mosquitto.org -t "sensors/#" | head -20
   
   # Should see consistent values, not jumping around
   ```

4. **Verify thresholds are reasonable**:
   ```python
   "temperature": {
       "min_normal": 18.0,  # Check these are realistic
       "max_normal": 28.0,
   }
   ```

---

## Flask App Not Loading Dashboard

### Problem: 404 error or blank page when accessing http://localhost:5000

**Symptoms**:
- Error 404 Not Found
- Blank page loads
- Console shows errors

**Causes**:
- Flask app not running
- index.html missing from templates directory
- Wrong port configured

**Solutions**:

1. **Check if Flask app is running**:
   ```bash
   # Verify process
   ps aux | grep app.py
   
   # Or start it
   python app.py
   ```

2. **Verify index.html exists**:
   ```bash
   # Should exist
   ls -l templates/index.html
   
   # Should not be empty
   wc -l templates/index.html
   ```

3. **Check Flask logs**:
   ```bash
   # Flask should print to console
   python app.py
   
   # Look for errors like:
   # - "Error loading 'templates/index.html'" 
   # - "Template file not found"
   ```

4. **Try different port if 5000 is in use**:
   ```bash
   # Check if port is in use
   lsof -i :5000
   
   # Kill other process
   kill -9 <PID>
   
   # Or modify app.py
   # app.run(debug=True, port=5001)  # Use different port
   ```

---

## Dashboard Updates Slow or Stalled

### Problem: Dashboard charts freeze or update very slowly

**Symptoms**:
- Dashboard loads but doesn't update
- Network tab shows stalled requests
- CPU not spiking

**Causes**:
- Log file locked by bridge process
- Network latency
- Server overload
- Browser cache issue

**Solutions**:

1. **Check network requests**:
   ```bash
   # Open browser developer tools (F12)
   # Network tab -> watch /data requests
   # Should see 200 response every 3 seconds
   ```

2. **Check log file is accessible**:
   ```bash
   # Verify file is readable
   tail -f log.json
   
   # Check permissions
   ls -l log.json
   # Should have read permission for your user
   ```

3. **Force browser refresh**:
   ```bash
   # Hard refresh
   Ctrl+Shift+R (or Cmd+Shift+R on Mac)
   # Clears cache and reloads
   ```

4. **Restart both services**:
   ```bash
   # Kill all processes
   pkill -f bridge.py
   pkill -f app.py
   
   # Start fresh
   python bridge.py &
   python app.py &
   ```

5. **Check server logs**:
   ```bash
   # Terminal running app.py should show requests
   # Should see "GET /data 200" every 3 seconds
   ```

---

## Temperature/Humidity Values Seem Wrong

### Problem: Readings don't match actual conditions

**Symptoms**:
- Extreme values (e.g., -500°C)
- Values stuck at 0
- Not matching other thermometers

**Causes**:
- Sensor malfunction
- Bad calibration
- Wrong topic being monitored
- Data transmission error

**Solutions**:

1. **Verify sensor is working**:
   ```bash
   # Check raw MQTT messages
   mosquitto_sub -h test.mosquitto.org -t "sensors/#"
   
   # Should see temperature field
   # {"temperature": 23.5, "humidity": 45.0}
   ```

2. **Check sensor topic**:
   ```bash
   # Verify bridge subscribes to correct topic
   grep "base_topic" config.py
   
   # Should match what device publishes to
   ```

3. **Validate sensor readings in code**:
   ```python
   # In bridge.py, add debug logging
   if not (0 <= temperature <= 100):
       print(f"WARNING: Temperature out of range: {temperature}")
   ```

4. **Test with known good values**:
   ```bash
   # Publish test values manually
   mosquitto_pub -h test.mosquitto.org -t "sensors/test-device/telemetry" \
     -m '{"temperature": 25.0, "humidity": 50.0, "status": "OK"}'
   ```

5. **Check sensor calibration**:
   ```python
   # Add calibration offset if sensor is consistently off
   calibration = {
       "temperature_offset": -2.0,  # Sensor reads 2°C too high
       "humidity_offset": 5.0,
   }
   ```

---

## Common Error Messages

### "JSON Decode Error"

```
json.JSONDecodeError: Expecting value: line 1 column 1
```

**Meaning**: Received non-JSON MQTT message

**Fix**: Ensure device sends valid JSON:
```json
{"temperature": 23.5, "humidity": 45.0, "status": "OK"}
```

### "Key Error: 'temperature'"

```
KeyError: 'temperature'
```

**Meaning**: MQTT message missing required field

**Fix**: Device must include all required fields

### "Connection timeout"

```
socket.timeout: _ssl.c:1001: The handshake operation timed out
```

**Meaning**: MQTT broker not responding

**Fix**: Check network, verify broker address, increase timeout

---

## Health Check Commands

Quick commands to verify system is working:

```bash
# 1. Check all processes running
ps aux | grep -E "(bridge|app)\.py"

# 2. Check MQTT broker reachable
mosquitto_pub -h test.mosquitto.org -t "test/ping" -m "ping"

# 3. Check log file being updated
watch -n 1 'ls -lh log.json'

# 4. Check Flask responding
curl http://localhost:5000/health | python -m json.tool

# 5. Check /data endpoint
curl http://localhost:5000/data | python -m json.tool | head -20

# 6. Monitor bridges logs in real time
tail -f logs/bridge.log | grep -E "(ERROR|WARNING|CRITICAL)"

# 7. Check temperature readings
tail -f log.json | python -m json.tool | grep temperature | head -5

# 8. Test MQTT subscription
mosquitto_sub -h test.mosquitto.org -t "sensors/#" -C 5
```

---

## Getting Help

If you can't find the solution here:

1. **Check logs**:
   ```bash
   cat logs/bridge.log
   cat logs/app.log
   ```

2. **Run diagnostic script**:
   ```bash
   python -c "
   import json
   try:
       with open('log.json') as f:
           lines = f.readlines()
           print(f'Log file: {len(lines)} entries')
           latest = json.loads(lines[-1])
           print(f'Latest: {latest}')
   except Exception as e:
       print(f'Error: {e}')
   "
   ```

3. **Check system resources**:
   ```bash
   # CPU and memory
   top -b -n 1 | head -20
   
   # Disk space
   df -h
   
   # Network connections
   netstat -an | grep :1883
   ```

4. **Enable debug logging**:
   ```python
   # In bridge.py
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```
