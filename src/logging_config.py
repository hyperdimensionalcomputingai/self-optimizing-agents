"""
Logging configuration for the self-optimizing-agents project.
Provides consistent logging setup across all modules.
"""

import logging
import os
import sys
from typing import Optional


def setup_logging(
    level: Optional[str] = None,
    log_file: Optional[str] = None,
    log_format: Optional[str] = None
) -> logging.Logger:
    """
    Set up logging configuration for the application.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path to write logs to
        log_format: Optional custom format string
        
    Returns:
        Configured logger instance
    """
    # Get log level from environment or use default
    if level is None:
        level = os.environ.get("LOG_LEVEL", "INFO").upper()
    
    # Convert string to logging level
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Default format
    if log_format is None:
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Create formatter
    formatter = logging.Formatter(log_format)
    
    # Create a separate logger for the application instead of configuring root logger
    # This allows httpx and other libraries to keep their default logging behavior
    app_logger = logging.getLogger("self_optimizing_agents")
    app_logger.setLevel(numeric_level)
    
    # Clear any existing handlers to avoid duplicates
    app_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    app_logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        try:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(numeric_level)
            file_handler.setFormatter(formatter)
            app_logger.addHandler(file_handler)
        except Exception as e:
            app_logger.warning(f"Failed to create file handler for {log_file}: {e}")
    
    # Ensure the logger propagates to parent loggers (but we're not configuring root)
    app_logger.propagate = False
    
    return app_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Logger instance
    """
    # Use the application logger as the parent for all module loggers
    if name == "__main__":
        return logging.getLogger("self_optimizing_agents")
    else:
        return logging.getLogger(f"self_optimizing_agents.{name}")


# Initialize logging when module is imported
setup_logging() 