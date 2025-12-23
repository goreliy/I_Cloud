"""Archive configuration model."""
from __future__ import annotations

import enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Integer,
    String,
    Text,
)
from sqlalchemy.sql import func

from app.database import Base


class ArchiveBackendType(str, enum.Enum):
    SQLITE = "sqlite"
    POSTGRES = "postgres"


class ArchiveSettings(Base):
    __tablename__ = "archive_settings"

    id = Column(Integer, primary_key=True, index=True)
    enabled = Column(Boolean, default=False, nullable=False)
    backend_type = Column(Enum(ArchiveBackendType), nullable=False, default=ArchiveBackendType.SQLITE)

    # SQLite configuration
    sqlite_file_path = Column(String(500), nullable=True)

    # PostgreSQL configuration
    pg_host = Column(String(255), nullable=True)
    pg_port = Column(Integer, nullable=True)
    pg_db = Column(String(255), nullable=True)
    pg_user = Column(String(255), nullable=True)
    pg_password_enc = Column(Text, nullable=True)
    pg_schema = Column(String(255), nullable=True)
    pg_ssl = Column(Boolean, default=False, nullable=True)

    # Common settings
    retention_days = Column(Integer, default=30, nullable=False)
    schedule_interval_seconds = Column(Integer, default=3600, nullable=False)
    schedule_cron = Column(String(100), nullable=True)
    copy_then_delete = Column(Boolean, default=True, nullable=False)

    last_run_at = Column(DateTime(timezone=True), nullable=True)
    last_status = Column(String(50), nullable=True)
    last_error = Column(Text, nullable=True)
    last_processed = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

