import json
from pathlib import Path
from collectors.product_manuals import ProductManualCollector

def main():
    print("Testing FIXED Product Manual Collector for IS 2082")

    # Load existing metadata from checkpoint 1
    metadata_path = Path("storage/data/IS_2082/metadata.json")
    if not metadata_path.exists():
        print(f"ERROR: {metadata_path} not found. Run verify_kys_single.py first.")
        return

    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    print(f"Loaded metadata for: {metadata['is_number']}")
    print(f"Standard ID (numeric): {metadata.get('standard_id')}")
    print(f"Standard Enc ID: {metadata.get('standard_enc_id')[:50]}...")

    # Initialize collector
    collector = ProductManualCollector(storage_base="storage/data", delay=1.0)

    # Temporarily override the standard_id to use the encrypted version for testing
    # This is what we need to fix in the actual collector
    original_standard_id = metadata.get("standard_id")
    metadata["standard_id"] = metadata.get("standard_enc_id")  # Use encrypted ID

    print("\nUsing encrypted ID in standardId field for API call...")

    # Run the collector
    updated_metadata = collector.collect_manuals(metadata)

    # Restore original value
    metadata["standard_id"] = original_standard_id

    if updated_metadata:
        print("\nSUCCESS! Updated Metadata:")
        product_manuals = updated_metadata.get("product_manuals", "Not found or error")
        print(json.dumps(product_manuals, indent=2))

        # Check if PDF saved to disk
        if updated_metadata.get("product_manuals"):
            expected_pdf = Path(updated_metadata["product_manuals"][0]["local_path"])
            if expected_pdf.exists():
                print(f"\nVerified: PDF downloaded at {expected_pdf} ({expected_pdf.stat().st_size} bytes)")

                # Also check if metadata was updated
                if expected_pdf.parent.exists():
                    print("Documents directory created successfully")
            else:
                print(f"\nERROR: Expected PDF at {expected_pdf} not found!")
        else:
            print("\nNo product manuals found in returned metadata")
    else:
        print("\nFAILED: No metadata returned.")
        print("Errors recorded:", collector.get_errors())

if __name__ == "__main__":
    main()