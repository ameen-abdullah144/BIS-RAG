import requests
import json

# Get the encrypted ID from the existing metadata
with open("storage/data/IS_2082/metadata.json", "r") as f:
    metadata = json.load(f)

standard_enc_id = metadata.get("standard_enc_id")
print(f"Using standard_enc_id: {standard_enc_id}")

# Base URL
base_url = "https://standardsadmin.bis.gov.in/review-service/"

# Common endpoint patterns to try
endpoints_to_try = [
    "getSitDetails",
    "getSITDetails",
    "getSitInfo",
    "getSITInfo",
    "getSchemeDetails",
    "getSchemeInformation",
    "getSitDocuments",
    "getSITDocuments",
    "getSitByStandardId",
    "getSITByStandardId"
]

headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Content-Type": "application/json"
}

# Try with standardId field (which worked for product manuals)
payload_base = {
    "standardId": standard_enc_id,
    "token": None,
    "refreshToken": None,
    "clientId": None,
    "clientSecret": None,
    "sub": None
}

print("\nTrying different SIT endpoints with standardId field:")
for endpoint in endpoints_to_try:
    url = f"{base_url}{endpoint}"
    try:
        resp = requests.post(url, json=payload_base, headers=headers, timeout=10)
        print(f"{endpoint}: {resp.status_code}")
        if resp.status_code == 200:
            print(f"  SUCCESS! Response: {resp.text[:200]}...")
            break
        elif resp.status_code != 404:
            print(f"  Response: {resp.text[:100]}...")
    except Exception as e:
        print(f"{endpoint}: Error - {e}")

# Also try with standardEncId field
payload_base2 = {
    "standardEncId": standard_enc_id,
    "token": None,
    "refreshToken": None,
    "clientId": None,
    "clientSecret": None,
    "sub": None
}

print("\n\nTrying different SIT endpoints with standardEncId field:")
for endpoint in endpoints_to_try:
    url = f"{base_url}{endpoint}"
    try:
        resp = requests.post(url, json=payload_base2, headers=headers, timeout=10)
        print(f"{endpoint}: {resp.status_code}")
        if resp.status_code == 200:
            print(f"  SUCCESS! Response: {resp.text[:200]}...")
            break
        elif resp.status_code != 404:
            print(f"  Response: {resp.text[:100]}...")
    except Exception as e:
        print(f"{endpoint}: Error - {e}")