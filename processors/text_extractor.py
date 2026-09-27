"""
PDF text extraction utility for checking embedded content like SIT.
"""
import logging
import fitz  # PyMuPDF
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_path: Path, max_pages: int = 10) -> Optional[str]:
    """
    Extract text from a PDF file to check for embedded content.

    Args:
        pdf_path: Path to the PDF file
        max_pages: Maximum number of pages to extract text from (for efficiency)

    Returns:
        Extracted text as string, or None if extraction fails
    """
    if not pdf_path.exists():
        logger.error(f"PDF file not found: {pdf_path}")
        return None

    try:
        doc = fitz.open(pdf_path)
        text = ""

        # Extract text from first max_pages pages (or all if fewer)
        pages_to_process = min(max_pages, len(doc))

        for page_num in range(pages_to_process):
            page = doc[page_num]
            text += page.get_text()

        doc.close()
        logger.info(f"Extracted text from {pdf_path} ({len(text)} characters from {pages_to_process} pages)")
        return text

    except Exception as e:
        logger.error(f"Failed to extract text from PDF {pdf_path}: {e}")
        return None


def contains_sit_indicators(text: str) -> bool:
    """
    Check if extracted text contains SIT (Scheme of Inspection and Testing) indicators.

    Args:
        text: Extracted text from PDF

    Returns:
        True if SIT indicators found, False otherwise
    """
    if not text:
        return False

    # Convert to lowercase for case-insensitive matching
    text_lower = text.lower()

    # Common SIT indicators in BIS product manuals
    sit_indicators = [
        "scheme of inspection and testing",
        "s.i.t.",
        "sit ",
        "sampling guidelines",
        "level of inspection",
        "test requirements",
        "factory testing",
        "acceptance tests"
    ]

    for indicator in sit_indicators:
        if indicator in text_lower:
            logger.info(f"Found SIT indicator: '{indicator}'")
            return True

    return False


def extract_sit_section_if_embedded(text: str) -> Optional[str]:
    """
    If SIT content is embedded in the text, attempt to extract the relevant section.
    Returns the SIT section text if found, None otherwise.
    """
    if not text or not contains_sit_indicators(text):
        return None

    # Simple approach: return text around SIT indicators for now
    # In a more advanced implementation, we could use regex or NLP to extract exact sections
    lines = text.split('\n')
    sit_lines = []
    found_sit = False

    for line in lines:
        line_lower = line.lower()
        if any(indicator in line_lower for indicator in ["scheme of inspection", "sampling guidelines", "test requirements"]):
            found_sit = True
            sit_lines.append(line)
        elif found_sit and line.strip() == "":
            # Stop at first empty line after finding SIT content
            break
        elif found_sit:
            sit_lines.append(line)

    if sit_lines:
        return '\n'.join(sit_lines)

    return None