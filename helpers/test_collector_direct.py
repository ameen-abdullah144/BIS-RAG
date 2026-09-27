import json
from pathlib import Path
from collectors.product_manuals import ProductManualCollector

def main():
    print("Testing Product Manuals Collector Directly")

    # Load metadata
    metadata_path = Path("storage/data/IS_2082/metadata.json")
    if not metadata_path.exists():
        print(f"ERROR: {metadata_path} not found. Run verify_kys_single.py first.")
        return

    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    print(f"Loaded metadata for: {metadata['is_number']}")
    print(f"Standard ID: {metadata.get('standard_id')}")
    print(f"Standard Enc ID: {metadata.get('standard_enc_id')[:50]}...")

    # Initialize collector
    collector = ProductManualCollector(storage_base="storage/data", delay=1.0)

    # Run the collector
    print("\nRunning collector...")
    updated_metadata = collector.collect_manuals(metadata)

    if updated_metadata:
        print("\nSUCCESS! Updated Metadata Received:")
        print(f"Collection status: {updated_metadata.get('collection_status')}")
        product_manuals = updated_metadata.get("product_manuals")
        print(f"Product manuals: {product_manuals}")

        if product_manuals:
            print(f"Number of product manuals: {len(product_manuals)}")
            for i, pm in enumerate(product_manuals):
                print(f"  PM {i+1}: {pm.get('documentName', 'Unknown')} - {pm.get('local_path', 'No path')}")
        else:
            print("No product_manuals field in metadata")

        # Check if PDF saved to disk
        if product_manuals and len(product_manuals) > 0:
            first_pm = product_manuals[0]
            local_path = first_pm.get("local_path")
            if local_path:
                expected_pdf = Path(local_path)
                if expected_pdf.exists():
                    print(f"\nVerified: PDF downloaded at {expected_pdf} ({expected_pdf.stat().st_size} bytes)")
                else:
                    print(f"\nPDF file not found at: {expected_pdf}")
            else:
                print("No local_path in first product manual")
    else:
        print("\nFAILED: No metadata returned.")
        print("Errors recorded:", collector.get_errors())

if __name__ == "__main__":
    main()