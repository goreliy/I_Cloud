"""Pydantic-схемы для конфигурации ИИ сервисов и шаблонов предпромптов."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.ai_service import AIScope


class AIServiceBase(BaseModel):
    name: str = Field(..., max_length=255)
    alias: str = Field(..., max_length=100)
    url: str = Field(..., max_length=500)
    is_enabled: bool = True
    display_order: int = 0
    default_prompt_common: Optional[str] = None
    default_prompt_html: Optional[str] = None
    default_prompt_css: Optional[str] = None
    default_prompt_js: Optional[str] = None
    default_prompt_refine: Optional[str] = None


class AIServiceCreate(AIServiceBase):
    pass


class AIServiceUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    alias: Optional[str] = Field(None, max_length=100)
    url: Optional[str] = Field(None, max_length=500)
    is_enabled: Optional[bool] = None
    display_order: Optional[int] = None
    default_prompt_common: Optional[str] = None
    default_prompt_html: Optional[str] = None
    default_prompt_css: Optional[str] = None
    default_prompt_js: Optional[str] = None
    default_prompt_refine: Optional[str] = None


class AIServiceResponse(AIServiceBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AIServicePromptOverrideBase(BaseModel):
    service_id: int
    scope: AIScope
    channel_id: Optional[int] = None
    widget_id: Optional[int] = None
    prompt_common: Optional[str] = None
    prompt_html: Optional[str] = None
    prompt_css: Optional[str] = None
    prompt_js: Optional[str] = None
    prompt_refine: Optional[str] = None


class AIServicePromptOverrideCreate(AIServicePromptOverrideBase):
    pass


class AIServicePromptOverrideUpdate(BaseModel):
    prompt_common: Optional[str] = None
    prompt_html: Optional[str] = None
    prompt_css: Optional[str] = None
    prompt_js: Optional[str] = None
    prompt_refine: Optional[str] = None


class AIServicePromptOverrideScopedCreate(BaseModel):
    service_id: int
    prompt_common: Optional[str] = None
    prompt_html: Optional[str] = None
    prompt_css: Optional[str] = None
    prompt_js: Optional[str] = None
    prompt_refine: Optional[str] = None


class AIServicePromptOverrideResponse(AIServicePromptOverrideBase):
    id: int
    created_by: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

