import json
from pathlib import Path
from collectors.qco import QcoCollector

def main():
    print("Testing QCO Collector for IS 2082")

    # Load existing metadata
    metadata_path = Path("storage/data/IS_2082/metadata.json")
    if not metadata_path.exists():
        print(f"ERROR: {metadata_path} not found. Run verify_kys_single.py first.")
        return

    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    # Initialize collector
    collector = QcoCollector(storage_base="storage/data", delay=1.0)

    # Run the collector
    updated_metadata = collector.collect_qco(metadata)

    if updated_metadata:
        print("\nSUCCESS! Updated Metadata:")
        qco_status = updated_metadata.get("collection_status", {}).get("qco_gazette", "not_found")
        print(f"QCO Collection Status: {qco_status}")

        qco_docs = updated_metadata.get("qco_gazettes", [])
        if qco_docs:
            print(f"Found {len(qco_docs)} QCO documents:")
            for doc in qco_docs:
                print(f"  - {doc.get('document_id')}: {doc.get('local_path')} ({doc.get('status')})")
        else:
            print("No QCO documents found (status: not_found or empty)")

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