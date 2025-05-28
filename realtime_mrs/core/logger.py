"""
Logging utilities for the realtime-mrs package.

Provides centralized logging configuration and management for all package components.
Supports both file and console logging with configurable levels.
"""

import logging
import os
import sys
from pathlib import Path
from typing import Optional, Union

_logging_configured = False
_default_log_file = None

def get_package_root() -> Path:
    """Get the root directory of the package."""
    return Path(__file__).parent.parent.parent

def setup_logging(
    log_file: Optional[Union[str, Path]] = None,
    log_level: str = "INFO",
    console_level: str = "INFO",
    file_level: str = "DEBUG",
    log_format: Optional[str] = None,
    force_reconfigure: bool = False
) -> Path:
    """
    Setup logging configuration for the realtime-mrs package.
    
    Args:
        log_file: Path to log file. If None, uses default location.
        log_level: Root logger level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        console_level: Console handler level
        file_level: File handler level
        log_format: Custom log format string
        force_reconfigure: Force reconfiguration even if already configured
        
    Returns:
        Path to the log file being used
    """
    global _logging_configured, _default_log_file
    
    if _logging_configured and not force_reconfigure:
        return Path(_default_log_file) if _default_log_file else get_package_root() / 'realtime_mrs.log'

    # Determine log file path
    if log_file is None:
        log_file = get_package_root() / 'realtime_mrs.log'
    else:
        log_file = Path(log_file)
    
    # Ensure log directory exists
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    _default_log_file = str(log_file)

    # Clear existing handlers
    root_logger = logging.getLogger()
    if root_logger.hasHandlers():
        for handler in list(root_logger.handlers):
            root_logger.removeHandler(handler)
            handler.close()
        
    # Set root logger level
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Create formatter
    if log_format is None:
        log_format = '%(asctime)s - %(name)s - [%(levelname)s] - %(message)s'
    formatter = logging.Formatter(log_format)

    # Setup file handler
    try:
        file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
        file_handler.setFormatter(formatter)
        file_handler.setLevel(getattr(logging, file_level.upper(), logging.DEBUG))
        root_logger.addHandler(file_handler)
    except Exception as e:
        print(f"Critical Error: Could not set up file logger at {log_file}. Error: {e}", file=sys.stderr)

    # Setup console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(getattr(logging, console_level.upper(), logging.INFO))
    root_logger.addHandler(console_handler)

    _logging_configured = True
    
    # Log the configuration
    setup_logger = logging.getLogger("realtime_mrs.core.logger")
    setup_logger.info(f"Logging configured. Root level: {log_level}, File level: {file_level}, Console level: {console_level}")
    setup_logger.info(f"Log file: {log_file}")
    
    return log_file

def get_logger(name: str, auto_setup: bool = True) -> logging.Logger:
    """
    Get a logger instance for the given name.
    
    Args:
        name: Logger name (typically module name)
        auto_setup: Automatically setup logging if not already configured
        
    Returns:
        Logger instance
    """
    if auto_setup and not _logging_configured:
        setup_logging()
    
    # Ensure the logger name starts with the package name for consistency
    if not name.startswith('realtime_mrs'):
        name = f'realtime_mrs.{name}'
    
    return logging.getLogger(name)

def get_log_file_path() -> Optional[Path]:
    """Get the current log file path."""
    return Path(_default_log_file) if _default_log_file else None

def set_log_level(level: str, logger_name: Optional[str] = None):
    """
    Set log level for a specific logger or root logger.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        logger_name: Specific logger name, or None for root logger
    """
    if logger_name:
        logger = logging.getLogger(logger_name)
    else:
        logger = logging.getLogger()
    
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

def add_file_handler(
    logger_name: str,
    log_file: Union[str, Path],
    level: str = "DEBUG",
    format_string: Optional[str] = None
):
    """
    Add an additional file handler to a specific logger.
    
    Args:
        logger_name: Name of the logger
        log_file: Path to the log file
        level: Log level for this handler
        format_string: Custom format string
    """
    logger = logging.getLogger(logger_name)
    
    # Create handler
    handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
    handler.setLevel(getattr(logging, level.upper(), logging.DEBUG))
    
    # Set formatter
    if format_string is None:
        format_string = '%(asctime)s - %(name)s - [%(levelname)s] - %(message)s'
    formatter = logging.Formatter(format_string)
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)

# Convenience function for backward compatibility
def setup_logging_legacy():
    """Legacy setup function for backward compatibility."""
    return setup_logging() 