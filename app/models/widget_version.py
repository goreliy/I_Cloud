"""Модель хранит историю изменений пользовательских виджетов."""
from __future__ import annotations

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class WidgetVersion(Base):
    __tablename__ = "widget_versions"

    id = Column(Integer, primary_key=True, index=True)
    widget_id = Column(Integer, ForeignKey("custom_widgets.id", ondelete="CASCADE"), nullable=False, index=True)
    ai_service_id = Column(Integer, ForeignKey("ai_services.id", ondelete="SET NULL"), nullable=True)
    prompt_used = Column(Text, nullable=True)
    comment = Column(String(255), nullable=True)

    html_code = Column(Text, nullable=True)
    css_code = Column(Text, nullable=True)
    js_code = Column(Text, nullable=True)

    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    widget = relationship("CustomWidget", back_populates="versions")
    ai_service = relationship("AIService")
    creator = relationship("User")

