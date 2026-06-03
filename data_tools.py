"""
Data export and analysis utilities for the Edge IoT system.

Provides functionality to export sensor data in various formats
for analysis, backup, and integration with external tools.
"""

import json
import csv
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from pathlib import Path


class DataExporter:
    """Export sensor data in multiple formats."""
    
    @staticmethod
    def export_to_csv(
        data_entries: List[Dict[str, Any]],
        output_file: str,
        include_fields: Optional[List[str]] = None,
    ) -> bool:
        """
        Export data entries to CSV format.
        
        Args:
            data_entries: List of data dictionaries
            output_file: Output CSV file path
            include_fields: Specific fields to include (None = all)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not data_entries:
                return False
            
            # Determine fields to include
            if include_fields is None:
                include_fields = list(data_entries[0].keys())
            
            # Write CSV
            with open(output_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=include_fields)
                writer.writeheader()
                for entry in data_entries:
                    row = {k: entry.get(k, '') for k in include_fields}
                    writer.writerow(row)
            
            return True
        except Exception as e:
            print(f"Error exporting to CSV: {e}")
            return False
    
    @staticmethod
    def export_to_json(
        data_entries: List[Dict[str, Any]],
        output_file: str,
        pretty_print: bool = True,
    ) -> bool:
        """
        Export data entries to JSON format.
        
        Args:
            data_entries: List of data dictionaries
            output_file: Output JSON file path
            pretty_print: Pretty-print JSON for readability
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(output_file, 'w') as f:
                if pretty_print:
                    json.dump(data_entries, f, indent=2)
                else:
                    json.dump(data_entries, f)
            return True
        except Exception as e:
            print(f"Error exporting to JSON: {e}")
            return False
    
    @staticmethod
    def export_to_jsonl(
        data_entries: List[Dict[str, Any]],
        output_file: str,
    ) -> bool:
        """
        Export data entries to JSONL (newline-delimited JSON) format.
        
        Args:
            data_entries: List of data dictionaries
            output_file: Output JSONL file path
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(output_file, 'w') as f:
                for entry in data_entries:
                    f.write(json.dumps(entry) + '\n')
            return True
        except Exception as e:
            print(f"Error exporting to JSONL: {e}")
            return False


class DataAnalyzer:
    """Analyze sensor data for insights."""
    
    @staticmethod
    def calculate_statistics(
        values: List[float],
    ) -> Dict[str, float]:
        """
        Calculate statistics for a list of values.
        
        Args:
            values: List of numeric values
            
        Returns:
            Dictionary with min, max, mean, median, std_dev
        """
        if not values:
            return {
                "count": 0,
                "min": 0,
                "max": 0,
                "mean": 0,
                "median": 0,
                "std_dev": 0,
            }
        
        values_sorted = sorted(values)
        n = len(values)
        mean = sum(values) / n
        variance = sum((x - mean) ** 2 for x in values) / n
        std_dev = variance ** 0.5
        
        # Median
        if n % 2 == 0:
            median = (values_sorted[n // 2 - 1] + values_sorted[n // 2]) / 2
        else:
            median = values_sorted[n // 2]
        
        return {
            "count": n,
            "min": min(values),
            "max": max(values),
            "mean": round(mean, 2),
            "median": median,
            "std_dev": round(std_dev, 2),
        }
    
    @staticmethod
    def find_outliers(
        values: List[float],
        std_dev_threshold: float = 2.0,
    ) -> List[int]:
        """
        Find outlier indices using standard deviation method.
        
        Args:
            values: List of values
            std_dev_threshold: Number of std deviations (default 2.0)
            
        Returns:
            List of indices that are outliers
        """
        if len(values) < 3:
            return []
        
        stats = DataAnalyzer.calculate_statistics(values)
        mean = stats["mean"]
        std_dev = stats["std_dev"]
        
        if std_dev == 0:
            return []
        
        outliers = []
        for i, value in enumerate(values):
            z_score = abs((value - mean) / std_dev)
            if z_score > std_dev_threshold:
                outliers.append(i)
        
        return outliers
    
    @staticmethod
    def hourly_aggregate(
        data_entries: List[Dict[str, Any]],
        sensor_field: str,
    ) -> Dict[str, float]:
        """
        Aggregate sensor data by hour.
        
        Args:
            data_entries: List of data dictionaries with 'timestamp'
            sensor_field: Field to aggregate (e.g., 'temperature')
            
        Returns:
            Dictionary mapping hour to average value
        """
        hourly_data = {}
        
        for entry in data_entries:
            try:
                timestamp = datetime.fromisoformat(entry['timestamp'])
                hour_key = timestamp.strftime('%Y-%m-%d %H:00')
                
                if hour_key not in hourly_data:
                    hourly_data[hour_key] = []
                
                if sensor_field in entry:
                    hourly_data[hour_key].append(entry[sensor_field])
            except (KeyError, ValueError):
                continue
        
        # Calculate averages
        return {
            hour: sum(values) / len(values)
            for hour, values in hourly_data.items()
            if values
        }


class DataValidator:
    """Validate sensor data integrity."""
    
    @staticmethod
    def validate_entry(
        entry: Dict[str, Any],
        required_fields: List[str],
        field_validators: Optional[Dict[str, callable]] = None,
    ) -> tuple[bool, List[str]]:
        """
        Validate a single data entry.
        
        Args:
            entry: Data entry to validate
            required_fields: Fields that must be present
            field_validators: Optional validator functions per field
            
        Returns:
            Tuple of (is_valid, error_list)
        """
        errors = []
        
        # Check required fields
        for field in required_fields:
            if field not in entry:
                errors.append(f"Missing required field: {field}")
        
        # Check field validators
        if field_validators:
            for field, validator in field_validators.items():
                if field in entry:
                    try:
                        if not validator(entry[field]):
                            errors.append(f"Invalid value for {field}: {entry[field]}")
                    except Exception as e:
                        errors.append(f"Validation error for {field}: {e}")
        
        return (len(errors) == 0, errors)
    
    @staticmethod
    def validate_dataset(
        entries: List[Dict[str, Any]],
        required_fields: List[str],
    ) -> Dict[str, Any]:
        """
        Validate an entire dataset.
        
        Args:
            entries: List of data entries
            required_fields: Required fields for each entry
            
        Returns:
            Validation report with counts and details
        """
        valid_count = 0
        invalid_count = 0
        errors = []
        
        for i, entry in enumerate(entries):
            is_valid, entry_errors = DataValidator.validate_entry(
                entry, required_fields
            )
            if is_valid:
                valid_count += 1
            else:
                invalid_count += 1
                errors.append({
                    "entry_index": i,
                    "errors": entry_errors,
                })
        
        return {
            "total_entries": len(entries),
            "valid_count": valid_count,
            "invalid_count": invalid_count,
            "validity_percent": (valid_count / len(entries) * 100) if entries else 0,
            "errors": errors[:10],  # First 10 errors
        }


class DataCleaner:
    """Clean and normalize sensor data."""
    
    @staticmethod
    def remove_duplicates(
        entries: List[Dict[str, Any]],
        key_field: str = 'timestamp',
    ) -> List[Dict[str, Any]]:
        """
        Remove duplicate entries based on key field.
        
        Args:
            entries: List of data entries
            key_field: Field to use for duplicate detection
            
        Returns:
            List with duplicates removed
        """
        seen = set()
        cleaned = []
        
        for entry in entries:
            key = entry.get(key_field)
            if key and key not in seen:
                seen.add(key)
                cleaned.append(entry)
        
        return cleaned
    
    @staticmethod
    def normalize_temperature_range(
        value: float,
        min_val: float = -50,
        max_val: float = 150,
    ) -> Optional[float]:
        """
        Normalize temperature to valid range.
        
        Args:
            value: Temperature value
            min_val: Minimum valid temperature
            max_val: Maximum valid temperature
            
        Returns:
            Normalized value, or None if invalid
        """
        if min_val <= value <= max_val:
            return value
        return None
    
    @staticmethod
    def interpolate_missing(
        values: List[Optional[float]],
    ) -> List[float]:
        """
        Interpolate missing (None) values in sequence.
        
        Args:
            values: List with possible None values
            
        Returns:
            List with missing values interpolated
        """
        result = []
        
        for i, value in enumerate(values):
            if value is not None:
                result.append(value)
            else:
                # Find previous and next valid values
                prev_val = None
                next_val = None
                
                for j in range(i - 1, -1, -1):
                    if values[j] is not None:
                        prev_val = values[j]
                        break
                
                for j in range(i + 1, len(values)):
                    if values[j] is not None:
                        next_val = values[j]
                        break
                
                # Interpolate
                if prev_val is not None and next_val is not None:
                    result.append((prev_val + next_val) / 2)
                elif prev_val is not None:
                    result.append(prev_val)
                elif next_val is not None:
                    result.append(next_val)
                else:
                    result.append(0.0)
        
        return result
