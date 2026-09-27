import json
from pathlib import Path
from collectors.guidelines import GuidelinesCollector

def main():
    print("Testing Guidelines Collector for IS 2082")

    # Load existing metadata from storage
    metadata_path = Path("storage/data/IS_2082/metadata.json")
    if not metadata_path.exists():
        print(f"ERROR: {metadata_path} not found. Run verify_kys_single.py first.")
        return

    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    # Initialize collector
    collector = GuidelinesCollector(storage_base="storage/data", delay=1.0)

    # Run the collector
    updated_metadata = collector.collect_guidelines(metadata)

    if updated_metadata:
        print("\nSUCCESS! Updated Metadata:")
        guidelines_info = updated_metadata.get("guidelines", "Not found or error")
        print(f"Guidelines: {json.dumps(guidelines_info, indent=2)}")

        # Check if guidelines were found and saved
        if updated_metadata.get("guidelines"):
            guidelines_list = updated_metadata["guidelines"]
            if guidelines_list:
                first_guideline = guidelines_list[0]
                expected_pdf = Path(first_guideline["local_path"])
                if expected_pdf.exists():
                    print(f"\nVerified: Guideline PDF downloaded at {expected_pdf} ({expected_pdf.stat().st_size} bytes)")
                    print(f"SHA-256: {first_guideline.get('sha256', 'Not available')}")
                else:
                    print(f"\nINFO: Guideline PDF not downloaded (may not be available for this IS number)")
                    print(f"Expected path: {expected_pdf}")
            else:
                print("\nINFO: No guideline documents found for this IS number (empty list)")
        else:
            print("\nINFO: No guidelines field in metadata (collection may not have run or found nothing)")

        # Show collection status
        collection_status = updated_metadata.get("collection_status", {})
        guidelines_status = collection_status.get("guidelines", "not_found")
        print(f"\nGuidelines collection status: {guidelines_status}")
    else:
        print("\nFAILED: No metadata returned.")
        print("Errors recorded:", collector.get_errors())

if __name__ == "__main__":
    main()