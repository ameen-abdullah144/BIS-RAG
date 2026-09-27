#!/usr/bin/env python3
"""
Test script to run Product Manuals collector on all 5 IS numbers from config
"""

import json
import sys
import os
import time
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from collectors.product_manuals import ProductManualCollector

def get_storage_directory(is_info):
    """Convert IS info to storage directory name based on actual structure."""
    doc_no = is_info['doc_no']
    part = is_info.get('part')
    section = is_info.get('section')

    if part is not None and section is not None:
        # For parts like IS 302 (Part 2/Sec 21):2018
        return f"IS_{doc_no}_Part_{part}_Sec_{section}"
    else:
        # For standard IS numbers like IS 2082:2018
        return f"IS_{doc_no}"

def main():
    # Load the niche configuration
    config_path = os.path.join("config", "niches", "water_heaters.json")

    with open(config_path, 'r') as f:
        config = json.load(f)

    print(f"Testing Product Manuals collection for niche: {config['niche']}")
    print(f"IS numbers to process: {len(config['is_numbers'])}")
    print("=" * 60)

    # Initialize the Product Manuals collector
    collector = ProductManualCollector(storage_base="storage/data", delay=1.5)

    # Process each IS number
    for i, is_info in enumerate(config['is_numbers'], 1):
        is_number = is_info['is_number']
        dir_name = get_storage_directory(is_info)
        print(f"\n[{i}/{len(config['is_numbers'])}] Processing: {is_number}")
        print(f"Title: {is_info['title']}")
        print(f"Storage directory: {dir_name}")

        # Load existing metadata for this IS number
        metadata_path = os.path.join("storage", "data", dir_name, "metadata.json")

        if not os.path.exists(metadata_path):
            print(f"  [ERROR] Metadata file not found: {metadata_path}")
            print(f"  [INFO] Please run KYS collector first for this IS number")
            continue

        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)

            print(f"  Loaded metadata for: {metadata['is_number']}")

            # Run the collector
            print(f"  Running Product Manuals collector...")
            updated_metadata = collector.collect_manuals(metadata)

            if updated_metadata:
                print(f"  [SUCCESS] Product Manuals collection completed for {is_number}")

                # Check if PDFs were found
                product_manuals = updated_metadata.get("product_manuals", [])
                if product_manuals:
                    print(f"  [INFO] Found {len(product_manuals)} product manual(s)")
                    for j, pm in enumerate(product_manuals):
                        local_path = pm.get("local_path", "Unknown")
                        status = pm.get("status", "Unknown")
                        sha256 = pm.get("sha256", "Unknown")[:16] + "..." if pm.get("sha256") else "None"
                        print(f"    [{j+1}] {os.path.basename(local_path)} - Status: {status}, SHA-256: {sha256}")

                        # Verify file exists
                        if os.path.exists(local_path):
                            file_size = os.path.getsize(local_path)
                            print(f"        File size: {file_size} bytes")
                        else:
                            print(f"        [WARNING] File not found on disk: {local_path}")
                else:
                    print(f"  [INFO] No product manuals found for {is_number}")

                # Show collection status
                coll_status = updated_metadata.get("collection_status", {})
                pm_status = coll_status.get("product_manual", "unknown")
                print(f"  [STATUS] Product Manual: {pm_status}")

                # Save updated metadata
                collector._save_json(updated_metadata, metadata_path)
                print(f"  [INFO] Updated metadata saved to {metadata_path}")

            else:
                print(f"  [ERROR] Failed to collect product manuals for {is_number}")
                print(f"  [INFO] Errors recorded: {collector.get_errors()}")

        except Exception as e:
            print(f"  [ERROR] Error processing {is_number}: {str(e)}")
            import traceback
            traceback.print_exc()

        # Add delay between IS numbers to be extra safe with rate limits
        if i < len(config['is_numbers']):
            print(f"  [INFO] Waiting 2 seconds before next IS number...")
            time.sleep(2)

    print("\n" + "=" * 60)
    print("Product Manuals collection test completed.")

    # Summary of what was collected
    print("\nSummary of collected Product Manuals:")
    storage_dir = os.path.join("storage", "data")
    if os.path.exists(storage_dir):
        is_dirs = [d for d in os.listdir(storage_dir) if d.startswith("IS_")]
        for is_dir in sorted(is_dirs):
            metadata_file = os.path.join(storage_dir, is_dir, "metadata.json")
            if os.path.exists(metadata_file):
                try:
                    with open(metadata_file, "r", encoding="utf-8") as f:
                        metadata = json.load(f)
                    is_number = metadata.get("is_number", "Unknown")
                    pm_status = metadata.get("collection_status", {}).get("product_manual", "unknown")
                    pdf_count = len(metadata.get("product_manuals", []))
                    print(f"  {is_number}: Product Manuals = {pm_status} ({pdf_count} PDFs)")
                except Exception as e:
                    print(f"  {is_dir}: Error reading metadata - {e}")
            else:
                print(f"  {is_dir}: No metadata file found")

if __name__ == "__main__":
    main()