"""Automation rules model for channel automation"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class AutomationRule(Base):
    __tablename__ = "automation_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(Integer, ForeignKey("channels.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    rule_type = Column(String(50), default='condition')  # 'condition', 'pid', 'math'
    
    # Condition rules
    trigger_field = Column(String(20), nullable=True)  # "field1"
    condition = Column(String(50), nullable=True)  # ">", "<", "==", "!=", ">=", "<="
    threshold_value = Column(Float, nullable=True)  # Пороговое значение
    
    # Action
    target_field = Column(String(20), nullable=True)  # "field2"
    action_type = Column(String(50), nullable=True)  # "set_value", "increment", "decrement"
    action_value = Column(Float, nullable=True)  # Для set_value
    
    # PID controller settings
    pid_setpoint = Column(Float, nullable=True)  # Целевое значение
    pid_kp = Column(Float, nullable=True)  # Пропорциональный коэф.
    pid_ki = Column(Float, nullable=True)  # Интегральный коэф.
    pid_kd = Column(Float, nullable=True)  # Дифференциальный коэф.
    pid_integral = Column(Float, default=0.0)  # Накопленная ошибка
    pid_last_error = Column(Float, default=0.0)  # Предыдущая ошибка
    pid_output_min = Column(Float, default=0.0)  # Минимум выхода
    pid_output_max = Column(Float, default=100.0)  # Максимум выхода
    
    # Math expression
    expression = Column(Text, nullable=True)  # "field2 = field1 * 2 + 10"
    
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=0)  # Порядок выполнения (меньше = раньше)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationship
    channel = relationship("Channel", back_populates="automation_rules")
















