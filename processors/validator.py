#!/usr/bin/env python3
"""
Validator for BIS Knowledge Ingestion Pipeline
Validates the outputs of Phase 2 processing (text, metadata, relationships).
"""
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)

def validate_json_file(file_path: Path) -> Tuple[bool, Optional[Dict], Optional[str]]:
    """
    Validate that a file exists and contains valid JSON.

    Returns (is_valid, data, error_message)
    """
    if not file_path.exists():
        return False, None, f"File not found: {file_path}"
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return True, data, None
    except json.JSONDecodeError as e:
        return False, None, f"Invalid JSON in {file_path}: {e}"
    except Exception as e:
        return False, None, f"Error reading {file_path}: {e}"

def validate_document(is_dir: Path, document_stem: str) -> Dict[str, Any]:
    """
    Validate the outputs for a single document (based on its stem).

    Expected files:
      - storage/data/IS_*/text/{stem}_extracted.json
      - storage/data/IS_*/text/cleaned/{stem}_cleaned.json
      - storage/data/IS_*/metadata/{stem}_metadata.json

    Returns a dictionary with validation results for this document.
    """
    result = {
        "document": document_stem,
        "is_dir": str(is_dir.name),
        "valid": True,
        "errors": [],
        "warnings": [],
        "info": {}
    }

    # Define file paths
    text_dir = is_dir / "text"
    cleaned_dir = text_dir / "cleaned"
    meta_dir = is_dir / "metadata"

    extracted_path = text_dir / f"{document_stem}_extracted.json"
    cleaned_path = cleaned_dir / f"{document_stem}_cleaned.json"
    metadata_path = meta_dir / f"{document_stem}_metadata.json"

    # Validate extracted text
    valid, data, error = validate_json_file(extracted_path)
    if not valid:
        result["valid"] = False
        result["errors"].append(f"Extracted text: {error}")
    else:
        result["info"]["extracted_pages"] = len(data) if isinstance(data, list) else 1
        if result["info"]["extracted_pages"] == 0:
            result["warnings"].append("Extracted text is empty")

    # Validate cleaned text
    valid, data, error = validate_json_file(cleaned_path)
    if not valid:
        result["valid"] = False
        result["errors"].append(f"Cleaned text: {error}")
    else:
        result["info"]["cleaned_pages"] = len(data) if isinstance(data, list) else 1
        if result["info"]["cleaned_pages"] == 0:
            result["warnings"].append("Cleaned text is empty")

    # Validate metadata
    valid, data, error = validate_json_file(metadata_path)
    if not valid:
        result["valid"] = False
        result["errors"].append(f"Metadata: {error}")
    else:
        # Expect data to be a list of pages (each page is a dict with a 'metadata' field)
        if not isinstance(data, list):
            result["warnings"].append("Metadata is not a list of pages")
            # Treat as empty for further checks
            data = []
        # Aggregate metadata across pages
        all_clause_numbers = []
        all_is_references = []
        all_scope_statements = []
        all_requirement_statements = []
        for page in data:
            if not isinstance(page, dict):
                continue
            meta = page.get("metadata", {})
            if isinstance(meta, dict):
                all_clause_numbers.extend(meta.get("clause_numbers", []))
                all_is_references.extend(meta.get("is_references", []))
                all_scope_statements.extend(meta.get("scope_statements", []))
                all_requirement_statements.extend(meta.get("requirement_statements", []))
        # Check for expected metadata fields (if we found any pages)
        if data:
            expected_fields = ["clause_numbers", "is_references", "scope_statements", "requirement_statements"]
            # We'll check if we have at least one entry in each aggregated list? Not required.
            # Instead, we'll just note if all are empty.
            if not (all_clause_numbers or all_is_references or all_scope_statements or all_requirement_statements):
                result["warnings"].append("Metadata appears empty (no clause numbers, IS references, scope statements, or requirement statements found)")
        # Info about counts
        result["info"]["clause_count"] = len(all_clause_numbers)
        result["info"]["is_ref_count"] = len(all_is_references)
        result["info"]["scope_count"] = len(all_scope_statements)
        result["info"]["req_count"] = len(all_requirement_statements)
        # Store the aggregated lists if needed? Not necessary.

    return result

