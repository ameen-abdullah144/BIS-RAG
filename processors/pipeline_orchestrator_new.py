#!/usr/bin/env python3
"""
Pipeline Orchestrator for BIS Knowledge Ingestion Pipeline
Scales Phase 2 processing (PDF extraction, text cleaning, metadata extraction,
relationship mapping) across all IS numbers and document types.
"""
import json
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

# Import our processor modules
sys.path.append(str(Path(__file__).parent))
from pdf_extractor import extract_text_from_pdf, save_extracted_text
from text_cleaner import clean_pages
from metadata_extractor import extract_metadata_from_pages
from relationship_mapper import extract_relationships

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("pipeline_orchestrator.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class PipelineOrchestrator:
    def __init__(self, storage_base: Path = Path("storage/data")):
        self.storage_base = storage_base
        self.storage_base.mkdir(parents=True, exist_ok=True)

    def get_is_directories(self) -> List[Path]:
        """Return list of IS_* directories in storage_base."""
        if not self.storage_base.exists():
            logger.warning(f"Storage base {self.storage_base} does not exist")
            return []
        return [d for d in self.storage_base.iterdir()
                if d.is_dir() and d.name.startswith("IS_")]

    def get_metadata(self, is_dir: Path) -> Optional[Dict]:
        """Load metadata.json for an IS directory."""
        metadata_path = is_dir / "metadata.json"
        if not metadata_path.exists():
            logger.error(f"No metadata.json found in {is_dir}")
            return None
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load metadata.json in {is_dir}: {e}")
            return None

    def get_pdf_files(self, is_dir: Path) -> List[Path]:
        """Return list of PDF files in the IS directory's documents folder."""
        docs_dir = is_dir / "documents"
        if not docs_dir.exists():
            logger.warning(f"No documents directory in {is_dir}")
            return []
        return list(docs_dir.glob("*.pdf"))

    def ensure_output_dirs(self, is_dir: Path):
        """Ensure output directories exist for an IS directory."""
        (is_dir / "text").mkdir(parents=True, exist_ok=True)
        (is_dir / "text" / "cleaned").mkdir(parents=True, exist_ok=True)
        (is_dir / "metadata").mkdir(parents=True, exist_ok=True)

    def process_pdf(self, pdf_path: Path, is_dir: Path, metadata: Dict) -> tuple[bool, List[Dict]]:
        """
        Process a single PDF file through all four stages.

        Returns (success, relationships) where relationships is a list of relationship dicts.
        """
        logger.info(f"Processing {pdf_path.name} in {is_dir.name}")

        # Build source ID prefix from metadata
        is_number = metadata.get("is_number", "UNKNOWN_IS")
        year = metadata.get("year", "0000")
        # Clean for use in IDs: replace spaces and special chars
        source_id_prefix = f"{is_number.replace(' ', '_').replace(':', '_')}_{year}"

        try:
            # Stage 1: PDF Extraction
            logger.info(f"  Stage 1: Extracting text from PDF")
            pages = extract_text_from_pdf(pdf_path)
            if pages is None:
                logger.error(f"  PDF extraction failed for {pdf_path.name}")
                return False, []

            # Save extracted text
            text_dir = is_dir / "text"
            text_dir.mkdir(parents=True, exist_ok=True)
            extracted_json_path = text_dir / f"{pdf_path.stem}_extracted.json"
            if not save_extracted_text(pages, extracted_json_path):
                logger.error(f"  Failed to save extracted text for {pdf_path.name}")
                return False, []
            logger.info(f"  Saved extracted text to {extracted_json_path}")

            # Stage 2: Text Cleaning
            logger.info(f"  Stage 2: Cleaning text")
            cleaned_pages = clean_pages(pages)
            cleaned_dir = is_dir / "text" / "cleaned"
            cleaned_dir.mkdir(parents=True, exist_ok=True)
            cleaned_json_path = cleaned_dir / f"{pdf_path.stem}_cleaned.json"
            if not save_extracted_text(cleaned_pages, cleaned_json_path):
                logger.error(f"  Failed to save cleaned text for {pdf_path.name}")
                return False, []
            logger.info(f"  Saved cleaned text to {cleaned_json_path}")

            # Stage 3: Metadata Extraction
            logger.info(f"  Stage 3: Extracting metadata")
            pages_with_meta = extract_metadata_from_pages(cleaned_pages)
            meta_dir = is_dir / "metadata"
            meta_dir.mkdir(parents=True, exist_ok=True)
            meta_json_path = meta_dir / f"{pdf_path.stem}_metadata.json"
            with open(meta_json_path, 'w', encoding='utf-8') as f:
                json.dump(pages_with_meta, f, indent=2, ensure_ascii=False)
            logger.info(f"  Saved metadata to {meta_json_path}")

            # Stage 4: Relationship Mapping
            logger.info(f"  Stage 4: Mapping relationships")
            relationships = extract_relationships(pages_with_meta, source_id_prefix)
            logger.info(f"  Extracted {len(relationships)} relationships for {pdf_path.name}")

            logger.info(f"  Successfully processed {pdf_path.name}")
            return True, relationships

        except Exception as e:
            logger.error(f"  Unexpected error processing {pdf_path.name}: {e}", exc_info=True)
            return False, []

    def process_is_directory(self, is_dir: Path) -> bool:
        """
        Process all PDF documents in an IS directory.

        Returns True if at least one PDF was processed successfully.
        """
        logger.info(f"Processing IS directory: {is_dir.name}")

        # Load metadata
        metadata = self.get_metadata(is_dir)
        if metadata is None:
            return False

        # Ensure output directories exist
        self.ensure_output_dirs(is_dir)

        # Get PDF files
        pdf_files = self.get_pdf_files(is_dir)
        if not pdf_files:
            logger.warning(f"No PDF files found in {is_dir}")
            return False

        # Process each PDF and accumulate relationships
        success_count = 0
        all_relationships = []  # accumulate relationships from all PDFs

        for pdf_path in pdf_files:
            success, rels = self.process_pdf(pdf_path, is_dir, metadata)
            if success:
                success_count += 1
                all_relationships.extend(rels)
                logger.info(f"Accumulated relationships: {len(all_relationships)} total so far")
            else:
                logger.error(f"Failed to process {pdf_path.name}")

        # Write combined relationships.json for this IS directory
        if all_relationships:
            rel_json_path = is_dir / "relationships.json"
            # Deduplicate relationships: same source_id, relationship, target_id
            seen = set()
            unique_rels = []
            for rel in all_relationships:
                key = (rel["source_id"], rel["relationship"], rel["target_id"])
                if key not in seen:
                    seen.add(key)
                    unique_rels.append(rel)
            with open(rel_json_path, 'w', encoding='utf-8') as f:
                json.dump(unique_rels, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved {len(unique_rels)} unique relationships to {rel_json_path}")
        else:
            logger.warning(f"No relationships extracted for {is_dir.name}")

        logger.info(f"Finished processing {is_dir.name}: {success_count}/{len(pdf_files)} PDFs successful")

        return success_count > 0

    def run(self, is_numbers: Optional[List[str]] = None):
        """
        Run the pipeline orchestrator.

        Args:
            is_numbers: List of IS numbers to process (e.g., ["IS 2082:2018"]).
                        If None, process all IS directories.
        """
        is_dirs = self.get_is_directories()

        if is_numbers:
            # Filter directories by IS number (assuming metadata contains the IS number string)
            filtered_dirs = []
            for is_dir in is_dirs:
                metadata = self.get_metadata(is_dir)
                if metadata:
                    is_number = metadata.get("is_number", "")
                    if is_number in is_numbers:
                        filtered_dirs.append(is_dir)
            is_dirs = filtered_dirs
            logger.info(f"Filtered to {len(is_dirs)} IS directories based on IS numbers")
        else:
            logger.info(f"Found {len(is_dirs)} IS directories to process")

        if not is_dirs:
            logger.warning("No IS directories to process")
            return

        # Process each IS directory
        success_count = 0
        for is_dir in is_dirs:
            if self.process_is_directory(is_dir):
                success_count += 1

        logger.info(f"Pipeline orchestrator finished: {success_count}/{len(is_dirs)} IS directories processed successfully")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Scale Phase 2 processing across IS numbers")
    parser.add_argument("--all-is", action="store_true", help="Process all IS numbers")
    parser.add_argument("--is", nargs="*", default=[], help="Process specific IS numbers (e.g., 'IS 2082:2018')")
    parser.add_argument("--storage-base", default="storage/data", help="Base storage directory")

    args = parser.parse_args()

    orchestrator = PipelineOrchestrator(Path(args.storage_base))

    if args.is:
        orchestrator.run(is_numbers=args.is)
    elif args.all_is:
        orchestrator.run()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()