"""
Pipeline Utility Functions
Common utilities for logging, error handling, configuration, and progress reporting
used throughout the BIS Knowledge Ingestion Pipeline orchestrator.
"""

import json
import logging
import os
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


class PipelineLogger:
    """Custom logger for pipeline operations with both file and console output."""

    def __init__(self, name: str = "bis_pipeline", log_dir: str = "logs"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        # Prevent duplicate handlers
        if self.logger.handlers:
            return

        # Create logs directory
        log_path = Path(log_dir)
        log_path.mkdir(exist_ok=True)

        # File handler for detailed logs
        log_file = log_path / f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)

        # Console handler for progress and errors
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)

        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

        self.log_file = str(log_file)

    def get_logger(self) -> logging.Logger:
        return self.logger

    def get_log_file(self) -> str:
        return self.log_file


def setup_pipeline_logging(name: str = "bis_pipeline", log_dir: str = "logs") -> PipelineLogger:
    """Set up and return a pipeline logger instance."""
    return PipelineLogger(name, log_dir)


def load_config(config_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Load configuration from JSON file.

    Args:
        config_path: Path to the configuration file

    Returns:
        Dictionary containing configuration data

    Raises:
        FileNotFoundError: If config file doesn't exist
        json.JSONDecodeError: If config file is not valid JSON
    """
    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    return config


def save_config(config: Dict[str, Any], config_path: Union[str, Path]) -> None:
    """
    Save configuration to JSON file.

    Args:
        config: Configuration dictionary to save
        config_path: Path where to save the configuration file
    """
    config_path = Path(config_path)
    config_path.parent.mkdir(parents=True, exist_ok=True)

    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, sort_keys=True)


def validate_config(config: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
    """
    Validate configuration against a schema.

    Args:
        config: Configuration dictionary to validate
        schema: Schema dictionary defining required fields and types

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    def _validate(obj: Any, schema_obj: Any, path: str = ""):
        if isinstance(schema_obj, dict):
            if not isinstance(obj, dict):
                errors.append(f"{path}: Expected object, got {type(obj).__name__}")
                return

            # Check required fields
            for key, key_schema in schema_obj.items():
                if key.endswith('?'):  # Optional field
                    actual_key = key[:-1]
                    if actual_key in obj:
                        _validate(obj[actual_key], key_schema, f"{path}.{actual_key}" if path else actual_key)
                else:  # Required field
                    if key not in obj:
                        errors.append(f"{path}.{key}: Required field missing" if path else f"{key}: Required field missing")
                    else:
                        _validate(obj[key], key_schema, f"{path}.{key}" if path else key)

            # Check for unexpected fields
            schema_keys = {k[:-1] if k.endswith('?') else k for k in schema_obj.keys()}
            for key in obj:
                if key not in schema_keys:
                    errors.append(f"{path}.{key}: Unexpected field" if path else f"{key}: Unexpected field")

        elif isinstance(schema_obj, list):
            if not isinstance(obj, list):
                errors.append(f"{path}: Expected array, got {type(obj).__name__}")
                return

            if len(schema_obj) > 0:
                item_schema = schema_obj[0]
                for i, item in enumerate(obj):
                    _validate(item, item_schema, f"{path}[{i}]")

        elif isinstance(schema_obj, type):
            if not isinstance(obj, schema_obj):
                errors.append(f"{path}: Expected {schema_obj.__name__}, got {type(obj).__name__}")

        elif schema_obj == "any":
            pass  # Accept any type
        else:
            # Literal value check
            if obj != schema_obj:
                errors.append(f"{path}: Expected {schema_obj}, got {obj}")

    _validate(config, schema)
    return errors


def retry_on_exception(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    Decorator to retry a function on exception.

    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay after each retry
        exceptions: Tuple of exceptions to catch and retry on
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            _delay = delay
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_retries:
                        raise e
                    time.sleep(_delay)
                    _delay *= backoff
            return None  # Should never reach here
        return wrapper
    return decorator


class PipelineError(Exception):
    """Custom exception for pipeline-specific errors."""

    def __init__(self, message: str, phase: str = "", is_number: str = ""):
        self.message = message
        self.phase = phase
        self.is_number = is_number
        super().__init__(self.message)

    def __str__(self):
        parts = [f"PipelineError: {self.message}"]
        if self.phase:
            parts.append(f"Phase: {self.phase}")
        if self.is_number:
            parts.append(f"IS Number: {self.is_number}")
        return " | ".join(parts)


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human-readable string.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted duration string (e.g., "2h 30m 15s")
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:
        parts.append(f"{secs}s")

    return " ".join(parts)


def safe_filename(filename: str) -> str:
    """
    Convert a string to a safe filename by removing/replacing invalid characters.

    Args:
        filename: Original filename string

    Returns:
        Safe filename string
    """
    # Replace invalid characters with underscore
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')

    # Remove leading/trailing spaces and dots
    filename = filename.strip(' .')

    # Ensure not empty
    if not filename:
        filename = "unnamed"

    return filename


def ensure_directory(path: Union[str, Path]) -> Path:
    """
    Ensure a directory exists, creating it if necessary.

    Args:
        path: Directory path

    Returns:
        Path object of the directory
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_file_size(file_path: Union[str, Path]) -> int:
    """
    Get file size in bytes.

    Args:
        file_path: Path to the file

    Returns:
        File size in bytes, 0 if file doesn't exist
    """
    try:
        return Path(file_path).stat().st_size
    except (OSError, FileNotFoundError):
        return 0


def is_file_newer_than(target: Union[str, Path], reference: Union[str, Path]) -> bool:
    """
    Check if target file is newer than reference file.

    Args:
        target: Path to target file
        reference: Path to reference file

    Returns:
        True if target is newer than reference or if reference doesn't exist
    """
    try:
        target_time = Path(target).stat().st_mtime
        ref_time = Path(reference).stat().st_mtime
        return target_time > ref_time
    except (OSError, FileNotFoundError):
        # If reference doesn't exist, consider target newer
        return not Path(reference).exists()


def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """
    Split a list into chunks of specified size.

    Args:
        lst: List to chunk
        chunk_size: Size of each chunk

    Returns:
        List of chunks
    """
    if chunk_size <= 0:
        return [lst]

    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def flatten_list(lst: List[List[Any]]) -> List[Any]:
    """
    Flatten a list of lists into a single list.

    Args:
        lst: List of lists to flatten

    Returns:
        Flattened list
    """
    return [item for sublist in lst for item in sublist]


def remove_duplicates(lst: List[Any]) -> List[Any]:
    """
    Remove duplicates from a list while preserving order.

    Args:
        lst: List to deduplicate

    Returns:
        List with duplicates removed
    """
    seen = set()
    result = []
    for item in lst:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def truncate_string(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate a string to a maximum length.

    Args:
        text: String to truncate
        max_length: Maximum length including suffix
        suffix: String to append when truncating

    Returns:
        Truncated string
    """
    if len(text) <= max_length:
        return text

    if len(suffix) >= max_length:
        return suffix[:max_length]

    return text[:max_length - len(suffix)] + suffix


def parse_is_number_range(range_str: str) -> List[str]:
    """
    Parse IS number range string into list of IS numbers.

    Supports formats like:
    - "IS 100-IS 105" -> ["IS 100", "IS 101", "IS 102", "IS 103", "IS 104", "IS 105"]
    - "IS 100, IS 102, IS 105" -> ["IS 100", "IS 102", "IS 105"]
    - "IS 100-IS 102, IS 105" -> ["IS 100", "IS 101", "IS 102", "IS 105"]

    Args:
        range_str: IS number range string

    Returns:
        List of IS number strings
    """
    is_numbers = []

    # Split by comma first
    parts = [part.strip() for part in range_str.split(',')]

    for part in parts:
        if '-' in part and 'IS' in part.upper():
            # Handle range format
            range_parts = [p.strip() for p in part.split('-')]
            if len(range_parts) == 2:
                try:
                    # Extract numbers from "IS XXX" format
                    start_str = range_parts[0].upper().replace('IS', '').strip()
                    end_str = range_parts[1].upper().replace('IS', '').strip()

                    start_num = int(start_str)
                    end_num = int(end_str)

                    # Generate range
                    for num in range(start_num, end_num + 1):
                        is_numbers.append(f"IS {num}")
                except ValueError:
                    # If parsing fails, treat as literal
                    is_numbers.append(part)
            else:
                # Invalid range format, treat as literal
                is_numbers.append(part)
        else:
            # Single IS number or literal
            is_numbers.append(part)

    return remove_duplicates(is_numbers)