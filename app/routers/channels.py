"""Channel management routes"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.schemas.channel import ChannelCreate, ChannelUpdate, ChannelResponse
from app.schemas.api_key import ApiKeyResponse, ApiKeyCreate
from app.services import channel_service, upload_service
from app.dependencies import get_current_user, get_current_user_optional
from app.models.user import User

router = APIRouter(prefix="/api/channels", tags=["channels"])


@router.post("", response_model=ChannelResponse, status_code=status.HTTP_201_CREATED)
def create_channel(
    channel: ChannelCreate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Create a new channel"""
    if settings.AUTH_ENABLED and not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    return channel_service.create_channel(db, channel, current_user)


@router.get("", response_model=List[ChannelResponse])
def list_channels(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Get list of channels"""
    return channel_service.get_channels(db, current_user, skip, limit)


@router.get("/{channel_id}", response_model=ChannelResponse)
def get_channel(
    channel_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Get channel details"""
    channel = channel_service.get_channel(db, channel_id)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel not found"
        )
    
    if not channel_service.check_channel_access(channel, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return channel


@router.put("/{channel_id}", response_model=ChannelResponse)
def update_channel(
    channel_id: int,
    channel_update: ChannelUpdate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Update channel"""
    channel = channel_service.get_channel(db, channel_id)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel not found"
        )
    
    if not channel_service.check_channel_access(channel, current_user, require_owner=True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only channel owner can update it"
        )
    
    return channel_service.update_channel(db, channel, channel_update)


@router.delete("/{channel_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_channel(
    channel_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Delete channel"""
    channel = channel_service.get_channel(db, channel_id)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel not found"
        )
    
    if not channel_service.check_channel_access(channel, current_user, require_owner=True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only channel owner can delete it"
        )
    
    channel_service.delete_channel(db, channel)


@router.get("/{channel_id}/api-keys", response_model=List[ApiKeyResponse])
def list_api_keys(
    channel_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Get API keys for channel"""
    channel = channel_service.get_channel(db, channel_id)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel not found"
        )
    
    if not channel_service.check_channel_access(channel, current_user, require_owner=True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only channel owner can view API keys"
        )
    
    return channel_service.get_channel_api_keys(db, channel_id)


@router.post("/{channel_id}/api-keys", response_model=ApiKeyResponse, status_code=status.HTTP_201_CREATED)
def create_api_key(
    channel_id: int,
    api_key_create: ApiKeyCreate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Create new API key for channel"""
    channel = channel_service.get_channel(db, channel_id)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel not found"
        )
    
    if not channel_service.check_channel_access(channel, current_user, require_owner=True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only channel owner can create API keys"
        )
    
    return channel_service.create_api_key(db, channel_id, api_key_create.type)


@router.post("/{channel_id}/upload-image", response_model=ChannelResponse)
async def upload_channel_image(
    channel_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Upload channel main image"""
    channel = channel_service.get_channel(db, channel_id)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel not found"
        )
    
    if not channel_service.check_channel_access(channel, current_user, require_owner=True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only channel owner can upload images"
        )
    
    # Delete old image if exists
    if channel.image_url:
        upload_service.delete_file(channel.image_url)
    
    # Save new image
    image_url = await upload_service.save_channel_image(file, channel_id, "image")
    channel.image_url = image_url
    db.commit()
    db.refresh(channel)
    
    return channel


@router.post("/{channel_id}/upload-background", response_model=ChannelResponse)
async def upload_channel_background(
    channel_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Upload channel background image"""
    channel = channel_service.get_channel(db, channel_id)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel not found"
        )
    
    if not channel_service.check_channel_access(channel, current_user, require_owner=True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only channel owner can upload background"
        )
    
    # Delete old background if exists
    if channel.background_url:
        upload_service.delete_file(channel.background_url)
    
    # Save new background
    background_url = await upload_service.save_channel_image(file, channel_id, "background")
    channel.background_url = background_url
    db.commit()
    db.refresh(channel)
    
    return channel

