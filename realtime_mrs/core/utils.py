"""
Utility functions for the realtime-mrs package.

Provides common helper functions used throughout the package.
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import json
import time
import threading
from datetime import datetime

from .logger import get_logger

logger = get_logger(__name__)

def get_package_root() -> Path:
    """Get the root directory of the package."""
    return Path(__file__).parent.parent.parent

def ensure_data_dir(data_dir: Optional[Union[str, Path]] = None) -> Path:
    """
    Ensure the data directory exists and return its path.
    
    Args:
        data_dir: Optional data directory path. If None, uses 'data' in current directory.
        
    Returns:
        Path to the data directory
    """
    if data_dir is None:
        data_dir = Path.cwd() / 'data'
    else:
        data_dir = Path(data_dir)
    
    data_dir.mkdir(parents=True, exist_ok=True)
    logger.debug(f"Data directory ensured: {data_dir}")
    return data_dir

def validate_config(config: Dict[str, Any], required_keys: List[str]) -> bool:
    """
    Validate that a configuration dictionary contains required keys.
    
    Args:
        config: Configuration dictionary to validate
        required_keys: List of required keys (supports dot notation)
        
    Returns:
        True if all required keys are present, False otherwise
    """
    for key in required_keys:
        if not get_nested_value(config, key):
            logger.error(f"Required configuration key missing: {key}")
            return False
    return True

def get_nested_value(data: Dict[str, Any], key_path: str, default: Any = None) -> Any:
    """
    Get a value from a nested dictionary using dot notation.
    
    Args:
        data: Dictionary to search
        key_path: Dot-separated key path (e.g., 'network.ip')
        default: Default value if key not found
        
    Returns:
        Value at the key path or default
    """
    keys = key_path.split('.')
    value = data
    
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return default
    
    return value

def set_nested_value(data: Dict[str, Any], key_path: str, value: Any):
    """
    Set a value in a nested dictionary using dot notation.
    
    Args:
        data: Dictionary to modify
        key_path: Dot-separated key path (e.g., 'network.ip')
        value: Value to set
    """
    keys = key_path.split('.')
    current = data
    
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
    
    current[keys[-1]] = value

def timestamp_string(format_str: str = "%Y%m%d_%H%M%S") -> str:
    """
    Generate a timestamp string.
    
    Args:
        format_str: Format string for datetime.strftime
        
    Returns:
        Formatted timestamp string
    """
    return datetime.now().strftime(format_str)

def safe_filename(filename: str, replacement: str = "_") -> str:
    """
    Make a filename safe by replacing invalid characters.
    
    Args:
        filename: Original filename
        replacement: Character to replace invalid characters with
        
    Returns:
        Safe filename
    """
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, replacement)
    return filename

def create_backup_filename(original_path: Union[str, Path]) -> Path:
    """
    Create a backup filename by adding timestamp.
    
    Args:
        original_path: Original file path
        
    Returns:
        Backup file path
    """
    original_path = Path(original_path)
    timestamp = timestamp_string()
    backup_name = f"{original_path.stem}_{timestamp}{original_path.suffix}"
    return original_path.parent / backup_name

def load_json_file(file_path: Union[str, Path]) -> Optional[Dict[str, Any]]:
    """
    Load a JSON file safely.
    
    Args:
        file_path: Path to JSON file
        
    Returns:
        Loaded JSON data or None if failed
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load JSON file {file_path}: {e}")
        return None

def save_json_file(data: Dict[str, Any], file_path: Union[str, Path], indent: int = 2) -> bool:
    """
    Save data to a JSON file safely.
    
    Args:
        data: Data to save
        file_path: Path to save to
        indent: JSON indentation
        
    Returns:
        True if successful, False otherwise
    """
    try:
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Failed to save JSON file {file_path}: {e}")
        return False

class ThreadSafeCounter:
    """Thread-safe counter for tracking events."""
    
    def __init__(self, initial_value: int = 0):
        self._value = initial_value
        self._lock = threading.Lock()
    
    def increment(self, amount: int = 1) -> int:
        """Increment the counter and return new value."""
        with self._lock:
            self._value += amount
            return self._value
    
    def decrement(self, amount: int = 1) -> int:
        """Decrement the counter and return new value."""
        with self._lock:
            self._value -= amount
            return self._value
    
    def get(self) -> int:
        """Get the current value."""
        with self._lock:
            return self._value
    
    def set(self, value: int) -> int:
        """Set the counter value."""
        with self._lock:
            self._value = value
            return self._value

class Timer:
    """Simple timer utility for measuring elapsed time."""
    
    def __init__(self):
        self._start_time = None
        self._end_time = None
    
    def start(self):
        """Start the timer."""
        self._start_time = time.time()
        self._end_time = None
    
    def stop(self) -> float:
        """Stop the timer and return elapsed time."""
        if self._start_time is None:
            raise RuntimeError("Timer not started")
        self._end_time = time.time()
        return self.elapsed()
    
    def elapsed(self) -> float:
        """Get elapsed time (whether timer is stopped or not)."""
        if self._start_time is None:
            return 0.0
        end_time = self._end_time if self._end_time is not None else time.time()
        return end_time - self._start_time
    
    def is_running(self) -> bool:
        """Check if timer is currently running."""
        return self._start_time is not None and self._end_time is None

def retry_on_exception(
    func,
    max_retries: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    Retry a function on exception with exponential backoff.
    
    Args:
        func: Function to retry
        max_retries: Maximum number of retries
        delay: Initial delay between retries
        backoff_factor: Factor to multiply delay by after each retry
        exceptions: Tuple of exceptions to catch
        
    Returns:
        Function result or raises last exception
    """
    last_exception = None
    current_delay = delay
    
    for attempt in range(max_retries + 1):
        try:
            return func()
        except exceptions as e:
            last_exception = e
            if attempt < max_retries:
                logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {current_delay:.1f}s...")
                time.sleep(current_delay)
                current_delay *= backoff_factor
            else:
                logger.error(f"All {max_retries + 1} attempts failed. Last error: {e}")
    
    raise last_exception

def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human-readable string.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted duration string
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.1f}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours}h {minutes}m {secs:.1f}s"

def check_dependencies(dependencies: List[str]) -> Dict[str, bool]:
    """
    Check if required dependencies are available.
    
    Args:
        dependencies: List of module names to check
        
    Returns:
        Dictionary mapping module names to availability status
    """
    results = {}
    for dep in dependencies:
        try:
            __import__(dep)
            results[dep] = True
        except ImportError:
            results[dep] = False
    return results

def get_system_info() -> Dict[str, Any]:
    """
    Get system information for debugging.
    
    Returns:
        Dictionary with system information
    """
    import platform
    
    return {
        'platform': platform.platform(),
        'python_version': platform.python_version(),
        'architecture': platform.architecture(),
        'processor': platform.processor(),
        'machine': platform.machine(),
        'system': platform.system(),
        'release': platform.release(),
    } 