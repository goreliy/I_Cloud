"""Automation engine for executing channel rules"""
from sqlalchemy.orm import Session
from app.models.automation_rule import AutomationRule
from app.models.feed import Feed
import re
import math


class AutomationEngine:
    """Execute automation rules for channels"""
    
    def execute_rules(self, channel_id: int, feed: Feed, db: Session) -> Feed:
        """
        Execute all active rules for channel in priority order
        Returns modified feed with calculated fields
        """
        rules = db.query(AutomationRule).filter(
            AutomationRule.channel_id == channel_id,
            AutomationRule.is_active == True
        ).order_by(AutomationRule.priority.asc()).all()
        
        for rule in rules:
            try:
                feed = self._execute_rule(rule, feed, db)
            except Exception as e:
                print(f"Error executing rule {rule.id}: {e}")
                # Continue with other rules
        
        return feed
    
    def _execute_rule(self, rule: AutomationRule, feed: Feed, db: Session) -> Feed:
        """Execute single rule based on type"""
        
        if rule.rule_type == 'condition':
            return self._execute_condition(rule, feed)
        elif rule.rule_type == 'pid':
            return self._execute_pid(rule, feed, db)
        elif rule.rule_type == 'math':
            return self._execute_math(rule, feed)
        
        return feed
    
    def _execute_condition(self, rule: AutomationRule, feed: Feed) -> Feed:
        """Execute IF-THEN condition rule"""
        if not rule.trigger_field or not rule.target_field:
            return feed
        
        trigger_value = getattr(feed, rule.trigger_field, None)
        if trigger_value is None:
            return feed
        
        # Check condition
        condition_met = False
        
        if rule.condition == '>':
            condition_met = trigger_value > rule.threshold_value
        elif rule.condition == '<':
            condition_met = trigger_value < rule.threshold_value
        elif rule.condition == '==':
            condition_met = trigger_value == rule.threshold_value
        elif rule.condition == '>=':
            condition_met = trigger_value >= rule.threshold_value
        elif rule.condition == '<=':
            condition_met = trigger_value <= rule.threshold_value
        elif rule.condition == '!=':
            condition_met = trigger_value != rule.threshold_value
        
        # Execute action if condition met
        if condition_met:
            if rule.action_type == 'set_value':
                setattr(feed, rule.target_field, rule.action_value)
            
            elif rule.action_type == 'increment':
                current = getattr(feed, rule.target_field, None) or 0
                setattr(feed, rule.target_field, current + rule.action_value)
            
            elif rule.action_type == 'decrement':
                current = getattr(feed, rule.target_field, None) or 0
                setattr(feed, rule.target_field, current - rule.action_value)
        
        return feed
    
    def _execute_pid(self, rule: AutomationRule, feed: Feed, db: Session) -> Feed:
        """Execute PID controller"""
        if not rule.trigger_field or not rule.target_field:
            return feed
        
        # Get current value (process variable)
        current_value = getattr(feed, rule.trigger_field, None)
        if current_value is None:
            return feed
        
        # Calculate error
        error = rule.pid_setpoint - current_value
        
        # Proportional term
        P = rule.pid_kp * error
        
        # Integral term
        rule.pid_integral += error
        I = rule.pid_ki * rule.pid_integral
        
        # Derivative term
        D = rule.pid_kd * (error - rule.pid_last_error)
        
        # PID output
        output = P + I + D
        
        # Limit output
        output = max(rule.pid_output_min, min(rule.pid_output_max, output))
        
        # Write to target field
        setattr(feed, rule.target_field, round(output, 2))
        
        # Save PID state
        rule.pid_last_error = error
        db.flush()  # Flush to save rule state without committing feed yet
        
        return feed
    
    def _execute_math(self, rule: AutomationRule, feed: Feed) -> Feed:
        """Execute mathematical expression"""
        if not rule.expression:
            return feed
        
        # Parse expression: "field2 = field1 * 2 + 10"
        match = re.match(r'(\w+)\s*=\s*(.+)', rule.expression.strip())
        if not match:
            return feed
        
        target_field = match.group(1)
        expression = match.group(2)
        
        # Build context with field values
        context = {}
        for i in range(1, 9):
            field_name = f'field{i}'
            field_value = getattr(feed, field_name, None)
            context[field_name] = field_value if field_value is not None else 0
        
        # Add math functions
        context.update({
            'sqrt': math.sqrt,
            'abs': abs,
            'pow': pow,
            'min': min,
            'max': max,
            'round': round,
        })
        
        try:
            # Evaluate expression safely
            result = self._safe_eval(expression, context)
            
            # Set target field
            if result is not None and target_field.startswith('field'):
                setattr(feed, target_field, round(result, 2))
        
        except Exception as e:
            print(f"Error evaluating expression: {e}")
        
        return feed
    
    def _safe_eval(self, expression: str, context: dict) -> float:
        """
        Safely evaluate mathematical expression
        Only allows basic math operations and whitelisted functions
        """
        # Replace ^ with **
        expression = expression.replace('^', '**')
        
        # Whitelist of allowed operations
        allowed_names = {
            'field1', 'field2', 'field3', 'field4',
            'field5', 'field6', 'field7', 'field8',
            'sqrt', 'abs', 'pow', 'min', 'max', 'round'
        }
        
        # Simple validation - check that only allowed characters are used
        if not re.match(r'^[a-zA-Z0-9\s\+\-\*\/\(\)\.,_]+$', expression):
            raise ValueError("Invalid characters in expression")
        
        # Use eval with restricted context (not 100% safe but better than nothing)
        # For production, consider using asteval library
        result = eval(expression, {"__builtins__": {}}, context)
        
        return float(result)


def get_output_fields(channel_id: int, db: Session) -> set:
    """
    Получить список выходных полей для канала
    Возвращает set полей (field1-field8), которые изменяются правилами автоматизации
    """
    rules = db.query(AutomationRule).filter(
        AutomationRule.channel_id == channel_id,
        AutomationRule.is_active == True
    ).all()
    
    output_fields = set()
    for rule in rules:
        if rule.target_field:
            output_fields.add(rule.target_field)
    
    return output_fields


# Singleton instance
automation_engine = AutomationEngine()


