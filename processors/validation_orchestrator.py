#!/usr/bin/env python3
"""
Validation Orchestrator for BIS Knowledge Ingestion Pipeline
Runs validation on processed data across all IS numbers or specific IS numbers.
"""
import json
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

# Import our validator module
sys.path.append(str(Path(__file__).parent))
from validator import validate_is_directory, validate_corpus, generate_validation_report

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("validation_orchestrator.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class ValidationOrchestrator:
    def __init__(self, storage_base: Path = Path("storage/data")):
        self.storage_base = storage_base
        if not self.storage_base.exists():
            logger.warning(f"Storage base {self.storage_base} does not exist")

    def get_is_directories(self) -> List[Path]:
        """Return list of IS_* directories in storage_base."""
        if not self.storage_base.exists():
            return []
        return [d for d in self.storage_base.iterdir()
                if d.is_dir() and d.name.startswith("IS_")]

    def validate_is_directory(self, is_dir: Path) -> Dict[str, Any]:
        """Validate a single IS directory and return results."""
        logger.info(f"Validating IS directory: {is_dir.name}")
        return validate_is_directory(is_dir)

    def run(self, is_numbers: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Run the validation orchestrator.

        Args:
            is_numbers: List of IS numbers to process (e.g., ["IS 2082:2018"]).
                        If None, process all IS directories.

        Returns:
            The full validation report.
        """
        is_dirs = self.get_is_directories()

        if is_numbers:
            # Filter directories by IS number (assuming the directory name matches the IS number pattern)
            # Note: directory names are like IS_17150, IS_2082, etc.
            # We'll assume the provided is_numbers match the directory names after replacing spaces and colons with underscores?
            # For simplicity, we'll just check if the IS number string is in the directory name.
            # This is not perfect but works for the current naming.
            filtered_dirs = []
            for is_dir in is_dirs:
                # Convert directory name to a comparable form: IS_17150 -> IS 17150? We'll just check if the given string is in the dir name.
                for is_num in is_numbers:
                    if is_num.replace(' ', '_').replace(':', '_') in is_dir.name:
                        filtered_dirs.append(is_dir)
                        break
            is_dirs = filtered_dirs
            logger.info(f"Filtered to {len(is_dirs)} IS directories based on IS numbers")
        else:
            logger.info(f"Found {len(is_dirs)} IS directories to validate")

        if not is_dirs:
            logger.warning("No IS directories to validate")
            return {"error": "No IS directories to validate"}

        # Validate each IS directory
        is_dir_results = []
        for is_dir in is_dirs:
            result = self.validate_is_directory(is_dir)
            is_dir_results.append(result)

        # Perform corpus-level validation
        logger.info("Performing corpus-level validation")
        corpus_result = validate_corpus(is_dir_results)

        # Generate final report
        report = generate_validation_report(is_dir_results, corpus_result)

        logger.info(f"Validation orchestrator finished: {report['summary']['valid_is']}/{report['summary']['total_is']} IS directories valid")

        return report

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Run validation on processed BIS data")
    parser.add_argument("--all-is", action="store_true", help="Validate all IS numbers")
    parser.add_argument("--is", nargs="*", default=[], help="Validate specific IS numbers (e.g., 'IS 2082:2018')")
    parser.add_argument("--storage-base", default="storage/data", help="Base storage directory")
    parser.add_argument("--output", default=None, help="Output file for validation report (JSON)")

    args = parser.parse_args()

    orchestrator = ValidationOrchestrator(Path(args.storage_base))

    if len(getattr(args, 'is')) > 0:
        report = orchestrator.run(is_numbers=getattr(args, 'is'))
    elif args.all_is:
        report = orchestrator.run()
    else:
        parser.print_help()
        return

    # Output the report
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
        logger.info(f"Validation report saved to {output_path}")
    else:
        # Print to stdout
        print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()