"""Channel statistics service."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.feed import Feed


class ChannelStats:
    """Channel statistics."""

    def __init__(
        self,
        avg_interval_seconds: Optional[float] = None,
        min_interval_seconds: Optional[float] = None,
        recent_count: int = 0,
        last_feed_at: Optional[datetime] = None,
        total_feeds: int = 0,
    ):
        self.avg_interval_seconds = avg_interval_seconds
        self.min_interval_seconds = min_interval_seconds
        self.recent_count = recent_count
        self.last_feed_at = last_feed_at
        self.total_feeds = total_feeds

    def to_dict(self) -> dict:
        """Convert stats to dictionary."""
        return {
            "avg_interval_seconds": self.avg_interval_seconds,
            "min_interval_seconds": self.min_interval_seconds,
            "recent_count": self.recent_count,
            "last_feed_at": self.last_feed_at.isoformat() if self.last_feed_at else None,
            "total_feeds": self.total_feeds,
        }


def calculate_channel_stats(channel_id: int, db: Session) -> ChannelStats:
    """Calculate statistics for a channel.

    Args:
        channel_id: Channel ID
        db: Database session

    Returns:
        ChannelStats object with calculated statistics
    """
    # Get total count
    total_feeds = db.query(func.count(Feed.id)).filter(Feed.channel_id == channel_id).scalar() or 0

    # Get last feed
    last_feed = (
        db.query(Feed).filter(Feed.channel_id == channel_id).order_by(Feed.created_at.desc()).first()
    )
    last_feed_at = last_feed.created_at if last_feed else None

    # Get recent count (last 24 hours)
    yesterday = datetime.utcnow() - timedelta(days=1)
    recent_count = (
        db.query(func.count(Feed.id))
        .filter(Feed.channel_id == channel_id, Feed.created_at >= yesterday)
        .scalar()
        or 0
    )

    # Calculate intervals between feeds
    # Use window function to get time differences
    if total_feeds < 2:
        # Need at least 2 feeds to calculate intervals
        return ChannelStats(
            avg_interval_seconds=None,
            min_interval_seconds=None,
            recent_count=recent_count,
            last_feed_at=last_feed_at,
            total_feeds=total_feeds,
        )

    # Calculate intervals in Python for compatibility
    feeds = (
        db.query(Feed.created_at)
        .filter(Feed.channel_id == channel_id)
        .order_by(Feed.created_at)
        .all()
    )
    intervals = []
    for i in range(1, len(feeds)):
        delta = feeds[i].created_at - feeds[i - 1].created_at
        intervals.append(delta.total_seconds())

    if not intervals:
        return ChannelStats(
            avg_interval_seconds=None,
            min_interval_seconds=None,
            recent_count=recent_count,
            last_feed_at=last_feed_at,
            total_feeds=total_feeds,
        )

    avg_interval = sum(intervals) / len(intervals)
    min_interval = min(intervals)

    return ChannelStats(
        avg_interval_seconds=avg_interval,
        min_interval_seconds=min_interval,
        recent_count=recent_count,
        last_feed_at=last_feed_at,
        total_feeds=total_feeds,
    )

