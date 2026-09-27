"""
Scheme of Inspection and Testing (SIT) collector.
Collects SIT documents for BIS standards.
"""
import logging
from pathlib import Path
from .base import BaseCollector

logger = logging.getLogger(__name__)

class SITCollector(BaseCollector):
    """
    Collects Scheme of Inspection and Testing (SIT) documents.

    For each IS number with available standard_id:
    1. Fetches SIT details via getSitDetails API endpoint
    2. Downloads SIT PDFs from verified official sources
    3. Updates metadata with SIT document information
    """

    def collect_sit_documents(self, metadata: dict) -> dict:
        """
        Fetch SIT details and download the PDFs.

        Args:
            metadata: The metadata dict for the IS number (needs standard_id).

        Returns:
            Updated metadata dict with collection status and document links.
        """
        is_number = metadata["is_number"]

        # Check if SIT is already embedded in product manual
        sit_status = metadata.get("collection_status", {}).get("sit", "")
        if sit_status == "embedded_in_product_manual":
            logger.info(f"SIT is embedded in product manual for {is_number}, skipping separate SIT collection.")
            return metadata

        standard_id = metadata.get("standard_id")

        if not standard_id or standard_id == "not_found":
            logger.warning(f"No standard_id for {is_number}, skipping SIT collection.")
            return metadata

        logger.info(f"Collecting SIT documents for {is_number}...")

        # Use the encrypted ID for API calls as determined from testing
        standard_enc_id = metadata.get("standard_enc_id")
        if not standard_enc_id or standard_enc_id == "not_found":
            logger.warning(f"No standard_enc_id for {is_number}, skipping SIT collection.")
            return metadata

        payload = {
            "standardId": standard_enc_id,  # Use encrypted ID as verified working
            **self._default_auth_payload()
        }

        # Try to get SIT details - endpoint name based on pattern from other collectors
        response = self._api_post("getSitDetails", payload)

        if not response:
            logger.info(f"No SIT response received for {is_number}")
            metadata["collection_status"]["sit"] = "not_found"
            return metadata

        # Handle different possible response structures
        sit_details = []
        if isinstance(response, dict):
            if response.get("status") == "SUCCESS":
                data = response.get("data", {})
                if isinstance(data, dict):
                    sit_details = data.get("sit_details", []) or data.get("documents", [])
                elif isinstance(data, list):
                    sit_details = data
            else:
                # Maybe the response is the details directly
                sit_details = response.get("sit_details", []) or response.get("documents", [])
        elif isinstance(response, list):
            sit_details = response

        if not sit_details:
            logger.info(f"No SIT documents found for {is_number}")
            metadata["collection_status"]["sit"] = "not_found"
            return metadata

        # Process each SIT document
        storage_dir = self._get_is_storage_dir(is_number) / "documents"
        storage_dir.mkdir(parents=True, exist_ok=True)

        downloaded_docs = []

        for item in sit_details:
            # Extract file information - field names may vary
            doc_url = item.get("file_path") or item.get("documentUrl") or item.get("url")
            doc_name = item.get("file_name") or item.get("documentName") or f"sit_document_{len(downloaded_docs)}"
            doc_type = item.get("document_type", "sit")

            if not doc_url:
                logger.warning(f"SIT item missing URL: {item}")
                continue

            # Only process if it's from an official domain
            if not self._is_official_source(doc_url):
                logger.warning(f"Skipping unofficial document URL: {doc_url}")
                continue

            local_path = storage_dir / f"{doc_name}.pdf"

            doc_record = self._download_file(doc_url, local_path)

            if doc_record:
                doc_record["document_type"] = doc_type
                doc_record["document_id"] = f"DOC_{metadata['doc_no']}_SIT_{item.get('pk_is_id', len(downloaded_docs))}"
                downloaded_docs.append(doc_record)

        if downloaded_docs:
            metadata["collection_status"]["sit"] = "available"
            metadata["sit_documents"] = downloaded_docs
        else:
            metadata["collection_status"]["sit"] = "not_found"

        # Update metadata.json on disk
        self._save_json(metadata, self._get_is_storage_dir(is_number) / "metadata.json")

        return metadata

    def collect_all(self, metadata_list: list[dict]) -> list[dict]:
        """
        Collect SIT documents for all IS numbers in the metadata list.

        Args:
            metadata_list: List of metadata dicts for IS numbers.

        Returns:
            List of updated metadata dicts.
        """
        results = []
        for metadata in metadata_list:
            try:
                updated_metadata = self.collect_sit_documents(metadata)
                if updated_metadata:
                    results.append(updated_metadata)
            except Exception as e:
                logger.error(f"Failed to collect SIT for {metadata.get('is_number')}: {e}")
                self._record_error(metadata.get("is_number", "unknown"), str(e), 0)
        return results