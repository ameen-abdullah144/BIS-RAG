#!/usr/bin/env python3
"""
Metadata Extractor for BIS Knowledge Ingestion Pipeline
Extracts structured metadata from cleaned text: clause numbers, IS references,
scope statements, requirements, etc.
"""
import re
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

def extract_metadata(text: str) -> Dict[str, Any]:
    """
    Extract metadata from cleaned text.

    Args:
        text: Cleaned text string (could be full document or per page)

    Returns:
        Dictionary with keys:
            - clause_numbers: list of strings (e.g., ["1.2.3", "2.1"])
            - is_references: list of strings (e.g., ["IS 302-1:2008", "IS 2082"])
            - scope_statements: list of strings (sentences containing scope)
            - requirement_statements: list of strings (sentences containing shall/required)
            - other_patterns: dict of any other patterns we might add
    """
    if not text:
        return {
            "clause_numbers": [],
            "is_references": [],
            "scope_statements": [],
            "requirement_statements": [],
            "other_patterns": {}
        }

    # Initialize results
    results = {
        "clause_numbers": [],
        "is_references": [],
        "scope_statements": [],
        "requirement_statements": [],
        "other_patterns": {}
    }

    # 1. Extract clause numbers: patterns like \d+\.\d+(\.\d+)* (allowing optional subclauses)
    # Also consider clauses like "1.", "1.1", "1.1.1", etc.
    clause_pattern = r'\b\d+(?:\.\d+){0,2}\b(?!\w)'  # matches 1, 1.2, 1.2.3 but not as part of a word
    # We'll refine: we want to capture numbers with dots, but avoid matching page numbers or years.
    # For simplicity, we'll use the pattern and then filter.
    potential_clauses = re.findall(clause_pattern, text)
    # Filter out those that are likely years (e.g., 2023) or other numbers.
    # We'll assume clause numbers are less than 100 maybe? Not reliable.
    # Instead, we'll look for patterns where the clause is followed by a space and lowercase letter (start of sentence)
    # or is at start of line. We'll do a simple filter: keep if length < 3? Not good.
    # Given time, we'll keep all matches and later we can dedupe.
    # But we'll also look for patterns like "Clause 1.2" or "clause 1.2:" to increase precision.
    # Let's do two passes: first, look for explicit clause references.
    explicit_clause_pattern = r'(?i)clause\s+\d+(?:\.\d+){0,2}'
    explicit_matches = re.findall(explicit_clause_pattern, text)
    for match in explicit_matches:
        # Extract the number part
        num_match = re.search(r'\d+(?:\.\d+){0,2}', match)
        if num_match:
            results["clause_numbers"].append(num_match.group())
    # Also look for numbers at start of sentences (after period and space) or start of lines.
    # We'll do a simple approach: split into sentences and check if first word is a clause number pattern.
    sentences = re.split(r'[.!?]\s+', text)
    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue
        # First word might be a number with dots
        first_word = sent.split()[0] if sent.split() else ''
        if re.fullmatch(r'\d+(?:\.\d+){0,2}', first_word):
            results["clause_numbers"].append(first_word)
    # Dedupe
    results["clause_numbers"] = list(dict.fromkeys(results["clause_numbers"]))

    # 2. Extract IS references: patterns like IS \d+(?:-\d+)?(?::\d{4})?
    is_pattern = r'\bIS\s+\d+(?:-\d+)?(?::\d{4})?\b'
    is_matches = re.findall(is_pattern, text, flags=re.IGNORECASE)
    # Normalize: uppercase IS, remove extra spaces
    normalized = []
    for match in is_matches:
        # Ensure single space between IS and number
        normalized_match = re.sub(r'\s+', ' ', match.strip()).upper()
        normalized.append(normalized_match)
    results["is_references"] = list(dict.fromkeys(normalized))

    # 3. Extract scope statements: sentences containing scope (case-insensitive)
    # We'll split into sentences and keep those that contain the word scope.
    scope_sentences = []
    for sent in sentences:
        if re.search(r'\bscope\b', sent, flags=re.IGNORECASE):
            scope_sentences.append(sent.strip())
    results["scope_statements"] = scope_sentences[:5]  # limit to first 5

    # 4. Extract requirement statements: sentences containing shall or must or required
    req_pattern = r'\b(shall|must|required|required\s+to)\b'
    req_sentences = []
    for sent in sentences:
        if re.search(req_pattern, sent, flags=re.IGNORECASE):
            req_sentences.append(sent.strip())
    results["requirement_statements"] = req_sentences[:5]  # limit

    # 5. Other patterns: we can add extraction of definitions, etc. but skip for now.

    logger.info(f"Extracted metadata: {len(results['clause_numbers'])} clause numbers, "
                f"{len(results['is_references'])} IS references, "
                f"{len(results['scope_statements'])} scope statements, "
                f"{len(results['requirement_statements'])} requirement statements")
    return results

def extract_metadata_from_pages(pages_data: List[Dict]) -> List[Dict]:
    """
    Extract metadata for each page in the page-wise data.

    Args:
        pages_data: List of dicts (each with page_number, text, char_count)

    Returns:
        List of dicts with original page data plus a 'metadata' key containing extracted metadata.
    """
    pages_with_metadata = []
    for page in pages_data:
        metadata = extract_metadata(page["text"])
        page_with_meta = page.copy()
        page_with_meta["metadata"] = metadata
        pages_with_metadata.append(page_with_meta)
    logger.info(f"Extracted metadata for {len(pages_with_metadata)} pages")
    return pages_with_metadata

# Example usage (for testing)
if __name__ == "__main__":
    import sys
    import json
    if len(sys.argv) < 2:
        print("Usage: python metadata_extractor.py <input_json_path> [output_json_path]")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    with open(input_path, 'r', encoding='utf-8') as f:
        pages_data = json.load(f)

    pages_with_meta = extract_metadata_from_pages(pages_data)

    if output_path:
        import os
        os.makedirs(os.path.dirname(output_path), exist_ok=True) if os.path.dirname(output_path) else None
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(pages_with_meta, f, indent=2, ensure_ascii=False)
        print(f"Saved metadata-extracted pages to {output_path}")
    else:
        # Print summary for first page
        if pages_with_meta:
            meta = pages_with_meta[0]["metadata"]
            print(f"Page {pages_with_meta[0]['page_number']} metadata:")
            print(f"  Clause numbers: {meta['clause_numbers'][:5]}")
            print(f"  IS references: {meta['is_references'][:5]}")
            print(f"  Scope statements: {len(meta['scope_statements'])} found")
            print(f"  Requirement statements: {len(meta['requirement_statements'])} found")