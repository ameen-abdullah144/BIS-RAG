import logging
from pathlib import Path
from .base import BaseCollector
try:
    # When imported as part of the package
    from ..processors.text_extractor import contains_sit_indicators, extract_text_from_pdf
except ImportError:
    # When run directly or in different context
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent))
    from processors.text_extractor import contains_sit_indicators, extract_text_from_pdf

logger = logging.getLogger(__name__)

class ProductManualCollector(BaseCollector):
    """
    Collects Product Manuals and Scheme of Inspection and Testing (SIT) documents.
    """

    def collect_manuals(self, metadata: dict) -> dict:
        """
        Fetch product manual details and download the PDFs.

        Args:
            metadata: The metadata dict for the IS number (needs standard_id).

        Returns:
            Updated metadata dict with collection status and document links.
        """
        # DEBUG: See if this method is called at all
        debug_file = Path("C:/Users/NAME/Documents/Myprojects/BIS1/debug_collector.txt")
        try:
            with open(debug_file, "w") as f:
                f.write(f"collect_manuals called for {metadata.get('is_number', 'unknown')}\n")
        except:
            pass

        is_number = metadata["is_number"]
        standard_id = metadata.get("standard_id")

        if not standard_id or standard_id == "not_found":
            logger.warning(f"No standard_id for {is_number}, skipping manual collection.")
            return metadata

        logger.info(f"Collecting product manuals for {is_number}...")

        # Use the encrypted ID for API calls as determined from testing
        standard_enc_id = metadata.get("standard_enc_id")
        if not standard_enc_id or standard_enc_id == "not_found":
            logger.warning(f"No standard_enc_id for {is_number}, skipping manual collection.")
            return metadata

        payload = {
            "standardId": standard_enc_id,  # Use encrypted ID as verified working
            "fromPage": "guestUserPage",
            **self._default_auth_payload()
        }

        response = self._api_post("getProductManualDetails", payload)

        if not response:
            logger.info(f"No product manual found for {is_number}")
            metadata["collection_status"]["product_manual"] = "not_found"
            return metadata

        # Handle different possible response structures
        product_manuals = []
        if isinstance(response, dict):
            if response.get("status") == "SUCCESS":
                data = response.get("data", {})
                if isinstance(data, dict):
                    product_manuals = data.get("product_manuals_details", [])
                elif isinstance(data, list):
                    product_manuals = data
            else:
                # Maybe the response is the details directly
                product_manuals = response.get("product_manuals_details", [])
        elif isinstance(response, list):
            product_manuals = response

        if not product_manuals:
            logger.info(f"No product manual found for {is_number}")
            metadata["collection_status"]["product_manual"] = "not_found"
            return metadata

        # Example response item: {"pmId": 123, "documentName": "PM_IS-2082", "documentUrl": "https://..."}
        storage_dir = self._get_is_storage_dir(is_number) / "documents"
        storage_dir.mkdir(parents=True, exist_ok=True)

        downloaded_docs = []

        for item in product_manuals:
            doc_path = item.get("file_path") or item.get("documentUrl")
            doc_name = item.get("file_name") or item.get("documentName", "product_manual")

            if not doc_path:
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

            local_path = storage_dir / doc_name

            doc_record = self._download_file(doc_url, local_path)

            if doc_record:
                doc_record["document_type"] = "product_manual"
                doc_record["document_id"] = f"DOC_{metadata['doc_no']}_PM_{item.get('pk_is_id', len(downloaded_docs))}"
                downloaded_docs.append(doc_record)

        if downloaded_docs:
            metadata["collection_status"]["product_manual"] = "available"
            metadata["product_manuals"] = downloaded_docs

            # Check for embedded SIT in downloaded product manuals
            self._check_for_embedded_sit(metadata, storage_dir, downloaded_docs)
        else:
            metadata["collection_status"]["product_manual"] = "not_found"

        # Update metadata.json on disk
        self._save_json(metadata, self._get_is_storage_dir(is_number) / "metadata.json")

        return metadata

    def _check_for_embedded_sit(self, metadata: dict, storage_dir: Path, downloaded_docs: list):
        """
        Check if SIT (Scheme of Inspection and Testing) is embedded in the product manuals.
        If found, update metadata to reflect that SIT is embedded rather than a separate document.
        """
        is_number = metadata["is_number"]

        # Check each downloaded product manual for embedded SIT content
        for doc_record in downloaded_docs:
            if doc_record.get("document_type") == "product_manual":
                pdf_path = Path(doc_record["local_path"])

                if pdf_path.exists():
                    logger.info(f"Checking for embedded SIT in product manual: {pdf_path}")

                    # Extract text from first few pages (enough to find SIT if present)
                    text = extract_text_from_pdf(pdf_path, max_pages=10)

                    if text and contains_sit_indicators(text):
                        logger.info(f"Found embedded SIT in product manual for {is_number}")
                        metadata["collection_status"]["sit"] = "embedded_in_product_manual"

                        # Store the extracted SIT text for reference (optional)
                        # We keep SIT as part of product manual per user request
                        sit_text = None
                        # Could extract specific SIT section if needed for validation
                        # For now, we just note that it's embedded

                        # Update metadata.json on disk immediately after finding embedded SIT
                        self._save_json(metadata, self._get_is_storage_dir(is_number) / "metadata.json")
                        return  # Found embedded SIT, no need to check other product manuals
                    else:
                        logger.info(f"No embedded SIT found in product manual for {is_number}")
                else:
                    logger.warning(f"Product manual PDF not found: {pdf_path}")