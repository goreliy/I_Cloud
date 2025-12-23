"""Schemas for archive configuration and actions."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.archive_config import ArchiveBackendType


class ArchiveConfigCore(BaseModel):
    enabled: bool = False
    backend_type: ArchiveBackendType = ArchiveBackendType.SQLITE

    # SQLite
    sqlite_file_path: Optional[str] = None

    # PostgreSQL
    pg_host: Optional[str] = None
    pg_port: Optional[int] = Field(default=5432, ge=1, le=65535)
    pg_db: Optional[str] = None
    pg_user: Optional[str] = None
    pg_schema: Optional[str] = None
    pg_ssl: bool = False

    # Common
    retention_days: int = Field(default=30, ge=1, le=3650)
    schedule_interval_seconds: int = Field(default=3600, ge=300)
    schedule_cron: Optional[str] = None
    copy_then_delete: bool = True

    @model_validator(mode='after')
    def validate_backend_config(self):
        if self.backend_type == ArchiveBackendType.SQLITE:
            if not self.sqlite_file_path or not self.sqlite_file_path.strip():
                raise ValueError('Необходимо указать путь к файлу SQLite')
        elif self.backend_type == ArchiveBackendType.POSTGRES:
            if not self.pg_host:
                raise ValueError('Поле pg_host обязательно для PostgreSQL')
            if not self.pg_db:
                raise ValueError('Поле pg_db обязательно для PostgreSQL')
            if not self.pg_user:
                raise ValueError('Поле pg_user обязательно для PostgreSQL')
        return self


class ArchiveConfigResponse(ArchiveConfigCore):
    id: int
    last_run_at: Optional[datetime] = None
    last_status: Optional[str] = None
    last_error: Optional[str] = None
    last_processed: Optional[int] = None
    pg_password: Optional[str] = None  # Всегда None при чтении из БД

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class ArchiveConfigUpdate(ArchiveConfigCore):
    pg_password: Optional[str] = None


class ArchiveTestRequest(BaseModel):
    config: ArchiveConfigUpdate


class ArchiveRunResponse(BaseModel):
    processed: int
    deleted: int
    duration_seconds: float
    status: str
    error: Optional[str] = None


class ArchiveStatusResponse(BaseModel):
    enabled: bool
    backend_type: ArchiveBackendType
    last_run_at: Optional[datetime]
    last_status: Optional[str]
    last_error: Optional[str]
    last_processed: Optional[int]
    scheduler_running: bool


class ArchiveMigrationRequest(BaseModel):
    source_config: ArchiveConfigUpdate
    target_config: ArchiveConfigUpdate


class ArchiveMigrationResponse(BaseModel):
    total_read: int
    total_written: int
    errors: list[str]
    duration_seconds: float
    success: bool

