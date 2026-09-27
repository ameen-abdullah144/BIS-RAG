#!/usr/bin/env python3
"""
BIS Knowledge Ingestion Pipeline Orchestrator
Main entry point for executing the automated pipeline.
"""

import argparse
import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.pipeline_orchestrator import BISPipelineOrchestrator
from scripts.pipeline_utils import PipelineLogger


def main():
    """Main entry point for the pipeline orchestrator."""
    parser = argparse.ArgumentParser(
        description="BIS Knowledge Ingestion Pipeline Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full pipeline with default configuration
  python scripts/run_pipeline.py

  # Run only collection and processing phases
  python scripts/run_pipeline.py --phases collection processing

  # Run pipeline with specific IS numbers
  python scripts/run_pipeline.py --is-numbers IS 2082 IS 302 IS 368

  # Run pipeline in continuous loop mode
  python scripts/run_pipeline.py --mode continuous

  # Show current IS number queue status
  python scripts/run_pipeline.py --status

  # Reset IS number state
  python scripts/run_pipeline.py --reset
        """
    )

    parser.add_argument(
        "--config",
        type=str,
        default="config/pipeline_config.json",
        help="Path to pipeline configuration file"
    )

    parser.add_argument(
        "--phases",
        nargs="+",
        choices=["collection", "processing", "validation", "indexing", "reporting"],
        help="Specific phases to run (default: all enabled phases)"
    )

    parser.add_argument(
        "--is-numbers",
        nargs="+",
        help="Specific IS numbers to process (overrides config)"
    )

    parser.add_argument(
        "--mode",
        choices=["single", "continuous", "daemon"],
        default="single",
        help="Execution mode (default: single)"
    )

    parser.add_argument(
        "--status",
        action="store_true",
        help="Show IS number queue status and exit"
    )

    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset IS number state and exit"
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Override log level from config"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be executed without actually running"
    )

    args = parser.parse_args()

    # Set up logging
    logger = PipelineLogger("bis_pipeline_orchestrator").get_logger()
    logger.info("Starting BIS Knowledge Ingestion Pipeline Orchestrator")
    logger.info(f"Project root: {project_root}")

    try:
        # Initialize the orchestrator
        orchestrator = BISPipelineOrchestrator(
            config_path=args.config,
            log_level_override=args.log_level
        )

        # Handle special commands
        if args.status:
            status = orchestrator.get_is_number_manager().get_status()
            print("IS Number Queue Status:")
            for key, value in status.items():
                print(f"  {key.capitalize()}: {value}")
            return 0

        if args.reset:
            orchestrator.get_is_number_manager().clear_all()
            print("IS number state has been reset")
            return 0

        # Run the pipeline
        result = orchestrator.run_pipeline(
            phases=args.phases,
            is_numbers=args.is_numbers,
            mode=args.mode,
            dry_run=args.dry_run
        )

        if result:
            logger.info("Pipeline execution completed successfully")
            return 0
        else:
            logger.error("Pipeline execution failed")
            return 1

    except KeyboardInterrupt:
        logger.info("Pipeline execution interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Unexpected error in pipeline orchestrator: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())