from collectors.base import BaseCollector
from collectors.kys import KYSCollector
import json

def main():
    print("Testing different guideline API endpoints")

    # First, get a valid standardEncId from KYS search for IS 2082
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

    kys_collector = KYSCollector(storage_base="storage/data", delay=1.0)
    search_result = kys_collector._search_standard(test_entry)
    if not search_result:
        print("No search result found")
        return

    enc_id = search_result.get("standardEncId")
    print(f"Using standardEncId: {enc_id}")

    # Test different endpoint names
    endpoints_to_test = [
        "getGuidelineDetails",
        "getGuidelinesDetails",
        "getGuideDetails",
        "getStandardGuidelines",
        "getGuidelineInfo",
        "getGuidesDetails"
    ]

    base_collector = BaseCollector(storage_base="storage/data", delay=1.0)

    for endpoint in endpoints_to_test:
        print(f"\nTesting endpoint: {endpoint}")
        payload = {
            "standardEncId": enc_id,
            **base_collector._default_auth_payload()
        }

        result = base_collector._api_post(endpoint, payload)
        if result:
            print(f"  SUCCESS! Got response: {str(result)[:100]}...")
        else:
            print(f"  FAILED: No result (errors: {len(base_collector.get_errors())})")
            # Show last error if any
            if base_collector.get_errors():
                last_error = base_collector.get_errors()[-1]
                print(f"    Last error: {last_error['reason']}")

if __name__ == "__main__":
    main()