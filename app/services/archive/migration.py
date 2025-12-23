"""Archive data migration service."""
from __future__ import annotations

import time
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.models.archive_config import ArchiveBackendType, ArchiveSettings
from app.services.archive.backends import ArchiveBackend
from app.services.archive.service import get_backend


class MigrationStats:
    """Statistics for migration process."""

    def __init__(self):
        self.total_read = 0
        self.total_written = 0
        self.errors = []
        self.start_time = time.monotonic()
        self.end_time: Optional[float] = None

    @property
    def duration_seconds(self) -> float:
        """Get migration duration in seconds."""
        end = self.end_time or time.monotonic()
        return end - self.start_time

    def to_dict(self) -> dict:
        """Convert stats to dictionary."""
        return {
            "total_read": self.total_read,
            "total_written": self.total_written,
            "errors": self.errors,
            "duration_seconds": self.duration_seconds,
            "success": len(self.errors) == 0,
        }


def migrate_archive_data(
    source_config: ArchiveSettings,
    target_config: ArchiveSettings,
    db: Session,
    batch_size: int = 1000,
    progress_callback: Optional[callable] = None,
) -> MigrationStats:
    """Migrate archive data from source backend to target backend.

    Args:
        source_config: Source archive configuration
        target_config: Target archive configuration
        db: Database session (for logging, not used for archive backends)
        batch_size: Number of records to process per batch
        progress_callback: Optional callback function(processed_count, total_count) for progress updates

    Returns:
        MigrationStats object with migration statistics
    """
    stats = MigrationStats()

    try:
        # Create backends
        source_backend = get_backend(source_config)
        target_backend = get_backend(target_config)

        # Initialize target schema
        target_backend.init_schema()

        # Get total count from source (for progress tracking)
        try:
            total_count = source_backend.count_records()
        except Exception:
            # If count fails, we'll still migrate but without progress
            total_count = None

        # Read and write data in batches
        processed = 0
        for batch in source_backend.read_all(batch_size=batch_size):
            try:
                written = target_backend.archive_batch(batch)
                stats.total_read += len(batch)
                stats.total_written += written
                processed += len(batch)

                # Call progress callback if provided
                if progress_callback and total_count:
                    progress_callback(processed, total_count)

            except Exception as e:
                error_msg = f"Error processing batch starting at record {processed}: {str(e)}"
                stats.errors.append(error_msg)
                # Continue with next batch

        stats.end_time = time.monotonic()

    except Exception as e:
        stats.end_time = time.monotonic()
        stats.errors.append(f"Migration failed: {str(e)}")

    return stats


def create_backend_from_config(config: ArchiveSettings) -> ArchiveBackend:
    """Create archive backend from configuration.

    This is a helper function that can be used to create backends
    from temporary configurations (e.g., for manual migration UI).
    """
    return get_backend(config)

