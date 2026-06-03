"""
API response builders for Flask endpoints.

Provides consistent, structured responses for API endpoints
with proper formatting and data transformation.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone


class APIResponse:
    """
    Helper class for building consistent API responses.
    
    Provides methods to format data for JSON serialization
    in a consistent way across all endpoints.
    """
    
    @staticmethod
    def success(data: Any = None, message: str = "Success") -> Dict[str, Any]:
        """
        Build a successful API response.
        
        Format:
        {
            "success": true,
            "message": "Success",
            "data": {...},
            "timestamp": "2024-01-15T14:30:45.123456+00:00"
        }
        
        Args:
            data: Response data (can be dict, list, or any JSON-serializable)
            message: Optional message string
            
        Returns:
            Response dictionary ready for jsonify()
        """
        return {
            "success": True,
            "message": message,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    
    @staticmethod
    def error(error_code: str, message: str, details: Any = None) -> Dict[str, Any]:
        """
        Build an error API response.
        
        Format:
        {
            "success": false,
            "error": "ERROR_CODE",
            "message": "Error message",
            "details": {...},
            "timestamp": "..."
        }
        
        Args:
            error_code: Machine-readable error code (e.g., "INVALID_INPUT")
            message: Human-readable error message
            details: Optional additional error details
            
        Returns:
            Error response dictionary
        """
        return {
            "success": False,
            "error": error_code,
            "message": message,
            "details": details,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    
    @staticmethod
    def paginated(
        items: List[Any],
        page: int,
        page_size: int,
        total: int,
    ) -> Dict[str, Any]:
        """
        Build a paginated response.
        
        Format:
        {
            "success": true,
            "data": [...],
            "pagination": {
                "page": 1,
                "page_size": 10,
                "total": 45,
                "pages": 5
            }
        }
        
        Args:
            items: List of items for this page
            page: Current page number (1-indexed)
            page_size: Items per page
            total: Total number of items across all pages
            
        Returns:
            Paginated response dictionary
        """
        total_pages = (total + page_size - 1) // page_size  # Ceiling division
        
        return {
            "success": True,
            "data": items,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "pages": total_pages,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    
    @staticmethod
    def dashboard_data(
        temperatures: List[float],
        humidities: List[float],
        timestamps: List[str],
        latest: Dict[str, Any],
        alert: bool,
    ) -> Dict[str, Any]:
        """
        Build dashboard data response for chart visualization.
        
        Specifically formatted for Chart.js consumption.
        
        Args:
            temperatures: Array of temperature readings
            humidities: Array of humidity readings  
            timestamps: Array of timestamp labels for X-axis
            latest: Latest reading summary
            alert: Whether alert is active
            
        Returns:
            Dashboard data response
        """
        return {
            "success": True,
            "charts": {
                "temperature": {
                    "data": temperatures,
                    "label": "Temperature (°C)",
                },
                "humidity": {
                    "data": humidities,
                    "label": "Humidity (%)",
                },
                "timestamps": timestamps,
            },
            "latest": latest,
            "alert": alert,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    
    @staticmethod
    def health_check(status: str) -> Dict[str, Any]:
        """
        Build health check response.
        
        Simple format for /health endpoint.
        
        Args:
            status: Status string ("ok", "degraded", "error")
            
        Returns:
            Health check response
        """
        return {
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": "Edge IoT Dashboard",
        }
    
    @staticmethod
    def device_list(devices: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Build device listing response.
        
        Includes aggregated device statistics.
        
        Args:
            devices: List of device dictionaries
            
        Returns:
            Device list response with statistics
        """
        online_count = sum(1 for d in devices if d.get("online", False))
        
        return {
            "success": True,
            "data": devices,
            "summary": {
                "total": len(devices),
                "online": online_count,
                "offline": len(devices) - online_count,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


class ResponseValidator:
    """
    Validates and ensures API responses have required fields.
    
    Useful for catching missing or malformed responses.
    """
    
    @staticmethod
    def validate_chart_data(data: Dict[str, Any]) -> bool:
        """
        Validate that response has all required chart data fields.
        
        Required fields:
        - charts.temperature.data
        - charts.humidity.data
        - charts.timestamps
        - latest
        - alert
        
        Args:
            data: Response data to validate
            
        Returns:
            True if valid, False if missing required fields
        """
        required_paths = [
            ["charts", "temperature", "data"],
            ["charts", "humidity", "data"],
            ["charts", "timestamps"],
            ["latest"],
            ["alert"],
        ]
        
        for path in required_paths:
            value = data
            for key in path:
                if not isinstance(value, dict) or key not in value:
                    return False
                value = value[key]
        
        return True
    
    @staticmethod
    def validate_device_health(data: Dict[str, Any]) -> bool:
        """
        Validate device health response.
        
        Args:
            data: Health data to validate
            
        Returns:
            True if valid structure
        """
        required_keys = ["online", "risk", "temperature", "humidity"]
        return all(key in data for key in required_keys)
