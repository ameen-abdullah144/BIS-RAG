"""
IS Number Manager
Centralized repository for tracking and managing IS (Indian Standards) numbers
to be processed by the BIS Knowledge Ingestion Pipeline.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union
from .pipeline_utils import PipelineLogger, safe_filename


class ISNumberManager:
    """
    Manages the queue of IS numbers to be processed, tracking their status
    and supporting dynamic addition of new IS numbers during pipeline execution.
    """

    def __init__(self, storage_dir: str = "is_number_state"):
        """
        Initialize the IS Number Manager.

        Args:
            storage_dir: Directory to store state files
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)

        # State files
        self.pending_file = self.storage_dir / "pending_is_numbers.json"
        self.processing_file = self.storage_dir / "processing_is_numbers.json"
        self.completed_file = self.storage_dir / "completed_is_numbers.json"
        self.failed_file = self.storage_dir / "failed_is_numbers.json"

        # Initialize logger
        self.logger = PipelineLogger("is_number_manager").get_logger()

        # Load existing state
        self._load_state()

    def _load_state(self) -> None:
        """Load IS number state from JSON files."""
        self.pending: Set[str] = self._load_set_from_file(self.pending_file)
        self.processing: Set[str] = self._load_set_from_file(self.processing_file)
        self.completed: Set[str] = self._load_set_from_file(self.completed_file)
        self.failed: Set[str] = self._load_set_from_file(self.failed_file)

        self.logger.debug(f"Loaded IS number state: "
                         f"{len(self.pending)} pending, {len(self.processing)} processing, "
                         f"{len(self.completed)} completed, {len(self.failed)} failed")

    def _save_state(self) -> None:
        """Save current state to JSON files."""
        self._save_set_to_file(self.pending, self.pending_file)
        self._save_set_to_file(self.processing, self.processing_file)
        self._save_set_to_file(self.completed, self.completed_file)
        self._save_set_to_file(self.failed, self.failed_file)

    def _load_set_from_file(self, file_path: Path) -> Set[str]:
        """Load a set of strings from a JSON file."""
        if not file_path.exists():
            return set()

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return set(data) if isinstance(data, list) else set()
        except (json.JSONDecodeError, IOError) as e:
            self.logger.warning(f"Could not load state from {file_path}: {e}")
            return set()

    def _save_set_to_file(self, data_set: Set[str], file_path: Path) -> None:
        """Save a set of strings to a JSON file."""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(sorted(list(data_set)), f, indent=2)
        except IOError as e:
            self.logger.error(f"Could not save state to {file_path}: {e}")

    def add_is_numbers(self, is_numbers: List[str], source: str = "unknown") -> int:
        """
        Add IS numbers to the pending queue.

        Args:
            is_numbers: List of IS number strings to add
            source: Source of these IS numbers (for logging)

        Returns:
            Number of new IS numbers added
        """
        # Normalize IS numbers
        normalized = set()
        for is_num in is_numbers:
            # Ensure consistent format: "IS ####"
            is_num = is_num.strip().upper()
            if not is_num.startswith("IS"):
                is_num = f"IS {is_num}"
            # Extract number part and reformat to ensure consistency
            try:
                num_part = ''.join(filter(str.isdigit, is_num))
                if num_part:
                    normalized.add(f"IS {int(num_part)}")
            except ValueError:
                # If we can't extract a number, keep as-is but log warning
                self.logger.warning(f"Could not normalize IS number: {is_num}")
                normalized.add(is_num)

        # Remove any that are already completed or failed
        new_numbers = normalized - self.completed - self.failed

        # Add to pending
        before_count = len(self.pending)
        self.pending.update(new_numbers)
        added_count = len(self.pending) - before_count

        if added_count > 0:
            self.logger.info(f"Added {added_count} new IS numbers from {source}. "
                           f"Total pending: {len(self.pending)}")
            self._save_state()

        return added_count

    def add_is_number_range(self, range_str: str, source: str = "range") -> int:
        """
        Add IS numbers from a range string.

        Args:
            range_str: IS number range string (e.g., "IS 100-IS 105")
            source: Source of these IS numbers

        Returns:
            Number of new IS numbers added
        """
        from .pipeline_utils import parse_is_number_range
        is_numbers = parse_is_number_range(range_str)
        return self.add_is_numbers(is_numbers, source)

    def get_next_batch(self, batch_size: int = 10) -> List[str]:
        """
        Get the next batch of IS numbers to process.

        Args:
            batch_size: Maximum number of IS numbers to return

        Returns:
            List of IS numbers to process
        """
        if batch_size <= 0:
            return []

        # Move IS numbers from pending to processing
        to_process = []
        while len(to_process) < batch_size and self.pending:
            is_num = self.pending.pop()
            # Skip if already completed or failed (double-check)
            if is_num not in self.completed and is_num not in self.failed:
                to_process.append(is_num)
                self.processing.add(is_num)

        if to_process:
            self.logger.debug(f"Moving {len(to_process)} IS numbers to processing")
            self._save_state()

        return to_process

    def mark_as_completed(self, is_numbers: List[str]) -> None:
        """
        Mark IS numbers as successfully processed.

        Args:
            is_numbers: List of IS number strings to mark as completed
        """
        for is_num in is_numbers:
            self.processing.discard(is_num)
            self.completed.add(is_num)

        if is_numbers:
            self.logger.debug(f"Marked {len(is_numbers)} IS numbers as completed")
            self._save_state()

    def mark_as_failed(self, is_numbers: List[str], error_msg: str = "") -> None:
        """
        Mark IS numbers as failed.

        Args:
            is_numbers: List of IS number strings to mark as failed
            error_msg: Optional error message for failure tracking
        """
        for is_num in is_numbers:
            self.processing.discard(is_num)
            self.failed.add(is_num)

        if is_numbers:
            self.logger.warning(f"Marked {len(is_numbers)} IS numbers as failed: {error_msg}")
            self._save_state()

    def get_status(self) -> Dict[str, int]:
        """
        Get current status counts.

        Returns:
            Dictionary with counts for each status
        """
        return {
            "pending": len(self.pending),
            "processing": len(self.processing),
            "completed": len(self.completed),
            "failed": len(self.failed),
            "total": len(self.pending) + len(self.processing) + len(self.completed) + len(self.failed)
        }

    def get_is_numbers_by_status(self, status: str) -> List[str]:
        """
        Get IS numbers by their status.

        Args:
            status: One of "pending", "processing", "completed", "failed"

        Returns:
            List of IS numbers with the specified status
        """
        status_map = {
            "pending": self.pending,
            "processing": self.processing,
            "completed": self.completed,
            "failed": self.failed
        }

        if status not in status_map:
            raise ValueError(f"Invalid status: {status}. Must be one of {list(status_map.keys())}")

        return sorted(list(status_map[status]))

    def reset_status(self, status: str) -> int:
        """
        Reset IS numbers from a given status back to pending.

        Args:
            status: Status to reset from ("processing", "failed", or "completed")

        Returns:
            Number of IS numbers reset
        """
        if status not in ["processing", "failed", "completed"]:
            raise ValueError("Can only reset from processing, failed, or completed status")

        source_set = getattr(self, status)
        reset_count = len(source_set)

        if status == "processing":
            # For processing, move back to pending
            self.pending.update(source_set)
            source_set.clear()
        else:
            # For failed/completed, move to pending (allowing retry)
            self.pending.update(source_set)
            source_set.clear()

        if reset_count > 0:
            self.logger.info(f"Reset {reset_count} IS numbers from {status} to pending")
            self._save_state()

        return reset_count

    def clear_all(self) -> None:
        """Clear all IS number state."""
        self.pending.clear()
        self.processing.clear()
        self.completed.clear()
        self.failed.clear()
        self._save_state()
        self.logger.info("Cleared all IS number state")

    def export_state(self, export_path: Union[str, Path]) -> None:
        """
        Export current state to a JSON file.

        Args:
            export_path: Path where to export the state
        """
        export_path = Path(export_path)
        export_path.parent.mkdir(parents=True, exist_ok=True)

        state = {
            "pending": sorted(list(self.pending)),
            "processing": sorted(list(self.processing)),
            "completed": sorted(list(self.completed)),
            "failed": sorted(list(self.failed)),
            "exported_at": datetime.now().isoformat(),
            "total_counts": self.get_status()
        }

        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2)

        self.logger.info(f"Exported IS number state to {export_path}")

    def import_state(self, import_path: Union[str, Path], merge: bool = True) -> None:
        """
        Import IS number state from a JSON file.

        Args:
            import_path: Path to the state file to import
            merge: If True, merge with existing state; if False, replace existing state
        """
        import_path = Path(import_path)
        if not import_path.exists():
            raise FileNotFoundError(f"State file not found: {import_path}")

        with open(import_path, 'r', encoding='utf-8') as f:
            state = json.load(f)

        if merge:
            # Merge with existing state
            self.pending.update(set(state.get("pending", [])))
            self.processing.update(set(state.get("processing", [])))
            self.completed.update(set(state.get("completed", [])))
            self.failed.update(set(state.get("failed", [])))
        else:
            # Replace existing state
            self.pending = set(state.get("pending", []))
            self.processing = set(state.get("processing", []))
            self.completed = set(state.get("completed", []))
            self.failed = set(state.get("failed", []))

        self._save_state()
        self.logger.info(f"Imported IS number state from {import_path} (merge={merge})")

    def has_work_remaining(self) -> bool:
        """
        Check if there is any work remaining to be done.

        Returns:
            True if there are pending or processing IS numbers
        """
        return len(self.pending) > 0 or len(self.processing) > 0

    def get_next_is_number(self) -> Optional[str]:
        """
        Get the next single IS number to process (batch size of 1).

        Returns:
            Next IS number to process, or None if none available
        """
        batch = self.get_next_batch(1)
        return batch[0] if batch else None


# Global instance for easy access
_is_number_manager: Optional[ISNumberManager] = None


def get_is_number_manager(storage_dir: str = "is_number_state") -> ISNumberManager:
    """
    Get or create the global IS Number Manager instance.

    Args:
        storage_dir: Directory to store state files (only used on first call)

    Returns:
        The global ISNumberManager instance
    """
    global _is_number_manager
    if _is_number_manager is None:
        _is_number_manager = ISNumberManager(storage_dir)
    return _is_number_manager


def reset_is_number_manager() -> None:
    """Reset the global IS Number Manager instance (mainly for testing)."""
    global _is_number_manager
    _is_number_manager = None