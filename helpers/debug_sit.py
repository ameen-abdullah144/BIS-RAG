import json
from pathlib import Path
from collectors.sit import SITCollector
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

def main():
    print("Debugging SIT Collector for IS 2082")

    # Load existing metadata
    metadata_path = Path("storage/data/IS_2082/metadata.json")
    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    print(f"Loaded metadata for: {metadata['is_number']}")
    print(f"Initial SIT status: {metadata.get('collection_status', {}).get('sit', 'MISSING')}")

    # Initialize collector
    collector = SITCollector(storage_base="storage/data", delay=1.0)

    # Run the collector
    print("\nCalling collect_sit_documents...")
    updated_metadata = collector.collect_sit_documents(metadata)

    if updated_metadata:
        print("\nSUCCESS! Got updated metadata:")
        sit_status = updated_metadata.get("collection_status", {}).get("sit", "not_found")
        print(f"SIT Collection Status: {sit_status}")

        sit_documents = updated_metadata.get("sit_documents", [])
        print(f"SIT Documents Found: {len(sit_documents)}")

        if sit_documents:
            for i, doc in enumerate(sit_documents):
                print(f"  Document {i+1}: {doc.get('document_id')} - {doc.get('status')}")
    else:
        print("\nFAILED: No metadata returned.")
        print("Errors recorded:", collector.get_errors())

    # Check what's actually on disk now
    print("\n" + "="*50)
    print("Checking disk metadata:")
    try:
        with open(metadata_path, "r", encoding="utf-8") as f:
            disk_metadata = json.load(f)
        disk_sit_status = disk_metadata.get("collection_status", {}).get("sit", "MISSING")
        print(f"Disk SIT status: {disk_sit_status}")

        if "sit_documents" in disk_metadata:
            print(f"Disk SIT documents: {len(disk_metadata['sit_documents'])}")
        else:
            print("No sit_documents array in disk metadata")

    except Exception as e:
        print(f"Error reading disk metadata: {e}")

if __name__ == "__main__":
    main()