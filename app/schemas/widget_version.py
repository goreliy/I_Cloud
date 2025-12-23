"""Pydantic-схемы для истории версий виджетов."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class WidgetVersionCreate(BaseModel):
    widget_id: int
    ai_service_id: Optional[int] = None
    prompt_used: Optional[str] = None
    comment: Optional[str] = None
    html_code: Optional[str] = None
    css_code: Optional[str] = None
    js_code: Optional[str] = None


class WidgetVersionResponse(BaseModel):
    id: int
    widget_id: int
    ai_service_id: Optional[int]
    prompt_used: Optional[str]
    comment: Optional[str]
    html_code: Optional[str]
    css_code: Optional[str]
    js_code: Optional[str]
    created_by: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True

