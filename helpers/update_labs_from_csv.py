#!/usr/bin/env python3
"""
Update laboratory data in metadata.json files from CSV files.
"""
import os
import json
import csv
from datetime import datetime, timezone
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

    # Parse IS number components for URL construction
    is_number = metadata["is_number"]
    doc_no = metadata.get("doc_no", "")
    year = metadata.get("year", "")
    part = metadata.get("part", "")
    section = metadata.get("section", "")

    # Build LIMS source URL for these lab records
    LIMS_URL = "https://lims.bis.gov.in/home/search_is_number/"
    params = {
        "is_number__doc_no": doc_no,
        "is_number__year": year,
        "is_number__part": part,
        "is_number__section": section,
        "lab__lab_name__icontains": "",
        "is_title": ""
    }
    from urllib.parse import urlencode
    query_string = urlencode(params)
    source_url = f"{LIMS_URL}?{query_string}" if query_string else LIMS_URL

    # Process CSV file
    laboratories = []
    tested_by_relations = []

    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            # Use csv.reader to handle quoted fields properly
            reader = csv.DictReader(f)

            for row_num, row in enumerate(reader, start=2):  # Start at 2 for header row
                # Skip empty rows
                if not any(row.values()):
                    continue

                # Extract lab name and OSL code
                lab_name = row.get("Lab Name", "").strip()
                osl_code = row.get("Osl Code", "").strip()

                # Skip if no lab name or code
                if not lab_name and not osl_code:
                    continue

                # Create laboratory record
                lab_record = {
                    "laboratory_id": osl_code or f"LAB_{len(laboratories) + 1}",
                    "name": lab_name,
                    "address": "",  # Not available in CSV
                    "contact": "",  # Not available in CSV
                    "email": "",    # Not available in CSV
                    "website": "",  # Not available in CSV
                    "status": "",   # Not available in CSV
                    "source_url": source_url,
                    "retrieved_at": datetime.now(timezone.utc).isoformat(),
                    "raw_data": {
                        "is_number": is_number,
                        "lab_name": lab_name,
                        "lab_code": osl_code,
                        "is_number_from_table": row.get("Indian Standard No.", ""),
                        "product": row.get("Product", ""),
                        "grade_type_size": row.get("Grade / Type / Size / Designation etc.", ""),
                        "testing_charges": row.get("Testing Charges (Excl. Of Taxes)", ""),
                        "validity_date": row.get("Validity Date", ""),
                        "remark": row.get("Remark", "")
                    }
                }

                laboratories.append(lab_record)

                # Create TESTED_BY relationship
                tested_by_relations.append({
                    "source_id": is_number,
                    "relationship": "TESTED_BY",
                    "target_id": f"LAB_{lab_record['laboratory_id']}",
                    "target_type": "laboratory",
                    "lab_name": lab_name,
                    "lab_id": lab_record["laboratory_id"]
                })

    except Exception as e:
        print(f"  ERROR processing CSV: {e}")
        return False

    if not laboratories:
        print(f"  WARNING: No valid laboratory records found in CSV")
        return False

    # Update metadata
    metadata["collection_status"]["laboratories"] = "available"
    metadata["laboratories"] = laboratories

    # Handle TESTED_BY relationships
    if "tested_by_relations" not in metadata:
        metadata["tested_by_relations"] = []
    else:
        # Remove any existing TESTED_BY relationships for this IS number to avoid duplicates
        metadata["tested_by_relations"] = [
            rel for rel in metadata["tested_by_relations"]
            if rel.get("source_id") != is_number
        ]

    metadata["tested_by_relations"].extend(tested_by_relations)

    # Save updated metadata
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print(f"  SUCCESS: Updated {len(laboratories)} laboratory records")
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