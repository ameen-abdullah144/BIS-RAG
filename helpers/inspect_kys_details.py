import json
from pathlib import Path
from collectors.kys import KYSCollector

def main():
    print("Inspecting KYS details for IS 2082")

    # Load existing metadata to get the standard_enc_id
    metadata_path = Path("storage/data/IS_2082/metadata.json")
    if not metadata_path.exists():
        print(f"ERROR: {metadata_path} not found. Run verify_kys_single.py first.")
        return

    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    standard_enc_id = metadata.get("standard_enc_id")
    print(f"Standard Enc ID: {standard_enc_id}")

    if not standard_enc_id or standard_enc_id == "not_found":
        print("No standard_enc_id found.")
        return

    # Initialize KYS collector
    collector = KYSCollector(storage_base="storage/data", delay=1.0)

    # Prepare payload for getWebsiteStandardDetails
    payload = {
        "standardEncId": standard_enc_id,
        **collector._default_auth_payload()
    }

    # Call the API
    details = collector._api_post("getWebsiteStandardDetails", payload)

    if details:
        print("\nDetails from getWebsiteStandardDetails:")
        print(json.dumps(details, indent=2))
    else:
        print("\nNo details returned from getWebsiteStandardDetails.")

if __name__ == "__main__":
    main()