#!/usr/bin/env python3
"""
Test script for pipeline components
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_is_number_manager():
    """Test the IS Number Manager."""
    print("Testing IS Number Manager...")

    from scripts.is_number_manager import ISNumberManager

    # Create a temporary manager for testing
    manager = ISNumberManager("test_is_number_state")

    # Test adding IS numbers
    added = manager.add_is_numbers(["IS 100", "IS 101", "IS 102"], "test")
    print(f"Added {added} IS numbers")

    # Test adding range
    added = manager.add_is_number_range("IS 105-IS 107", "test")
    print(f"Added {added} IS numbers from range")

    # Test getting next batch
    batch = manager.get_next_batch(3)
    print(f"Next batch: {batch}")

    # Test marking as completed
    manager.mark_as_completed(["IS 100"])
    print("Marked IS 100 as completed")

    # Test status
    status = manager.get_status()
    print(f"Status: {status}")

    # Clean up
    import shutil
    if os.path.exists("test_is_number_state"):
        shutil.rmtree("test_is_number_state")

    print("IS Number Manager test completed\n")


def test_pipeline_utils():
    """Test pipeline utilities."""
    print("Testing Pipeline Utilities...")

    from scripts.pipeline_utils import (
        safe_filename, parse_is_number_range, format_duration,
        chunk_list, truncate_string, remove_duplicates
    )

    # Test safe filename
    safe = safe_filename("test<>:file|name*.txt")
    print(f"Safe filename: {safe}")

    # Test parse IS number range
    numbers = parse_is_number_range("IS 100-IS 102, IS 105")
    print(f"Parsed range: {numbers}")

    # Test format duration
    duration = format_duration(3661)  # 1 hour, 1 minute, 1 second
    print(f"Formatted duration: {duration}")

    # Test chunk list
    chunks = chunk_list([1, 2, 3, 4, 5, 6, 7], 3)
    print(f"Chunked list: {chunks}")

    # Test truncate string
    truncated = truncate_string("This is a very long string that should be truncated", 20)
    print(f"Truncated string: {truncated}")

    # Test remove duplicates
    deduped = remove_duplicates([1, 2, 2, 3, 1, 4, 5])
    print(f"Deduplicated list: {deduped}")

    print("Pipeline Utilities test completed\n")


def test_config_loading():
    """Test configuration loading."""
    print("Testing Configuration Loading...")

    from scripts.pipeline_utils import load_config, save_config
    import json

    # Test saving and loading a simple config
    test_config = {
        "version": "1.0.0",
        "test": "value",
        "numbers": [1, 2, 3]
    }

    save_config(test_config, "test_config.json")
    loaded = load_config("test_config.json")

    print(f"Original config: {test_config}")
    print(f"Loaded config: {loaded}")

    # Clean up
    if os.path.exists("test_config.json"):
        os.remove("test_config.json")

    print("Configuration Loading test completed\n")


if __name__ == "__main__":
    print("Running pipeline component tests...\n")

    try:
        test_is_number_manager()
        test_pipeline_utils()
        test_config_loading()

        print("All tests completed successfully!")

    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)