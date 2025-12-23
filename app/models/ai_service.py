"""Модели для конфигурации ИИ сервисов и шаблонов предпромптов."""
from __future__ import annotations

import enum
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class AIScope(enum.Enum):
    """Уровень применения шаблона предпромпта."""

    GLOBAL = "global"
    CHANNEL = "channel"
    WIDGET = "widget"


class AIService(Base):
    """Описание внешнего ИИ сервиса (iframe)."""

    __tablename__ = "ai_services"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    alias = Column(String(100), nullable=False, unique=True)
    url = Column(String(500), nullable=False)
    is_enabled = Column(Boolean, default=True)
    display_order = Column(Integer, default=0)

    # Базовые шаблоны предпромпта (могут переопределяться)
    default_prompt_common = Column(Text, nullable=True)
    default_prompt_html = Column(Text, nullable=True)
    default_prompt_css = Column(Text, nullable=True)
    default_prompt_js = Column(Text, nullable=True)
    default_prompt_refine = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    prompts = relationship(
        "AIServicePromptOverride",
        back_populates="service",
        cascade="all, delete-orphan",
    )


class AIServicePromptOverride(Base):
    """Переопределение шаблонов предпромпта для канала или виджета."""

    __tablename__ = "ai_service_prompts"

    id = Column(Integer, primary_key=True, index=True)
    service_id = Column(Integer, ForeignKey("ai_services.id", ondelete="CASCADE"), nullable=False)
    scope = Column(Enum(AIScope), nullable=False, default=AIScope.GLOBAL)
    channel_id = Column(Integer, ForeignKey("channels.id", ondelete="CASCADE"), nullable=True)
    widget_id = Column(Integer, ForeignKey("custom_widgets.id", ondelete="CASCADE"), nullable=True)

    prompt_common = Column(Text, nullable=True)
    prompt_html = Column(Text, nullable=True)
    prompt_css = Column(Text, nullable=True)
    prompt_js = Column(Text, nullable=True)
    prompt_refine = Column(Text, nullable=True)

    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    service = relationship("AIService", back_populates="prompts")

    # Дополнительные связи (lazy='joined' не требуется здесь)
    channel = relationship("Channel", back_populates="ai_prompt_overrides", lazy="joined")
    widget = relationship("CustomWidget", back_populates="ai_prompt_overrides", lazy="joined")
    creator = relationship("User")

    def applies_to_channel(self, channel_id: Optional[int]) -> bool:
        if self.scope != AIScope.CHANNEL:
            return False
        return self.channel_id == channel_id

    def applies_to_widget(self, widget_id: Optional[int]) -> bool:
        if self.scope != AIScope.WIDGET:
            return False
        return self.widget_id == widget_id

