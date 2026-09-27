"""
Know Your Standard (KYS) collector.
Calls the BIS review-service API to collect standard metadata for each IS number.
"""
import logging
from pathlib import Path
from .base import BaseCollector

logger = logging.getLogger(__name__)


class KYSCollector(BaseCollector):
    """
    Collects standard metadata from the BIS Know Your Standard API.

    For each IS number in the niche config:
    1. Searches via searchKnowStandards to get the standardEncId
    2. Fetches full details via getWebsiteStandardDetails
    3. Stores structured metadata JSON per IS number
    """

    def collect_standard_metadata(self, is_entry: dict) -> dict | None:
        """
        Collect metadata for a single IS number.

        Args:
            is_entry: Dict from niche config with keys: is_number, doc_no, part, section, year, title, class

        Returns:
            Metadata dict or None on failure.
        """
        is_number = is_entry["is_number"]
        logger.info(f"Collecting metadata for {is_number}...")

        # Step 1: Search to get standardEncId
        search_result = self._search_standard(is_entry)
        if not search_result:
            logger.warning(f"No search result for {is_number}")
            return self._build_not_found_metadata(is_entry)

        # Step 2: Get full details
        details = self._get_standard_details(search_result)

        # Step 3: Build and save metadata
        metadata = self._build_metadata(is_entry, search_result, details)

        # Save to storage
        storage_dir = self._get_is_storage_dir(is_number)
        self._save_json(metadata, storage_dir / "metadata.json")

        return metadata

    def collect_all(self, is_entries: list[dict]) -> list[dict]:
        """
        Collect metadata for all IS numbers in the niche config.

        Returns:
            List of metadata dicts.
        """
        results = []
        for entry in is_entries:
            try:
                metadata = self.collect_standard_metadata(entry)
                if metadata:
                    results.append(metadata)
            except Exception as e:
                logger.error(f"Failed to collect {entry['is_number']}: {e}")
                self._record_error(entry["is_number"], str(e), 0)
        return results

    def _search_standard(self, is_entry: dict) -> dict | None:
        """
        Search for a standard using the KYS search API.
        Tries multiple search strategies to find the best match.
        """
        # Strategy 1: Search by full IS number (e.g., "IS 2082:2018")
        search_text = is_entry["is_number"]
        result = self._do_search(search_text, is_entry)
        if result:
            return result

        # Strategy 2: Search by doc_no only (e.g., "2082")
        search_text = is_entry["doc_no"]
        result = self._do_search(search_text, is_entry)
        if result:
            return result

        # Strategy 3: For multi-part standards, try "IS 302"
        if is_entry.get("part"):
            search_text = f"IS {is_entry['doc_no']}"
            result = self._do_search(search_text, is_entry)
            if result:
                return result

        return None

    def _do_search(self, search_text: str, is_entry: dict) -> dict | None:
        """Execute a single search API call and find the matching standard."""
        payload = {
            "searchText": search_text,
            **self._default_auth_payload(),
        }

        response = self._api_post("searchKnowStandards", payload)
        if not response:
            return None

        # Response may be a list or a dict with a data key
        standards = response if isinstance(response, list) else response.get("data", response)
        if not isinstance(standards, list):
            standards = [standards] if standards else []

        # Find the best match
        return self._find_best_match(standards, is_entry)

    def _find_best_match(self, standards: list, is_entry: dict) -> dict | None:
        """
        Find the standard in search results that best matches the is_entry.
        Matches on doc_no, part, section, and year.
        """
        doc_no = is_entry["doc_no"]
        part = is_entry.get("part")
        section = is_entry.get("section")
        year = is_entry.get("year")

        for std in standards:
            std_number = std.get("standardNumber", "")

            # Must contain the doc number
            if doc_no not in std_number:
                continue

            # For multi-part standards, check part and section
            if part:
                if f"Part {part}" not in std_number and f"(Part {part}" not in std_number:
                    continue
                if section and f"Sec {section}" not in std_number and f"Section {section}" not in std_number:
                    continue

            # Check year if present
            if year and year in std_number:
                return std

            # If no year match but doc_no matches, still accept
            if not year:
                return std

        # Fallback: return first result that at least has the doc_no
        for std in standards:
            if doc_no in std.get("standardNumber", ""):
                return std

        return None

    def _get_standard_details(self, search_result: dict) -> dict | None:
        """Fetch full standard details using the encrypted ID."""
        enc_id = search_result.get("standardEncId")
        if not enc_id:
            return None

        payload = {
            "standardEncId": enc_id,
            **self._default_auth_payload()
        }
        return self._api_post("getWebsiteStandardDetails", payload)

    def _build_metadata(self, is_entry: dict, search_result: dict, details: dict | None) -> dict:
        """Build the structured metadata record for an IS number."""
        metadata = {
            "is_number": is_entry["is_number"],
            "doc_no": is_entry["doc_no"],
            "part": is_entry.get("part"),
            "section": is_entry.get("section"),
            "year": is_entry.get("year"),
            "title": is_entry.get("title", ""),
            "class": is_entry.get("class", "UNKNOWN"),
            "fuel_type": is_entry.get("fuel_type"),
            # From search result
            "standard_enc_id": search_result.get("standardEncId"),
            "standard_id": search_result.get("standardId"),
            "standard_number_api": search_result.get("standardNumber"),
            "standard_name_api": search_result.get("standardName"),
            "published_on": search_result.get("publishedOn"),
            "valid_upto": search_result.get("validUpto"),
            "withdraw_status": search_result.get("withdrawStatus"),
            "department_id": search_result.get("departmentId"),
            "committee_id": search_result.get("committeeId"),
            # Full standard access status (always restricted for current standards)
            "full_standard_access": "restricted",
            # Data collection status tracking
            "collection_status": {
                "metadata": "available",
                "product_manual": "pending",
                "sit": "pending",
                "amendments": "pending",
                "qco_gazette": "pending",
                "laboratories": "pending",
            },
        }

        # Merge any additional details from the details API
        if details:
            if isinstance(details, dict):
                metadata["details_raw"] = details
                # Extract specific fields if available
                for key in ["departmentName", "committeeName", "memberSecretary",
                            "degreeOfEquivalence", "reaffirmationYear", "scope"]:
                    if key in details:
                        metadata[key] = details[key]

        return metadata

    def _build_not_found_metadata(self, is_entry: dict) -> dict:
        """Build a metadata record when a standard is not found in the API."""
        return {
            "is_number": is_entry["is_number"],
            "doc_no": is_entry["doc_no"],
            "part": is_entry.get("part"),
            "section": is_entry.get("section"),
            "year": is_entry.get("year"),
            "title": is_entry.get("title", ""),
            "class": is_entry.get("class", "UNKNOWN"),
            "fuel_type": is_entry.get("fuel_type"),
            "standard_enc_id": "not_found",
            "standard_id": "not_found",
            "full_standard_access": "restricted",
            "collection_status": {
                "metadata": "not_found",
                "product_manual": "not_found",
                "sit": "not_found",
                "amendments": "not_found",
                "qco_gazette": "not_found",
                "laboratories": "not_found",
            },
        }
