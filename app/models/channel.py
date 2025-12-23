"""Channel model"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Channel(Base):
    __tablename__ = "channels"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    public = Column(Boolean, default=True)
    timezone = Column(String(100), default="UTC")
    last_entry_id = Column(Integer, default=0)
    
    # Customization fields
    image_url = Column(String(500), nullable=True)
    background_url = Column(String(500), nullable=True)
    color_scheme = Column(String(50), default="light")  # light, dark, blue, green, custom
    custom_css = Column(Text, nullable=True)
    
    # Field labels (for field1-8)
    field1_label = Column(String(100), nullable=True)
    field2_label = Column(String(100), nullable=True)
    field3_label = Column(String(100), nullable=True)
    field4_label = Column(String(100), nullable=True)
    field5_label = Column(String(100), nullable=True)
    field6_label = Column(String(100), nullable=True)
    field7_label = Column(String(100), nullable=True)
    field8_label = Column(String(100), nullable=True)
    
    # Field visibility (for field1-8) - по умолчанию все видимы
    field1_visible = Column(Boolean, default=True)
    field2_visible = Column(Boolean, default=True)
    field3_visible = Column(Boolean, default=True)
    field4_visible = Column(Boolean, default=True)
    field5_visible = Column(Boolean, default=True)
    field6_visible = Column(Boolean, default=True)
    field7_visible = Column(Boolean, default=True)
    field8_visible = Column(Boolean, default=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="channels")
    feeds = relationship("Feed", back_populates="channel", cascade="all, delete-orphan")
    api_keys = relationship("ApiKey", back_populates="channel", cascade="all, delete-orphan")
    widgets = relationship("CustomWidget", back_populates="channel", cascade="all, delete-orphan")
    automation_rules = relationship("AutomationRule", back_populates="channel", cascade="all, delete-orphan")
    ai_prompt_overrides = relationship(
        "AIServicePromptOverride",
        back_populates="channel",
        cascade="all, delete-orphan",
    )

