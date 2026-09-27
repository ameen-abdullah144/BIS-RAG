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

# BIS API base URL (from base.py)
REVIEW_SERVICE_URL = "https://standardsadmin.bis.gov.in/review-service/"
BIS_MAIN_URL = "https://www.bis.gov.in"

# Official BIS domain whitelist — only these are trusted sources
OFFICIAL_DOMAINS = [
    "bis.gov.in",
    "standards.bis.gov.in",
    "standardsadmin.bis.gov.in",
    "lims.bis.gov.in",
    "egazette.gov.in",
    "dpiit.gov.in",
    # Oracle Cloud Storage used by BIS for document hosting
    "bmqsdqljvwgm.compat.objectstorage.ap-mumbai-1.oraclecloud.com",
]

def _rate_limit(delay: float = 1.5):
    """Sleep to respect rate limits."""
    time.sleep(delay)

def _api_post(endpoint: str, payload: dict, max_retries: int = 3) -> dict | None:
    """
    POST to a BIS review-service API endpoint with retry logic.

    Args:
        endpoint: API endpoint name (e.g., 'getProductManualDetails')
        payload: JSON payload dict
        max_retries: Number of retries on failure

    Returns:
        Parsed JSON response or None on failure.
    """
    url = f"{REVIEW_SERVICE_URL}{endpoint}"
    for attempt in range(1, max_retries + 1):
        try:
            _rate_limit()
            resp = requests.post(url, json=payload, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout on {endpoint} (attempt {attempt}/{max_retries})")
        except requests.exceptions.HTTPError as e:
            logger.warning(f"HTTP error on {endpoint}: {e} (attempt {attempt}/{max_retries})")
            if resp.status_code in (401, 403, 404):
                break  # Don't retry auth/not-found errors
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request error on {endpoint}: {e} (attempt {attempt}/{max_retries})")
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON from {endpoint} (attempt {attempt}/{max_retries})")
            break

    return None

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

    hasher = hashlib.sha256()
    with open(local_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
            hasher.update(chunk)

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
    print("Downloading Product Manual for IS 2082 using FIXED approach")
    print("=" * 60)

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
    payload = {
        "standardId": standard_enc_id,  # THIS IS THE FIX - use encrypted ID
        "fromPage": "guestUserPage",
        **_default_auth_payload()
    }

    response = _api_post("getProductManualDetails", payload)

    if not response:
        print("ERROR: Failed to get product manual details from API")
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

    # Step 3: Download each product manual
    storage_dir = _get_is_storage_dir(is_number) / "documents"
    storage_dir.mkdir(parents=True, exist_ok=True)

    downloaded_docs = []

    for i, item in enumerate(product_manuals_details):
        doc_url = item.get("file_path")  # Note: the API returns 'file_path', not 'documentUrl'
        doc_name = item.get("file_name", f"product_manual_{i}")

        print(f"\nProcessing manual {i+1}:")
        print(f"  File name: {doc_name}")
        print(f"  File path: {doc_url}")

        if not doc_url:
            print("  WARNING: No file path provided, skipping")
            continue

        # Construct full URL - need to determine the base
        # Based on debug_api3.py, the file_path seems to be relative to standardsadmin or object storage
        if doc_url.startswith("http"):
            full_url = doc_url
        else:
            # Try standardsadmin first
            full_url = f"https://standardsadmin.bis.gov.in/{doc_url}"

            # We'll verify if this is an official source, if not try alternatives
            if not _is_official_source(full_url):
                # Try Oracle Cloud pattern from debug_api3.py
                full_url = f"https://bmqsdqljvwgm.compat.objectstorage.ap-mumbai-1.oraclecloud.com/n/bmqsdqljvwgm/b/bis_storage/o/{doc_url}"

                if not _is_official_source(full_url):
                    # Try just the object storage domain
                    full_url = f"https://bmqsdqljvwgm.compat.objectstorage.ap-mumbai-1.oraclecloud.com/{doc_url}"

        print(f"  Full URL: {full_url}")

        # Verify it's an official source
        if not _is_official_source(full_url):
            print(f"  ERROR: URL does not appear to be from official BIS domain")
            print(f"  Hostname: {__import__('urllib.parse').urlparse(full_url).hostname}")
            continue

        local_path = storage_dir / doc_name

        print(f"  Downloading to: {local_path}")
        doc_record = _download_file(full_url, local_path)

        if doc_record:
            doc_record["document_type"] = "product_manual"
            doc_record["document_id"] = f"DOC_{metadata['doc_no']}_PM_{item.get('pk_is_id', i)}"
            downloaded_docs.append(doc_record)
            print(f"  SUCCESS: Downloaded and saved")
        else:
            print(f"  ERROR: Failed to download")

    # Step 4: Update metadata
    if downloaded_docs:
        metadata["collection_status"]["product_manual"] = "available"
        metadata["product_manuals"] = downloaded_docs

        # Save updated metadata
        _save_json(metadata, metadata_path)

        print(f"\n" + "=" * 60)
        print("DOWNLOAD COMPLETE")
        print(f"Updated metadata saved to: {metadata_path}")
        print(f"Collection status: {metadata['collection_status']['product_manual']}")
        print(f"Number of product manuals downloaded: {len(downloaded_docs)}")

        for doc in downloaded_docs:
            print(f"  - {doc['document_id']}: {doc['local_path']} ({doc['status']})")
    else:
        print("\nNo product manuals were downloaded")
        metadata["collection_status"]["product_manual"] = "not_found"
        _save_json(metadata, metadata_path)

if __name__ == "__main__":
    main()