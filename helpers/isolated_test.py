"""
Isolated test of ProductManualCollector to verify embedded SIT detection.
"""
import json
import sys
from pathlib import Path
from collectors.product_manuals import ProductManualCollector

def main():
    print("Isolated Test of Product Manual Collector with Embedded SIT Detection")
    print("=" * 70)

    # Create minimal metadata for IS 2082:2018 (simulating what KYS would produce)
    metadata = {
        "is_number": "IS 2082:2018",
        "doc_no": "2082",
        "part": None,
        "section": None,
        "year": "2018",
        "title": "Stationary Storage Type Electric Water Heaters - Specification",
        "class": "CORE",
        "fuel_type": "electric",
        "standard_enc_id": "eyJpdiI6Ik1OekVmNUo0QmNIMjU3VWV5aFRKYmc9PSIsInZhbHVlIjoiMEN6dTBtRlVDK3lNLzdud01CTmx4QT09IiwibWFjIjoiN2MzNWIwYjAxYTIwZTZjMDE2MjYwY2UxNzI4NDY3NWU4N2I0ZDJlNGZiZTg0N2IxNjM0MWE4NTQ1MWE1ZTFmNiIsInRhZyI6IiJ9",  # Use a known good one
        "standard_id": 18707,
        "collection_status": {
            "metadata": "available",
            "product_manual": "pending",
            "sit": "pending",
            "amendments": "pending",
            "qco_gazette": "pending",
            "laboratories": "pending"
        }
    }

    print(f"Input metadata for: {metadata['is_number']}")
    print(f"Initial SIT status: {metadata.get('collection_status', {}).get('sit', 'not_set')}")

    # Initialize collector
    collector = ProductManualCollector(storage_base="storage/data", delay=1.0)

    # Run the collector
    print("\nRunning product manual collector...")
    updated_metadata = collector.collect_manuals(metadata)

    if updated_metadata:
        print("\nSUCCESS! Collector returned metadata:")
        sit_status = updated_metadata.get("collection_status", {}).get("sit", "not_set")
        print(f"SIT Collection Status: {sit_status}")

        product_manuals = updated_metadata.get("product_manuals", [])
        if product_manuals:
            print(f"Found {len(product_manuals)} product manual(s):")
            for doc in product_manuals:
                print(f"  - {doc.get('document_id')}: {doc.get('local_path')} ({doc.get('status')})")
        else:
            print("No product manuals found in returned metadata")

        # Check what was saved to disk
        metadata_path = Path("storage/data/IS_2082/metadata.json")
        if metadata_path.exists():
            print(f"\nChecking metadata saved to disk at {metadata_path}:")
            with open(metadata_path, "r", encoding="utf-8") as f:
                saved_metadata = json.load(f)
            saved_sit_status = saved_metadata.get("collection_status", {}).get("sit", "not_set")
            print(f"SIT status in saved metadata: {saved_sit_status}")
        else:
            print(f"\nERROR: Metadata file not found at {metadata_path}!")
    else:
        print("\nFAILED: No metadata returned from collector.")
        print("Errors recorded:", collector.get_errors())

if __name__ == "__main__":
    main()