"""Custom widget schemas"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class CustomWidgetBase(BaseModel):
    name: str
    widget_type: str = 'svg'
    width: int = 6
    height: int = 300


class CustomWidgetCreate(CustomWidgetBase):
    svg_bindings: Optional[str] = None
    html_code: Optional[str] = None
    css_code: Optional[str] = None
    js_code: Optional[str] = None


class CustomWidgetUpdate(BaseModel):
    name: Optional[str] = None
    svg_bindings: Optional[str] = None
    html_code: Optional[str] = None
    css_code: Optional[str] = None
    js_code: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    position: Optional[int] = None
    is_active: Optional[bool] = None
    version_comment: Optional[str] = None
    ai_service_id: Optional[int] = None
    prompt_used: Optional[str] = None


class CustomWidgetResponse(CustomWidgetBase):
    id: int
    channel_id: int
    svg_file_url: Optional[str]
    svg_bindings: Optional[str]
    html_code: Optional[str]
    css_code: Optional[str]
    js_code: Optional[str]
    position: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True







