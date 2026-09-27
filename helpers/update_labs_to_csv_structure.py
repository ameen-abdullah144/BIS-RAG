#!/usr/bin/env python3
"""
Update laboratory data in metadata.json files to match CSV structure exactly.
Replace the laboratories array with objects having keys as CSV headers.
"""
import os
import json
import csv
from pathlib import Path

def process_is_directory(is_dir):
    """Process a single IS directory and update its metadata with lab data from CSV."""
    is_dir_path = Path(is_dir)
    metadata_path = is_dir_path / "metadata.json"
    docs_dir = is_dir_path / "documents"

    if not metadata_path.exists():
        print(f"  SKIPPING: No metadata.json found in {is_dir}")
        return False

    # Find CSV file in documents directory
    csv_files = list(docs_dir.glob("* Labs - Sheet1.csv")) if docs_dir.exists() else []
    if not csv_files:
        print(f"  SKIPPING: No CSV file found in {docs_dir}")
        return False

    csv_path = csv_files[0]
    print(f"  Processing {csv_path.name}")

    # Load existing metadata
    with open(metadata_path, 'r', encoding='utf-8') as f:
        metadata = json.load(f)

    # Process CSV file
    laboratories = []

    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            # Use csv.reader to get rows
            reader = csv.reader(f)
            headers = None
            for row in reader:
                if headers is None:
                    # First row is header
                    headers = [cell.strip() for cell in row]
                    continue
                # Skip empty rows
                if not any(cell.strip() for cell in row):
                    continue
                # Create object with header keys
                lab_obj = {}
                for i, header in enumerate(headers):
                    # If row has fewer columns, use empty string
                    value = row[i].strip() if i < len(row) else ""
                    lab_obj[header] = value
                laboratories.append(lab_obj)

    except Exception as e:
        print(f"  ERROR processing CSV: {e}")
        return False

    if not laboratories:
        print(f"  WARNING: No valid laboratory records found in CSV")
        return False

    # Update metadata: replace laboratories array
    metadata["collection_status"]["laboratories"] = "available"
    metadata["laboratories"] = laboratories

    # Note: We are not modifying tested_by_relations as per user request?
    # The user only asked to change the labs part. We'll leave tested_by_relations as is.
    # However, if we want to be consistent, we might need to update tested_by_relations
    # to match the new lab IDs? But the user didn't ask for that.
    # We'll keep it unchanged.

    # Save updated metadata
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print(f"  SUCCESS: Updated {len(laboratories)} laboratory records with CSV structure")
    return True

def main():
    """Process all IS directories in storage/data."""
    storage_dir = Path("storage/data")
    if not storage_dir.exists():
        print("ERROR: storage/data directory not found")
        return

    # Get all IS_* directories
    is_dirs = [d for d in storage_dir.iterdir()
               if d.is_dir() and d.name.startswith("IS_")]

    if not is_dirs:
        print("ERROR: No IS_* directories found in storage/data")
        return

    print(f"Found {len(is_dirs)} IS directories to process:")
    for is_dir in is_dirs:
        print(f"  - {is_dir.name}")

    print("\nProcessing...")
    success_count = 0

    for is_dir in sorted(is_dirs):
        print(f"\nProcessing {is_dir.name}:")
        if process_is_directory(is_dir):
            success_count += 1

    print(f"\n=== SUMMARY ===")
    print(f"Successfully processed: {success_count}/{len(is_dirs)} directories")

    if success_count == len(is_dirs):
        print("All IS directories updated successfully!")
    else:
        print(f"{len(is_dirs) - success_count} directories failed to process")

if __name__ == "__main__":
    main()