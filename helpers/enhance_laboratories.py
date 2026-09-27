#!/usr/bin/env python3
"""
Laboratories data enhancement script for Phase 2 Step 4.
Enhances laboratories data for all IS numbers in water heaters niche using LIMS.
"""
import json
import os
from pathlib import Path
from collectors.labs import LaboratoriesCollector

def main():
    print("Phase 2 Step 4: Laboratories Data Enhancement")
    print("=" * 50)

    # Load niche config to get expected IS numbers
    config_path = Path("config/niches/water_heaters.json")
    if not config_path.exists():
        print("ERROR: Config file not found at config/niches/water_heaters.json")
        return False

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    expected_is_numbers = [entry["is_number"] for entry in config["is_numbers"]]
    print(f"Enhancing laboratories data for {len(expected_is_numbers)} IS numbers:")
    for is_num in expected_is_numbers:
        print(f"  - {is_num}")

    # Initialize laboratories collector
    collector = LaboratoriesCollector(storage_base="storage/data", delay=1.0)

    print("\nProcessing IS numbers...")
    print("-" * 50)

    success_count = 0
    total_labs_found = 0

    for is_number in expected_is_numbers:
        # Parse IS number to determine directory name format
        if ":" in is_number:
            base_part = is_number.split(":")[0].strip()
        else:
            base_part = is_number.strip()
        # Convert to directory name format
        # Replace spaces with underscores, remove parentheses, replace forward slashes with underscores
        dir_name = base_part.replace(" ", "_").replace("(", "").replace(")", "").replace("/", "_")

        metadata_path = Path(f"storage/data/{dir_name}/metadata.json")

        if not metadata_path.exists():
            print(f"SKIPPING {is_number}: metadata.json not found")
            continue

        try:
            # Load metadata
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)

            # Verify is_number matches
            if metadata["is_number"] != is_number:
                print(f"SKIPPING {is_number}: is_number mismatch in metadata")
                continue

            print(f"\nProcessing {is_number}:")

            # Collect laboratories data
            updated_metadata = collector.collect_laboratories(metadata)

            labs_count = len(updated_metadata.get("laboratories", []))
            status = updated_metadata.get("collection_status", {}).get("laboratories", "unknown")

            print(f"  Laboratories status: {status}")
            print(f"  Laboratories found: {labs_count}")

            if labs_count > 0:
                total_labs_found += labs_count
                # Show first lab as example
                first_lab = updated_metadata["laboratories"][0]
                print(f"  Example lab: {first_lab.get('name', 'N/A')} ({first_lab.get('laboratory_id', 'N/A')})")

            # Save updated metadata
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(updated_metadata, f, indent=2, ensure_ascii=False)

            print(f"  Metadata updated and saved")
            success_count += 1

        except Exception as e:
            print(f"  ERROR processing {is_number}: {e}")

    print("=" * 50)
    print("LABORATORIES ENHANCEMENT SUMMARY")
    print("=" * 50)
    print(f"IS numbers processed: {success_count}/{len(expected_is_numbers)}")
    print(f"Total laboratories found: {total_labs_found}")

    if success_count == len(expected_is_numbers):
        print("\nSUCCESS: Laboratories data enhanced for all IS numbers")
        return True
    else:
        print(f"\nPARTIAL SUCCESS: {len(expected_is_numbers) - success_count} IS numbers failed")
        return success_count > 0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)