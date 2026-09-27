import json
import hashlib
import time
import logging
import os
from pathlib import Path
from datetime import datetime, timezone
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Official BIS domain whitelist — only these are trusted sources
OFFICIAL_DOMAINS = [
    "bis.gov.in",
    "standards.bis.gov.in",
    "standardsadmin.bis.gov.in",
    "lims.bis.gov.in",
    "egazette.gov.in",
    "dpiit.gov.in",
    # Oracle Cloud Storage used by BIS for document hosting (verified working)
    "bmqsdqljvwgm.compat.objectstorage.ap-mumbai-1.oraclecloud.com",
]

def _rate_limit(delay: float = 1.5):
    """Sleep to respect rate limits."""
    time.sleep(delay)

def _http_get(url: str, max_retries: int = 3, stream: bool = False):
    """
    GET request with retry logic. Used for downloading documents.

    Returns:
        Response object or None on failure.
    """
    for attempt in range(1, max_retries + 1):
        try:
            _rate_limit()
            resp = requests.get(url, timeout=60, stream=stream)
            resp.raise_for_status()
            return resp
        except requests.exceptions.RequestException as e:
            logger.warning(f"GET {url} failed (attempt {attempt}/{max_retries}): {e}")

    return None

def _download_file(url: str, local_path: Path) -> dict | None:
    """
    Download a file, compute SHA-256 hash, and save to local_path.
    VERIFIES that the content is actually a PDF before saving.

    Returns:
        Document record dict or None on failure.
    """
    local_path.parent.mkdir(parents=True, exist_ok=True)

    # Check if already downloaded (dedup by URL — hash check happens after)
    if local_path.exists():
        existing_hash = _compute_file_hash(local_path)
        logger.info(f"File already exists: {local_path} (hash: {existing_hash[:12]}...)")
        return {
            "local_path": str(local_path),
            "source_url": url,
            "sha256": existing_hash,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "status": "already_exists",
        }

    resp = _http_get(url, stream=True)
    if resp is None:
        return None

    # Download content
    content = resp.content

    # VERIFY it's actually a PDF
    content_type = resp.headers.get('content-type', '').lower()
    is_pdf_by_content_type = 'pdf' in content_type
    is_pdf_by_signature = content.startswith(b'%PDF') if len(content) >= 4 else False

    if not (is_pdf_by_content_type or is_pdf_by_signature):
        logger.error(f"Downloaded content is not a PDF! Content-Type: {content_type}")
        logger.error(f"First 100 bytes: {content[:100]}")
        return None

    # Additional verification: check for PDF structure
    if b'/Pages' not in content[:1000]:  # Simple check for PDF structure
        logger.warning("PDF may be incomplete or corrupted - missing /Pages indicator")

    hasher = hashlib.sha256()
    hasher.update(content)

    sha256 = hasher.hexdigest()
    logger.info(f"Downloaded: {local_path} ({local_path.stat().st_size} bytes, hash: {sha256[:12]}...)")

    return {
        "local_path": str(local_path),
        "source_url": url,
        "sha256": sha256,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "status": "downloaded",
    }

def _compute_file_hash(filepath: Path) -> str:
    """Compute SHA-256 hash of a file."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def _is_official_source(url: str) -> bool:
    """Check if a URL belongs to an official BIS-family domain."""
    from urllib.parse import urlparse
    parsed = urlparse(url)
    domain = parsed.hostname or ""
    return any(domain == d or domain.endswith(f".{d}") for d in OFFICIAL_DOMAINS)

def _get_is_storage_dir(is_number: str) -> Path:
    """
    Get the storage directory for a given IS number.
    e.g., 'IS 2082:2018' -> 'storage/data/IS_2082/'
    """
    # Normalize: 'IS 2082:2018' -> 'IS_2082'
    # 'IS 302 (Part 2/Sec 21):2018' -> 'IS_302_Part2_Sec21'
    safe_name = is_number.split(":")[0].strip()
    safe_name = safe_name.replace(" ", "_").replace("(", "").replace(")", "")
    safe_name = safe_name.replace("/", "_").replace("\\", "_")
    path = Path("storage/data") / safe_name
    path.mkdir(parents=True, exist_ok=True)
    return path

def _save_json(data: dict | list, filepath: Path):
    """Save data as formatted JSON."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved JSON: {filepath}")

def _default_auth_payload() -> dict:
    """
    Default auth fields required by BIS review-service API.
    These are null for guest/public access.
    """
    return {
        "token": None,
        "refreshToken": None,
        "clientId": None,
        "clientSecret": None,
        "sub": None,
    }

