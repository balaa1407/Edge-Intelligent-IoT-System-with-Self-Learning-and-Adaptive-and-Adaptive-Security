"""
Command-line interface for testing and managing the Edge IoT system.

Provides utilities for testing MQTT connections, publishing data,
and monitoring system health.
"""

import argparse
import json
import time
from typing import Dict, Any
import paho.mqtt.client as mqtt


class EdgeIoTCLI:
    """Command-line interface for Edge IoT system."""
    
    def __init__(self, broker: str = "test.mosquitto.org", port: int = 1883):
        """Initialize CLI with MQTT broker settings."""
        self.broker = broker
        self.port = port
        self.client = None
    
    def test_mqtt_connection(self) -> bool:
        """
        Test connection to MQTT broker.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="test-cli")
            client.connect(self.broker, self.port, keepalive=5)
            client.loop_start()
            
            time.sleep(1)
            
            client.loop_stop()
            client.disconnect()
            
            print(f"✓ Successfully connected to {self.broker}:{self.port}")
            return True
        except Exception as e:
            print(f"✗ Failed to connect to {self.broker}:{self.port}")
            print(f"  Error: {e}")
            return False
    
    def publish_test_data(self, device_id: str, count: int = 5, interval: float = 1.0) -> bool:
        """
        Publish test sensor data to MQTT broker.
        
        Args:
            device_id: Device identifier
            count: Number of messages to publish
            interval: Interval between messages in seconds
            
        Returns:
            True if successful
        """
        def on_connect(client, userdata, connect_flags, rc, properties=None):
            if rc == 0:
                print(f"Connected to broker")
        
        try:
            self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"pub-{device_id}")
            self.client.on_connect = on_connect
            self.client.connect(self.broker, self.port, keepalive=60)
            self.client.loop_start()
            
            base_temp = 22.0
            base_humidity = 45.0
            
            for i in range(count):
                temperature = base_temp + (i * 0.5)
                humidity = base_humidity + (i * 1.0)
                
                payload = {
                    "device_id": device_id,
                    "temperature": round(temperature, 1),
                    "humidity": round(humidity, 1),
                    "status": "OK",
                    "uptime": i * interval,
                }
                
                topic = f"sensors/{device_id}/telemetry"
                self.client.publish(topic, json.dumps(payload))
                print(f"Published ({i+1}/{count}): {payload}")
                
                if i < count - 1:
                    time.sleep(interval)
            
            self.client.loop_stop()
            self.client.disconnect()
            
            print(f"✓ Successfully published {count} test messages")
            return True
        except Exception as e:
            print(f"✗ Failed to publish test data: {e}")
            return False
    
    def subscribe_to_topic(self, topic: str, timeout: float = 10.0) -> bool:
        """
        Subscribe to MQTT topic and listen for messages.
        
        Args:
            topic: MQTT topic to subscribe to
            timeout: Timeout in seconds
            
        Returns:
            True if received at least one message
        """
        message_count = 0
        
        def on_connect(client, userdata, connect_flags, rc, properties=None):
            if rc == 0:
                print(f"Connected to broker")
                client.subscribe(topic)
        
        def on_message(client, userdata, msg):
            nonlocal message_count
            message_count += 1
            print(f"Received ({message_count}): {msg.payload.decode()}")
        
        try:
            self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="sub-cli")
            self.client.on_connect = on_connect
            self.client.on_message = on_message
            self.client.connect(self.broker, self.port, keepalive=60)
            self.client.loop_start()
            
            print(f"Listening to {topic} for {timeout} seconds...")
            time.sleep(timeout)
            
            self.client.loop_stop()
            self.client.disconnect()
            
            if message_count > 0:
                print(f"✓ Received {message_count} messages")
                return True
            else:
                print(f"✗ No messages received")
                return False
        except Exception as e:
            print(f"✗ Failed to subscribe: {e}")
            return False
    
    def validate_log_file(self, filename: str = "log.json") -> bool:
        """
        Validate log.json file structure.
        
        Args:
            filename: Path to log file
            
        Returns:
            True if valid
        """
        try:
            with open(filename, 'r') as f:
                lines = f.readlines()
            
            print(f"Log file has {len(lines)} entries")
            
            valid_count = 0
            invalid_count = 0
            
            for i, line in enumerate(lines):
                try:
                    entry = json.loads(line.strip())
                    valid_count += 1
                    
                    # Check required fields
                    required = ['timestamp', 'temperature', 'humidity']
                    missing = [f for f in required if f not in entry]
                    
                    if missing:
                        print(f"  Entry {i}: Missing fields {missing}")
                except json.JSONDecodeError:
                    invalid_count += 1
                    print(f"  Entry {i}: Invalid JSON")
            
            print(f"✓ Valid entries: {valid_count}")
            if invalid_count > 0:
                print(f"✗ Invalid entries: {invalid_count}")
            
            return invalid_count == 0
        except FileNotFoundError:
            print(f"✗ File not found: {filename}")
            return False
        except Exception as e:
            print(f"✗ Error validating log file: {e}")
            return False
    
    def show_log_summary(self, filename: str = "log.json") -> bool:
        """
        Show summary statistics from log file.
        
        Args:
            filename: Path to log file
            
        Returns:
            True if successful
        """
        try:
            temperatures = []
            humidities = []
            risks = []
            
            with open(filename, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        if 'temperature' in entry:
                            temperatures.append(entry['temperature'])
                        if 'humidity' in entry:
                            humidities.append(entry['humidity'])
                        if 'risk' in entry:
                            risks.append(entry['risk'])
                    except json.JSONDecodeError:
                        pass
            
            if not temperatures:
                print(f"✗ No data in log file")
                return False
            
            print(f"\nLog File Summary:")
            print(f"  Total entries: {len(temperatures)}")
            
            print(f"\nTemperature (°C):")
            print(f"  Min: {min(temperatures):.1f}")
            print(f"  Max: {max(temperatures):.1f}")
            print(f"  Avg: {sum(temperatures)/len(temperatures):.1f}")
            
            if humidities:
                print(f"\nHumidity (%):")
                print(f"  Min: {min(humidities):.1f}")
                print(f"  Max: {max(humidities):.1f}")
                print(f"  Avg: {sum(humidities)/len(humidities):.1f}")
            
            if risks:
                print(f"\nRisk Score (0-10):")
                print(f"  Min: {min(risks)}")
                print(f"  Max: {max(risks)}")
                print(f"  Avg: {sum(risks)/len(risks):.1f}")
            
            return True
        except Exception as e:
            print(f"✗ Error reading log file: {e}")
            return False


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Edge IoT System Command-Line Interface"
    )
    
    parser.add_argument(
        '--broker',
        default='test.mosquitto.org',
        help='MQTT broker address (default: test.mosquitto.org)'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=1883,
        help='MQTT broker port (default: 1883)'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # test-mqtt command
    subparsers.add_parser(
        'test-mqtt',
        help='Test MQTT broker connection'
    )
    
    # publish command
    pub_parser = subparsers.add_parser(
        'publish',
        help='Publish test data'
    )
    pub_parser.add_argument('device_id', help='Device identifier')
    pub_parser.add_argument('--count', type=int, default=5, help='Number of messages')
    pub_parser.add_argument('--interval', type=float, default=1.0, help='Interval between messages')
    
    # subscribe command
    sub_parser = subparsers.add_parser(
        'subscribe',
        help='Subscribe to MQTT topic'
    )
    sub_parser.add_argument('topic', help='MQTT topic to subscribe to')
    sub_parser.add_argument('--timeout', type=float, default=10.0, help='Timeout in seconds')
    
    # validate command
    subparsers.add_parser(
        'validate',
        help='Validate log.json file'
    )
    
    # summary command
    subparsers.add_parser(
        'summary',
        help='Show log file summary'
    )
    
    args = parser.parse_args()
    
    cli = EdgeIoTCLI(broker=args.broker, port=args.port)
    
    if args.command == 'test-mqtt':
        cli.test_mqtt_connection()
    elif args.command == 'publish':
        cli.publish_test_data(args.device_id, args.count, args.interval)
    elif args.command == 'subscribe':
        cli.subscribe_to_topic(args.topic, args.timeout)
    elif args.command == 'validate':
        cli.validate_log_file()
    elif args.command == 'summary':
        cli.show_log_summary()
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
