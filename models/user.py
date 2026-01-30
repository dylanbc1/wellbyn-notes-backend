"""
Modelo de Usuario y Sesión
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SQLEnum
from sqlalchemy.sql import func
from database import Base
import enum


class UserRole(str, enum.Enum):
    """Roles de usuario"""
    DOCTOR = "doctor"
    ADMINISTRATOR = "administrator"


class User(Base):
    """
    Modelo para usuarios del sistema
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Información básica
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    
    # Rol (usando native_enum=False para que use el valor del enum como string)
    role = Column(SQLEnum(UserRole, native_enum=False, length=20), nullable=False, default=UserRole.DOCTOR)
    
    # Estado
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self):
        return f"<User {self.id}: {self.email} ({self.role.value})>"


class Session(Base):
    """
    Modelo para sesiones de usuario
    """
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Relación con usuario
    user_id = Column(Integer, nullable=False, index=True)
    
    # Token de sesión
    session_token = Column(String(255), unique=True, index=True, nullable=False)
    
    # Información de sesión
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(String(500), nullable=True)
    
    # Expiración
    expires_at = Column(DateTime(timezone=True), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_activity = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<Session {self.id}: User {self.user_id}>"
