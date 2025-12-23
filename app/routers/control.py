"""Control API for secure widget management"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, validator
from typing import Optional
import logging

from app.database import get_db
from app.dependencies import get_current_user, get_current_user_optional
from app.models.user import User
from app.services import channel_service

router = APIRouter(prefix="/api/channels", tags=["control"])
logger = logging.getLogger(__name__)


class FieldUpdate(BaseModel):
    """Schema for updating channel field"""
    field_name: str  # field1-field8
    value: float
    
    @validator('field_name')
    def validate_field_name(cls, v):
        valid_fields = [f'field{i}' for i in range(1, 9)]
        if v not in valid_fields:
            raise ValueError(f'field_name must be one of {valid_fields}')
        return v
    
    @validator('value')
    def validate_value(cls, v):
        if not (-1e10 <= v <= 1e10):  # Reasonable bounds
            raise ValueError('value out of range')
        return v


@router.post("/{channel_id}/control", status_code=status.HTTP_200_OK)
async def update_channel_field(
    request: Request,
    channel_id: int,
    field_update: FieldUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # Requires authentication!
):
    """
    Secure channel field update through widget control.
    
    Requires:
    - JWT authentication
    - Channel owner permissions
    
    Uses Write API key internally on backend.
    """
    # 1. Get channel
    channel = channel_service.get_channel(db, channel_id)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel not found"
        )
    
    # 2. Check permissions (owner only)
    if not channel_service.check_channel_access(channel, current_user, require_owner=True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only channel owner can control it"
        )
    
    # 3. Get Write API key for channel
    api_keys = channel_service.get_channel_api_keys(db, channel_id)
    write_key = next((k for k in api_keys if k.type == "write" and k.is_active), None)
    
    if not write_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Channel has no active write API key"
        )
    
    # 4. Prepare feed data with output fields preservation
    from app.schemas.feed import FeedCreate
    from app.services import feed_service
    from app.services.automation_service import get_output_fields
    
    # Get output fields and last feed to preserve automation state
    output_fields = get_output_fields(channel_id, db)
    last_feed = feed_service.get_last_feed(db, channel_id) if output_fields else None
    
    # Create field values dict
    feed_data_dict = {}
    for i in range(1, 9):
        field_name = f'field{i}'
        if field_name == field_update.field_name:
            # This is the field we're updating
            feed_data_dict[field_name] = field_update.value
        elif field_name in output_fields and last_feed:
            # This is an output field - preserve its value
            feed_data_dict[field_name] = getattr(last_feed, field_name, None)
        else:
            # All other fields - None
            feed_data_dict[field_name] = None
    
    feed_data = FeedCreate(**feed_data_dict)
    
    try:
        # Create feed without committing (for automation)
        feed = feed_service.create_feed(db, channel, feed_data, auto_commit=False)
        
        # Execute automation rules
        from app.services.automation_service import automation_engine
        feed = automation_engine.execute_rules(channel.id, feed, db)
        
        # Commit
        db.commit()
        db.refresh(feed)
        
        # 5. Logging
        logger.info(
            f"Widget control: User {current_user.id} updated "
            f"channel {channel_id} {field_update.field_name}={field_update.value}"
        )
        
        return {
            "success": True,
            "entry_id": feed.entry_id,
            "field": field_update.field_name,
            "value": getattr(feed, field_update.field_name)
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating field: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update field: {str(e)}"
        )


@router.get("/{channel_id}/fields/{field_name}")
async def get_field_value(
    channel_id: int,
    field_name: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Get current field value (for widgets)"""
    # Validate field_name
    valid_fields = [f'field{i}' for i in range(1, 9)]
    if field_name not in valid_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid field name"
        )
    
    # Get channel and check access
    channel = channel_service.get_channel(db, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    if not channel_service.check_channel_access(channel, current_user):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get last value
    from app.services import feed_service
    last_feed = feed_service.get_last_feed(db, channel_id)
    
    if not last_feed:
        return {"field": field_name, "value": None}
    
    value = getattr(last_feed, field_name, None)
    return {"field": field_name, "value": value}

