"""Feed (data entry) model"""
from sqlalchemy import Column, Integer, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Feed(Base):
    __tablename__ = "feeds"
    
    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(Integer, ForeignKey("channels.id", ondelete="CASCADE"), nullable=False, index=True)
    entry_id = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Data fields (8 data fields)
    field1 = Column(Float, nullable=True)
    field2 = Column(Float, nullable=True)
    field3 = Column(Float, nullable=True)
    field4 = Column(Float, nullable=True)
    field5 = Column(Float, nullable=True)
    field6 = Column(Float, nullable=True)
    field7 = Column(Float, nullable=True)
    field8 = Column(Float, nullable=True)
    
    # Location data
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    elevation = Column(Float, nullable=True)
    
    # Status text
    status = Column(Text, nullable=True)
    
    # Relationship
    channel = relationship("Channel", back_populates="feeds")

