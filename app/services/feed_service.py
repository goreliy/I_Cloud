"""Feed (data entry) service"""
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.feed import Feed
from app.models.channel import Channel
from app.schemas.feed import FeedCreate


def create_feed(db: Session, channel: Channel, feed_data: FeedCreate, auto_commit: bool = True) -> Feed:
    """Create new feed entry"""
    # Increment entry_id for channel
    channel.last_entry_id += 1
    
    # Create feed entry
    db_feed = Feed(
        channel_id=channel.id,
        entry_id=channel.last_entry_id,
        field1=feed_data.field1,
        field2=feed_data.field2,
        field3=feed_data.field3,
        field4=feed_data.field4,
        field5=feed_data.field5,
        field6=feed_data.field6,
        field7=feed_data.field7,
        field8=feed_data.field8,
        latitude=feed_data.latitude,
        longitude=feed_data.longitude,
        elevation=feed_data.elevation,
        status=feed_data.status
    )
    
    db.add(db_feed)
    
    if auto_commit:
        db.commit()
        db.refresh(db_feed)
        db.refresh(channel)
    else:
        db.flush()  # Get IDs without committing
    
    return db_feed


def get_feeds(
    db: Session,
    channel_id: int,
    results: int = 100,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None
) -> List[Feed]:
    """Get feed entries for channel"""
    query = db.query(Feed).filter(Feed.channel_id == channel_id)
    
    if start:
        query = query.filter(Feed.created_at >= start)
    if end:
        query = query.filter(Feed.created_at <= end)
    
    query = query.order_by(desc(Feed.created_at)).limit(results)
    
    return query.all()


def get_last_feed(db: Session, channel_id: int) -> Optional[Feed]:
    """Get last feed entry for channel"""
    return db.query(Feed).filter(
        Feed.channel_id == channel_id
    ).order_by(desc(Feed.created_at)).first()


def get_field_data(
    db: Session,
    channel_id: int,
    field_num: int,
    results: int = 100,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None
) -> List[Feed]:
    """Get data for specific field"""
    if field_num < 1 or field_num > 8:
        return []
    
    field_name = f"field{field_num}"
    query = db.query(Feed).filter(
        Feed.channel_id == channel_id,
        getattr(Feed, field_name).isnot(None)
    )
    
    if start:
        query = query.filter(Feed.created_at >= start)
    if end:
        query = query.filter(Feed.created_at <= end)
    
    query = query.order_by(desc(Feed.created_at)).limit(results)
    
    return query.all()


def get_feed_count(db: Session, channel_id: int) -> int:
    """Get total number of feed entries for channel"""
    return db.query(Feed).filter(Feed.channel_id == channel_id).count()

