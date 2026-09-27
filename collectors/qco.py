"""
QCO collector.
Collects QCO gazette notifications for BIS standards.
"""
import logging
import json
import re
from datetime import datetime
from pathlib import Path
from .base import BaseCollector

logger = logging.getLogger(__name__)

class QcoCollector(BaseCollector):
    """
    Collects QCO gazette notifications.

    For each IS number in the niche (QCO is common to the niche):
    1. Constructs the QCO gazette URL from the niche config
    2. Downloads QCO PDF from verified official source
    3. Updates metadata with QCO document information
    """

    def __init__(self, storage_base: str = "storage/data", delay: float = 1.5, config_path: str = "config/niches/water_heaters.json"):
        """
        Args:
            storage_base: Root directory for all stored data.
            delay: Seconds to wait between API calls (rate limiting).
            config_path: Path to the niche config JSON file.
        """
        super().__init__(storage_base=storage_base, delay=delay)
        self.config_path = Path(config_path)
        self._qco_url = None  # Cache the constructed URL

    def _construct_qco_url(self) -> str:
        """
        Construct the download URL for the QCO gazette from the niche config.
        """
        if self._qco_url is not None:
            return self._qco_url

        if not self.config_path.exists():
            logger.warning(f"Config file not found: {self.config_path}")
            return ""

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load config file {self.config_path}: {e}")
            return ""

        qco_ref = config.get("qco_reference")
        if not qco_ref:
            logger.warning("qco_reference not found in config")
            return ""

        # Extract published date
        published_str = qco_ref.get("published")
        if not published_str:
            logger.warning("published date not found in qco_reference")
            return ""

        try:
            # Published date format: "2024-03-05"
            published_date = datetime.strptime(published_str, "%Y-%m-%d")
            year = published_date.year
            month = published_date.month
        except Exception as e:
            logger.error(f"Failed to parse published date '{published_str}': {e}")
            return ""

        # Construct base URL
        base_url = "https://www.bis.gov.in/wp-content/uploads/"
        url_path = f"{year:04d}/{month:02d}/"

        # Create filename from title
        title = qco_ref.get("title", "")
        # Remove parentheses and comma, replace spaces with hyphens
        # We'll try to mimic the URL we found:
        #   "Electrical-Appliances-for-domestic-water-heating-Quality-Control-Order-2023.pdf"
        # The title is: "Electrical Appliances for domestic water heating (Quality Control) Order, 2023"
        # We want to remove the parentheses and comma, and replace spaces with hyphens.
        # Also note the year in the filename is 2023, which is from the title? Actually the title has ", 2023" at the end.
        # We can extract the year from the title or use the year from the published date? The published date is 2024-03-05, but the year in the filename is 2023.
        # The gazette_id is S.O. 1253(E) and published 2024-03-05, but the title mentions 2023.
        # This is confusing.

        # Let's try to create a filename by:
        #   - Removing any text in parentheses and the comma after it.
        #   - Then replacing spaces with hyphens.
        #   - Then appending ".pdf"
        # But we saw the filename includes the year 2023 at the end.

        # Let's try to extract the year from the title if it ends with a year.
        # We'll look for a 4-digit number at the end of the title.
        year_match = re.search(r'(\d{4})$', title)
        if year_match:
            title_year = year_match.group(1)
            # Remove the year and any preceding comma and space from the title for the base
            title_without_year = title[:year_match.start()].strip()
            # Remove trailing comma and space
            title_without_year = title_without_year.rstrip(', ')
        else:
            title_year = str(year)  # fallback to the year from published date
            title_without_year = title

        # Now replace spaces with hyphens and remove any other unwanted characters
        # We'll keep only alphanumeric, hyphen, and space, then replace spaces with hyphens
        try:
            filename_base = re.sub(r'[^a-zA-Z0-9\s]', '', title_without_year)  # remove non-alnum/space
            filename_base = re.sub(r'\s+', '-', filename_base.strip())  # replace spaces with hyphens
            # Append the year (from title if found, else from published date) and .pdf
            filename = f"{filename_base}-{title_year}.pdf"
        except Exception as e:
            logger.error(f"Error constructing QCO filename: {e}")
            return ""

        # Construct full URL
        full_url = base_url + url_path + filename
        self._qco_url = full_url
        logger.info(f"Constructed QCO URL: {full_url}")
        return full_url

    def collect_qco(self, metadata: dict) -> dict:
        """
        Download QCO gazette and update metadata.

        Args:
            metadata: The metadata dict for the IS number.

        Returns:
            Updated metadata dict with collection status and document links.
        """
        is_number = metadata["is_number"]
        logger.info(f"Collecting QCO for {is_number}...")

        # Construct the QCO URL
        qco_url = self._construct_qco_url()
        if not qco_url:
            logger.warning(f"Could not construct QCO URL for {is_number}")
            metadata["collection_status"]["qco_gazette"] = "not_found"
            return metadata

        # Only process if it's from an official domain
        if not self._is_official_source(qco_url):
            logger.warning(f"Skipping unofficial document URL: {qco_url}")
            metadata["collection_status"]["qco_gazette"] = "not_found"
            return metadata

        # Prepare storage directory
        storage_dir = self._get_is_storage_dir(is_number) / "documents"
        storage_dir.mkdir(parents=True, exist_ok=True)

        # Generate a filename for the QCO PDF
        # We can use a fixed name like "qco_gazette.pdf" or derive from URL
        # Let's use the filename from the URL
        from urllib.parse import urlparse
        parsed = urlparse(qco_url)
        qco_filename = Path(parsed.path).name
        if not qco_filename.endswith('.pdf'):
            qco_filename = "qco_gazette.pdf"
        local_path = storage_dir / qco_filename

        # Download the file
        doc_record = self._download_file(qco_url, local_path)

        if doc_record:
            doc_record["document_type"] = "qco"
            doc_record["document_id"] = f"DOC_{metadata['doc_no']}_QCO_0"
            # Update metadata
            metadata["collection_status"]["qco_gazette"] = "available"
            if "qco_gazettes" not in metadata:
                metadata["qco_gazettes"] = []
            metadata["qco_gazettes"].append(doc_record)
            logger.info(f"QCO gazette downloaded and recorded for {is_number}")
        else:
            logger.warning(f"Failed to download QCO gazette for {is_number}")
            metadata["collection_status"]["qco_gazette"] = "not_found"

        # Update metadata.json on disk
        self._save_json(metadata, self._get_is_storage_dir(is_number) / "metadata.json")

        return metadata

    def collect_all(self, metadata_list: list[dict]) -> list[dict]:
        """
        Collect QCO gazette notifications for all IS numbers in the metadata list.

        Args:
            metadata_list: List of metadata dicts for IS numbers.

        Returns:
            List of updated metadata dicts.
        """
        results = []
        for metadata in metadata_list:
            try:
                updated_metadata = self.collect_qco(metadata)
                if updated_metadata:
                    results.append(updated_metadata)
            except Exception as e:
                logger.error(f"Failed to collect QCO for {metadata.get('is_number')}: {e}")
                self._record_error(metadata.get("is_number", "unknown"), str(e), 0)
        return results