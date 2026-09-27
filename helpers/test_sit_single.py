import json
from pathlib import Path
from collectors.sit import SITCollector

def main():
    print("Testing SIT Collector for IS 2082")

    # Load existing metadata
    metadata_path = Path("storage/data/IS_2082/metadata.json")
    if not metadata_path.exists():
        print(f"ERROR: {metadata_path} not found. Run verify_kys_single.py first.")
        return

    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    # Initialize collector
    collector = SITCollector(storage_base="storage/data", delay=1.0)

    # Run the collector
    updated_metadata = collector.collect_sit_documents(metadata)

    if updated_metadata:
        print("\nSUCCESS! Updated Metadata:")
        sit_status = updated_metadata.get("collection_status", {}).get("sit", "not_found")
        print(f"SIT Collection Status: {sit_status}")

        sit_documents = updated_metadata.get("sit_documents", [])
        if sit_documents:
            print(f"Found {len(sit_documents)} SIT documents:")
            for doc in sit_documents:
                print(f"  - {doc.get('document_id')}: {doc.get('local_path')} ({doc.get('status')})")
        else:
            print("No SIT documents found (status: not_found or empty)")

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