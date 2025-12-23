"""Feed (data entry) schemas"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class FeedBase(BaseModel):
    field1: Optional[float] = None
    field2: Optional[float] = None
    field3: Optional[float] = None
    field4: Optional[float] = None
    field5: Optional[float] = None
    field6: Optional[float] = None
    field7: Optional[float] = None
    field8: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    elevation: Optional[float] = None
    status: Optional[str] = None


class FeedCreate(FeedBase):
    """For creating new feed entry"""
    pass


class FeedUpdate(FeedBase):
    """For update endpoint"""
    api_key: str


class FeedResponse(FeedBase):
    id: int
    channel_id: int
    entry_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class FeedListResponse(BaseModel):
    """Response for feed list"""
    channel: dict
    feeds: list[FeedResponse]
    
    class Config:
        from_attributes = True

