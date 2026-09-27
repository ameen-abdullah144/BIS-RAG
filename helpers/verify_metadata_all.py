import json
from pathlib import Path

def main():
    print("Phase 1 Step 8: Check every IS_*/metadata.json")
    print("=" * 50)

    # Load niche config to get expected IS numbers
    config_path = Path("config/niches/water_heaters.json")
    if not config_path.exists():
        print("ERROR: Config file not found at config/niches/water_heaters.json")
        return False

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    expected_is_numbers = [entry["is_number"] for entry in config["is_numbers"]]
    print(f"Expected IS numbers from config: {len(expected_is_numbers)}")
    for is_num in expected_is_numbers:
        print(f"  - {is_num}")

    print("\nChecking metadata.json files...")
    print("-" * 50)

    all_good = True
    results = []

    for is_number in expected_is_numbers:
        # Parse IS number to determine directory name format
        # Examples:
        #   "IS 2082:2018" -> "IS_2082"
        #   "IS 302 (Part 2/Sec 21):2018" -> "IS_302_Part_2_Sec_21"
        #   "IS 17150:2019" -> "IS_17150"

        # Remove year (everything after last colon)
        if ":" in is_number:
            base_part = is_number.split(":")[0].strip()
        else:
            base_part = is_number.strip()

        # Convert to directory name format
        # Replace spaces with underscores, remove parentheses, replace forward slashes with underscores
        dir_name = base_part.replace(" ", "_").replace("(", "").replace(")", "").replace("/", "_")

        metadata_path = Path(f"storage/data/{dir_name}/metadata.json")

        status_text = f"Checking {is_number}..."
        print(status_text, end=" ")

        if not metadata_path.exists():
            print("MISSING")
            all_good = False
            results.append({
                "is_number": is_number,
                "status": "missing",
                "valid": False,
                "error": "File not found"
            })
            continue

        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)

            # Check for essential fields
            required_fields = ["is_number", "standard_id", "collection_status"]
            missing_fields = [field for field in required_fields if field not in metadata]

            if missing_fields:
                print(f"INVALID (missing fields: {', '.join(missing_fields)})")
                all_good = False
                results.append({
                    "is_number": is_number,
                    "status": "invalid",
                    "valid": False,
                    "error": f"Missing fields: {missing_fields}"
                })
                continue

            # Check if is_number matches
            if metadata["is_number"] != is_number:
                print(f"INVALID (is_number mismatch: expected {is_number}, got {metadata['is_number']})")
                all_good = False
                results.append({
                    "is_number": is_number,
                    "status": "invalid",
                    "valid": False,
                    "error": f"is_number mismatch: expected {is_number}, got {metadata['is_number']}"
                })
                continue

            # Check collection status
            collection_status = metadata.get("collection_status", {})
            status_summary = []
            for key, value in collection_status.items():
                if value in ["available", "not_found", "pending", "embedded_in_product_manual"]:
                    status_summary.append(f"{key}:{value}")

            print(f"OK ({', '.join(status_summary)})")
            results.append({
                "is_number": is_number,
                "status": "valid",
                "valid": True,
                "collection_status": collection_status
            })

        except json.JSONDecodeError as e:
            print(f"INVALID JSON: {e}")
            all_good = False
            results.append({
                "is_number": is_number,
                "status": "invalid_json",
                "valid": False,
                "error": str(e)
            })
        except Exception as e:
            print(f"ERROR: {e}")
            all_good = False
            results.append({
                "is_number": is_number,
                "status": "error",
                "valid": False,
                "error": str(e)
            })

    print("=" * 50)
    print("SUMMARY")
    print("=" * 50)
    print(f"Total IS numbers checked: {len(expected_is_numbers)}")

    valid_count = sum(1 for r in results if r["valid"])
    print(f"Valid metadata files: {valid_count}/{len(expected_is_numbers)}")

    if all_good:
        print("\nSUCCESS: All metadata.json files are present and valid")
    else:
        print("\nFAILURE: Some metadata files are missing or invalid")
        print("\nFailed checks:")
        for result in results:
            if not result["valid"]:
                print(f"  - {result['is_number']}: {result['status']} ({result.get('error', 'unknown')})")

    # Also check for any unexpected IS_* directories
    print("\nChecking for unexpected IS_* directories...")
    storage_dir = Path("storage/data")
    if storage_dir.exists():
        existing_dirs = [d.name for d in storage_dir.iterdir() if d.is_dir() and d.name.startswith("IS_")]
        # Generate expected directory names from config
        expected_dirs = []
        for is_number in expected_is_numbers:
            if ":" in is_number:
                base_part = is_number.split(":")[0].strip()
            else:
                base_part = is_number.strip()
            dir_name = base_part.replace(" ", "_").replace("(", "").replace(")", "").replace("/", "_")
            expected_dirs.append(dir_name)

        unexpected = [d for d in existing_dirs if d not in expected_dirs]
        missing = [d for d in expected_dirs if d not in existing_dirs]

        if unexpected:
            print(f"Unexpected directories found: {unexpected}")
        if missing:
            print(f"Expected directories missing: {missing}")

    return all_good

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)