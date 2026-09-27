from collectors.base import BaseCollector
import json

def main():
    print("Testing getWebsiteStandardDetails with known good enc_id")

    # Use the standardEncId that worked in the KYS test
    enc_id = "eyJpdiI6IjNkcDBHeEhrVU9nSXlKeHRKcENrbEE9PSIsInZhbHVlIjoidFRsY1FhWEwwWFVmMDQ4MG1WQVlhUT09IiwibWFjIjoiMDJlNjU0NGI4OWY3OTNjMjgyYTI5MTg3NjYzMzgyNTBmNzU1ZmEyMDkxOWY0YjY4ZWJjMTg1MWQxZGFlZjFjOCIsInRhZyI6IiJ9"

    # Initialize collector
    collector = BaseCollector(storage_base="storage/data", delay=1.0)

    # Try to get standard details
    payload = {
        "standardEncId": enc_id,
        **collector._default_auth_payload()
    }

    print(f"Payload: {json.dumps(payload, indent=2)}")

    result = collector._api_post("getWebsiteStandardDetails", payload)

    if result:
        print(f"SUCCESS! Response: {json.dumps(result, indent=2)[:500]}...")
    else:
        print("FAILED: No result returned")
        print(f"Errors: {collector.get_errors()}")

if __name__ == "__main__":
    main()