"""Request logging model"""
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from app.database import Base


class RequestLog(Base):
    __tablename__ = "request_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    channel_id = Column(Integer, ForeignKey("channels.id", ondelete="SET NULL"), nullable=True)
    endpoint = Column(String(500), nullable=False)
    method = Column(String(10), nullable=False)  # GET, POST, PUT, DELETE
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(Text, nullable=True)
    response_status = Column(Integer, nullable=False)
    response_time = Column(Float, nullable=False)  # milliseconds
    api_key_used = Column(String(255), nullable=True)
    
    __table_args__ = (
        Index('ix_request_logs_timestamp_status', 'timestamp', 'response_status'),
        Index('ix_request_logs_user_timestamp', 'user_id', 'timestamp'),
    )
















