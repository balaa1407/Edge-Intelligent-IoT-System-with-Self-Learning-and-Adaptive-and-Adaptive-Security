"""
Performance monitoring and metrics collection for the Edge IoT system.

Tracks system performance, response times, error rates, and device metrics.
"""

from typing import Dict, List, Any
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict
from collections import deque


@dataclass
class Metric:
    """Represents a single metric measurement."""
    name: str
    value: float
    unit: str
    timestamp: str
    tags: Dict[str, str] = None


class MetricsCollector:
    """Collects and aggregates system metrics."""
    
    def __init__(self, max_history: int = 1000):
        """
        Initialize metrics collector.
        
        Args:
            max_history: Maximum number of metrics to keep in memory
        """
        self.metrics: Dict[str, deque] = {}
        self.max_history = max_history
    
    def record_metric(
        self,
        name: str,
        value: float,
        unit: str,
        tags: Dict[str, str] = None,
    ) -> None:
        """
        Record a metric value.
        
        Args:
            name: Metric name (e.g., "temperature", "message_latency")
            value: Metric value
            unit: Unit of measurement (e.g., "°C", "ms", "count")
            tags: Optional tags for categorization
        """
        if name not in self.metrics:
            self.metrics[name] = deque(maxlen=self.max_history)
        
        metric = Metric(
            name=name,
            value=value,
            unit=unit,
            timestamp=datetime.now(timezone.utc).isoformat(),
            tags=tags or {},
        )
        
        self.metrics[name].append(metric)
    
    def get_average(self, name: str) -> float:
        """
        Get average value of a metric.
        
        Args:
            name: Metric name
            
        Returns:
            Average value, or 0 if no data
        """
        if name not in self.metrics or len(self.metrics[name]) == 0:
            return 0.0
        
        values = [m.value for m in self.metrics[name]]
        return sum(values) / len(values)
    
    def get_min(self, name: str) -> float:
        """Get minimum value of a metric."""
        if name not in self.metrics or len(self.metrics[name]) == 0:
            return 0.0
        return min(m.value for m in self.metrics[name])
    
    def get_max(self, name: str) -> float:
        """Get maximum value of a metric."""
        if name not in self.metrics or len(self.metrics[name]) == 0:
            return 0.0
        return max(m.value for m in self.metrics[name])
    
    def get_latest(self, name: str) -> float:
        """Get latest value of a metric."""
        if name not in self.metrics or len(self.metrics[name]) == 0:
            return 0.0
        return self.metrics[name][-1].value
    
    def get_summary(self, name: str) -> Dict[str, Any]:
        """
        Get summary statistics for a metric.
        
        Args:
            name: Metric name
            
        Returns:
            Dictionary with min, max, avg, latest, count
        """
        if name not in self.metrics:
            return {"count": 0, "min": 0, "max": 0, "avg": 0, "latest": 0}
        
        metrics_list = list(self.metrics[name])
        if not metrics_list:
            return {"count": 0, "min": 0, "max": 0, "avg": 0, "latest": 0}
        
        values = [m.value for m in metrics_list]
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "latest": values[-1],
            "unit": metrics_list[-1].unit,
        }


class SystemHealth:
    """Tracks overall system health status."""
    
    def __init__(self):
        """Initialize system health tracker."""
        self.start_time = datetime.now(timezone.utc)
        self.total_messages = 0
        self.total_errors = 0
        self.last_error_time = None
    
    def record_message(self) -> None:
        """Record a processed message."""
        self.total_messages += 1
    
    def record_error(self) -> None:
        """Record an error occurrence."""
        self.total_errors += 1
        self.last_error_time = datetime.now(timezone.utc)
    
    def get_uptime_seconds(self) -> int:
        """Get system uptime in seconds."""
        delta = datetime.now(timezone.utc) - self.start_time
        return int(delta.total_seconds())
    
    def get_uptime_formatted(self) -> str:
        """Get human-readable uptime."""
        seconds = self.get_uptime_seconds()
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours}h {minutes}m {secs}s"
    
    def get_error_rate(self) -> float:
        """
        Get error rate as percentage.
        
        Returns:
            Percentage of errors out of total messages
        """
        if self.total_messages == 0:
            return 0.0
        return (self.total_errors / self.total_messages) * 100
    
    def get_health_score(self) -> int:
        """
        Get overall health score (0-100).
        
        Returns:
            Score where 100 is perfect, 0 is critical
        """
        error_rate = self.get_error_rate()
        return max(0, int(100 - error_rate * 10))
    
    def get_status(self) -> str:
        """
        Get human-readable health status.
        
        Returns:
            Status string: "HEALTHY", "DEGRADED", "CRITICAL"
        """
        score = self.get_health_score()
        if score >= 90:
            return "HEALTHY"
        elif score >= 70:
            return "DEGRADED"
        else:
            return "CRITICAL"
    
    def to_dict(self) -> Dict[str, Any]:
        """Export health status as dictionary."""
        return {
            "uptime": self.get_uptime_formatted(),
            "uptime_seconds": self.get_uptime_seconds(),
            "total_messages": self.total_messages,
            "total_errors": self.total_errors,
            "error_rate": f"{self.get_error_rate():.2f}%",
            "health_score": self.get_health_score(),
            "status": self.get_status(),
            "last_error": self.last_error_time.isoformat() if self.last_error_time else None,
        }


class DeviceMetrics:
    """Track metrics for individual devices."""
    
    def __init__(self, device_id: str):
        """Initialize device metrics tracker."""
        self.device_id = device_id
        self.last_seen = datetime.now(timezone.utc)
        self.message_count = 0
        self.error_count = 0
        self.online = True
    
    def record_message(self) -> None:
        """Record a message from this device."""
        self.last_seen = datetime.now(timezone.utc)
        self.message_count += 1
        self.online = True
    
    def record_error(self) -> None:
        """Record an error for this device."""
        self.error_count += 1
    
    def set_offline(self) -> None:
        """Mark device as offline."""
        self.online = False
    
    def get_uptime(self) -> float:
        """Get device uptime as percentage."""
        if self.message_count + self.error_count == 0:
            return 0.0
        return (self.message_count / (self.message_count + self.error_count)) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Export device metrics as dictionary."""
        return {
            "device_id": self.device_id,
            "messages": self.message_count,
            "errors": self.error_count,
            "uptime_percent": f"{self.get_uptime():.1f}%",
            "online": self.online,
            "last_seen": self.last_seen.isoformat(),
        }


class PerformanceTimer:
    """Context manager for timing operations."""
    
    def __init__(self, name: str, collector: MetricsCollector = None):
        """
        Initialize performance timer.
        
        Args:
            name: Operation name
            collector: Optional MetricsCollector instance
        """
        self.name = name
        self.collector = collector
        self.start_time = None
    
    def __enter__(self):
        """Start timing."""
        self.start_time = datetime.now()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop timing and record metric."""
        if self.start_time:
            duration_ms = (datetime.now() - self.start_time).total_seconds() * 1000
            if self.collector:
                self.collector.record_metric(
                    f"{self.name}_latency",
                    duration_ms,
                    "ms",
                )