def validate_is_directory(is_dir: Path) -> Dict[str, Any]:
    """
    Validate all documents in an IS directory.

    Returns a dictionary with validation results for the IS directory.
    """
    result = {
        "is_dir": str(is_dir.name),
        "valid": True,
        "documents": [],
        "errors": [],
        "warnings": [],
        "info": {}
    }

    # Check that the directory exists
    if not is_dir.exists() or not is_dir.is_dir():
        result["valid"] = False
        result["errors"].append(f"IS directory not found: {is_dir}")
        return result

    # Find document stems from the text directory (assuming extracted files are there)
    text_dir = is_dir / "text"
    if not text_dir.exists():
        result["valid"] = False
        result["errors"].append(f"Text directory not found: {text_dir}")
        return result

    # Look for extracted files to get document stems
    extracted_files = list(text_dir.glob("*_extracted.json"))
    if not extracted_files:
        result["warnings"].append(f"No extracted text files found in {text_dir}")
        # We'll still try to validate whatever we can

    document_stems = [f.stem.replace("_extracted", "") for f in extracted_files]

    # Validate each document
    for stem in document_stems:
        doc_result = validate_document(is_dir, stem)
        result["documents"].append(doc_result)
        if not doc_result["valid"]:
            result["valid"] = False
        # Collect errors and warnings
        result["errors"].extend([f"[{stem}] {e}" for e in doc_result["errors"]])
        result["warnings"].extend([f"[{stem}] {w}" for w in doc_result["warnings"]])

    # Summary info
    result["info"]["document_count"] = len(document_stems)
    result["info"]["valid_document_count"] = sum(1 for d in result["documents"] if d["valid"])

    return result

def validate_corpus(is_dir_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Perform corpus-level validation across all IS directories.

    Returns a dictionary with corpus-level validation results.
    """
    result = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "info": {}
    }

    # Collect all IS numbers from the results
    is_numbers = [res["is_dir"] for res in is_dir_results if "is_dir" in res]
    result["info"]["is_numbers"] = is_numbers
    result["info"]["is_count"] = len(is_numbers)

    # Check for internal consistency: relationships should reference existing IS numbers
    # We'll need to load the relationships.json from each IS directory to check references.
    # For simplicity, we'll do a basic check: if a relationship references an IS, that IS should be in our list.
    # We'll skip this for now to keep it simple, but we can add if needed.

    # Check completeness: we could compare with expected IS numbers from a master list, but we don't have that.
    # Instead, we'll just note the IS numbers we found.

    # For now, we'll just compute aggregate statistics.
    total_docs = sum(res.get("info", {}).get("document_count", 0) for res in is_dir_results)
    valid_docs = sum(res.get("info", {}).get("valid_document_count", 0) for res in is_dir_results)
    result["info"]["total_documents"] = total_docs
    result["info"]["valid_documents"] = valid_docs

    if total_docs == 0:
        result["warnings"].append("No documents found in any IS directory")
        result["valid"] = False
    elif valid_docs < total_docs:
        result["valid"] = False
        result["warnings"].append(f"{total_docs - valid_docs} documents failed validation")

    # We could also check for empty relationships files, etc.
    # Let's add a check for relationships.json existence and validity.
    empty_relationships = 0
    missing_relationships = 0
    invalid_relationships = 0
    for res in is_dir_results:
        is_dir = Path("storage/data") / res["is_dir"]
        rel_path = is_dir / "relationships.json"
        if not rel_path.exists():
            missing_relationships += 1
        else:
            valid, data, error = validate_json_file(rel_path)
            if not valid:
                invalid_relationships += 1
                result["warnings"].append(f"Invalid relationships.json in {res['is_dir']}: {error}")
            else:
                if isinstance(data, list) and len(data) == 0:
                    empty_relationships += 1

    if missing_relationships > 0:
        result["warnings"].append(f"{missing_relationships} IS directories missing relationships.json")
    if invalid_relationships > 0:
        result["warnings"].append(f"{invalid_relationships} IS directories have invalid relationships.json")
        # Not setting valid to False because it's a warning
    if empty_relationships > 0:
        result["info"]["empty_relationships_count"] = empty_relationships
        result["warnings"].append(f"{empty_relationships} IS directories have empty relationships lists")

    return result

def generate_validation_report(is_dir_results: List[Dict[str, Any]], corpus_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a final validation report combining IS-level and corpus-level results.
    """
    report = {
        "timestamp": str(Path(__file__).parent),  # We'll just use a placeholder; in reality we'd use datetime
        "corpus_validation": corpus_result,
        "is_validations": is_dir_results,
        "summary": {
            "overall_valid": corpus_result.get("valid", False) and all(is_res.get("valid", False) for is_res in is_dir_results),
            "total_is": len(is_dir_results),
            "valid_is": sum(1 for is_res in is_dir_results if is_res.get("valid", False)),
            "total_documents": corpus_result.get("info", {}).get("total_documents", 0),
            "valid_documents": corpus_result.get("info", {}).get("valid_documents", 0)
        }
    }
    return report

# Example usage (for testing)
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python validator.py <is_directory_path> [document_stem]")
        sys.exit(1)

    is_dir = Path(sys.argv[1])
    if len(sys.argv) > 2:
        document_stem = sys.argv[2]
        result = validate_document(is_dir, document_stem)
        print(json.dumps(result, indent=2))
    else:
        result = validate_is_directory(is_dir)
        print(json.dumps(result, indent=2))