"""User schemas"""
from pydantic import BaseModel, ConfigDict, EmailStr, field_validator
from datetime import datetime
from typing import Optional


class UserBase(BaseModel):
    email: EmailStr
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        """Validate email: no spaces, only allowed characters"""
        email_str = str(v)
        
        # Проверка на пробелы
        if ' ' in email_str:
            raise ValueError('Email не может содержать пробелы')
        
        # Проверка на недопустимые символы (только стандартные для email)
        allowed_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@.-_+')
        if not all(c in allowed_chars for c in email_str):
            raise ValueError('Email содержит недопустимые символы. Разрешены: буквы, цифры, @.-_+')
        
        return email_str.lower().strip()


class UserCreate(UserBase):
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(UserBase):
    id: int
    is_active: bool
    is_admin: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    user_id: Optional[int] = None


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None
    display_name: Optional[str] = None


class UserDetailResponse(UserResponse):
    last_login: Optional[datetime] = None
    display_name: Optional[str] = None
    channel_count: int = 0
    
    model_config = ConfigDict(from_attributes=True)