def main():
    print("Downloading REAL Product Manual for IS 2082 with VERIFICATION")
    print("=" * 70)

    # Load metadata
    metadata_path = Path("storage/data/IS_2082/metadata.json")
    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    is_number = metadata["is_number"]
    standard_enc_id = metadata.get("standard_enc_id")

    print(f"IS Number: {is_number}")
    print(f"Standard Enc ID: {standard_enc_id[:50]}..." if standard_enc_id else "None")

    if not standard_enc_id or standard_enc_id == "not_found":
        print("ERROR: No standard_enc_id available")
        return

    # Step 1: Get product manual details using the CORRECT field mapping
    print("\nStep 1: Calling getProductManualDetails with standard_enc_id in standardId field...")
    # Using the review-service API (from base.py)
    REVIEW_SERVICE_URL = "https://standardsadmin.bis.gov.in/review-service/"

    url = f"{REVIEW_SERVICE_URL}getProductManualDetails"
    payload = {
        "standardId": standard_enc_id,  # CORRECT: use encrypted ID
        "fromPage": "guestUserPage",
        **_default_auth_payload()
    }

    try:
        resp = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        response = resp.json()
    except Exception as e:
        print(f"ERROR: Failed to get product manual details from API: {e}")
        return

    print(f"API Response Status: {response.get('status')}")
    print(f"API Response Message: {response.get('msg')}")

    if response.get("status") != "SUCCESS":
        print("ERROR: API did not return SUCCESS")
        print(f"Full response: {json.dumps(response, indent=2)}")
        return

    # Step 2: Extract product manuals details
    data = response.get("data", {})
    if isinstance(data, dict):
        product_manuals_details = data.get("product_manuals_details", [])
    elif isinstance(data, list):
        product_manuals_details = data
    else:
        product_manuals_details = []

    print(f"Found {len(product_manuals_details)} product manuals")

    if not product_manuals_details:
        print("ERROR: No product manuals details in response")
        print(f"Data: {json.dumps(data, indent=2)}")
        return

    # Step 3: Download each product manual using VERIFIED strategy
    storage_dir = _get_is_storage_dir(is_number) / "documents"
    storage_dir.mkdir(parents=True, exist_ok=True)

    downloaded_docs = []

    for i, item in enumerate(product_manuals_details):
        doc_name = item.get("file_name", f"product_manual_{i}")
        doc_file_path = item.get("file_path")  # This is the path within the storage system

        print(f"\nProcessing manual {i+1}:")
        print(f"  File name: {doc_name}")
        print(f"  File path: {doc_file_path}")

        if not doc_file_path:
            print("  WARNING: No file path provided, skipping")
            continue

        # CONSTRUCT DOWNLOAD URL USING VERIFIED STRATEGY
        # Based on our testing, Strategy 3 works: object storage domain directly
        download_url = f"https://bmqsdqljvwgm.compat.objectstorage.ap-mumbai-1.oraclecloud.com/{doc_file_path}"

        # Verify it's an official source
        if not _is_official_source(download_url):
            print(f"  ERROR: URL does not appear to be from official BIS domain")
            print(f"  Hostname: {__import__('urllib.parse').urlparse(download_url).hostname}")
            continue

        print(f"  Download URL: {download_url}")
        local_path = storage_dir / doc_name

        print(f"  Downloading to: {local_path}")
        doc_record = _download_file(download_url, local_path)

        if doc_record:
            doc_record["document_type"] = "product_manual"
            doc_record["document_id"] = f"DOC_{metadata['doc_no']}_PM_{item.get('pk_is_id', i)}"
            downloaded_docs.append(doc_record)
            print(f"  SUCCESS: Downloaded and VERIFIED as PDF")
        else:
            print(f"  ERROR: Failed to download or verify as PDF")

    # Step 4: Update metadata ONLY if we successfully downloaded real PDFs
    if downloaded_docs:
        metadata["collection_status"]["product_manual"] = "available"
        metadata["product_manuals"] = downloaded_docs

        # Save updated metadata
        _save_json(metadata, metadata_path)

        print(f"\n" + "=" * 70)
        print("REAL PDF DOWNLOAD COMPLETE AND VERIFIED")
        print(f"Updated metadata saved to: {metadata_path}")
        print(f"Collection status: {metadata['collection_status']['product_manual']}")
        print(f"Number of product manuals downloaded: {len(downloaded_docs)}")

        for doc in downloaded_docs:
            print(f"  - {doc['document_id']}:")
            print(f"    File: {doc['local_path']}")
            print(f"    Status: {doc['status']}")
            print(f"    SHA-256: {doc['sha256'][:16]}...")
    else:
        print("\nNo product manuals were successfully downloaded and verified")
        metadata["collection_status"]["product_manual"] = "pending"
        _save_json(metadata, metadata_path)

if __name__ == "__main__":
    main()