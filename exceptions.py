"""
Custom exception classes for the Edge IoT system.

Defines domain-specific exceptions for better error handling
and more informative error messages throughout the application.
"""


class EdgeIOTException(Exception):
    """Base exception for all Edge IoT system errors."""
    pass


class ConfigurationError(EdgeIOTException):
    """Raised when configuration is invalid or missing required settings."""
    pass


class MQTTError(EdgeIOTException):
    """Raised when MQTT operation fails."""
    pass


class MQTTConnectionError(MQTTError):
    """Raised when unable to connect to MQTT broker."""
    
    def __init__(self, broker: str, port: int, reason: str = ""):
        message = f"Failed to connect to MQTT broker {broker}:{port}"
        if reason:
            message += f" - {reason}"
        super().__init__(message)


class MQTTPublishError(MQTTError):
    """Raised when publishing message to MQTT topic fails."""
    
    def __init__(self, topic: str, reason: str = ""):
        message = f"Failed to publish to MQTT topic {topic}"
        if reason:
            message += f" - {reason}"
        super().__init__(message)


class SensorDataError(EdgeIOTException):
    """Raised when sensor data is invalid or corrupted."""
    pass


class InvalidSensorReading(SensorDataError):
    """Raised when a sensor reading fails validation."""
    
    def __init__(self, device_id: str, sensor_type: str, value: any):
        message = f"Invalid {sensor_type} reading from {device_id}: {value}"
        super().__init__(message)


class AnomalyDetectionError(EdgeIOTException):
    """Raised when anomaly detection fails."""
    pass


class InsufficientHistoryError(AnomalyDetectionError):
    """Raised when not enough historical data for anomaly detection."""
    
    def __init__(self, required: int, available: int):
        message = f"Insufficient history for anomaly detection (need {required}, have {available})"
        super().__init__(message)


class LoggingError(EdgeIOTException):
    """Raised when logging operations fail."""
    pass


class LogFileError(LoggingError):
    """Raised when log file operations fail."""
    
    def __init__(self, file_path: str, operation: str, reason: str = ""):
        message = f"Log file error for {file_path} during {operation}"
        if reason:
            message += f" - {reason}"
        super().__init__(message)


class DataAggregationError(EdgeIOTException):
    """Raised when data aggregation fails."""
    pass


class DeviceManagementError(EdgeIOTException):
    """Raised when device management operations fail."""
    pass


class DeviceNotFoundError(DeviceManagementError):
    """Raised when specified device cannot be found."""
    
    def __init__(self, device_id: str):
        message = f"Device not found: {device_id}"
        super().__init__(message)


class APIError(EdgeIOTException):
    """Base exception for API-related errors."""
    pass


class InvalidRequestError(APIError):
    """Raised when API request is invalid."""
    
    def __init__(self, endpoint: str, reason: str = ""):
        message = f"Invalid request to {endpoint}"
        if reason:
            message += f" - {reason}"
        super().__init__(message)


class ResourceNotFoundError(APIError):
    """Raised when requested resource doesn't exist."""
    
    def __init__(self, resource: str, identifier: str = ""):
        message = f"Resource not found: {resource}"
        if identifier:
            message += f" ({identifier})"
        super().__init__(message)


class ValidationError(EdgeIOTException):
    """Raised when data validation fails."""
    
    def __init__(self, field: str, value: any, reason: str = ""):
        message = f"Validation failed for '{field}': {value}"
        if reason:
            message += f" - {reason}"
        super().__init__(message)


class TimeoutError(EdgeIOTException):
    """Raised when an operation times out."""
    
    def __init__(self, operation: str, timeout_seconds: int):
        message = f"Operation timed out: {operation} (timeout: {timeout_seconds}s)"
        super().__init__(message)


def handle_exception(exception: Exception, logger=None) -> None:
    """
    Handle an exception with proper logging and context.
    
    Args:
        exception: The exception that occurred
        logger: Optional logger instance for recording the error
    """
    error_message = str(exception)
    
    if logger:
        if isinstance(exception, EdgeIOTException):
            logger.error(f"[EdgeIOT Error] {error_message}", exc_info=True)
        else:
            logger.error(f"[Unexpected Error] {error_message}", exc_info=True)
    
    # Re-raise the exception so caller can handle it
    raise exception
