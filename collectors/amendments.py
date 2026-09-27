"""
Amendments collector.
Collects amendment documents for BIS standards.
"""
import logging
from pathlib import Path
from .base import BaseCollector

logger = logging.getLogger(__name__)

class AmendmentsCollector(BaseCollector):
    """
    Collects amendment documents.

    For each IS number with available standard_id:
    1. Fetches amendment details via getAmendmentDetails API endpoint
    2. Downloads amendment PDFs from verified official sources
    3. Updates metadata with amendment document information
    """

    def collect_amendments(self, metadata: dict) -> dict:
        """
        Fetch amendment details and download the PDFs.

        Args:
            metadata: The metadata dict for the IS number (needs standard_id).

        Returns:
            Updated metadata dict with collection status and document links.
        """
        is_number = metadata["is_number"]
        standard_id = metadata.get("standard_id")

        if not standard_id or standard_id == "not_found":
            logger.warning(f"No standard_id for {is_number}, skipping amendments collection.")
            return metadata

        logger.info(f"Collecting amendments for {is_number}...")

        # Use the encrypted ID for API calls as determined from testing
        standard_enc_id = metadata.get("standard_enc_id")
        if not standard_enc_id or standard_enc_id == "not_found":
            logger.warning(f"No standard_enc_id for {is_number}, skipping amendments collection.")
            return metadata

        payload = {
            "standardId": standard_enc_id,  # Use encrypted ID as verified working
            **self._default_auth_payload()
        }

        # Try to get amendment details
        response = self._api_post("getAmendmentDetails", payload)

        if not response:
            logger.info(f"No amendment response received for {is_number}")
            metadata["collection_status"]["amendments"] = "not_found"
            return metadata

        # Handle different possible response structures
        amendment_details = []
        if isinstance(response, dict):
            if response.get("status") == "SUCCESS":
                data = response.get("data", {})
                if isinstance(data, dict):
                    amendment_details = data.get("amendments", []) or data.get("documents", [])
                elif isinstance(data, list):
                    amendment_details = data
            else:
                # Maybe the response is the details directly
                amendment_details = response.get("amendments", []) or response.get("documents", [])
        elif isinstance(response, list):
            amendment_details = response

        if not amendment_details:
            logger.info(f"No amendment documents found for {is_number}")
            metadata["collection_status"]["amendments"] = "not_found"
            return metadata

        # Process each amendment document
        storage_dir = self._get_is_storage_dir(is_number) / "documents"
        storage_dir.mkdir(parents=True, exist_ok=True)

        downloaded_docs = []

        for item in amendment_details:
            # Extract file information - field names may vary
            doc_path = item.get("file_path") or item.get("documentUrl") or item.get("url") or item.get("is_documents")
            doc_name = item.get("file_name") or item.get("documentName") or f"amendment_{len(downloaded_docs)}"
            doc_type = item.get("document_type", "amendment")

            if not doc_path:
                logger.warning(f"Amendment item missing URL/path: {item}")
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
                doc_record["document_id"] = f"DOC_{metadata['doc_no']}_AM_{item.get('pk_is_id', len(downloaded_docs))}"
                downloaded_docs.append(doc_record)

        if downloaded_docs:
            metadata["collection_status"]["amendments"] = "available"
            metadata["amendments"] = downloaded_docs
        else:
            metadata["collection_status"]["amendments"] = "not_found"

        # Update metadata.json on disk
        self._save_json(metadata, self._get_is_storage_dir(is_number) / "metadata.json")

        return metadata

    def collect_all(self, metadata_list: list[dict]) -> list[dict]:
        """
        Collect amendment documents for all IS numbers in the metadata list.

        Args:
            metadata_list: List of metadata dicts for IS numbers.

        Returns:
            List of updated metadata dicts.
        """
        results = []
        for metadata in metadata_list:
            try:
                updated_metadata = self.collect_amendments(metadata)
                if updated_metadata:
                    results.append(updated_metadata)
            except Exception as e:
                logger.error(f"Failed to collect amendments for {metadata.get('is_number')}: {e}")
                self._record_error(metadata.get("is_number", "unknown"), str(e), 0)
        return results