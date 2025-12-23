"""Custom widget model for SVG and HTML/JS visualizations"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class CustomWidget(Base):
    __tablename__ = "custom_widgets"
    
    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(Integer, ForeignKey("channels.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    widget_type = Column(String(50), default='svg')  # 'svg', 'html', 'custom'
    
    # SVG specific
    svg_file_url = Column(String(500), nullable=True)
    svg_bindings = Column(Text, nullable=True)  # JSON string with bindings
    
    # Custom HTML/CSS/JS
    html_code = Column(Text, nullable=True)
    css_code = Column(Text, nullable=True)
    js_code = Column(Text, nullable=True)
    
    # Layout
    position = Column(Integer, default=0)
    width = Column(Integer, default=6)  # 1-12 Bootstrap columns
    height = Column(Integer, default=300)  # pixels
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationship
    channel = relationship("Channel", back_populates="widgets")
    ai_prompt_overrides = relationship(
        "AIServicePromptOverride",
        back_populates="widget",
        cascade="all, delete-orphan",
    )
    versions = relationship(
        "WidgetVersion",
        back_populates="widget",
        cascade="all, delete-orphan",
        order_by="WidgetVersion.created_at.desc()",
    )







