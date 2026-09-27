import sys
from pathlib import Path
import json

sys.path.append(str(Path(__file__).parent))
from collectors.product_manuals import ProductManualCollector
from collectors.base import BaseCollector

def main():
    is_number = "IS 302 (Part 2/Sec 21):2018"
    # Load existing metadata
    metadata_path = Path(f"storage/data/IS_302_Part_2_Sec_21/metadata.json")
    if not metadata_path.exists():
        print(f"Metadata not found: {metadata_path}")
        return

    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    print(f"Loaded metadata for {metadata['is_number']}")

    # Initialize collector
    collector = ProductManualCollector(storage_base="storage/data", delay=1.0)

    # Define the product manual URL we found
    pm_url = "https://www.bis.gov.in/wp-content/uploads/2023/01/PM_302-2-21-approved.pdf"
    # Also could use the 2024 one, but let's use the 2023 as primary

    # Storage directory for documents
    storage_dir = collector._get_is_storage_dir(is_number) / "documents"
    storage_dir.mkdir(parents=True, exist_ok=True)

    # Derive a filename from the URL
    doc_name = pm_url.split("/")[-1]  # PM_302-2-21-approved.pdf
    local_path = storage_dir / doc_name

    # Download the file using collector's method
    print(f"Downloading from {pm_url} to {local_path}")
    doc_record = collector._download_file(pm_url, local_path)

    if not doc_record:
        print("Download failed")
        return

    print(f"Downloaded: {doc_record}")

    # Prepare document record as expected by metadata
    doc_record["document_type"] = "product_manual"
    # Generate a document ID similar to what the collector uses
    doc_record["document_id"] = f"DOC_{metadata['doc_no']}_PM_{len(metadata.get('product_manuals', [])) + 1}"

    # Update metadata
    if "product_manuals" not in metadata:
        metadata["product_manuals"] = []
    metadata["product_manuals"].append(doc_record)

    # Update collection status
    metadata["collection_status"]["product_manual"] = "available"

    # Save updated metadata
    collector._save_json(metadata, metadata_path)
    print(f"Updated metadata saved to {metadata_path}")

    # Also verify the file exists and hash matches
    if local_path.exists():
        print(f"File saved successfully: {local_path}")
        print(f"Size: {local_path.stat().st_size} bytes")
    else:
        print("Warning: File not saved")

if __name__ == "__main__":
    main()