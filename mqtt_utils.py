"""
MQTT utilities for simplified broker communication.

Provides wrapper functions for common MQTT operations.
"""

from typing import Dict, Any, Optional, Callable
import paho.mqtt.client as mqtt
import json
import logging


class MQTTPublisher:
    """Simple MQTT publisher wrapper."""
    
    def __init__(self, broker: str, port: int = 1883):
        """
        Initialize MQTT publisher.
        
        Args:
            broker: MQTT broker hostname/IP
            port: MQTT broker port (default 1883)
        """
        self.broker = broker
        self.port = port
        self.client = None
    
    def connect(self) -> bool:
        """
        Connect to MQTT broker.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
            self.client.connect(self.broker, self.port, keepalive=60)
            self.client.loop_start()
            return True
        except Exception as e:
            logging.error(f"Failed to connect to MQTT: {e}")
            return False
    
    def publish(self, topic: str, payload: Dict[str, Any], retain: bool = False) -> bool:
        """
        Publish message to MQTT topic.
        
        Args:
            topic: MQTT topic to publish to
            payload: Dictionary to publish as JSON
            retain: Whether to retain the message
            
        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            logging.error("MQTT client not connected")
            return False
        
        try:
            json_payload = json.dumps(payload)
            self.client.publish(topic, json_payload, retain=retain)
            return True
        except Exception as e:
            logging.error(f"Failed to publish to {topic}: {e}")
            return False
    
    def disconnect(self) -> None:
        """Disconnect from MQTT broker."""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()


class MQTTTopic:
    """MQTT topic builder with validation."""
    
    @staticmethod
    def build_device_telemetry(device_id: str, base_path: str = "edgeiot") -> str:
        """
        Build MQTT topic for device telemetry.
        
        Args:
            device_id: Device identifier
            base_path: Base topic path (default "edgeiot")
            
        Returns:
            Topic string like "edgeiot/device_id/telemetry"
        """
        return f"{base_path}/{device_id}/telemetry"
    
    @staticmethod
    def build_device_status(device_id: str, base_path: str = "edgeiot") -> str:
        """
        Build MQTT topic for device status.
        
        Args:
            device_id: Device identifier
            base_path: Base topic path
            
        Returns:
            Topic string like "edgeiot/device_id/status"
        """
        return f"{base_path}/{device_id}/status"
    
    @staticmethod
    def build_subscription(base_path: str = "edgeiot", device_id: str = None) -> str:
        """
        Build subscription topic with wildcards.
        
        Args:
            base_path: Base topic path
            device_id: Specific device ID (if None, uses wildcard)
            
        Returns:
            Topic filter string for subscription
        """
        if device_id:
            return f"{base_path}/{device_id}/#"
        else:
            return f"{base_path}/#"
    
    @staticmethod
    def parse_topic(topic: str) -> Dict[str, str]:
        """
        Parse MQTT topic into components.
        
        Args:
            topic: MQTT topic string
            
        Returns:
            Dictionary with parsed components
        """
        parts = topic.split("/")
        
        return {
            "base": parts[0] if len(parts) > 0 else None,
            "device_id": parts[1] if len(parts) > 1 else None,
            "subtopic": parts[2] if len(parts) > 2 else None,
            "full_topic": topic,
        }


def create_mqtt_client(
    client_id: str,
    on_connect: Optional[Callable] = None,
    on_disconnect: Optional[Callable] = None,
    on_message: Optional[Callable] = None,
) -> mqtt.Client:
    """
    Create and configure an MQTT client.
    
    Args:
        client_id: Unique client identifier
        on_connect: Callback for connection events
        on_disconnect: Callback for disconnection events
        on_message: Callback for incoming messages
        
    Returns:
        Configured mqtt.Client instance
    """
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
    
    if on_connect:
        client.on_connect = on_connect
    if on_disconnect:
        client.on_disconnect = on_disconnect
    if on_message:
        client.on_message = on_message
    
    return client


def validate_mqtt_payload(payload: str) -> bool:
    """
    Validate that payload is valid JSON.
    
    Args:
        payload: Payload string to validate
        
    Returns:
        True if valid JSON, False otherwise
    """
    try:
        json.loads(payload)
        return True
    except (json.JSONDecodeError, ValueError):
        return False


def extract_json_payload(payload_str: str) -> Optional[Dict[str, Any]]:
    """
    Safely extract JSON from MQTT payload.
    
    Args:
        payload_str: Payload string
        
    Returns:
        Parsed JSON dictionary, or None if invalid
    """
    try:
        return json.loads(payload_str)
    except (json.JSONDecodeError, ValueError):
        return None
