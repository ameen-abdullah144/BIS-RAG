import json
from pathlib import Path
from collectors.product_manuals import ProductManualCollector
import requests

def main():
    print("Debugging Product Manual Collector for IS 2082")

    # Load existing metadata
    metadata_path = Path("storage/data/IS_2082/metadata.json")
    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    print(f"Loaded metadata for: {metadata['is_number']}")

    # Initialize collector
    collector = ProductManualCollector(storage_base="storage/data", delay=1.0)

    # Manually test what the collector does
    is_number = metadata["is_number"]
    standard_id = metadata.get("standard_id")
    standard_enc_id = metadata.get("standard_enc_id")

    print(f"Standard ID (numeric): {standard_id}")
    print(f"Standard Enc ID: {standard_enc_id}")

    if not standard_enc_id or standard_enc_id == "not_found":
        print("No standard_enc_id available")
        return

    print("\nTesting direct API call with standard_enc_id in standardId field...")

    # This is what the fixed version should do
    payload = {
        "standardId": standard_enc_id,  # Use the encrypted ID
        "fromPage": "guestUserPage",
        **collector._default_auth_payload()
    }

    print(f"Payload: {json.dumps(payload, indent=2)}")

    url = f"{collector.REVIEW_SERVICE_URL}getProductManualDetails"
    print(f"URL: {url}")

    try:
        resp = collector.session.post(url, json=payload, timeout=30)
        print(f"Status Code: {resp.status_code}")
        print(f"Response Headers: {dict(resp.headers)}")

        if resp.status_code == 200:
            response_data = resp.json()
            print(f"Response: {json.dumps(response_data, indent=2)}")

            # Check if we got product manuals details
            if response_data.get("status") == "SUCCESS" and response_data.get("data"):
                data = response_data["data"]
                if isinstance(data, dict) and "product_manuals_details" in data:
                    manuals = data["product_manuals_details"]
                    print(f"Found {len(manuals)} product manuals:")
                    for i, manual in enumerate(manuals):
                        print(f"  {i+1}. {manual.get('file_name')} - {manual.get('file_path')}")
                elif isinstance(data, list):
                    print(f"Found {len(data)} product manuals (direct list)")
                    for i, manual in enumerate(data):
                        print(f"  {i+1}. {manual.get('file_name')} - {manual.get('file_path')}")
                else:
                    print(f"Unexpected data format: {type(data)}")
                    print(f"Data: {data}")
            else:
                print("API returned success but no product manuals data")
                print(f"Full response: {response_data}")
        else:
            print(f"API Error: {resp.status_code}")
            print(f"Response: {resp.text}")

    except Exception as e:
        print(f"Exception during API call: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()