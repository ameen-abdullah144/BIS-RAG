#!/usr/bin/env python3
"""
PDF Extractor for BIS Knowledge Ingestion Pipeline
Extracts text from PDF files with page-level tracking.
"""
import fitz  # PyMuPDF
from pathlib import Path
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

def extract_text_from_pdf(pdf_path: Path) -> Optional[List[Dict]]:
    """
    Extract text from a PDF file, returning page-wise text with metadata.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        List of dictionaries, each containing:
            - page_number: int (1-based)
            - text: str (extracted text from the page)
            - char_count: int
        Returns None if extraction fails.
    """
    if not pdf_path.is_file():
        logger.error(f"PDF file not found: {pdf_path}")
        return None

    try:
        doc = fitz.open(pdf_path)
        pages_data = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text")  # plain text
            # Optionally, we could also get blocks, words, etc.
            pages_data.append({
                "page_number": page_num + 1,  # 1-based for human readability
                "text": text,
                "char_count": len(text)
            })

        doc.close()
        logger.info(f"Extracted text from {pdf_path.name}: {len(pages_data)} pages")
        return pages_data

    except Exception as e:
        logger.error(f"Failed to extract text from PDF {pdf_path}: {e}")
        return None

def save_extracted_text(pages_data: List[Dict], output_path: Path) -> bool:
    """
    Save extracted page-wise text to a JSON file for inspection.

    Args:
        pages_data: Output from extract_text_from_pdf
        output_path: Path to save JSON file

    Returns:
        True if successful, False otherwise
    """
    try:
        import json
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(pages_data, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved extracted text to {output_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to save extracted text to {output_path}: {e}")
        return False

def extract_full_text(pages_data: List[Dict]) -> str:
    """
    Combine all page text into a single string with page separators.

    Args:
        pages_data: Output from extract_text_from_pdf

    Returns:
        Single string with form feed (\\f) between pages or custom separator.
    """
    if not pages_data:
        return ""
    separator = "\n\\f\n"  # Form feed for page separation
    return separator.join([page["text"] for page in pages_data])

# Example usage (for testing)
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python pdf_extractor.py <pdf_path> [output_json_path]")
        sys.exit(1)

    pdf_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else None

    pages = extract_text_from_pdf(pdf_path)
    if pages is None:
        sys.exit(1)

    print(f"Successfully extracted {len(pages)} pages")
    for page in pages[:3]:  # Show first 3 pages
        print(f"Page {page['page_number']}: {page['char_count']} chars")
        # Print first 200 chars of text
        preview = page['text'][:200].replace('\n', ' ')
        print(f"  Preview: {preview}...")

    if output_path:
        if save_extracted_text(pages, output_path):
            print(f"Saved full extraction to {output_path}")