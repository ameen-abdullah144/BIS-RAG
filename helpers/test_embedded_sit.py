"""
Test script to verify embedded SIT detection in product manual collector.
"""
import json
import sys
from pathlib import Path
from collectors.product_manuals import ProductManualCollector

def main():
    print("Testing Product Manual Collector with Embedded SIT Detection")
    print("=" * 60)

    # Load existing metadata from KYS collection
    metadata_path = Path("storage/data/IS_2082/metadata.json")
    if not metadata_path.exists():
        print(f"ERROR: {metadata_path} not found. Run verify_kys_single.py first.")
        return

    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    print(f"Loaded metadata for: {metadata['is_number']}")
    print(f"Initial SIT status: {metadata.get('collection_status', {}).get('sit', 'not_set')}")

    # Initialize collector
    collector = ProductManualCollector(storage_base="storage/data", delay=1.0)

    # Run the collector
    print("\nRunning product manual collector...")
    updated_metadata = collector.collect_manuals(metadata)

    if updated_metadata:
        print("\nSUCCESS! Updated Metadata:")
        sit_status = updated_metadata.get("collection_status", {}).get("sit", "not_set")
        print(f"SIT Collection Status: {sit_status}")

        product_manuals = updated_metadata.get("product_manuals", [])
        if product_manuals:
            print(f"Found {len(product_manuals)} product manual(s):")
            for doc in product_manuals:
                print(f"  - {doc.get('document_id')}: {doc.get('local_path')} ({doc.get('status')})")
        else:
            print("No product manuals found")

        # Check if saved to disk
        if Path("storage/data/IS_2082/metadata.json").exists():
            print(f"\nVerified: Metadata file saved at storage/data/IS_2082/metadata.json")

            # Show the updated metadata
            with open("storage/data/IS_2082/metadata.json", "r", encoding="utf-8") as f:
                final_metadata = json.load(f)
            final_sit_status = final_metadata.get("collection_status", {}).get("sit", "not_set")
            print(f"Final SIT status in saved metadata: {final_sit_status}")
        else:
            print(f"\nERROR: Expected metadata file not found!")
    else:
        print("\nFAILED: No metadata returned.")
        print("Errors recorded:", collector.get_errors())

if __name__ == "__main__":
    main()