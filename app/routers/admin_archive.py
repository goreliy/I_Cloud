"""Admin API for archive configuration."""
from __future__ import annotations

import asyncio
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_admin
from app.models.user import User
from app.schemas.archive import (
    ArchiveConfigResponse,
    ArchiveConfigUpdate,
    ArchiveMigrationRequest,
    ArchiveMigrationResponse,
    ArchiveRunResponse,
    ArchiveStatusResponse,
    ArchiveTestRequest,
)
from app.services.archive import migration as archive_migration
from app.services.archive import service as archive_service
from app.services.archive.scheduler import archive_scheduler


router = APIRouter(prefix="/api/admin/archive", tags=["admin-archive"], dependencies=[Depends(get_current_admin)])


def _build_response(config) -> ArchiveConfigResponse:
    return ArchiveConfigResponse.model_validate(config)


@router.get("/config", response_model=ArchiveConfigResponse)
def get_config(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    config = archive_service.load_config(db)
    return _build_response(config)


@router.put("/config", response_model=ArchiveConfigResponse)
async def update_config(
    payload: ArchiveConfigUpdate,
    migrate_existing_data: bool = False,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Update archive configuration.
    
    If migrate_existing_data is True and backend_type changes,
    existing data will be migrated to the new backend.
    """
    from app.models.archive_config import ArchiveSettings
    
    config = archive_service.load_config(db)
    old_backend_type = config.backend_type
    
    archive_service.apply_update(config, payload)
    
    # If backend type changed and migration requested, perform migration
    if migrate_existing_data and old_backend_type != payload.backend_type:
        # Create source config from old settings
        source_config = ArchiveSettings()
        source_config.backend_type = old_backend_type
        source_config.sqlite_file_path = config.sqlite_file_path
        source_config.pg_host = config.pg_host
        source_config.pg_port = config.pg_port
        source_config.pg_db = config.pg_db
        source_config.pg_user = config.pg_user
        source_config.pg_password_enc = config.pg_password_enc
        source_config.pg_schema = config.pg_schema
        source_config.pg_ssl = config.pg_ssl
        
        # Target config is the new one
        target_config = ArchiveSettings()
        archive_service.apply_update(target_config, payload)
        
        # Perform migration
        try:
            archive_migration.migrate_archive_data(
                source_config=source_config,
                target_config=target_config,
                db=db,
                batch_size=1000,
            )
        except Exception as e:
            # Log error but don't fail the config update
            # The migration can be retried manually
            pass
    
    db.commit()
    # Restart scheduler with new settings
    await archive_scheduler.stop()
    if payload.enabled:
        await archive_scheduler.start()
    return _build_response(config)


@router.post("/test")
def test_connection(
    request: ArchiveTestRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    from app.models.archive_config import ArchiveSettings

    config = ArchiveSettings()
    archive_service.apply_update(config, request.config)
    try:
        archive_service.test_backend_connection(config)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return {"status": "ok"}


@router.post("/run", response_model=ArchiveRunResponse)
def run_archive_now(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    config = archive_service.load_config(db)
    processed, deleted, duration, error = archive_service.archive_once_with_handling(db, config)
    if error:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error)
    return ArchiveRunResponse(
        processed=processed,
        deleted=deleted,
        duration_seconds=duration,
        status="success",
    )


@router.get("/status", response_model=ArchiveStatusResponse)
def get_status(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    config = archive_service.load_config(db)
    return ArchiveStatusResponse(
        enabled=config.enabled,
        backend_type=config.backend_type,
        last_run_at=config.last_run_at,
        last_status=config.last_status,
        last_error=config.last_error,
        last_processed=config.last_processed,
        scheduler_running=archive_scheduler.is_running,
    )


@router.post("/migrate", response_model=ArchiveMigrationResponse)
def migrate_archive(
    request: ArchiveMigrationRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Migrate archive data from source backend to target backend."""
    from app.models.archive_config import ArchiveSettings

    # Create temporary config objects from request
    source_config = ArchiveSettings()
    archive_service.apply_update(source_config, request.source_config)
    
    target_config = ArchiveSettings()
    archive_service.apply_update(target_config, request.target_config)

    # Test both connections before migration
    try:
        archive_service.test_backend_connection(source_config)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Source backend connection failed: {str(e)}"
        )

    try:
        archive_service.test_backend_connection(target_config)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Target backend connection failed: {str(e)}"
        )

    # Perform migration
    try:
        stats = archive_migration.migrate_archive_data(
            source_config=source_config,
            target_config=target_config,
            db=db,
            batch_size=1000,
        )
        return ArchiveMigrationResponse(**stats.to_dict())
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Migration failed: {str(e)}"
        )

