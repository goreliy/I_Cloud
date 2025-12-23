"""Stress test run model for tracking load tests"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from sqlalchemy.sql import func
from app.database import Base


class StressTestRun(Base):
    """История запусков стресс-тестов"""
    __tablename__ = "stress_test_runs"
    
    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(Integer, nullable=False, index=True)
    workers = Column(Integer, nullable=False)
    target_rps = Column(Integer, nullable=False)
    duration = Column(Integer, nullable=False)
    
    # Results
    total_requests = Column(Integer, nullable=True)
    successful_requests = Column(Integer, nullable=True)
    failed_requests = Column(Integer, nullable=True)
    actual_rps = Column(Float, nullable=True)
    avg_latency_ms = Column(Float, nullable=True)
    min_latency_ms = Column(Float, nullable=True)
    max_latency_ms = Column(Float, nullable=True)
    p95_latency_ms = Column(Float, nullable=True)
    
    status = Column(String(50), default='pending', nullable=False)  # pending, running, completed, failed
    error_message = Column(Text, nullable=True)
    
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    results_json = Column(Text, nullable=True)  # Полные результаты в JSON















