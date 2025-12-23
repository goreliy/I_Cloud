"""Automation rule schemas"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class AutomationRuleBase(BaseModel):
    name: str
    rule_type: str = 'condition'
    priority: int = 0


class AutomationRuleCreate(AutomationRuleBase):
    # Condition fields
    trigger_field: Optional[str] = None
    condition: Optional[str] = None
    threshold_value: Optional[float] = None
    target_field: Optional[str] = None
    action_type: Optional[str] = None
    action_value: Optional[float] = None
    
    # PID fields
    pid_setpoint: Optional[float] = None
    pid_kp: Optional[float] = None
    pid_ki: Optional[float] = None
    pid_kd: Optional[float] = None
    pid_output_min: Optional[float] = 0.0
    pid_output_max: Optional[float] = 100.0
    
    # Math fields
    expression: Optional[str] = None


class AutomationRuleUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = None
    
    # Condition fields
    trigger_field: Optional[str] = None
    condition: Optional[str] = None
    threshold_value: Optional[float] = None
    target_field: Optional[str] = None
    action_type: Optional[str] = None
    action_value: Optional[float] = None
    
    # PID fields
    pid_setpoint: Optional[float] = None
    pid_kp: Optional[float] = None
    pid_ki: Optional[float] = None
    pid_kd: Optional[float] = None
    pid_output_min: Optional[float] = None
    pid_output_max: Optional[float] = None
    
    # Math fields
    expression: Optional[str] = None


class AutomationRuleResponse(AutomationRuleBase):
    id: int
    channel_id: int
    trigger_field: Optional[str]
    condition: Optional[str]
    threshold_value: Optional[float]
    target_field: Optional[str]
    action_type: Optional[str]
    action_value: Optional[float]
    
    pid_setpoint: Optional[float]
    pid_kp: Optional[float]
    pid_ki: Optional[float]
    pid_kd: Optional[float]
    pid_integral: float
    pid_last_error: float
    pid_output_min: float
    pid_output_max: float
    
    expression: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True
















