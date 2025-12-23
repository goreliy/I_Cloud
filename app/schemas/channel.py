"""Channel schemas"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class ChannelBase(BaseModel):
    name: str
    description: Optional[str] = None
    public: bool = True
    timezone: str = "UTC"


class ChannelCreate(ChannelBase):
    pass


class ChannelUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    public: Optional[bool] = None
    timezone: Optional[str] = None
    color_scheme: Optional[str] = None
    custom_css: Optional[str] = None
    field1_label: Optional[str] = None
    field2_label: Optional[str] = None
    field3_label: Optional[str] = None
    field4_label: Optional[str] = None
    field5_label: Optional[str] = None
    field6_label: Optional[str] = None
    field7_label: Optional[str] = None
    field8_label: Optional[str] = None
    field1_visible: Optional[bool] = None
    field2_visible: Optional[bool] = None
    field3_visible: Optional[bool] = None
    field4_visible: Optional[bool] = None
    field5_visible: Optional[bool] = None
    field6_visible: Optional[bool] = None
    field7_visible: Optional[bool] = None
    field8_visible: Optional[bool] = None


class ChannelResponse(ChannelBase):
    id: int
    user_id: Optional[int]
    last_entry_id: int
    image_url: Optional[str]
    background_url: Optional[str]
    color_scheme: str
    custom_css: Optional[str]
    field1_label: Optional[str]
    field2_label: Optional[str]
    field3_label: Optional[str]
    field4_label: Optional[str]
    field5_label: Optional[str]
    field6_label: Optional[str]
    field7_label: Optional[str]
    field8_label: Optional[str]
    field1_visible: bool
    field2_visible: bool
    field3_visible: bool
    field4_visible: bool
    field5_visible: bool
    field6_visible: bool
    field7_visible: bool
    field8_visible: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ChannelWithStats(ChannelResponse):
    """Channel with statistics"""
    feed_count: int = 0
    last_feed_at: Optional[datetime] = None

