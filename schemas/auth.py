"""
Schemas para autenticación y usuarios
"""

from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from models.user import UserRole


class UserCreate(BaseModel):
    """Schema para crear usuario"""
    email: EmailStr
    full_name: str
    password: str
    role: UserRole = UserRole.DOCTOR


class UserResponse(BaseModel):
    """Schema para respuesta de usuario"""
    id: int
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class PublicRegisterRequest(BaseModel):
    """Schema para registro público (sin role)"""
    email: EmailStr
    full_name: str
    password: str


class LoginRequest(BaseModel):
    """Schema para login"""
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    """Schema para respuesta de login"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
    expires_in: int


class SessionResponse(BaseModel):
    """Schema para respuesta de sesión"""
    session_token: str
    expires_at: datetime
    user: UserResponse
    
    class Config:
        from_attributes = True
