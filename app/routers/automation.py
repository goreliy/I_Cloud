"""Automation rules API"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.automation_rule import AutomationRule
from app.models.user import User
from app.schemas.automation import AutomationRuleCreate, AutomationRuleUpdate, AutomationRuleResponse
from app.services import channel_service
from app.dependencies import get_current_user_optional

router = APIRouter(prefix="/api/channels", tags=["automation"])


@router.post("/{channel_id}/automation", response_model=AutomationRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_automation_rule(
    channel_id: int,
    rule_create: AutomationRuleCreate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Create automation rule"""
    # Check access
    channel = channel_service.get_channel(db, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    if not channel_service.check_channel_access(channel, current_user, require_owner=True):
        raise HTTPException(status_code=403, detail="Only channel owner can create rules")
    
    # Create rule
    rule = AutomationRule(
        channel_id=channel_id,
        name=rule_create.name,
        rule_type=rule_create.rule_type,
        priority=rule_create.priority,
        trigger_field=rule_create.trigger_field,
        condition=rule_create.condition,
        threshold_value=rule_create.threshold_value,
        target_field=rule_create.target_field,
        action_type=rule_create.action_type,
        action_value=rule_create.action_value,
        pid_setpoint=rule_create.pid_setpoint,
        pid_kp=rule_create.pid_kp,
        pid_ki=rule_create.pid_ki,
        pid_kd=rule_create.pid_kd,
        pid_output_min=rule_create.pid_output_min,
        pid_output_max=rule_create.pid_output_max,
        expression=rule_create.expression
    )
    
    db.add(rule)
    db.commit()
    db.refresh(rule)
    
    return rule


@router.get("/{channel_id}/automation", response_model=List[AutomationRuleResponse])
def list_automation_rules(
    channel_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """List automation rules"""
    # Check access
    channel = channel_service.get_channel(db, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    if not channel_service.check_channel_access(channel, current_user, require_owner=True):
        raise HTTPException(status_code=403, detail="Access denied")
    
    rules = db.query(AutomationRule).filter(
        AutomationRule.channel_id == channel_id
    ).order_by(AutomationRule.priority.asc()).all()
    
    return rules


@router.get("/{channel_id}/automation/{rule_id}", response_model=AutomationRuleResponse)
def get_automation_rule(
    channel_id: int,
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Get automation rule"""
    # Check access
    channel = channel_service.get_channel(db, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    if not channel_service.check_channel_access(channel, current_user, require_owner=True):
        raise HTTPException(status_code=403, detail="Access denied")
    
    rule = db.query(AutomationRule).filter(
        AutomationRule.id == rule_id,
        AutomationRule.channel_id == channel_id
    ).first()
    
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    return rule


@router.put("/{channel_id}/automation/{rule_id}", response_model=AutomationRuleResponse)
async def update_automation_rule(
    channel_id: int,
    rule_id: int,
    rule_update: AutomationRuleUpdate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Update automation rule"""
    # Check access
    channel = channel_service.get_channel(db, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    if not channel_service.check_channel_access(channel, current_user, require_owner=True):
        raise HTTPException(status_code=403, detail="Access denied")
    
    rule = db.query(AutomationRule).filter(
        AutomationRule.id == rule_id,
        AutomationRule.channel_id == channel_id
    ).first()
    
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    # Update fields
    update_data = rule_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rule, field, value)
    
    db.commit()
    db.refresh(rule)
    
    return rule


@router.delete("/{channel_id}/automation/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_automation_rule(
    channel_id: int,
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Delete automation rule"""
    # Check access
    channel = channel_service.get_channel(db, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    if not channel_service.check_channel_access(channel, current_user, require_owner=True):
        raise HTTPException(status_code=403, detail="Access denied")
    
    rule = db.query(AutomationRule).filter(
        AutomationRule.id == rule_id,
        AutomationRule.channel_id == channel_id
    ).first()
    
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    db.delete(rule)
    db.commit()
















