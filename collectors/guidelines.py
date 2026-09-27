"""
Guidelines collector.
Collects guideline documents for BIS standards.
"""
import logging
from pathlib import Path
from .base import BaseCollector

logger = logging.getLogger(__name__)

class GuidelinesCollector(BaseCollector):
    """
    Collects guideline documents.

    For each IS number with available standard_id:
    1. Fetches guideline details via getGuidelineDetails API endpoint
    2. Downloads guideline PDFs from verified official sources
    3. Updates metadata with guideline document information
    """

    def collect_guidelines(self, metadata: dict) -> dict:
        """
        Fetch guideline details and download the PDFs.

        Args:
            metadata: The metadata dict for the IS number (needs standard_id).

        Returns:
            Updated metadata dict with collection status and document links.
        """
        is_number = metadata["is_number"]
        standard_id = metadata.get("standard_id")

        if not standard_id or standard_id == "not_found":
            logger.warning(f"No standard_id for {is_number}, skipping guidelines collection.")
            return metadata

        logger.info(f"Collecting guidelines for {is_number}...")

        # Use the encrypted ID for API calls as determined from testing
        standard_enc_id = metadata.get("standard_enc_id")
        if not standard_enc_id or standard_enc_id == "not_found":
            logger.warning(f"No standard_enc_id for {is_number}, skipping guidelines collection.")
            return metadata

        payload = {
            "standardId": standard_enc_id,  # Use encrypted ID as verified working
            **self._default_auth_payload()
        }

        # Try to get guideline details
        response = self._api_post("getGuidelineDetails", payload)

        if not response:
            logger.info(f"No guideline response received for {is_number}")
            metadata["collection_status"]["guidelines"] = "not_found"
            return metadata

        # Handle different possible response structures
        guideline_details = []
        if isinstance(response, dict):
            if response.get("status") == "SUCCESS":
                data = response.get("data", {})
                if isinstance(data, dict):
                    guideline_details = data.get("guidelines", []) or data.get("documents", [])
                elif isinstance(data, list):
                    guideline_details = data
            else:
                # Maybe the response is the details directly
                guideline_details = response.get("guidelines", []) or response.get("documents", [])
        elif isinstance(response, list):
            guideline_details = response

        if not guideline_details:
            logger.info(f"No guideline documents found for {is_number}")
            metadata["collection_status"]["guidelines"] = "not_found"
            return metadata

        # Process each guideline document
        storage_dir = self._get_is_storage_dir(is_number) / "documents"
        storage_dir.mkdir(parents=True, exist_ok=True)

        downloaded_docs = []

        for item in guideline_details:
            # Extract file information - field names may vary
            doc_path = item.get("file_path") or item.get("documentUrl") or item.get("url") or item.get("is_documents")
            doc_name = item.get("file_name") or item.get("documentName") or f"guideline_{len(downloaded_docs)}"
            doc_type = item.get("document_type", "guideline")

            if not doc_path:
                logger.warning(f"Guideline item missing URL/path: {item}")
                continue

            # Construct full URL if needed
            if doc_path.startswith("http"):
                doc_url = doc_path
            else:
                # Use Oracle Cloud storage pattern (verified working for product manual)
                doc_url = f"https://bmqsdqljvwgm.compat.objectstorage.ap-mumbai-1.oraclecloud.com/{doc_path}"

            # Only process if it's from an official domain
            if not self._is_official_source(doc_url):
                logger.warning(f"Skipping unofficial document URL: {doc_url}")
                continue

            local_path = storage_dir / f"{doc_name}.pdf"

            doc_record = self._download_file(doc_url, local_path)

            if doc_record:
                doc_record["document_type"] = doc_type
                doc_record["document_id"] = f"DOC_{metadata['doc_no']}_GL_{item.get('pk_is_id', len(downloaded_docs))}"
                downloaded_docs.append(doc_record)

        if downloaded_docs:
            metadata["collection_status"]["guidelines"] = "available"
            metadata["guidelines"] = downloaded_docs
        else:
            metadata["collection_status"]["guidelines"] = "not_found"

        # Update metadata.json on disk
        self._save_json(metadata, self._get_is_storage_dir(is_number) / "metadata.json")

        return metadata

    def collect_all(self, metadata_list: list[dict]) -> list[dict]:
        """
        Collect guideline documents for all IS numbers in the metadata list.

        Args:
            metadata_list: List of metadata dicts for IS numbers.

        Returns:
            List of updated metadata dicts.
        """
        results = []
        for metadata in metadata_list:
            try:
                updated_metadata = self.collect_guidelines(metadata)
                if updated_metadata:
                    results.append(updated_metadata)
            except Exception as e:
                logger.error(f"Failed to collect guidelines for {metadata.get('is_number')}: {e}")
                self._record_error(metadata.get("is_number", "unknown"), str(e), 0)
        return results