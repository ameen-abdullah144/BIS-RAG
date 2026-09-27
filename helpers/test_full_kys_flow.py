from collectors.kys import KYSCollector
import json

def main():
    print("Testing full KYS flow: search then getWebsiteStandardDetails")

    # Target IS 2082
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

    # Initialize collector
    collector = KYSCollector(storage_base="storage/data", delay=1.0)

    # Step 1: Search to get standardEncId
    print("Step 1: Searching for standard...")
    search_result = collector._search_standard(test_entry)
    if not search_result:
        print("No search result found")
        return

    print(f"Search result standardEncId: {search_result.get('standardEncId')}")

    # Step 2: Get full details
    print("Step 2: Getting website standard details...")
    details = collector._get_standard_details(search_result)
    if details:
        print(f"SUCCESS! Got details (first 200 chars): {str(details)[:200]}...")
    else:
        print("FAILED: No website standard details found")
        print(f"Errors: {collector.get_errors()}")

if __name__ == "__main__":
    main()