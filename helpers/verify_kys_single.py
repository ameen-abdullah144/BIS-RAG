import json
from pathlib import Path
from collectors.kys import KYSCollector

def main():
    print("Testing KYS Collector for a SINGLE IS Number: IS 2082")
    
    # Target IS 2082
    test_entry = {
      "is_number": "IS 2082:2018",
      "doc_no": "2082",
      "part": None,
      "section": None,
      "year": "2018",
      "title": "Stationary Storage Type Electric Water Heaters - Specification",
      "class": "CORE",
      "fuel_type": "electric"
    }

    # Initialize collector with local storage dir
    collector = KYSCollector(storage_base="storage/data", delay=1.0)
    
    # Run the collector
    metadata = collector.collect_standard_metadata(test_entry)
    
    if metadata:
        print("\nSUCCESS! Extracted Metadata:")
        print(json.dumps(metadata, indent=2))
        
        # Check if saved to disk
        expected_path = Path("storage/data/IS_2082/metadata.json")
        if expected_path.exists():
            print(f"\nVerified: File saved at {expected_path}")
        else:
            print(f"\nERROR: Expected file at {expected_path} not found!")
    else:
        print("\nFAILED: No metadata returned.")
        print("Errors recorded:", collector.get_errors())

if __name__ == "__main__":
    main()
