import requests
import json

# Load metadata
with open("storage/data/IS_2082/metadata.json", "r") as f:
    metadata = json.load(f)

standard_enc_id = metadata.get("standard_enc_id")
print(f"Using standard_enc_id: {standard_enc_id}")

# Test the exact call that the collector should be making
url = "https://standardsadmin.bis.gov.in/review-service/getProductManualDetails"
payload = {
    "standardId": standard_enc_id,  # Use encrypted ID as verified working
    "fromPage": "guestUserPage",
    "token": None,
    "refreshToken": None,
    "clientId": None,
    "clientSecret": None,
    "sub": None
}

headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Content-Type": "application/json"
}

print("\nMaking API call...")
resp = requests.post(url, json=payload, headers=headers, timeout=30)
print(f"Status Code: {resp.status_code}")
print(f"Response Headers: {dict(resp.headers)}")
print(f"Response Text: {resp.text}")

if resp.status_code == 200:
    try:
        data = resp.json()
        print(f"\nParsed JSON: {json.dumps(data, indent=2)}")

        # Check the structure
        if isinstance(data, dict):
            if data.get("status") == "SUCCESS":
                resp_data = data.get("data", {})
                print(f"\nData section: {json.dumps(resp_data, indent=2)}")

                if isinstance(resp_data, dict):
                    product_manuals = resp_data.get("product_manuals_details", [])
                    print(f"\nProduct manuals details: {json.dumps(product_manuals, indent=2)}")
                elif isinstance(resp_data, list):
                    print(f"\nData is a list: {json.dumps(resp_data, indent=2)}")
            else:
                print(f"\nResponse status not SUCCESS: {data.get('status')}")
        elif isinstance(data, list):
            print(f"\nResponse is a direct list: {json.dumps(data, indent=2)}")

    except json.JSONDecodeError as e:
        print(f"\nFailed to parse JSON: {e}")
else:
    print(f"\nHTTP Error: {resp.status_code}")