import json
from pathlib import Path
from collectors.product_manuals import ProductManualCollector
import requests

def main():
    print("Debugging Product Manuals Collection for IS 2082")

    # Load metadata
    metadata_path = Path("storage/data/IS_2082/metadata.json")
    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    print(f"Loaded metadata for: {metadata['is_number']}")
    print(f"Standard ID (numeric): {metadata.get('standard_id')}")
    print(f"Standard Enc ID: {metadata.get('standard_enc_id')[:50]}...")

    # Initialize collector
    collector = ProductManualCollector(storage_base="storage/data", delay=1.0)

    # Temporarily override the standard_id to use the encrypted version for testing
    original_standard_id = metadata.get("standard_id")
    metadata["standard_id"] = metadata.get("standard_enc_id")  # Use encrypted ID

    print(f"\nAfter override - standard_id: {metadata['standard_id'][:50]}...")

    is_number = metadata["is_number"]
    standard_id = metadata.get("standard_id")

    if not standard_id or standard_id == "not_found":
        print("WARNING: No standard_id, skipping")
        return

    print(f"Collecting product manuals for {is_number}...")

    # Use the encrypted ID for API calls as determined from testing
    standard_enc_id = metadata.get("standard_enc_id")
    print(f"standard_enc_id from metadata: {standard_enc_id[:50] if standard_enc_id else None}...")

    if not standard_enc_id or standard_enc_id == "not_found":
        print("WARNING: No standard_enc_id, skipping")
        return

    payload = {
        "standardId": standard_enc_id,  # Use encrypted ID as verified working
        "fromPage": "guestUserPage",
        "token": None,
        "refreshToken": None,
        "clientId": None,
        "clientSecret": None,
        "sub": None
    }

    print(f"Making API call with payload: {{'standardId': '{standard_enc_id[:30]}...', 'fromPage': 'guestUserPage', ...}}")

    # Make the API call directly to see what we get
    url = "https://standardsadmin.bis.gov.in/review-service/getProductManualDetails"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    resp = requests.post(url, json=payload, headers=headers, timeout=30)
    print(f"API Response Status: {resp.status_code}")
    print(f"API Response Text: {resp.text}")

    if resp.status_code == 200:
        try:
            data = resp.json()
            print(f"Parsed JSON: {json.dumps(data, indent=2)[:200]}...")

            # Now test the collector's response handling logic
            response = data
            print(f"\nTesting collector's response handling:")
            print(f"Response type: {type(response)}")

            product_manuals = []
            if isinstance(response, dict):
                print("Response is dict")
                if response.get("status") == "SUCCESS":
                    print("Response status is SUCCESS")
                    data_section = response.get("data", {})
                    print(f"Data section: {data_section}")
                    if isinstance(data_section, dict):
                        product_manuals = data_section.get("product_manuals_details", [])
                        print(f"Found product_manuals_details: {len(product_manuals)} items")
                    elif isinstance(data_section, list):
                        product_manuals = data_section
                        print(f"Data is direct list: {len(product_manuals)} items")
                else:
                    print(f"Response status not SUCCESS: {response.get('status')}")
                    # Maybe the response is the details directly
                    product_manuals = response.get("product_manuals_details", [])
                    print(f"Trying to get product_manuals_details directly: {len(product_manuals)} items")
            elif isinstance(response, list):
                print("Response is direct list")
                product_manuals = response
                print(f"Direct list length: {len(product_manuals)}")

            print(f"Final product_manuals count: {len(product_manuals)}")
            if product_manuals:
                print(f"First item: {product_manuals[0]}")

        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON: {e}")
    else:
        print(f"HTTP Error: {resp.status_code}")

if __name__ == "__main__":
    main()