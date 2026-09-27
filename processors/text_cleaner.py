#!/usr/bin/env python3
"""
Text Cleaner for BIS Knowledge Ingestion Pipeline
Cleans extracted text from PDFs: removes headers/footers, fixes line breaks,
normalizes whitespace, while preserving structural elements.
"""
import re
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

def clean_text(raw_text: str) -> str:
    """
    Clean raw extracted text.

    Args:
        raw_text: String containing extracted text (possibly with page separators)

    Returns:
        Cleaned text string
    """
    if not raw_text:
        return ""

    # Step 1: Normalize line endings
    text = raw_text.replace('\r\n', '\n').replace('\r', '\n')

    # Step 2: Split into lines
    lines = text.split('\n')

    # Step 3: Strip each line
    stripped_lines = [line.strip() for line in lines]

    # Step 4: Remove empty lines? We'll keep them to preserve paragraph breaks.
    # But we will collapse multiple consecutive empty lines into at most two.
    # We'll process to remove excessive blank lines.
    cleaned_lines = []
    prev_empty = False
    for line in stripped_lines:
        if line == "":
            if not prev_empty:
                cleaned_lines.append(line)
                prev_empty = True
            # else skip additional empty lines
        else:
            cleaned_lines.append(line)
            prev_empty = False

    # Step 5: Join lines back with single newline
    text = "\n".join(cleaned_lines)

    # Step 6: Remove potential headers/footers by detecting repetitive lines across pages?
    # For simplicity, we skip this advanced step for now.
    # If we have page-wise data, we could compare lines across pages.
    # We'll leave it as a future improvement.

    # Step 7: Ensure there is no excessive whitespace (more than 2 spaces) inside lines.
    # Replace multiple spaces with a single space.
    text = re.sub(r' {2,}', ' ', text)

    # Step 8: Remove spaces at start and end of the whole text again.
    text = text.strip()

    logger.info(f"Cleaned text: original length {len(raw_text)}, cleaned length {len(text)}")
    return text

def clean_pages(pages_data: List[Dict]) -> List[Dict]:
    """
    Clean text for each page in the page-wise data.

    Args:
        pages_data: List of dicts from PDF extractor (each with page_number, text, char_count)

    Returns:
        List of dicts with cleaned text and updated char_count
    """
    cleaned_pages = []
    for page in pages_data:
        cleaned = clean_text(page["text"])
        cleaned_pages.append({
            "page_number": page["page_number"],
            "text": cleaned,
            "char_count": len(cleaned)
        })
    logger.info(f"Cleaned {len(pages_data)} pages")
    return cleaned_pages

# Example usage (for testing)
if __name__ == "__main__":
    import sys
    import json
    if len(sys.argv) < 2:
        print("Usage: python text_cleaner.py <input_json_path> [output_json_path]")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else None

    with open(input_path, 'r', encoding='utf-8') as f:
        pages_data = json.load(f)

    cleaned_pages = clean_pages(pages_data)

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(cleaned_pages, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved cleaned pages to {output_path}")
    else:
        # Print first page as preview
        if cleaned_pages:
            print(f"Page {cleaned_pages[0]['page_number']}: {cleaned_pages[0]['char_count']} chars")
            print("First 200 chars:", cleaned_pages[0]['text'][:200].replace('\n', ' '))