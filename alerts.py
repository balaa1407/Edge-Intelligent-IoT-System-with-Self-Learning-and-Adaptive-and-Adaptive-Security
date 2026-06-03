"""
Alert system for generating and managing system alerts.

Provides alert generation, filtering, and notification hooks.
"""

from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from enum import Enum


class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = 0
    WARNING = 1
    CRITICAL = 2


@dataclass
class Alert:
    """Represents a system alert."""
    level: AlertLevel
    device_id: str
    message: str
    timestamp: str
    details: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'level': self.level.name,
            'device_id': self.device_id,
            'message': self.message,
            'timestamp': self.timestamp,
            'details': self.details or {},
        }


class AlertManager:
    """Manage system alerts and notifications."""
    
    def __init__(self, max_alert_history: int = 100):
        """
        Initialize alert manager.
        
        Args:
            max_alert_history: Maximum alerts to keep in memory
        """
        self.alerts: List[Alert] = []
        self.max_history = max_alert_history
        self.handlers: List[Callable[[Alert], None]] = []
    
    def add_handler(self, handler: Callable[[Alert], None]) -> None:
        """
        Register an alert handler (notification callback).
        
        Args:
            handler: Function that takes Alert and sends notification
        """
        self.handlers.append(handler)
    
    def create_alert(
        self,
        level: AlertLevel,
        device_id: str,
        message: str,
        details: Dict[str, Any] = None,
    ) -> Alert:
        """
        Create and register a new alert.
        
        Args:
            level: Alert severity
            device_id: Device ID
            message: Human-readable message
            details: Additional context
            
        Returns:
            Created Alert instance
        """
        alert = Alert(
            level=level,
            device_id=device_id,
            message=message,
            timestamp=datetime.now(timezone.utc).isoformat(),
            details=details,
        )
        
        # Store alert
        self.alerts.append(alert)
        if len(self.alerts) > self.max_history:
            self.alerts.pop(0)
        
        # Notify handlers
        self._notify_handlers(alert)
        
        return alert
    
    def _notify_handlers(self, alert: Alert) -> None:
        """Call all registered handlers for an alert."""
        for handler in self.handlers:
            try:
                handler(alert)
            except Exception as e:
                # Handler failed, but don't crash
                print(f"Alert handler failed: {e}")
    
    def get_recent_alerts(self, minutes: int = 60) -> List[Alert]:
        """
        Get alerts from last N minutes.
        
        Args:
            minutes: Number of minutes to look back
            
        Returns:
            List of recent alerts
        """
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        
        return [
            a for a in self.alerts
            if datetime.fromisoformat(a.timestamp) >= cutoff
        ]
    
    def get_alerts_by_device(self, device_id: str) -> List[Alert]:
        """Get all alerts for a specific device."""
        return [a for a in self.alerts if a.device_id == device_id]
    
    def get_alerts_by_level(self, level: AlertLevel) -> List[Alert]:
        """Get all alerts of a specific severity level."""
        return [a for a in self.alerts if a.level == level]
    
    def clear_old_alerts(self, days: int = 30) -> int:
        """
        Clear alerts older than N days.
        
        Args:
            days: Days to keep
            
        Returns:
            Number of alerts removed
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        initial_count = len(self.alerts)
        
        self.alerts = [
            a for a in self.alerts
            if datetime.fromisoformat(a.timestamp) >= cutoff
        ]
        
        return initial_count - len(self.alerts)


class AlertRules:
    """Define rules for when to trigger alerts."""
    
    @staticmethod
    def check_temperature_threshold(
        temperature: float,
        min_normal: float,
        max_normal: float,
    ) -> Optional[AlertLevel]:
        """
        Check temperature threshold and return alert level.
        
        Args:
            temperature: Current temperature
            min_normal: Minimum acceptable
            max_normal: Maximum acceptable
            
        Returns:
            Alert level or None if normal
        """
        if temperature < min_normal * 0.9:  # 10% below minimum
            return AlertLevel.CRITICAL
        elif temperature < min_normal:
            return AlertLevel.WARNING
        elif temperature > max_normal * 1.1:  # 10% above maximum
            return AlertLevel.CRITICAL
        elif temperature > max_normal:
            return AlertLevel.WARNING
        return None
    
    @staticmethod
    def check_humidity_threshold(
        humidity: float,
        min_normal: float,
        max_normal: float,
    ) -> Optional[AlertLevel]:
        """Check humidity threshold and return alert level."""
        if humidity < min_normal * 0.9:
            return AlertLevel.CRITICAL
        elif humidity < min_normal:
            return AlertLevel.WARNING
        elif humidity > max_normal * 1.1:
            return AlertLevel.CRITICAL
        elif humidity > max_normal:
            return AlertLevel.WARNING
        return None
    
    @staticmethod
    def check_risk_score(risk_score: int) -> Optional[AlertLevel]:
        """Check risk score and return alert level."""
        if risk_score >= 7:
            return AlertLevel.CRITICAL
        elif risk_score >= 4:
            return AlertLevel.WARNING
        return None
    
    @staticmethod
    def check_device_offline(
        last_seen: datetime,
        timeout_seconds: int = 300,
    ) -> Optional[AlertLevel]:
        """
        Check if device is offline.
        
        Args:
            last_seen: Last time device communicated
            timeout_seconds: Seconds before considering offline
            
        Returns:
            Alert level or None if online
        """
        elapsed = (datetime.now(timezone.utc) - last_seen).total_seconds()
        
        if elapsed > timeout_seconds:
            return AlertLevel.CRITICAL
        return None


# Default alert handlers

def print_alert_handler(alert: Alert) -> None:
    """Print alert to console."""
    level_symbol = {
        AlertLevel.INFO: "ℹ️ ",
        AlertLevel.WARNING: "⚠️ ",
        AlertLevel.CRITICAL: "🚨 ",
    }[alert.level]
    
    print(f"{level_symbol} [{alert.level.name}] {alert.device_id}: {alert.message}")


def email_alert_handler(alert: Alert) -> None:
    """Send alert via email (stub implementation)."""
    if alert.level == AlertLevel.CRITICAL:
        # TODO: Implement email sending
        # send_email(
        #     to="admin@example.com",
        #     subject=f"CRITICAL: {alert.message}",
        #     body=alert.to_dict()
        # )
        pass


def slack_alert_handler(alert: Alert) -> None:
    """Send alert to Slack (stub implementation)."""
    if alert.level in [AlertLevel.WARNING, AlertLevel.CRITICAL]:
        # TODO: Implement Slack sending
        # webhook_url = os.getenv("SLACK_WEBHOOK_URL")
        # requests.post(webhook_url, json={"text": alert.message})
        pass


def sms_alert_handler(alert: Alert) -> None:
    """Send alert via SMS (stub implementation)."""
    if alert.level == AlertLevel.CRITICAL:
        # TODO: Implement SMS sending
        # Use Twilio or similar service
        pass


def log_alert_handler(alert: Alert) -> None:
    """Log alert to file."""
    import json
    import logging
    
    logger = logging.getLogger('alerts')
    logger.log(
        level=logging.WARNING if alert.level == AlertLevel.WARNING else logging.ERROR,
        msg=f"[{alert.device_id}] {alert.message}"
    )
