"""
BIS Pipeline Orchestrator
Main orchestration engine for the BIS Knowledge Ingestion Pipeline.
"""

import asyncio
import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import threading

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.pipeline_utils import (
    PipelineLogger, load_config, save_config, validate_config,
    PipelineError, retry_on_exception, ensure_directory, format_duration,
    parse_is_number_range, chunk_list, truncate_string
)
from scripts.is_number_manager import ISNumberManager


class PhaseStatus(Enum):
    """Status of a pipeline phase."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class PipelinePhase:
    """Represents a phase in the pipeline."""

    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.status = PhaseStatus.PENDING
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.error_message: Optional[str] = None
        self.results: Dict[str, Any] = {}

    @property
    def duration(self) -> Optional[float]:
        """Get phase duration in seconds."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None

    @property
    def is_complete(self) -> bool:
        """Check if phase is complete (either success or failure)."""
        return self.status in [PhaseStatus.COMPLETED, PhaseStatus.FAILED, PhaseStatus.SKIPPED]

    @property
    def is_successful(self) -> bool:
        """Check if phase completed successfully."""
        return self.status == PhaseStatus.COMPLETED


class BISPipelineOrchestrator:
    """Main orchestrator for the BIS Knowledge Ingestion Pipeline."""

    def __init__(self, config_path: Union[str, Path] = "config/pipeline_config.json",
                 log_level_override: Optional[str] = None):
        """
        Initialize the pipeline orchestrator.

        Args:
            config_path: Path to the pipeline configuration file
            log_level_override: Optional log level to override config
        """
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        self.logger: Optional[PipelineLogger] = None
        self.is_number_manager: Optional[ISNumberManager] = None

        # Pipeline state
        self.phases: Dict[str, PipelinePhase] = {}
        self.global_start_time: Optional[float] = None
        self.global_end_time: Optional[float] = None
        self.should_stop = False

        # Load configuration
        self._load_configuration(log_level_override)

        # Initialize IS Number Manager
        self.is_number_manager = ISNumberManager(
            self.config.get("is_number_management", {}).get("storage_dir", "is_number_state")
        )

        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _load_configuration(self, log_level_override: Optional[str] = None) -> None:
        """Load and validate pipeline configuration."""
        try:
            self.config = load_config(self.config_path)

            # Set up logging
            log_level = log_level_override or self.config.get("pipeline", {}).get("log_level", "INFO")
            self.logger = PipelineLogger(
                "bis_pipeline_orchestrator",
                self.config.get("advanced", {}).get("temp_dir", "logs")
            ).get_logger()

            self.logger.info(f"Loaded pipeline configuration from {self.config_path}")
            self.logger.info(f"Pipeline version: {self.config.get('version', 'unknown')}")

            # TODO: Add configuration validation against schema
            # For now, we'll assume the config is valid

        except Exception as e:
            print(f"Failed to load pipeline configuration: {e}")
            raise

    def _signal_handler(self, signum, frame) -> None:
        """Handle shutdown signals gracefully."""
        self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.should_stop = True

    def get_is_number_manager(self) -> ISNumberManager:
        """Get the IS Number Manager instance."""
        return self.is_number_manager

    def _initialize_phases(self, requested_phases: Optional[List[str]] = None) -> None:
        """
        Initialize pipeline phases based on configuration.

        Args:
            requested_phases: Optional list of phase names to run (None for all enabled)
        """
        phase_configs = self.config.get("phases", {})

        # Determine which phases to run
        if requested_phases is None:
            # Run all enabled phases
            phases_to_run = [
                name for name, config in phase_configs.items()
                if config.get("enabled", False)
            ]
        else:
            # Run requested phases (validate they exist and are enabled)
            phases_to_run = []
            for phase_name in requested_phases:
                if phase_name not in phase_configs:
                    self.logger.warning(f"Phase '{phase_name}' not found in configuration")
                    continue
                if not phase_configs[phase_name].get("enabled", False):
                    self.logger.warning(f"Phase '{phase_name}' is disabled in configuration")
                    continue
                phases_to_run.append(phase_name)

        # Initialize phase objects
        self.phases = {}
        for phase_name in phases_to_run:
            phase_config = phase_configs[phase_name]
            self.phases[phase_name] = PipelinePhase(phase_name, phase_config)

        self.logger.info(f"Initialized phases: {', '.join(self.phases.keys())}")

    def _run_phase_script(self, phase_name: str, script_path: Union[str, Path],
                         args: Dict[str, Any], timeout_minutes: int) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Run a pipeline phase script as a subprocess.

        Args:
            phase_name: Name of the phase
            script_path: Path to the script to execute
            args: Arguments to pass to the script
            timeout_minutes: Timeout in minutes

        Returns:
            Tuple of (success, output, results_dict)
        """
        # Convert script path to absolute
        script_abs = project_root / script_path
        if not script_abs.exists():
            return False, f"Script not found: {script_abs}", {}

        # Prepare command
        cmd = [sys.executable, str(script_abs)]

        # Add arguments
        for key, value in args.items():
            if isinstance(value, bool):
                if value:
                    cmd.extend([f"--{key}"])
            elif value is not None:
                cmd.extend([f"--{key}", str(value)])

        self.logger.info(f"Executing {phase_name}: {' '.join(cmd)}")

        try:
            # Run the process with timeout
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_minutes * 60,
                cwd=str(project_root)
            )

            # Prepare results
            results = {
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "command": " ".join(cmd)
            }

            # Try to parse JSON output if present
            if result.stdout.strip():
                try:
                    # Look for JSON in the output (some scripts might print JSON at the end)
                    lines = result.stdout.strip().split('\n')
                    for line in reversed(lines):  # Check from end backwards
                        if line.startswith('{') and line.endswith('}'):
                            results["json_output"] = json.loads(line)
                            break
                        elif line.startswith('[') and line.endswith(']'):
                            results["json_output"] = json.loads(line)
                            break
                except (json.JSONDecodeError, IndexError):
                    pass  # Not JSON output, that's fine

            success = result.returncode == 0
            output = result.stdout if success else result.stderr

            if success:
                self.logger.info(f"{phase_name} completed successfully (exit code {result.returncode})")
            else:
                self.logger.error(f"{phase_name} failed (exit code {result.returncode}): {result.stderr[:200]}...")

            return success, output, results

        except subprocess.TimeoutExpired:
            error_msg = f"{phase_name} timed out after {timeout_minutes} minutes"
            self.logger.error(error_msg)
            return False, error_msg, {"timeout": True}
        except Exception as e:
            error_msg = f"Failed to execute {phase_name}: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return False, error_msg, {"exception": str(e)}

    def _run_collection_phase(self, phase: PipelinePhase) -> bool:
        """Run the collection phase."""
        self.logger.info("Starting collection phase...")
        phase.status = PhaseStatus.RUNNING
        phase.start_time = time.time()

        try:
            # Get IS numbers to process
            is_numbers_to_process = []
            if self.is_number_manager.has_work_remaining():
                batch_size = self.config.get("is_number_management", {}).get("batch_size", 10)
                is_numbers_to_process = self.is_number_manager.get_next_batch(batch_size)
                self.logger.info(f"Got {len(is_numbers_to_process)} IS numbers to collect")
            else:
                # If no specific IS numbers, we might want to collect all or none
                # For now, we'll skip if no work
                self.logger.info("No IS numbers pending for collection")
                phase.status = PhaseStatus.SKIPPED
                phase.end_time = time.time()
                return True

            if not is_numbers_to_process:
                self.logger.info("No IS numbers to collect")
                phase.status = PhaseStatus.COMPLETED
                phase.end_time = time.time()
                return True

            # Run each collector
            collectors_config = self.config.get("phases", {}).get("collection", {}).get("collectors", {})
            collection_results = {}

            for collector_name, collector_config in collectors_config.items():
                if not collector_config.get("enabled", False):
                    continue

                self.logger.info(f"Running collector: {collector_name}")

                # Prepare arguments for the collector
                collector_args = collector_config.get("args", {}).copy()

                # Add IS numbers as arguments if the collector supports them
                # This assumes collectors accept --is-numbers or similar
                if is_numbers_to_process:
                    # Try both formats
                    collector_args["is_numbers"] = is_numbers_to_process

                # Run the collector script
                success, output, results = self._run_phase_script(
                    f"collection.{collector_name}",
                    collector_config["script"],
                    collector_args,
                    self.config.get("phases", {}).get("collection", {}).get("timeout_minutes", 30)
                )

                collection_results[collector_name] = {
                    "success": success,
                    "output": output[:500] if output else "",  # Truncate for storage
                    "results": results
                }

                if not success and not self.config.get("phases", {}).get("collection", {}).get("continue_on_error", True):
                    raise PipelineError(f"Collector {collector_name} failed", "collection")

            # TODO: After collection, check for newly discovered IS numbers and add them to the queue
            # This would involve scanning the output directory for new IS_* folders

            phase.results = {
                "collectors_run": list(collection_results.keys()),
                "is_numbers_processed": len(is_numbers_to_process),
                "collection_results": collection_results
            }

            # Mark IS numbers as completed (assuming collection succeeded)
            # In a real implementation, we'd want to track which succeeded/failed
            self.is_number_manager.mark_as_completed(is_numbers_to_process)

            phase.status = PhaseStatus.COMPLETED
            phase.end_time = time.time()
            return True

        except Exception as e:
            phase.error_message = str(e)
            phase.status = PhaseStatus.FAILED
            phase.end_time = time.time()
            self.logger.error(f"Collection phase failed: {e}", exc_info=True)
            return False

    def _run_processing_phase(self, phase: PipelinePhase) -> bool:
        """Run the processing phase."""
        self.logger.info("Starting processing phase...")
        phase.status = PhaseStatus.RUNNING
        phase.start_time = time.time()

        try:
            # TODO: Implement processing phase logic
            # This would typically process the collected documents
            # For now, we'll simulate success

            time.sleep(2)  # Simulate work

            phase.results = {
                "processed_files": 0,  # Placeholder
                "status": "simulated"
            }

            phase.status = PhaseStatus.COMPLETED
            phase.end_time = time.time()
            return True

        except Exception as e:
            phase.error_message = str(e)
            phase.status = PhaseStatus.FAILED
            phase.end_time = time.time()
            self.logger.error(f"Processing phase failed: {e}", exc_info=True)
            return False

    def _run_validation_phase(self, phase: PipelinePhase) -> bool:
        """Run the validation phase."""
        self.logger.info("Starting validation phase...")
        phase.status = PhaseStatus.RUNNING
        phase.start_time = time.time()

        try:
            # TODO: Implement validation phase logic
            # This would run validation scripts on processed data

            time.sleep(2)  # Simulate work

            phase.results = {
                "validation_passed": True,  # Placeholder
                "status": "simulated"
            }

            phase.status = PhaseStatus.COMPLETED
            phase.end_time = time.time()
            return True

        except Exception as e:
            phase.error_message = str(e)
            phase.status = PhaseStatus.FAILED
            phase.end_time = time.time()
            self.logger.error(f"Validation phase failed: {e}", exc_info=True)
            return False

    def _run_indexing_phase(self, phase: PipelinePhase) -> bool:
        """Run the indexing phase (building vector store)."""
        self.logger.info("Starting indexing phase...")
        phase.status = PhaseStatus.RUNNING
        phase.start_time = time.time()

        try:
            # Get IS numbers that were recently completed for indexing
            # In a full implementation, we'd track which IS numbers have new data
            # For now, we'll just run the indexer on all processed data

            indexer_config = self.config.get("phases", {}).get("indexing", {}).get("indexer", {})
            if not indexer_config.get("enabled", False):
                self.logger.info("Indexing phase disabled")
                phase.status = PhaseStatus.SKIPPED
                phase.end_time = time.time()
                return True

            # Run the vector store builder
            success, output, results = self._run_phase_script(
                "indexing",
                indexer_config["script"],
                indexer_config.get("args", {}),
                self.config.get("phases", {}).get("indexing", {}).get("timeout_minutes", 30)
            )

            phase.results = {
                "indexer_success": success,
                "output": output[:500] if output else "",
                "indexer_results": results
            }

            if not success:
                raise PipelineError("Indexing phase failed", "indexing")

            phase.status = PhaseStatus.COMPLETED
            phase.end_time = time.time()
            return True

        except Exception as e:
            phase.error_message = str(e)
            phase.status = PhaseStatus.FAILED
            phase.end_time = time.time()
            self.logger.error(f"Indexing phase failed: {e}", exc_info=True)
            return False

    def _run_reporting_phase(self, phase: PipelinePhase) -> bool:
        """Run the reporting phase."""
        self.logger.info("Starting reporting phase...")
        phase.status = PhaseStatus.RUNNING
        phase.start_time = time.time()

        try:
            # TODO: Implement reporting phase logic
            # This would generate a comprehensive report of the pipeline execution

            time.sleep(1)  # Simulate work

            phase.results = {
                "report_generated": True,  # Placeholder
                "status": "simulated"
            }

            phase.status = PhaseStatus.COMPLETED
            phase.end_time = time.time()
            return True

        except Exception as e:
            phase.error_message = str(e)
            phase.status = PhaseStatus.FAILED
            phase.end_time = time.time()
            self.logger.error(f"Reporting phase failed: {e}", exc_info=True)
            return False

    def _run_phase(self, phase_name: str) -> bool:
        """
        Run a specific pipeline phase.

        Args:
            phase_name: Name of the phase to run

        Returns:
            True if phase succeeded, False otherwise
        """
        if phase_name not in self.phases:
            self.logger.error(f"Unknown phase: {phase_name}")
            return False

        phase = self.phases[phase_name]

        # Check if we should stop
        if self.should_stop:
            self.logger.info("Pipeline execution stopped by user request")
            phase.status = PhaseStatus.SKIPPED
            return False

        # Run the appropriate phase handler
        phase_handlers = {
            "collection": self._run_collection_phase,
            "processing": self._run_processing_phase,
            "validation": self._run_validation_phase,
            "indexing": self._run_indexing_phase,
            "reporting": self._run_reporting_phase
        }

        handler = phase_handlers.get(phase_name)
        if not handler:
            self.logger.error(f"No handler implemented for phase: {phase_name}")
            phase.status = PhaseStatus.FAILED
            phase.error_message = "No handler implemented"
            return False

        return handler(phase)

    def run_pipeline(self, phases: Optional[List[str]] = None,
                    is_numbers: Optional[List[str]] = None,
                    mode: str = "single",
                    dry_run: bool = False) -> bool:
        """
        Run the pipeline.

        Args:
            phases: Optional list of specific phases to run
            is_numbers: Optional list of specific IS numbers to process
            mode: Execution mode ("single", "continuous", "daemon")
            dry_run: If True, show what would be run without executing

        Returns:
            True if pipeline succeeded, False otherwise
        """
        self.logger.info(f"Starting pipeline execution (mode: {mode})")
        self.global_start_time = time.time()

        try:
            # Handle IS numbers if provided
            if is_numbers:
                added = self.is_number_manager.add_is_numbers(is_numbers, "command_line")
                self.logger.info(f"Added {added} IS numbers from command line")

            # Initialize phases
            self._initialize_phases(phases)

            if dry_run:
                self.logger.info("DRY RUN - Would execute the following phases:")
                for name, phase in self.phases.items():
                    enabled = phase.config.get("enabled", False)
                    status = "ENABLED" if enabled else "DISABLED"
                    self.logger.info(f"  {name}: {status}")
                return True

            if mode == "single":
                return self._run_single_mode()
            elif mode == "continuous":
                return self._run_continuous_mode()
            elif mode == "daemon":
                return self._run_daemon_mode()
            else:
                self.logger.error(f"Unknown mode: {mode}")
                return False

        except Exception as e:
            self.logger.error(f"Pipeline execution failed: {e}", exc_info=True)
            return False
        finally:
            self.global_end_time = time.time()
            if not self.should_stop:
                self.logger.info(f"Pipeline execution finished in {format_duration(self.global_end_time - self.global_start_time)}")

    def _run_single_mode(self) -> bool:
        """Run pipeline once through all phases."""
        self.logger.info("Running pipeline in single mode")

        # Define phase dependencies (order of execution)
        phase_order = ["collection", "processing", "validation", "indexing", "reporting"]

        # Filter to only include phases we're actually running
        phase_order = [p for p in phase_order if p in self.phases]

        # Execute phases in order
        for phase_name in phase_order:
            if self.should_stop:
                self.logger.info("Pipeline execution stopped")
                break

            self.logger.info(f"--- Starting phase: {phase_name} ---")
            success = self._run_phase(phase_name)

            if not success:
                # Check if we should continue on error
                phase_config = self.phases[phase_name].config
                continue_on_error = phase_config.get("continue_on_error", True)

                if not continue_on_error:
                    self.logger.error(f"Phase {phase_name} failed and continue_on_error is False")
                    break
                else:
                    self.logger.warning(f"Phase {phase_name} failed but continuing due to continue_on_error=True")

            self.logger.info(f"--- Finished phase: {phase_name} ---")

        # Determine overall success
        failed_phases = [
            name for name, phase in self.phases.items()
            if phase.status == PhaseStatus.FAILED
        ]

        if failed_phases:
            self.logger.warning(f"Pipeline completed with failed phases: {', '.join(failed_phases)}")
            # Check if any critical phases failed
            critical_phases = ["collection", "processing", "validation", "indexing"]
            critical_failed = [p for p in failed_phases if p in critical_phases]
            if critical_failed:
                self.logger.error(f"Critical phases failed: {', '.join(critical_failed)}")
                return False

        self.logger.info("Pipeline execution completed successfully")
        return True

    def _run_continuous_mode(self) -> bool:
        """Run pipeline in continuous loop mode."""
        self.logger.info("Running pipeline in continuous mode")

        # Get continuous mode settings
        is_number_config = self.config.get("is_number_management", {})
        discovery_config = is_number_config.get("discovery", {})
        polling_interval = discovery_config.get("polling_interval_seconds", 300)
        max_new_per_poll = discovery_config.get("max_new_per_poll", 50)

        cycle_count = 0
        while not self.should_stop:
            cycle_count += 1
            self.logger.info(f"=== Pipeline Cycle {cycle_count} ===")

            # Run single pipeline iteration
            success = self._run_single_mode()

            if not success and not self.config.get("pipeline", {}).get("continue_on_error", True):
                self.logger.error("Pipeline cycle failed and continue_on_error is False")
                break

            # Check for new IS numbers from discovery sources
            if discovery_config.get("enabled", False):
                self._discover_new_is_numbers(max_new_per_poll)

            # Wait for next cycle (unless we're stopping)
            if not self.should_stop:
                self.logger.info(f"Waiting {polling_interval} seconds until next cycle...")
                # Sleep in small increments to check for stop signal
                for _ in range(polling_interval):
                    if self.should_stop:
                        break
                    time.sleep(1)

        self.logger.info(f"Continuous mode stopped after {cycle_count} cycles")
        return True  # Continuous mode is considered successful if it runs

    def _run_daemon_mode(self) -> bool:
        """Run pipeline as a daemon (similar to continuous but with different behavior)."""
        self.logger.info("Running pipeline in daemon mode")
        # For now, daemon mode is similar to continuous
        return self._run_continuous_mode()

    def _discover_new_is_numbers(self, max_new: int) -> None:
        """
        Discover new IS numbers from configured sources and add them to the queue.

        Args:
            max_new: Maximum number of new IS numbers to add in this discovery cycle
        """
        self.logger.info("Checking for new IS numbers from discovery sources...")

        discovery_config = self.config.get("is_number_management", {}).get("discovery", {})
        sources = discovery_config.get("sources", [])

        total_added = 0

        for source_config in sources:
            if not source_config.get("enabled", True):
                continue

            source_type = source_config.get("type")
            path = source_config.get("path", "")
            pattern = source_config.get("pattern", "*")
            extract_is_numbers = source_config.get("extract_is_numbers", True)

            try:
                if source_type == "directory_scan":
                    added = self._discover_from_directory(path, pattern, extract_is_numbers, max_new - total_added)
                    total_added += added

                # TODO: Add other source types (file_watch, api_poll)

                if total_added >= max_new:
                    break

            except Exception as e:
                self.logger.warning(f"Error discovering IS numbers from {source_type} source: {e}")

        if total_added > 0:
            self.logger.info(f"Discovered and added {total_added} new IS numbers")

    def _discover_from_directory(self, directory_path: str, pattern: str,
                                extract_is_numbers: bool, max_add: int) -> int:
        """
        Discover IS numbers from directory structure.

        Args:
            directory_path: Path to scan (relative to project root)
            pattern: Glob pattern to match directories
            extract_is_numbers: Whether to extract IS numbers from directory names
            max_add: Maximum number to add

        Returns:
            Number of new IS numbers added
        """
        if not directory_path:
            return 0

        search_path = project_root / directory_path
        if not search_path.exists():
            self.logger.warning(f"Discovery path does not exist: {search_path}")
            return 0

        added_count = 0

        # Find matching directories
        for item in search_path.glob(pattern):
            if item.is_dir():
                if extract_is_numbers:
                    # Try to extract IS number from directory name (e.g., IS_2082 -> IS 2082)
                    dir_name = item.name
                    if dir_name.startswith("IS_") and len(dir_name) > 3:
                        try:
                            num_part = dir_name[3:]  # Remove "IS_" prefix
                            if num_part.isdigit():
                                is_number = f"IS {int(num_part)}"
                                added = self.is_number_manager.add_is_numbers([is_number], "directory_discovery")
                                if added > 0:
                                    added_count += 1
                                    if added_count >= max_add:
                                        break
                        except ValueError:
                            pass  # Not a valid number
                else:
                    # Treat directory name as IS number literal
                    is_number = item.name
                    added = self.is_number_manager.add_is_numbers([is_number], "directory_discovery")
                    if added > 0:
                        added_count += 1
                        if added_count >= max_add:
                            break

        return added_count

    def get_pipeline_status(self) -> Dict[str, Any]:
        """
        Get current pipeline status.

        Returns:
            Dictionary containing pipeline status information
        """
        is_number_status = self.is_number_manager.get_status() if self.is_number_manager else {}

        phase_statuses = {}
        for name, phase in self.phases.items():
            phase_statuses[name] = {
                "status": phase.status.value,
                "duration": phase.duration,
                "error_message": phase.error_message,
                "is_successful": phase.is_successful
            }

        return {
            "is_running": self.global_start_time is not None and self.global_end_time is None and not self.should_stop,
            "should_stop": self.should_stop,
            "global_start_time": self.global_start_time,
            "global_end_time": self.global_end_time,
            "global_duration": self.global_end_time - self.global_start_time if self.global_start_time and self.global_end_time else None,
            "is_number_status": is_number_status,
            "phases": phase_statuses
        }

    def get_is_number_manager(self) -> ISNumberManager:
        """Get the IS Number Manager instance."""
        return self.is_number_manager