"""
Testing utilities for the Edge IoT system.

Provides helper functions and test data for unit testing
and integration testing of the system.
"""

from typing import Dict, List, Any
from datetime import datetime, timezone, timedelta
import random
import json


class TestDataGenerator:
    """Generate realistic test data for testing."""
    
    @staticmethod
    def generate_sensor_reading(
        device_id: str,
        temperature: float = None,
        humidity: float = None,
    ) -> Dict[str, Any]:
        """
        Generate a realistic sensor reading payload.
        
        Args:
            device_id: Device identifier
            temperature: Temperature value (if None, random 15-35°C)
            humidity: Humidity value (if None, random 30-80%)
            
        Returns:
            Sensor reading dictionary ready for MQTT publish
        """
        if temperature is None:
            temperature = round(random.uniform(15, 35), 1)
        if humidity is None:
            humidity = round(random.uniform(30, 80), 1)
        
        return {
            "device_id": device_id,
            "temperature": temperature,
            "humidity": humidity,
            "status": "OK",
            "uptime": random.randint(3600, 86400 * 30),  # 1 hour to 30 days
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    
    @staticmethod
    def generate_anomalous_reading(device_id: str) -> Dict[str, Any]:
        """
        Generate a reading with anomalous values.
        
        Useful for testing anomaly detection.
        
        Args:
            device_id: Device identifier
            
        Returns:
            Sensor reading with extreme values
        """
        return {
            "device_id": device_id,
            "temperature": round(random.choice([
                random.uniform(-10, 5),    # Too cold
                random.uniform(55, 75),    # Too hot
            ]), 1),
            "humidity": round(random.choice([
                random.uniform(0, 5),      # Too dry
                random.uniform(95, 100),   # Too wet
            ]), 1),
            "status": "WARNING",
            "uptime": random.randint(3600, 86400),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    
    @staticmethod
    def generate_offline_status(device_id: str) -> Dict[str, Any]:
        """
        Generate a Last Will Testament (offline) message.
        
        Args:
            device_id: Device identifier
            
        Returns:
            Offline status message
        """
        return {
            "device_id": device_id,
            "status": "OFFLINE",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


class MockDeviceState:
    """Mock DeviceState for testing without real devices."""
    
    def __init__(self, device_id: str):
        """Initialize mock device state."""
        self.device_id = device_id
        self.temp_hist = []
        self.humi_hist = []
        self.last_seen = datetime.now(timezone.utc)
        self.online = True
        self.latest = {}
    
    def add_reading(self, temperature: float, humidity: float) -> None:
        """Add a reading to history."""
        self.latest = {
            "temperature": temperature,
            "humidity": humidity,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.temp_hist.append(temperature)
        self.humi_hist.append(humidity)
        # Keep last 20
        if len(self.temp_hist) > 20:
            self.temp_hist.pop(0)
        if len(self.humi_hist) > 20:
            self.humi_hist.pop(0)
    
    def is_temp_anomaly(self) -> bool:
        """Mock anomaly detection."""
        if len(self.temp_hist) < 5:
            return False
        mean = sum(self.temp_hist) / len(self.temp_hist)
        latest = self.temp_hist[-1]
        return abs(latest - mean) > 10  # Simple threshold


class AssertionHelpers:
    """Helper functions for test assertions."""
    
    @staticmethod
    def assert_valid_json(text: str) -> None:
        """Assert that text is valid JSON."""
        try:
            json.loads(text)
        except json.JSONDecodeError as e:
            raise AssertionError(f"Invalid JSON: {e}")
    
    @staticmethod
    def assert_sensor_reading(data: Dict[str, Any]) -> None:
        """Assert that data is valid sensor reading."""
        required_fields = ["device_id", "temperature", "humidity", "timestamp"]
        for field in required_fields:
            if field not in data:
                raise AssertionError(f"Missing required field: {field}")
        
        if not isinstance(data["temperature"], (int, float)):
            raise AssertionError("Temperature must be numeric")
        if not isinstance(data["humidity"], (int, float)):
            raise AssertionError("Humidity must be numeric")
    
    @staticmethod
    def assert_risk_score(score: int) -> None:
        """Assert that risk score is in valid range."""
        if not isinstance(score, int) or score < 0 or score > 10:
            raise AssertionError(f"Risk score must be 0-10, got {score}")
    
    @staticmethod
    def assert_response_structure(response: Dict[str, Any]) -> None:
        """Assert that API response has correct structure."""
        required_keys = ["success", "data", "timestamp"]
        for key in required_keys:
            if key not in response:
                raise AssertionError(f"Response missing key: {key}")


class TestDatasets:
    """Pre-built datasets for testing."""
    
    NORMAL_CONDITIONS = [
        {"temperature": 22.0, "humidity": 45.0},
        {"temperature": 23.5, "humidity": 47.0},
        {"temperature": 21.5, "humidity": 44.0},
        {"temperature": 22.8, "humidity": 46.0},
        {"temperature": 23.0, "humidity": 45.5},
    ]
    
    ANOMALOUS_CONDITIONS = [
        {"temperature": 5.0, "humidity": 20.0},    # Too cold and dry
        {"temperature": 65.0, "humidity": 95.0},   # Too hot and humid
        {"temperature": -5.0, "humidity": 10.0},   # Extreme cold
        {"temperature": 75.0, "humidity": 100.0},  # Extreme heat
    ]
    
    WARNING_CONDITIONS = [
        {"temperature": 35.0, "humidity": 75.0},   # High temp and humidity
        {"temperature": 10.0, "humidity": 20.0},   # Low temp and humidity
        {"temperature": 40.0, "humidity": 80.0},   # Critical temp
    ]
    
    @staticmethod
    def get_realistic_sequence(hours: int = 24, anomaly_at: int = None) -> List[Dict[str, float]]:
        """
        Generate a realistic temperature sequence over time.
        
        Simulates typical daily temperature variation with optional anomaly.
        
        Args:
            hours: Number of hours to simulate
            anomaly_at: Hour at which to inject anomaly (None = no anomaly)
            
        Returns:
            List of temperature readings
        """
        readings = []
        base_temp = 22.0
        
        for hour in range(hours):
            # Simulate daily cycle (cooler at night, warmer during day)
            time_factor = (hour % 24) / 24.0  # 0-1
            cycle_variation = 5.0 * (1 - abs(time_factor - 0.5) * 2)  # -5 to +5
            
            # Add random variation
            noise = random.uniform(-1, 1)
            
            temp = base_temp + cycle_variation + noise
            humidity = 45 + random.uniform(-5, 5)
            
            # Inject anomaly if specified
            if anomaly_at is not None and hour == anomaly_at:
                temp = 60.0  # Extreme value
                humidity = 90.0
            
            readings.append({
                "temperature": round(temp, 1),
                "humidity": round(humidity, 1),
            })
        
        return readings
