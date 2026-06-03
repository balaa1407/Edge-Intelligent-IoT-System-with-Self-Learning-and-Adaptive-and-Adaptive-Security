"""
Configuration validation for the Edge IoT system.

This module validates configuration settings on startup to catch
errors early before they cause runtime failures.
"""

from typing import Any, Dict, List, Tuple


class ConfigValidator:
    """
    Validates configuration dictionaries against expected schemas.
    
    This class ensures that required config keys exist and have
    reasonable values before the application starts.
    """
    
    def __init__(self):
        """Initialize the validator with error tracking."""
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def validate_mqtt_config(self, mqtt_config: Dict[str, Any]) -> bool:
        """
        Validate MQTT configuration section.
        
        Checks that all required MQTT settings are present and valid:
        - server: hostname of MQTT broker
        - port: port number (1-65535)
        - client_id: unique client identifier
        - base_topic: MQTT topic to subscribe to
        
        Args:
            mqtt_config: Dictionary with MQTT settings
            
        Returns:
            True if valid, False if errors found (stored in self.errors)
        """
        required_keys = ["server", "port", "client_id", "base_topic"]
        
        # Check all required keys exist
        for key in required_keys:
            if key not in mqtt_config:
                self.errors.append(f"MQTT config missing: {key}")
                return False
        
        # Validate server is a string (hostname or IP)
        if not isinstance(mqtt_config["server"], str) or len(mqtt_config["server"]) == 0:
            self.errors.append("MQTT server must be non-empty string")
            return False
        
        # Validate port is integer in valid range
        port = mqtt_config.get("port")
        if not isinstance(port, int) or port < 1 or port > 65535:
            self.errors.append(f"MQTT port must be 1-65535, got {port}")
            return False
        
        # Validate client_id
        client_id = mqtt_config.get("client_id")
        if not isinstance(client_id, str) or len(client_id) == 0:
            self.errors.append("MQTT client_id must be non-empty string")
            return False
        
        return True
    
    def validate_thresholds(self, thresholds: Dict[str, float]) -> bool:
        """
        Validate sensor threshold settings.
        
        Ensures temperature and humidity thresholds make logical sense:
        - temp_critical_high > temp_high > temp_low
        - humi_high > humi_low
        - Values in reasonable sensor ranges
        
        Args:
            thresholds: Dictionary with temperature/humidity thresholds
            
        Returns:
            True if valid, False otherwise
        """
        required = ["temp_critical_high", "temp_high", "temp_low",
                   "humi_high", "humi_low"]
        
        # Check all required thresholds exist
        for key in required:
            if key not in thresholds:
                self.errors.append(f"Threshold missing: {key}")
                return False
        
        # Extract values
        tc = thresholds["temp_critical_high"]
        th = thresholds["temp_high"]
        tl = thresholds["temp_low"]
        hh = thresholds["humi_high"]
        hl = thresholds["humi_low"]
        
        # Validate logical ordering of temperature thresholds
        if not (tl < th < tc):
            self.errors.append(
                f"Temperature thresholds wrong order: "
                f"critical={tc}, high={th}, low={tl} "
                f"(should be low < high < critical)"
            )
            return False
        
        # Validate logical ordering of humidity thresholds
        if not (hl < hh):
            self.errors.append(
                f"Humidity thresholds wrong order: "
                f"high={hh}, low={hl} (should be low < high)"
            )
            return False
        
        # Warn if thresholds seem unreasonable for typical sensors
        if tc > 100:
            self.warnings.append(
                f"temp_critical_high={tc}°C seems very high for most environments"
            )
        
        if hh > 100:
            self.warnings.append(
                f"humi_high={hh}% is above 100% - impossible humidity"
            )
        
        return True
    
    def validate_anomaly_config(self, anomaly_config: Dict[str, Any]) -> bool:
        """
        Validate anomaly detection configuration.
        
        Ensures anomaly detection parameters are reasonable:
        - min_history: minimum readings before detection starts
        - max_history: rolling window size
        - z_threshold: how many std devs = anomaly
        
        Args:
            anomaly_config: Dictionary with anomaly detection settings
            
        Returns:
            True if valid, False otherwise
        """
        required = ["min_history", "max_history", "z_threshold"]
        
        for key in required:
            if key not in anomaly_config:
                self.errors.append(f"Anomaly config missing: {key}")
                return False
        
        min_h = anomaly_config["min_history"]
        max_h = anomaly_config["max_history"]
        z_thresh = anomaly_config["z_threshold"]
        
        # min_history should be < max_history
        if min_h >= max_h:
            self.errors.append(
                f"min_history ({min_h}) should be < max_history ({max_h})"
            )
            return False
        
        # Z-score threshold should be positive and reasonable
        if z_thresh <= 0:
            self.errors.append(f"z_threshold must be positive, got {z_thresh}")
            return False
        
        if z_thresh < 1.0:
            self.warnings.append(
                f"z_threshold={z_thresh} is very low - may flag too many false anomalies"
            )
        
        if z_thresh > 5.0:
            self.warnings.append(
                f"z_threshold={z_thresh} is very high - may miss real anomalies"
            )
        
        return True
    
    def validate_all(self, config: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
        """
        Validate entire configuration dictionary.
        
        This is the main entry point for configuration validation.
        Checks all sections and collects all errors and warnings.
        
        Args:
            config: Full configuration dictionary
            
        Returns:
            Tuple of (is_valid, list_of_errors, list_of_warnings)
            is_valid is False if any errors found, True otherwise
        """
        self.errors = []  # Reset error list
        self.warnings = []  # Reset warning list
        
        # Validate each section
        valid = True
        
        if "mqtt" in config:
            if not self.validate_mqtt_config(config["mqtt"]):
                valid = False
        else:
            self.errors.append("Config missing 'mqtt' section")
            valid = False
        
        if "thresholds" in config:
            if not self.validate_thresholds(config["thresholds"]):
                valid = False
        else:
            self.errors.append("Config missing 'thresholds' section")
            valid = False
        
        if "anomaly" in config:
            if not self.validate_anomaly_config(config["anomaly"]):
                valid = False
        else:
            self.errors.append("Config missing 'anomaly' section")
            valid = False
        
        return valid, self.errors, self.warnings
