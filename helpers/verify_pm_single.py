import json
from pathlib import Path
from collectors.product_manuals import ProductManualCollector

def main():
    print("Testing Product Manual Collector for IS 2082")
    
    # Load existing metadata from checkpoint 1
    metadata_path = Path("storage/data/IS_2082/metadata.json")
    if not metadata_path.exists():
        print(f"ERROR: {metadata_path} not found. Run verify_kys_single.py first.")
        return
        
    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)
        
    # Initialize collector
    collector = ProductManualCollector(storage_base="storage/data", delay=1.0)
    
    # Run the collector
    updated_metadata = collector.collect_manuals(metadata)
    
    if updated_metadata:
        print("\nSUCCESS! Updated Metadata:")
        print(json.dumps(updated_metadata.get("product_manuals", "Not found or error"), indent=2))
        
        # Check if PDF saved to disk
        if updated_metadata.get("product_manuals"):
            expected_pdf = Path(updated_metadata["product_manuals"][0]["local_path"])
            if expected_pdf.exists():
                print(f"\nVerified: PDF downloaded at {expected_pdf} ({expected_pdf.stat().st_size} bytes)")
            else:
                print(f"\nERROR: Expected PDF at {expected_pdf} not found!")
    else:
        print("\nFAILED: No metadata returned.")
        print("Errors recorded:", collector.get_errors())

if __name__ == "__main__":
    main()
