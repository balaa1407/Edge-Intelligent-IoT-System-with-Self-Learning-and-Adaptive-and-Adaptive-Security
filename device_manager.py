"""
Device management utilities for the Edge IoT system.

Provides utilities for managing device state, detecting offline devices,
and generating device health reports.
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone, timedelta


class DeviceManager:
    """
    Manages device lifecycle and state monitoring.
    
    Provides utilities for:
    - Detecting offline devices
    - Calculating device uptime
    - Generating device status reports
    - Managing device health
    """
    
    @staticmethod
    def check_offline_devices(
        devices: Dict[str, any],
        timeout_seconds: int = 60,
    ) -> List[Tuple[str, datetime]]:
        """
        Find devices that haven't sent data recently.
        
        A device is considered offline if we haven't heard from it
        in the specified timeout period.
        
        Args:
            devices: Dictionary mapping device_id to DeviceState
            timeout_seconds: Timeout threshold (default 60 seconds)
            
        Returns:
            List of (device_id, last_seen_time) for offline devices
        """
        offline = []
        now = datetime.now(timezone.utc)
        
        for device_id, device in devices.items():
            # Skip if we have no timestamp yet
            if not device.last_seen:
                continue
            
            # Calculate time since last message
            time_since_seen = now - device.last_seen
            
            # If it's been longer than timeout, it's offline
            if time_since_seen.total_seconds() > timeout_seconds:
                offline.append((device_id, device.last_seen))
        
        return offline
    
    @staticmethod
    def get_device_health(device, risk_score: int) -> Dict[str, any]:
        """
        Generate health report for a single device.
        
        Provides detailed status including uptime, anomalies, and risk level.
        
        Args:
            device: DeviceState object
            risk_score: Calculated risk score (0-10)
            
        Returns:
            Dictionary with comprehensive device health info
        """
        health = {
            "online": device.online,
            "risk": risk_score,
            "temperature": device.latest.get("temperature"),
            "humidity": device.latest.get("humidity"),
            "temperature_anomaly": device.is_temp_anomaly(),
            "humidity_anomaly": device.is_humi_anomaly(),
            "temp_history_size": len(device.temp_hist),
            "humidity_history_size": len(device.humi_hist),
            "readings_available": len(device.temp_hist) > 0,
        }
        
        # Calculate uptime from device if available
        if "uptime" in device.latest:
            try:
                uptime = int(device.latest["uptime"])
                health["uptime_seconds"] = uptime
                hours = uptime // 3600
                minutes = (uptime % 3600) // 60
                health["uptime_display"] = f"{hours}h {minutes}m"
            except (ValueError, TypeError):
                pass
        
        return health
    
    @staticmethod
    def get_system_health(
        devices: Dict[str, any],
        risk_scores: Dict[str, int],
    ) -> Dict[str, any]:
        """
        Generate health report for entire system.
        
        Aggregate view of all devices and overall system status.
        
        Args:
            devices: Dictionary of all DeviceState objects
            risk_scores: Dictionary mapping device_id to risk score
            
        Returns:
            System health report
        """
        online_count = sum(1 for d in devices.values() if d.online)
        total_count = len(devices)
        offline_count = total_count - online_count
        
        # Calculate overall risk
        max_risk = max(risk_scores.values()) if risk_scores else 0
        avg_risk = sum(risk_scores.values()) / len(risk_scores) if risk_scores else 0
        
        # Determine system status
        if max_risk >= 7:
            status = "CRITICAL"
        elif max_risk >= 4:
            status = "WARNING"
        else:
            status = "HEALTHY"
        
        # Count anomalies
        temp_anomalies = sum(1 for d in devices.values() if d.is_temp_anomaly())
        humi_anomalies = sum(1 for d in devices.values() if d.is_humi_anomaly())
        
        return {
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "devices": {
                "total": total_count,
                "online": online_count,
                "offline": offline_count,
                "health_percentage": (online_count / total_count * 100) if total_count > 0 else 0,
            },
            "risk": {
                "max": max_risk,
                "average": round(avg_risk, 2),
            },
            "anomalies": {
                "temperature": temp_anomalies,
                "humidity": humi_anomalies,
            },
        }
    
    @staticmethod
    def filter_devices_by_status(
        devices: Dict[str, any],
        online_only: bool = True,
    ) -> Dict[str, any]:
        """
        Filter devices by online/offline status.
        
        Useful for reporting only on active devices.
        
        Args:
            devices: Dictionary of all devices
            online_only: If True, return only online devices
            
        Returns:
            Filtered dictionary of devices
        """
        if online_only:
            return {k: v for k, v in devices.items() if v.online}
        else:
            return {k: v for k, v in devices.items() if not v.online}
    
    @staticmethod
    def get_device_summary_list(
        devices: Dict[str, any],
        risk_scores: Dict[str, int],
    ) -> List[Dict[str, any]]:
        """
        Get a list of summaries for all devices.
        
        Useful for displaying in dashboard or reports.
        
        Args:
            devices: Dictionary of DeviceState objects
            risk_scores: Dictionary of risk scores
            
        Returns:
            List of device summary dictionaries
        """
        summaries = []
        
        for device_id, device in devices.items():
            risk = risk_scores.get(device_id, 0)
            health = DeviceManager.get_device_health(device, risk)
            
            summary = {
                "device_id": device_id,
                "last_seen": device.last_seen.isoformat() if device.last_seen else None,
                **health,
            }
            summaries.append(summary)
        
        return summaries
    
    @staticmethod
    def estimate_uptime(last_seen: Optional[datetime]) -> str:
        """
        Estimate how long a device has been offline.
        
        Uses simple duration calculation from last_seen timestamp.
        
        Args:
            last_seen: Timestamp when device was last seen
            
        Returns:
            Human-readable string like "5 minutes", "2 hours"
        """
        if not last_seen:
            return "Never seen"
        
        now = datetime.now(timezone.utc)
        elapsed = now - last_seen
        
        # Convert to human readable format
        total_seconds = int(elapsed.total_seconds())
        
        if total_seconds < 60:
            return f"{total_seconds} seconds"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''}"
        elif total_seconds < 86400:
            hours = total_seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''}"
        else:
            days = total_seconds // 86400
            return f"{days} day{'s' if days != 1 else ''}"
