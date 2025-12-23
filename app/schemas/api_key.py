"""API Key schemas"""
from pydantic import BaseModel
from datetime import datetime
from typing import Literal


class ApiKeyBase(BaseModel):
    type: Literal["read", "write"]


class ApiKeyCreate(ApiKeyBase):
    pass


class ApiKeyResponse(ApiKeyBase):
    id: int
    channel_id: int
    key: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

