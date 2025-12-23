"""Channel service"""
import secrets
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.channel import Channel
from app.models.feed import Feed
from app.models.api_key import ApiKey
from app.models.user import User
from app.schemas.channel import ChannelCreate, ChannelUpdate
from app.config import settings


def generate_api_key() -> str:
    """Generate a random API key"""
    return secrets.token_urlsafe(32)


def create_channel(db: Session, channel: ChannelCreate, user: Optional[User] = None) -> Channel:
    """Create a new channel"""
    db_channel = Channel(
        user_id=user.id if user else None,
        name=channel.name,
        description=channel.description,
        public=channel.public,
        timezone=channel.timezone
    )
    db.add(db_channel)
    db.commit()
    db.refresh(db_channel)
    
    # Create default API keys
    write_key = ApiKey(
        channel_id=db_channel.id,
        key=generate_api_key(),
        type="write"
    )
    read_key = ApiKey(
        channel_id=db_channel.id,
        key=generate_api_key(),
        type="read"
    )
    db.add(write_key)
    db.add(read_key)
    db.commit()
    
    return db_channel


def get_channel(db: Session, channel_id: int) -> Optional[Channel]:
    """Get channel by ID"""
    return db.query(Channel).filter(Channel.id == channel_id).first()


def get_channels(
    db: Session,
    user: Optional[User] = None,
    skip: int = 0,
    limit: int = 100
) -> List[Channel]:
    """Get list of channels"""
    query = db.query(Channel)
    
    if settings.AUTH_ENABLED:
        if user:
            # Пользователь залогинен: его каналы + публичные
            query = query.filter(
                (Channel.user_id == user.id) | (Channel.public == True)
            )
        else:
            # НЕ залогинен: ТОЛЬКО публичные
            query = query.filter(Channel.public == True)
    # Если AUTH_ENABLED=false, показать все каналы
    
    return query.offset(skip).limit(limit).all()


def update_channel(
    db: Session,
    channel: Channel,
    channel_update: ChannelUpdate
) -> Channel:
    """Update channel"""
    update_data = channel_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(channel, field, value)
    db.commit()
    db.refresh(channel)
    return channel


def delete_channel(db: Session, channel: Channel) -> None:
    """Delete channel"""
    db.delete(channel)
    db.commit()


def get_channel_api_keys(db: Session, channel_id: int) -> List[ApiKey]:
    """Get API keys for channel"""
    return db.query(ApiKey).filter(ApiKey.channel_id == channel_id).all()


def create_api_key(db: Session, channel_id: int, key_type: str) -> ApiKey:
    """Create new API key for channel"""
    api_key = ApiKey(
        channel_id=channel_id,
        key=generate_api_key(),
        type=key_type
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    return api_key


def check_channel_access(
    channel: Channel,
    user: Optional[User],
    require_owner: bool = False
) -> bool:
    """Check if user has access to channel"""
    if not settings.AUTH_ENABLED:
        return True
    
    if require_owner:
        return user and channel.user_id == user.id
    
    # Can access if owner or channel is public
    if channel.public:
        return True
    
    return user and channel.user_id == user.id

