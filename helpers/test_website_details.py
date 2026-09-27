from collectors.kys import KYSCollector
import json

def main():
    print("Testing getWebsiteStandardDetails for IS 2082")

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
    search_result = collector._search_standard(test_entry)
    if not search_result:
        print("No search result found")
        return

    print(f"Search result: {json.dumps(search_result, indent=2)}")

    # Step 2: Get full details
    details = collector._get_standard_details(search_result)
    if details:
        print(f"Website standard details: {json.dumps(details, indent=2)}")
    else:
        print("No website standard details found")

if __name__ == "__main__":
    main()