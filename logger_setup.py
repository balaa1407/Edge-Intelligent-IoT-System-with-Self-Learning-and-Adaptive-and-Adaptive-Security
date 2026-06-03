"""
Logging configuration for the Edge IoT system.

Provides centralized logging setup that can be used by both
bridge.py and other modules for consistent logging behavior.
"""

import logging
import logging.handlers
import sys
from typing import Optional


def setup_logger(
    name: str,
    log_file: Optional[str] = None,
    level: int = logging.INFO,
    console: bool = True,
) -> logging.Logger:
    """
    Setup and configure a logger with consistent formatting.
    
    Creates a logger with:
    - Console output with colored messages (if console=True)
    - Optional file output with rotating file handler
    - Consistent timestamp and level formatting
    
    Usage:
        logger = setup_logger("my_app", log_file="my_app.log")
        logger.info("Application started")
    
    Args:
        name: Logger name (usually module name)
        log_file: Optional path to log file for persistent logging
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        console: Whether to also print to console
        
    Returns:
        Configured logger instance ready for use
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Avoid duplicate handlers if called multiple times
    if logger.handlers:
        return logger
    
    # Log format with timestamp, level, and message
    formatter = logging.Formatter(
        fmt='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )
    
    # Console handler (print to terminal)
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # File handler (write to rotating log file)
    if log_file:
        try:
            # RotatingFileHandler automatically rotates logs when they get too large
            # This prevents log files from growing infinitely
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=10 * 1024 * 1024,  # 10 MB max file size
                backupCount=5,               # Keep 5 backup files
            )
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except (IOError, OSError) as e:
            # If we can't write to file, just warn and continue
            logger.warning(f"Could not create file logger for {log_file}: {e}")
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger by name (doesn't configure, assumes already configured).
    
    Simple helper to get a logger after setup_logger() has been called.
    
    Args:
        name: Logger name to retrieve
        
    Returns:
        Logger instance (or default logger if not found)
    """
    return logging.getLogger(name)


class LoggingContext:
    """
    Context manager for temporary logging level changes.
    
    Useful when you want to temporarily change logging verbosity
    for a specific section of code.
    
    Usage:
        with LoggingContext(logger, logging.DEBUG):
            logger.debug("This will appear even if logger level is INFO")
    """
    
    def __init__(self, logger: logging.Logger, level: int):
        """
        Initialize context manager.
        
        Args:
            logger: Logger to modify
            level: Temporary logging level
        """
        self.logger = logger
        self.level = level
        self.old_level = logger.level
    
    def __enter__(self):
        """Enter context - save old level and set new one."""
        self.logger.setLevel(self.level)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context - restore original logging level."""
        self.logger.setLevel(self.old_level)


def log_exception(logger: logging.Logger, exception: Exception, prefix: str = "Error") -> None:
    """
    Log an exception with full traceback.
    
    This is a convenience function that logs the exception at ERROR level
    with full traceback information for debugging.
    
    Args:
        logger: Logger to use
        exception: Exception that occurred
        prefix: Prefix message (e.g., "Error", "Fatal Error")
    """
    logger.error(f"{prefix}: {exception}", exc_info=True)


def log_section(logger: logging.Logger, section_name: str) -> None:
    """
    Log a section separator for readability.
    
    Useful for breaking up log output into logical sections.
    
    Example output:
        ──────────────────────── Starting MQTT Connection ────────────────────────────
    
    Args:
        logger: Logger to use
        section_name: Name of the section
    """
    separator = "─" * 76
    logger.info(f"\n{separator}")
    logger.info(f"  {section_name}")
    logger.info(f"{separator}\n")
