#!/usr/bin/env python3
"""
Relationship Mapper for BIS Knowledge Ingestion Pipeline
Builds explicit relationship triples (source_id, relationship, target_id) from processed data.
"""
import re
from typing import List, Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)

def extract_relationships(pages_data: List[Dict], source_id_prefix: str) -> List[Dict[str, Any]]:
    """
    Extract relationships from page-wise data with metadata.

    Args:
        pages_data: List of dicts, each containing at least:
                    - page_number: int
                    - text: str
                    - metadata: dict (from metadata_extractor)
        source_id_prefix: Prefix for source IDs, e.g., "IS_2082_2018_QCO"

    Returns:
        List of relationship dicts, each with:
            - source_id: str
            - relationship: str
            - target_id: str
            - source_page: int (optional)
            - target_text: str (optional, snippet)
    """
    relationships = []

    # We'll define a helper to add a relationship
    def add_rel(rel_type: str, target_id: str, page_num: int = None, target_text: str = None):
        rel = {
            "source_id": source_id_prefix,
            "relationship": rel_type,
            "target_id": target_id,
        }
        if page_num is not None:
            rel["source_page"] = page_num
        if target_text is not None:
            rel["target_text"] = target_text[:200]  # limit snippet length
        relationships.append(rel)

    # Process each page
    for page in pages_data:
        page_num = page.get("page_number")
        text = page.get("text", "")
        metadata = page.get("metadata", {})

        # 1. Relationships from IS references in metadata
        is_refs = metadata.get("is_references", [])
        for is_ref in is_refs:
            # Normalize target ID: e.g., "IS 302-1:2008" -> "IS_302-1_2008"
            target_id = is_ref.replace(" ", "_").replace(":", "_")
            add_rel("REFERENCES_IS", target_id, page_num, is_ref)

        # 2. Relationships from clause numbers (if we want to link clauses within the document)
        # For simplicity, we can create clause IDs and link the page to them.
        clause_nums = metadata.get("clause_numbers", [])
        for clause in clause_nums:
            target_id = f"CLAUSE_{clause.replace('.', '_')}"
            add_rel("CONTAINS_CLAUSE", target_id, page_num, f"Clause {clause}")

        # 3. Detect document type from text (quick and simple)
        text_lower = text.lower()
        if "product manual" in text_lower or "product manual" in text_lower:
            # This document is a product manual for the IS number in source_id_prefix?
            # We'll assume the source_id_prefix already indicates the IS number.
            # We can add a relationship HAS_PRODUCT_MANUAL to the IS number.
            # But we need to know the IS number. We'll extract from source_id_prefix.
            # For now, skip.
            pass
        if "quality control" in text_lower and "order" in text_lower:
            # This is a QCO order
            pass

        # 4. Look for explicit relationship phrases in text
        # Patterns like "as per", "refer to", "see", "conforms to", etc.
        # We'll do a simple regex for "refers to" or "see"
        # This is more advanced; we'll skip for now.

    # Deduplicate relationships: same source_id, relationship, target_id
    seen = set()
    unique_rels = []
    for rel in relationships:
        key = (rel["source_id"], rel["relationship"], rel["target_id"])
        if key not in seen:
            seen.add(key)
            unique_rels.append(rel)

    logger.info(f"Extracted {len(unique_rels)} unique relationships from {len(pages_data)} pages")
    return unique_rels

# Example usage (for testing)
if __name__ == "__main__":
    import sys
    import json
    if len(sys.argv) < 3:
        print("Usage: python relationship_mapper.py <input_json_path> <source_id_prefix> [output_json_path]")
        sys.exit(1)

    input_path = sys.argv[1]
    source_id_prefix = sys.argv[2]
    output_path = sys.argv[3] if len(sys.argv) > 4 else None

    with open(input_path, 'r', encoding='utf-8') as f:
        pages_data = json.load(f)

    relationships = extract_relationships(pages_data, source_id_prefix)

    if output_path:
        import os
        os.makedirs(os.path.dirname(output_path), exist_ok=True) if os.path.dirname(output_path) else None
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(relationships, f, indent=2, ensure_ascii=False)
        print(f"Saved relationships to {output_path}")
    else:
        print(f"Found {len(relationships)} relationships:")
        for rel in relationships[:5]:  # show first 5
            print(f"  {rel['source_id']} --[{rel['relationship']}]--> {rel['target_id']}")