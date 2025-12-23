"""Service helpers for archive configuration and execution."""
from __future__ import annotations

import base64
import hashlib
import os
import time
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models.archive_config import ArchiveBackendType, ArchiveSettings
from app.models.feed import Feed
from app.schemas.archive import ArchiveConfigCore
from .backends import ArchiveBackend, SQLiteArchiveBackend, PostgresArchiveBackend, ARCHIVE_COLUMNS


ARCHIVE_DEFAULT_SQLITE = os.path.join("archive", "archive.db")
ARCHIVE_BATCH_SIZE = 500


def _encryption_salt() -> bytes:
    key = settings.JWT_SECRET_KEY or "default-secret"
    return hashlib.sha256(key.encode("utf-8")).digest()


def encrypt_password(password: Optional[str]) -> Optional[str]:
    if not password:
        return None
    data = _encryption_salt() + password.encode("utf-8")
    return base64.urlsafe_b64encode(data).decode("utf-8")


def decrypt_password(enc: Optional[str]) -> Optional[str]:
    if not enc:
        return None
    try:
        raw = base64.urlsafe_b64decode(enc)
        salt = _encryption_salt()
        if not raw.startswith(salt):
            return None
        return raw[len(salt):].decode("utf-8")
    except Exception:
        return None


def ensure_default_config(db: Session) -> ArchiveSettings:
    config = db.query(ArchiveSettings).first()
    if config:
        return config
    
    # Try to create default config, handle race condition if multiple workers start simultaneously
    archive_dir = os.path.dirname(ARCHIVE_DEFAULT_SQLITE)
    if archive_dir:
        os.makedirs(archive_dir, exist_ok=True)
    
    config = ArchiveSettings(
        enabled=False,
        backend_type=ArchiveBackendType.SQLITE,
        sqlite_file_path=ARCHIVE_DEFAULT_SQLITE,
        retention_days=30,
        schedule_interval_seconds=3600,
        copy_then_delete=True,
    )
    db.add(config)
    try:
        db.commit()
        db.refresh(config)
        return config
    except Exception:
        # If another worker created it, rollback and fetch existing
        db.rollback()
        config = db.query(ArchiveSettings).first()
        if config:
            return config
        raise


def load_config(db: Session) -> ArchiveSettings:
    return ensure_default_config(db)


def apply_update(config: ArchiveSettings, payload: ArchiveConfigCore) -> None:
    config.enabled = payload.enabled
    config.backend_type = payload.backend_type
    config.sqlite_file_path = payload.sqlite_file_path
    config.pg_host = payload.pg_host
    config.pg_port = payload.pg_port
    config.pg_db = payload.pg_db
    config.pg_user = payload.pg_user
    if payload.pg_password is not None:
        config.pg_password_enc = encrypt_password(payload.pg_password)
    config.pg_schema = payload.pg_schema
    config.pg_ssl = payload.pg_ssl
    config.retention_days = payload.retention_days
    config.schedule_interval_seconds = payload.schedule_interval_seconds
    config.schedule_cron = payload.schedule_cron
    config.copy_then_delete = payload.copy_then_delete


def get_backend(config: ArchiveSettings) -> ArchiveBackend:
    if config.backend_type == ArchiveBackendType.SQLITE:
        path = config.sqlite_file_path or ARCHIVE_DEFAULT_SQLITE
        os.makedirs(os.path.dirname(path), exist_ok=True)
        return SQLiteArchiveBackend(path)

    password = decrypt_password(config.pg_password_enc) or ""
    return PostgresArchiveBackend(
        host=config.pg_host or "localhost",
        port=config.pg_port or 5432,
        database=config.pg_db or "postgres",
        user=config.pg_user or "postgres",
        password=password,
        schema=config.pg_schema,
        ssl=bool(config.pg_ssl),
    )


def test_backend_connection(config: ArchiveSettings) -> None:
    backend = get_backend(config)
    backend.test_connection()
    backend.init_schema()


@contextmanager
def db_session_scope():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def archive_once(db: Session, config: ArchiveSettings, now: Optional[datetime] = None) -> Tuple[int, int, float]:
    """Archive data based on retention settings.

    Returns tuple(processed_rows, deleted_rows, duration_seconds)
    """
    backend = get_backend(config)
    backend.init_schema()
    cutoff = (now or datetime.utcnow()) - timedelta(days=config.retention_days)
    total_processed = 0
    total_deleted = 0
    start = time.monotonic()

    while True:
        feeds = (
            db.query(Feed)
            .filter(Feed.created_at < cutoff)
            .order_by(Feed.created_at)
            .limit(ARCHIVE_BATCH_SIZE)
            .all()
        )
        if not feeds:
            break

        rows = []
        for feed in feeds:
            row = {col: getattr(feed, col) for col in ARCHIVE_COLUMNS}
            rows.append(row)

        inserted = backend.archive_batch(rows)
        total_processed += inserted

        if inserted and config.copy_then_delete:
            feed_ids = [feed.id for feed in feeds]
            deleted = (
                db.query(Feed)
                .filter(Feed.id.in_(feed_ids))
                .delete(synchronize_session=False)
            )
            total_deleted += deleted
        db.commit()

        # If copy_without_delete and inserted rows less than batch (due to duplicates) -> avoid busy loop
        if inserted < ARCHIVE_BATCH_SIZE:
            break

    duration = time.monotonic() - start
    config.last_run_at = datetime.utcnow()
    config.last_processed = total_processed
    config.last_status = "success"
    config.last_error = None
    return total_processed, total_deleted, duration


def archive_once_with_handling(db: Session, config: ArchiveSettings) -> Tuple[int, int, float, Optional[str]]:
    try:
        processed, deleted, duration = archive_once(db, config)
        db.commit()
        return processed, deleted, duration, None
    except Exception as exc:  # pragma: no cover - log and propagate message
        db.rollback()
        config.last_run_at = datetime.utcnow()
        config.last_status = "error"
        config.last_error = str(exc)
        db.commit()
        return 0, 0, 0.0, str(exc)

