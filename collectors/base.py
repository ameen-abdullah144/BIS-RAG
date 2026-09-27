"""
Base collector with retry logic, rate limiting, error handling, and logging.
All collectors inherit from this.
"""
import requests
import hashlib
import json
import time
import logging
import os
from pathlib import Path
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class BaseCollector:
    """Base class for all BIS data collectors."""

    # BIS API base URL (discovered via Phase 0 browser inspection)
    REVIEW_SERVICE_URL = "https://standardsadmin.bis.gov.in/review-service/"
    BIS_MAIN_URL = "https://www.bis.gov.in"
    LIMS_URL = "https://lims.bis.gov.in"

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

    def __init__(self, storage_base: str = "storage/data", delay: float = 1.5):
        """
        Args:
            storage_base: Root directory for all stored data.
            delay: Seconds to wait between API calls (rate limiting).
        """
        self.storage_base = Path(storage_base)
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "BIS-DataPipeline/1.0 (SIH26107 Research)",
            "Accept": "application/json",
            "Content-Type": "application/json",
        })
        self.errors = []

    def _rate_limit(self):
        """Sleep to respect rate limits."""
        time.sleep(self.delay)

    def _api_post(self, endpoint: str, payload: dict, max_retries: int = 3) -> dict | None:
        """
        POST to a BIS review-service API endpoint with retry logic.

        Args:
            endpoint: API endpoint name (e.g., 'searchKnowStandards')
            payload: JSON payload dict
            max_retries: Number of retries on failure

        Returns:
            Parsed JSON response or None on failure.
        """
        url = f"{self.REVIEW_SERVICE_URL}{endpoint}"
        for attempt in range(1, max_retries + 1):
            try:
                self._rate_limit()
                resp = self.session.post(url, json=payload, timeout=30)
                resp.raise_for_status()
                return resp.json()
            except requests.exceptions.Timeout:
                logger.warning(f"Timeout on {endpoint} (attempt {attempt}/{max_retries})")
                self._record_error(endpoint, "HTTP timeout", attempt)
            except requests.exceptions.HTTPError as e:
                logger.warning(f"HTTP error on {endpoint}: {e} (attempt {attempt}/{max_retries})")
                self._record_error(endpoint, f"HTTP {resp.status_code}", attempt)
                if resp.status_code in (401, 403, 404):
                    break  # Don't retry auth/not-found errors
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request error on {endpoint}: {e} (attempt {attempt}/{max_retries})")
                self._record_error(endpoint, str(e), attempt)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON from {endpoint} (attempt {attempt}/{max_retries})")
                self._record_error(endpoint, "Invalid JSON response", attempt)
                break

        return None

    def _http_get(self, url: str, max_retries: int = 3, stream: bool = False):
        """
        GET request with retry logic. Used for downloading documents.

        Returns:
            Response object or None on failure.
        """
        for attempt in range(1, max_retries + 1):
            try:
                self._rate_limit()
                resp = self.session.get(url, timeout=60, stream=stream)
                resp.raise_for_status()
                return resp
            except requests.exceptions.RequestException as e:
                logger.warning(f"GET {url} failed (attempt {attempt}/{max_retries}): {e}")
                self._record_error(url, str(e), attempt)

        return None

    def _download_file(self, url: str, local_path: Path) -> dict | None:
        """
        Download a file, compute SHA-256 hash, and save to local_path.

        Returns:
            Document record dict or None on failure.
        """
        local_path.parent.mkdir(parents=True, exist_ok=True)

        # Check if already downloaded (dedup by URL — hash check happens after)
        if local_path.exists():
            existing_hash = self._compute_file_hash(local_path)
            logger.info(f"File already exists: {local_path} (hash: {existing_hash[:12]}...)")
            return {
                "local_path": str(local_path),
                "source_url": url,
                "sha256": existing_hash,
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "status": "already_exists",
            }

        resp = self._http_get(url, stream=True)
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

    def _compute_file_hash(self, filepath: Path) -> str:
        """Compute SHA-256 hash of a file."""
        hasher = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _is_official_source(self, url: str) -> bool:
        """Check if a URL belongs to an official BIS-family domain."""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.hostname or ""
        return any(domain == d or domain.endswith(f".{d}") for d in self.OFFICIAL_DOMAINS)

    def _get_is_storage_dir(self, is_number: str) -> Path:
        """
        Get the storage directory for a given IS number.
        e.g., 'IS 2082:2018' -> storage/data/IS_2082/
        """
        # Normalize: 'IS 2082:2018' -> 'IS_2082'
        # 'IS 302 (Part 2/Sec 21):2018' -> 'IS_302_Part2_Sec21'
        safe_name = is_number.split(":")[0].strip()
        safe_name = safe_name.replace(" ", "_").replace("(", "").replace(")", "")
        safe_name = safe_name.replace("/", "_").replace("\\", "_")
        path = self.storage_base / safe_name
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _save_json(self, data: dict | list, filepath: Path):
        """Save data as formatted JSON."""
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved JSON: {filepath}")

    def _load_json(self, filepath: Path) -> dict | list | None:
        """Load JSON from file, return None if doesn't exist."""
        if not filepath.exists():
            return None
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def _record_error(self, source: str, reason: str, retry_count: int):
        """Record an error for the error report."""
        self.errors.append({
            "source": source,
            "reason": reason,
            "retry_count": retry_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def _default_auth_payload(self) -> dict:
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

    def get_errors(self) -> list:
        """Return accumulated errors."""
        return self.errors
