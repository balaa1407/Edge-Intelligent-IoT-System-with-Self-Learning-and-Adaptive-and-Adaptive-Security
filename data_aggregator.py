"""
Data aggregation utilities for the Edge IoT system.

This module provides functions for aggregating sensor data from multiple
devices and performing statistical calculations on sensor readings.
"""

from typing import Dict, List, Any, Optional
from collections import deque


class DataAggregator:
    """
    Aggregates sensor data from multiple devices.
    
    Provides methods to calculate averages, find extreme values,
    and generate summary statistics from device readings.
    """
    
    @staticmethod
    def calculate_system_averages(
        devices: Dict[str, Any]
    ) -> Dict[str, Optional[float]]:
        """
        Calculate system-wide averages from all online devices.
        
        Safely handles:
        - Devices with missing data
        - Empty device list
        - Invalid sensor readings
        
        Args:
            devices: Dictionary mapping device_id to DeviceState objects
            
        Returns:
            Dictionary with "temperature" and "humidity" keys,
            values are averages or None if no valid data
        """
        # Collect all valid temperature and humidity readings
        temperatures = []
        humidity_readings = []
        
        for device in devices.values():
            # Skip if device doesn't have latest data
            if not hasattr(device, 'latest') or not device.latest:
                continue
            
            # Safely extract temperature
            if 'temperature' in device.latest:
                try:
                    temp = float(device.latest['temperature'])
                    temperatures.append(temp)
                except (ValueError, TypeError):
                    pass  # Skip invalid values
            
            # Safely extract humidity
            if 'humidity' in device.latest:
                try:
                    humi = float(device.latest['humidity'])
                    humidity_readings.append(humi)
                except (ValueError, TypeError):
                    pass  # Skip invalid values
        
        # Calculate averages with None if no data
        avg_temp = None
        if temperatures:
            avg_temp = round(sum(temperatures) / len(temperatures), 2)
        
        avg_humi = None
        if humidity_readings:
            avg_humi = round(sum(humidity_readings) / len(humidity_readings), 2)
        
        return {
            "temperature": avg_temp,
            "humidity": avg_humi,
        }
    
    @staticmethod
    def find_extremes(
        devices: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Find highest and lowest sensor readings across all devices.
        
        Useful for understanding the range of conditions across system.
        
        Args:
            devices: Dictionary of DeviceState objects
            
        Returns:
            Dictionary with max/min temps and humidities:
            {
                "temperature": {"max": 35.2, "min": 18.5, ...},
                "humidity": {"max": 75.0, "min": 30.0, ...}
            }
        """
        result = {
            "temperature": {
                "max": None,
                "max_device": None,
                "min": None,
                "min_device": None,
            },
            "humidity": {
                "max": None,
                "max_device": None,
                "min": None,
                "min_device": None,
            },
        }
        
        for device_id, device in devices.items():
            if not device.latest:
                continue
            
            # Temperature extremes
            if 'temperature' in device.latest:
                try:
                    temp = float(device.latest['temperature'])
                    if result["temperature"]["max"] is None or temp > result["temperature"]["max"]:
                        result["temperature"]["max"] = temp
                        result["temperature"]["max_device"] = device_id
                    if result["temperature"]["min"] is None or temp < result["temperature"]["min"]:
                        result["temperature"]["min"] = temp
                        result["temperature"]["min_device"] = device_id
                except (ValueError, TypeError):
                    pass
            
            # Humidity extremes
            if 'humidity' in device.latest:
                try:
                    humi = float(device.latest['humidity'])
                    if result["humidity"]["max"] is None or humi > result["humidity"]["max"]:
                        result["humidity"]["max"] = humi
                        result["humidity"]["max_device"] = device_id
                    if result["humidity"]["min"] is None or humi < result["humidity"]["min"]:
                        result["humidity"]["min"] = humi
                        result["humidity"]["min_device"] = device_id
                except (ValueError, TypeError):
                    pass
        
        return result
    
    @staticmethod
    def get_device_summary(device_id: str, device) -> Dict[str, Any]:
        """
        Create a summary dictionary for a single device.
        
        Useful for including in aggregated records.
        
        Args:
            device_id: The device's ID
            device: DeviceState object
            
        Returns:
            Dictionary with device summary info
        """
        return {
            "device_id": device_id,
            "temperature": device.latest.get("temperature"),
            "humidity": device.latest.get("humidity"),
            "status": device.latest.get("status", "OK"),
            "uptime": device.latest.get("uptime"),
            "last_seen": device.last_seen.isoformat() if device.last_seen else None,
            "online": device.online,
        }
    
    @staticmethod
    def count_anomalies(devices: Dict[str, Any]) -> Dict[str, int]:
        """
        Count how many devices are reporting anomalies.
        
        Useful for overall system health summary.
        
        Args:
            devices: Dictionary of DeviceState objects
            
        Returns:
            Dictionary with anomaly counts:
            {
                "temperature_anomalies": 2,
                "humidity_anomalies": 1,
                "total_devices": 5,
            }
        """
        temp_anomalies = 0
        humi_anomalies = 0
        total = len(devices)
        
        for device in devices.values():
            if device.is_temp_anomaly():
                temp_anomalies += 1
            if device.is_humi_anomaly():
                humi_anomalies += 1
        
        return {
            "temperature_anomalies": temp_anomalies,
            "humidity_anomalies": humi_anomalies,
            "total_devices": total,
        }
    
    @staticmethod
    def generate_summary_record(
        devices: Dict[str, Any],
        risk_score: int,
        device_records: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Generate a complete aggregated summary record.
        
        This is the main method that creates the JSON record
        written to log.json by the bridge.
        
        Args:
            devices: All online devices
            risk_score: Overall system risk (0-10)
            device_records: List of per-device summaries
            
        Returns:
            Complete aggregation record ready for logging
        """
        from datetime import datetime, timezone
        
        averages = DataAggregator.calculate_system_averages(devices)
        extremes = DataAggregator.find_extremes(devices)
        anomalies = DataAggregator.count_anomalies(devices)
        
        # Determine system mode based on risk
        if risk_score >= 7:
            mode = "CRITICAL"
            status = "Anomaly"
        elif risk_score >= 4:
            mode = "WARNING"
            status = "Anomaly"
        else:
            mode = "NORMAL"
            status = "Normal"
        
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "temperature": averages["temperature"],
            "humidity": averages["humidity"],
            "status": status,
            "mode": mode,
            "risk": risk_score,
            "device_count": len(devices),
            "device_id": "EDGE-AGG",
            "uptime": int(__import__('time').monotonic()),
            # Detailed breakdowns
            "devices": device_records,
            "extremes": extremes,
            "anomalies": anomalies,
        }
