"""
Example usage patterns for the Edge IoT system.

Demonstrates how to use the library components in real scenarios.
"""

import json
import time
from typing import Dict, Any
import paho.mqtt.client as mqtt
from datetime import datetime, timezone


# ============================================================================
# Example 1: Basic MQTT Publisher
# ============================================================================

def example_publish_sensor_data():
    """
    Example: Publish sensor data to MQTT broker.
    
    This demonstrates how a sensor device would publish data.
    """
    
    def on_connect(client, userdata, connect_flags, rc, properties=None):
        """Callback when client connects."""
        if rc == 0:
            print("Connected to MQTT broker")
        else:
            print(f"Connection failed with code {rc}")
    
    def on_disconnect(client, userdata, disconnect_flags, rc, properties=None):
        """Callback when client disconnects."""
        print("Disconnected from MQTT broker")
    
    # Create MQTT client
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="sensor-demo")
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    
    # Connect to broker
    client.connect("test.mosquitto.org", 1883, keepalive=60)
    client.loop_start()
    
    # Publish sample readings
    for i in range(5):
        sensor_data = {
            "device_id": "sensor-demo",
            "temperature": 20.0 + (i * 0.5),
            "humidity": 45.0 + (i * 2),
            "status": "OK",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        topic = "edgeiot/sensor-demo/telemetry"
        client.publish(topic, json.dumps(sensor_data))
        print(f"Published: {sensor_data}")
        
        time.sleep(1)
    
    client.loop_stop()
    client.disconnect()


# ============================================================================
# Example 2: Reading and Processing Log Data
# ============================================================================

def example_read_log_data():
    """
    Example: Read and process data from log.json file.
    
    This demonstrates how to parse and analyze logged sensor data.
    """
    
    log_entries = []
    
    try:
        with open('log.json', 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    log_entries.append(entry)
                except json.JSONDecodeError:
                    continue
    except FileNotFoundError:
        print("log.json not found")
        return
    
    if not log_entries:
        print("No data in log.json")
        return
    
    # Extract temperature readings
    temperatures = [e.get('temperature', 0) for e in log_entries if 'temperature' in e]
    humidities = [e.get('humidity', 0) for e in log_entries if 'humidity' in e]
    
    # Calculate statistics
    if temperatures:
        print(f"Temperature Statistics:")
        print(f"  Count: {len(temperatures)}")
        print(f"  Min: {min(temperatures):.1f}°C")
        print(f"  Max: {max(temperatures):.1f}°C")
        print(f"  Avg: {sum(temperatures)/len(temperatures):.1f}°C")
    
    if humidities:
        print(f"Humidity Statistics:")
        print(f"  Count: {len(humidities)}")
        print(f"  Min: {min(humidities):.1f}%")
        print(f"  Max: {max(humidities):.1f}%")
        print(f"  Avg: {sum(humidities)/len(humidities):.1f}%")


# ============================================================================
# Example 3: Detect Anomalies Using Z-Score
# ============================================================================

def example_detect_anomalies():
    """
    Example: Detect anomalies in temperature data using z-score method.
    
    Z-score measures how many standard deviations away from the mean.
    Values with |z-score| > 2 are considered anomalies.
    """
    
    # Sample temperature data
    temperatures = [22.1, 22.3, 21.9, 23.0, 22.2, 52.5, 22.4, 21.8]
    
    # Calculate mean and standard deviation
    mean = sum(temperatures) / len(temperatures)
    variance = sum((x - mean) ** 2 for x in temperatures) / len(temperatures)
    std_dev = variance ** 0.5
    
    # Calculate z-scores
    threshold = 2.0
    anomalies = []
    
    for i, temp in enumerate(temperatures):
        if std_dev > 0:
            z_score = abs((temp - mean) / std_dev)
            if z_score > threshold:
                anomalies.append({
                    "index": i,
                    "value": temp,
                    "z_score": z_score,
                    "is_anomaly": True,
                })
                print(f"Anomaly detected at index {i}: {temp}°C (z-score: {z_score:.2f})")
    
    print(f"Found {len(anomalies)} anomalies out of {len(temperatures)} readings")


# ============================================================================
# Example 4: Risk Scoring
# ============================================================================

def example_risk_scoring():
    """
    Example: Calculate risk score based on sensor readings.
    
    Risk score combines multiple factors:
    - Temperature out of range
    - Humidity out of range
    - Anomaly detection
    - Overall system state
    """
    
    # Configuration
    config = {
        "temp_normal": (18.0, 28.0),  # Min, Max
        "humidity_normal": (30.0, 70.0),
        "anomaly_threshold": 2.0,
    }
    
    # Sensor reading
    reading = {
        "temperature": 35.0,  # High temperature
        "humidity": 45.0,     # Normal humidity
        "is_anomaly": False,  # Not an anomaly
    }
    
    risk_score = 0
    reasons = []
    
    # Check temperature
    if reading["temperature"] < config["temp_normal"][0]:
        risk_score += 3
        reasons.append("Temperature too low")
    elif reading["temperature"] > config["temp_normal"][1]:
        risk_score += 3
        reasons.append("Temperature too high")
    
    # Check humidity
    if reading["humidity"] < config["humidity_normal"][0]:
        risk_score += 2
        reasons.append("Humidity too low")
    elif reading["humidity"] > config["humidity_normal"][1]:
        risk_score += 2
        reasons.append("Humidity too high")
    
    # Check anomaly
    if reading.get("is_anomaly"):
        risk_score += 4
        reasons.append("Anomalous value detected")
    
    # Clamp to 0-10
    risk_score = min(risk_score, 10)
    
    # Determine mode
    if risk_score >= 7:
        mode = "CRITICAL"
    elif risk_score >= 4:
        mode = "WARNING"
    else:
        mode = "NORMAL"
    
    print(f"Risk Score: {risk_score}/10")
    print(f"Mode: {mode}")
    print(f"Reasons: {', '.join(reasons)}")


# ============================================================================
# Example 5: Data Export
# ============================================================================

def example_export_data():
    """
    Example: Export sensor data to CSV for spreadsheet analysis.
    """
    
    import csv
    
    # Read log data
    log_entries = []
    try:
        with open('log.json', 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    log_entries.append(entry)
                except json.JSONDecodeError:
                    continue
    except FileNotFoundError:
        print("log.json not found")
        return
    
    # Export to CSV
    try:
        with open('sensor_data.csv', 'w', newline='') as f:
            if log_entries:
                fieldnames = ['timestamp', 'temperature', 'humidity', 'risk', 'mode']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for entry in log_entries:
                    writer.writerow({
                        'timestamp': entry.get('timestamp', ''),
                        'temperature': entry.get('temperature', ''),
                        'humidity': entry.get('humidity', ''),
                        'risk': entry.get('risk', ''),
                        'mode': entry.get('mode', ''),
                    })
        
        print(f"Exported {len(log_entries)} records to sensor_data.csv")
    except Exception as e:
        print(f"Error exporting: {e}")


# ============================================================================
# Example 6: Real-time Monitoring
# ============================================================================

def example_real_time_monitoring():
    """
    Example: Monitor sensor data in real-time via MQTT.
    
    This simulates a monitoring application that listens for
    sensor updates and prints alerts.
    """
    
    class MonitoringApp:
        """Simple monitoring application."""
        
        def __init__(self, broker: str):
            self.broker = broker
            self.client = None
            self.device_count = 0
        
        def on_connect(self, client, userdata, connect_flags, rc, properties=None):
            """Handle connection."""
            if rc == 0:
                print(f"Monitor connected to {self.broker}")
                client.subscribe("edgeiot/#")
            else:
                print(f"Connection failed: {rc}")
        
        def on_message(self, client, userdata, msg):
            """Handle incoming message."""
            try:
                payload = json.loads(msg.payload.decode())
                
                # Check for alerts
                if payload.get('mode') == 'CRITICAL':
                    print(f"⚠️  ALERT: Critical condition from {payload.get('device_id')}")
                    print(f"   Temperature: {payload.get('temperature')}°C")
                    print(f"   Risk: {payload.get('risk')}/10")
                
                # Count devices
                if payload.get('status') == 'ONLINE':
                    self.device_count += 1
                
            except json.JSONDecodeError:
                pass
        
        def start(self):
            """Start monitoring."""
            self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="monitor")
            self.client.on_connect = self.on_connect
            self.client.on_message = self.on_message
            
            self.client.connect(self.broker, 1883, keepalive=60)
            self.client.loop_start()
        
        def stop(self):
            """Stop monitoring."""
            if self.client:
                self.client.loop_stop()
                self.client.disconnect()
    
    # Create and run monitor
    monitor = MonitoringApp("test.mosquitto.org")
    monitor.start()
    
    print("Monitoring... (running for 30 seconds)")
    time.sleep(30)
    
    monitor.stop()
    print(f"Monitored {monitor.device_count} device updates")


# ============================================================================
# Run Examples
# ============================================================================

if __name__ == "__main__":
    print("Edge IoT System - Usage Examples\n")
    
    print("=" * 60)
    print("Example 1: Reading Log Data")
    print("=" * 60)
    example_read_log_data()
    
    print("\n" + "=" * 60)
    print("Example 3: Detect Anomalies")
    print("=" * 60)
    example_detect_anomalies()
    
    print("\n" + "=" * 60)
    print("Example 4: Risk Scoring")
    print("=" * 60)
    example_risk_scoring()
    
    print("\n" + "=" * 60)
    print("Example 5: Export Data to CSV")
    print("=" * 60)
    example_export_data()
    
    print("\nNote: Examples 1, 2, and 6 require running systems")
    print("  - Example 1 requires MQTT broker")
    print("  - Example 2 requires bridge.py logging data")
    print("  - Example 6 requires MQTT broker and active devices")
