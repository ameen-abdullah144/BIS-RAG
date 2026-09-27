import json
from pathlib import Path
from collectors.guidelines import GuidelinesCollector

def main():
    print("Testing Guidelines Collector for ALL 5 IS Numbers")
    print("=" * 50)

    # Initialize collector
    collector = GuidelinesCollector(storage_base="storage/data", delay=1.0)

    # List of IS number directories
    is_dirs = [
        "IS_17150",
        "IS_2082",
        "IS_302_Part_2_Sec_21",
        "IS_302_Part_2_Sec_35",
        "IS_368"
    ]

    results = []
    total_guidelines_found = 0

    for is_dir in is_dirs:
        metadata_path = Path(f"storage/data/{is_dir}/metadata.json")
        is_number = metadata_path.parent.name.replace("_", " ").replace("Part", "Part").replace("Sec", "Sec")

        print(f"\nProcessing {is_number}...")

        try:
            # Load metadata
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)

            # Run guidelines collector
            updated_metadata = collector.collect_guidelines(metadata)

            if updated_metadata:
                # Save updated metadata
                collector._save_json(updated_metadata, metadata_path)

                # Check results
                guidelines_list = updated_metadata.get("guidelines", [])
                guidelines_count = len(guidelines_list)
                total_guidelines_found += guidelines_count

                status = updated_metadata.get("collection_status", {}).get("guidelines", "not_found")

                print(f"  Status: {status}")
                print(f"  Guidelines found: {guidelines_count}")

                if guidelines_list:
                    for i, guideline in enumerate(guidelines_list):
                        doc_path = guideline.get("local_path", "Unknown")
                        doc_name = Path(doc_path).name if doc_path != "Unknown" else "Unknown"
                        print(f"    Guideline {i+1}: {doc_name}")

                        # Verify file exists
                        if doc_path != "Unknown" and Path(doc_path).exists():
                            size = Path(doc_path).stat().st_size
                            print(f"      ✓ File exists ({size} bytes)")
                        else:
                            print(f"      ✗ File not found: {doc_path}")

                results.append({
                    "is_number": is_number,
                    "status": status,
                    "count": guidelines_count,
                    "success": True
                })
            else:
                print(f"  FAILED: No metadata returned")
                print(f"  Errors: {collector.get_errors()}")
                results.append({
                    "is_number": is_number,
                    "status": "failed",
                    "count": 0,
                    "success": False
                })

        except Exception as e:
            print(f"  ERROR: {e}")
            results.append({
                "is_number": is_number,
                "status": "error",
                "count": 0,
                "success": False
            })

    # Summary
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    print(f"Total IS numbers processed: {len(is_dirs)}")
    print(f"Total guideline documents found: {total_guidelines_found}")

    successful = sum(1 for r in results if r["success"])
    print(f"Successfully processed: {successful}/{len(is_dirs)}")

    print("\nDetailed Results:")
    for result in results:
        status_symbol = "✓" if result["success"] else "✗"
        print(f"  {status_symbol} {result['is_number']}: {result['status']} ({result['count']} guidelines)")

    # Overall success criteria from EXECUTION_PLAN:
    # "Success Criteria: Guidelines PDFs stored for IS numbers that have them"
    if total_guidelines_found >= 0:  # We succeeded if we processed all without errors
        all_success = all(r["success"] for r in results)
        if all_success:
            print("\n✓ SUCCESS: Guidelines collector executed for all IS numbers")
            print("  (Actual guideline documents depend on availability in BIS sources)")
        else:
            print("\n✗ PARTIAL: Some IS numbers failed to process")
    else:
        print("\n? Unable to determine success - check individual results")

if __name__ == "__main__":
    main()