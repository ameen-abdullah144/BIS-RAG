#!/usr/bin/env python3
"""
Test script to run KYS collector on all 5 IS numbers from config
"""

import json
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from collectors.kys import KYSCollector

def main():
    # Load the niche configuration
    config_path = os.path.join("config", "niches", "water_heaters.json")

    with open(config_path, 'r') as f:
        config = json.load(f)

    print(f"Testing KYS collection for niche: {config['niche']}")
    print(f"IS numbers to process: {len(config['is_numbers'])}")
    print("=" * 50)

    # Initialize the KYS collector
    collector = KYSCollector()

    # Process each IS number
    for i, is_info in enumerate(config['is_numbers'], 1):
        is_number = is_info['is_number']
        print(f"\n[{i}/{len(config['is_numbers'])}] Processing: {is_number}")
        print(f"Title: {is_info['title']}")

        try:
            # Collect metadata for this IS number
            result = collector.collect_standard_metadata(is_info)

            if result:
                print(f"  [SUCCESS] Successfully collected metadata for {is_number}")
                print(f"  Title: {result.get('title', 'N/A')}")
                print(f"  Status: {result.get('collection_status', {}).get('metadata', 'unknown')}")
            else:
                print(f"  [ERROR] Failed to collect metadata for {is_number}")

        except Exception as e:
            print(f"  [ERROR] Error processing {is_number}: {str(e)}")

    print("\n" + "=" * 50)
    print("KYS collection test completed.")

    # Check what metadata files were created
    print("\nChecking created metadata files:")
    storage_dir = os.path.join("storage", "data")
    if os.path.exists(storage_dir):
        is_dirs = [d for d in os.listdir(storage_dir) if d.startswith("IS_")]
        for is_dir in sorted(is_dirs):
            metadata_file = os.path.join(storage_dir, is_dir, "metadata.json")
            if os.path.exists(metadata_file):
                print(f"  [FOUND] {metadata_file}")
            else:
                print(f"  [MISSING] {metadata_file}")
    else:
        print("  No storage directory found")

if __name__ == "__main__":
    main()