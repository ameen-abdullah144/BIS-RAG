"""
Laboratories Collector.
Collects laboratory testing facility information from lims.bis.gov.in.
"""
import logging
import re
from pathlib import Path
from bs4 import BeautifulSoup
from .base import BaseCollector

logger = logging.getLogger(__name__)

class LaboratoriesCollector(BaseCollector):
    """
    Collects laboratory testing facility information from lims.bis.gov.in "IS-Wise Test Facilities".

    For each IS number with available standard_id:
    1. Searches lims.bis.gov.in for laboratories authorized to test the IS number
    2. Retrieves laboratory information (name, address, contact, etc.)
    3. Updates metadata with laboratory information and TESTED_BY relationships
    """

    def _parse_is_number(self, is_number: str) -> dict:
        """
        Parse IS code into components for LIMS search.
        Supports formats like:
        - IS 2082:2018
        - IS 302 (Part 2/Sec 21):2018
        - IS 17150:2019
        Returns dict with keys: doc_no, year, part, section
        """
        # Remove leading/trailing whitespace
        is_number = is_number.strip()

        # Initialize defaults
        doc_no = ""
        year = ""
        part = ""
        section = ""

        # Extract year (after last colon)
        if ":" in is_number:
            year_part = is_number.split(":")[-1]
            if year_part.isdigit() and len(year_part) == 4:
                year = year_part
                # Remove the year part for further processing
                is_number_without_year = is_number[:-len(year_part)-1]
            else:
                is_number_without_year = is_number
        else:
            is_number_without_year = is_number

        # Extract part and section if present
        # Format: IS <doc_no> (Part <part>/Sec <section>)
        import re
        part_section_match = re.search(r'\(Part\s+(\d+)/Sec\s+(\d+)\)', is_number_without_year)
        if part_section_match:
            part = part_section_match.group(1)
            section = part_section_match.group(2)
            # Remove the part/section portion
            is_number_without_year = re.sub(r'\s*\(Part\s+\d+/Sec\s+\d+\)', '', is_number_without_year)

        # What remains should be "IS <doc_no>" or similar
        # Extract doc_no: digits after "IS "
        is_prefix = "IS "
        if is_number_without_year.startswith(is_prefix):
            doc_no_candidate = is_number_without_year[len(is_prefix):].strip()
            # doc_no should be digits only
            if doc_no_candidate.isdigit():
                doc_no = doc_no_candidate

        return {
            "doc_no": doc_no,
            "year": year,
            "part": part,
            "section": section
        }

    def collect_laboratories(self, metadata: dict) -> dict:
        """
        Fetch laboratory information and update metadata.

        Args:
            metadata: The metadata dict for the IS number (needs standard_id).

        Returns:
            Updated metadata dict with collection status and laboratory information.
        """
        is_number = metadata["is_number"]
        standard_id = metadata.get("standard_id")

        if not standard_id or standard_id == "not_found":
            logger.warning(f"No standard_id for {is_number}, skipping laboratories collection.")
            return metadata

        logger.info(f"Collecting laboratories for {is_number}...")

        # Parse IS number into components
        is_components = self._parse_is_number(is_number)
        doc_no = is_components["doc_no"]
        year = is_components["year"]
        part = is_components["part"]
        section = is_components["section"]

        # Build query parameters for LIMS search
        params = {
            "is_number__doc_no": doc_no,
            "is_number__year": year,
            "is_number__part": part,
            "is_number__section": section,
            "lab__lab_name__icontains": "",  # Optional lab name filter
            "is_title": ""                   # Optional IS title filter
        }

        # Use LIMS base URL from base class
        url = f"{self.LIMS_URL}/home/search_is_number/"

        # Make GET request to LIMS
        query_string = self._params_to_string(params)
        full_url = f"{url}?{query_string}" if query_string else url
        response = self._http_get(full_url)

        if not response:
            logger.info(f"No laboratory response received for {is_number}")
            metadata["collection_status"]["laboratories"] = "not_found"
            return metadata

        # Use raw HTML; we will handle malformed td/th tags per row after parsing
        html_text = response.text

        # Parse HTML response directly, trying lxml first then html.parser if table not found
        try:
            soup = BeautifulSoup(html_text, 'lxml')
            table = soup.find('table', id='review_lab_list')
        except Exception:
            soup = None
            table = None
        if table is None:
            try:
                soup = BeautifulSoup(html_text, 'html.parser')
                table = soup.find('table', id='review_lab_list')
            except Exception:
                soup = None
                table = None
        if table is None:
            logger.info(f"No laboratory table found in response for {is_number}")
            metadata["collection_status"]["laboratories"] = "not_found"
            return metadata

        logger.info(f"Laboratory table found. Checking for tbody...")

        # Get tbody
        tbody = table.find('tbody')
        if not tbody:
            logger.info(f"No tbody in laboratory table for {is_number}")
            metadata["collection_status"]["laboratories"] = "not_found"
            return metadata

        # Fix malformed </th> tags in tbody: replace '</th>' with '</td>' in the tbody's HTML
        tbody_html = str(tbody)
        fixed_tbody_html = re.sub(r'</th>', '</td>', tbody_html)
        # Parse the fixed HTML and extract the tbody contents
        fixed_tbody_soup = BeautifulSoup(fixed_tbody_html, 'html.parser')
        fixed_tbody = fixed_tbody_soup.find('tbody')
        if fixed_tbody:
            # Clear the tbody and replace its contents with the fixed tbody's contents
            tbody.clear()
            for element in fixed_tbody.contents:
                tbody.append(element)

        # Get all rows from tbody (these are the data rows; thead is separate)
        # Only direct child tr elements, to avoid rows from nested tables
        rows = tbody.find_all('tr', recursive=False)

        # Clear previous laboratory data and TESTED_BY relationships for this IS number
        metadata["laboratories"] = []
        if "tested_by_relations" in metadata:
            metadata["tested_by_relations"] = [
                rel for rel in metadata["tested_by_relations"]
                if rel.get("source_id") != metadata["is_number"]
            ]

        # Process each laboratory row
        processed_labs = []
        for row in rows:
            # Get the row's HTML as a string
            row_html = str(row)
            # Fix malformed closing tags: replace '</th>' with '</td>' in the row's HTML
            fixed_row_html = re.sub(r'</th>', '</td>', row_html)
            # Parse the fixed row HTML
            row_soup = BeautifulSoup(fixed_row_html, 'html.parser')
            # Get the actual tr element (since parsing a tr string creates a document containing the tr)
            tr_element = row_soup.find('tr')
            if tr_element is None:
                tr_element = row_soup  # fallback to original behavior
            # Get all td and th elements that are direct children of the tr element
            cells = [cell for cell in tr_element.find_all(['td', 'th']) if cell.parent == tr_element]
            # Expect at least 9 columns based on header
            if len(cells) < 9:
                # If we don't have enough cells, skip this row
                continue
            # Extract cell text
            cell_texts = [cell.get_text(strip=True) for cell in cells]
            # Map columns based on header:
            # 0: S.No.
            # 1: Lab Name
            # 2: Osl Code
            # 3: Indian Standard No.
            # 4: Product
            # 5: Grade / Type / Size / Designation etc.
            # 6: Testing Charges (Excl. Of Taxes)
            # 7: Validity Date
            # 8: Remark
            lab_name = cell_texts[1] if len(cell_texts) > 1 else ""
            lab_code = cell_texts[2] if len(cell_texts) > 2 else ""
            # Only process if we have at least a name or code
            if not lab_name and not lab_code:
                logger.warning(f"Laboratory item missing essential info: {cell_texts}")
                continue

            lab_record = {
                "laboratory_id": lab_code or f"LAB_{len(processed_labs)}",
                "name": lab_name,
                "address": "",  # Not available in search results
                "contact": "",  # Not available
                "email": "",    # Not available
                "website": "",  # Not available
                "status": "",   # Not available; we could use Remark or Validity Date? but leave blank for now
                "source_url": f"{url}?{self._params_to_string(params)}",
                "retrieved_at": self._get_current_timestamp(),
                "raw_data": {
                    "is_number": is_number,
                    "lab_name": lab_name,
                    "lab_code": lab_code,
                    "is_number_from_table": cell_texts[3] if len(cell_texts) > 3 else "",
                    "product": cell_texts[4] if len(cell_texts) > 4 else "",
                    "grade_type_size": cell_texts[5] if len(cell_texts) > 5 else "",
                    "testing_charges": cell_texts[6] if len(cell_texts) > 6 else "",
                    "validity_date": cell_texts[7] if len(cell_texts) > 7 else "",
                    "remark": cell_texts[8] if len(cell_texts) > 8 else ""
                }
            }

            processed_labs.append(lab_record)

        if processed_labs:
            metadata["collection_status"]["laboratories"] = "available"
            metadata["laboratories"] = processed_labs

            # Also create TESTED_BY relationships for the relationship mapper
            # Each lab gets a TESTED_BY relationship to the IS number
            tested_by_relations = []
            for lab in processed_labs:
                tested_by_relations.append({
                    "source_id": metadata["is_number"],
                    "relationship": "TESTED_BY",
                    "target_id": f"LAB_{lab['laboratory_id']}",
                    "target_type": "laboratory",
                    "lab_name": lab["name"],
                    "lab_id": lab["laboratory_id"]
                })

            if "tested_by_relations" not in metadata:
                metadata["tested_by_relations"] = []
            metadata["tested_by_relations"].extend(tested_by_relations)

            logger.info(f"Found {len(processed_labs)} laboratory facilities for {is_number}")
        else:
            metadata["collection_status"]["laboratories"] = "not_found"

        # Update metadata.json on disk
        logger.info(f"About to save metadata for {is_number} with {len(processed_labs)} laboratories")
        self._save_json(metadata, self._get_is_storage_dir(is_number) / "metadata.json")
        logger.info(f"Metadata saved successfully for {is_number}")

        return metadata

    def _params_to_string(self, params: dict) -> str:
        """Convert params dict to query string."""
        from urllib.parse import urlencode
        return urlencode(params)

    def collect_all(self, metadata_list: list[dict]) -> list[dict]:
        """
        Collect laboratory information for all IS numbers in the metadata list.

        Args:
            metadata_list: List of metadata dicts for IS numbers.

        Returns:
            List of updated metadata dicts.
        """
        results = []
        for metadata in metadata_list:
            try:
                updated_metadata = self.collect_laboratories(metadata)
                if updated_metadata:
                    results.append(updated_metadata)
            except Exception as e:
                logger.error(f"Failed to collect laboratories for {metadata.get('is_number')}: {e}")
                self._record_error(metadata.get("is_number", "unknown"), str(e), 0)
        return results

    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()