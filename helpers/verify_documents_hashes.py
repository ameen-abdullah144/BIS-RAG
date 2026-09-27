import json
import hashlib
from pathlib import Path

def compute_file_hash(filepath):
    """Compute SHA-256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def main():
    print("Phase 1 Step 9: Check every downloaded document and its hash")
    print("=" * 60)

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

    print("\nChecking downloaded documents and their hashes...")
    print("-" * 60)

    all_good = True
    total_documents_checked = 0
    total_documents_valid = 0
    total_documents_missing = 0
    total_hash_mismatch = 0

    # Document arrays to check (those that contain downloadable files with local_path and sha256)
    document_arrays = ["product_manuals", "amendments", "qco_gazettes"]

    for is_number in expected_is_numbers:
        # Parse IS number to determine directory name format
        if ":" in is_number:
            base_part = is_number.split(":")[0].strip()
        else:
            base_part = is_number.strip()
        # Convert to directory name format
        # Replace spaces with underscores, remove parentheses, replace forward slashes with underscores
        dir_name = base_part.replace(" ", "_").replace("(", "").replace(")", "").replace("/", "_")

        metadata_path = Path(f"storage/data/{dir_name}/metadata.json")

        if not metadata_path.exists():
            print(f"SKIPPING {is_number}: metadata.json not found")
            all_good = False
            continue

        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)

            # Verify is_number matches
            if metadata["is_number"] != is_number:
                print(f"SKIPPING {is_number}: is_number mismatch in metadata")
                all_good = False
                continue

            print(f"\nChecking {is_number}:")

            # Check each document array
            for array_name in document_arrays:
                document_list = metadata.get(array_name, [])
                if not document_list:
                    continue  # Skip empty arrays

                print(f"  {array_name} ({len(document_list)} documents):")

                for i, doc in enumerate(document_list):
                    total_documents_checked += 1
                    local_path_str = doc.get("local_path")
                    expected_hash = doc.get("sha256")
                    doc_type = doc.get("document_type", "unknown")
                    doc_id = doc.get("document_id", "unknown")
                    status = doc.get("status", "unknown")

                    if not local_path_str or not expected_hash:
                        print(f"    [{i+1}] SKIPPED: Missing local_path or sha256")
                        continue

                    # Construct full file path
                    file_path = Path(local_path_str)

                    # Check if file exists
                    if not file_path.exists():
                        print(f"    [{i+1}] MISSING: {file_path}")
                        total_documents_missing += 1
                        all_good = False
                        continue

                    # Compute actual hash
                    try:
                        actual_hash = compute_file_hash(file_path)
                    except Exception as e:
                        print(f"    [{i+1}] ERROR reading file: {e}")
                        all_good = False
                        total_documents_missing += 1  # Treat as missing for counting
                        continue

                    # Compare hashes
                    if actual_hash.lower() == expected_hash.lower():
                        print(f"    [{i+1}] VALID: {doc_type} ({doc_id}) - {status}")
                        total_documents_valid += 1
                    else:
                        print(f"    [{i+1}] HASH MISMATCH: {doc_type} ({doc_id})")
                        print(f"        Expected: {expected_hash}")
                        print(f"        Actual:   {actual_hash}")
                        total_hash_mismatch += 1
                        all_good = False

        except json.JSONDecodeError as e:
            print(f"ERROR parsing {is_number} metadata: {e}")
            all_good = False
        except Exception as e:
            print(f"ERROR processing {is_number}: {e}")
            all_good = False

    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total documents checked: {total_documents_checked}")
    print(f"Valid documents: {total_documents_valid}")
    print(f"Missing files: {total_documents_missing}")
    print(f"Hash mismatches: {total_hash_mismatch}")

    if all_good and total_documents_checked > 0:
        print("\nSUCCESS: All downloaded documents are present and have correct hashes")
    elif total_documents_checked == 0:
        print("\nWARNING: No documents were found to check")
    else:
        print("\nFAILURE: Some documents are missing or have incorrect hashes")

    return all_good and total_documents_checked > 0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)