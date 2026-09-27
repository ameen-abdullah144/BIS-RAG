"""
Test Laboratories Collector for a SINGLE IS Number: IS 2082
"""
import json
from pathlib import Path
from collectors.labs import LaboratoriesCollector

def main():
    print("Testing Laboratories Collector for IS 2082")

    # Load existing metadata from KYS collection (run verify_kys_single.py first)
    metadata_path = Path("storage/data/IS_2082/metadata.json")
    if not metadata_path.exists():
        print(f"ERROR: {metadata_path} not found. Run verify_kys_single.py first.")
        return

    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    # Initialize collector
    collector = LaboratoriesCollector(storage_base="storage/data", delay=1.0)

    # Run the collector
    updated_metadata = collector.collect_laboratories(metadata)

    if updated_metadata:
        print("\nSUCCESS! Updated Metadata:")
        labs_status = updated_metadata.get("collection_status", {}).get("laboratories", "not_found")
        print(f"Laboratories Collection Status: {labs_status}")

        laboratories = updated_metadata.get("laboratories", [])
        if laboratories:
            print(f"Found {len(laboratories)} laboratory facilities:")
            for lab in laboratories[:3]:  # Show first 3
                print(f"  - {lab.get('name', 'Unknown')} (ID: {lab.get('laboratory_id', 'N/A')})")
            if len(laboratories) > 3:
                print(f"  ... and {len(laboratories) - 3} more")
        else:
            print("No laboratory facilities found")

        # Check if saved to disk
        if Path("storage/data/IS_2082/metadata.json").exists():
            print(f"\nVerified: Metadata file saved at storage/data/IS_2082/metadata.json")
        else:
            print(f"\nERROR: Expected metadata file not found!")
    else:
        print("\nFAILED: No metadata returned.")
        print("Errors recorded:", collector.get_errors())

if __name__ == "__main__":
    main()