"""
Servicio para autenticación y gestión de usuarios
"""

from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from typing import Optional
import secrets
import hashlib
import bcrypt
import logging

from models.user import User, Session, UserRole
from schemas.auth import UserCreate, LoginRequest
from config import settings

logger = logging.getLogger(__name__)


class AuthService:
    """Servicio para autenticación"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hashea una contraseña usando bcrypt"""
        # Convertir contraseña a bytes
        password_bytes = password.encode('utf-8')
        # Generar salt y hashear
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password_bytes, salt)
        # Devolver como string
        return hashed.decode('utf-8')
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verifica una contraseña usando bcrypt"""
        try:
            # Convertir a bytes
            password_bytes = plain_password.encode('utf-8')
            hashed_bytes = hashed_password.encode('utf-8')
            # Verificar
            return bcrypt.checkpw(password_bytes, hashed_bytes)
        except Exception as e:
            logger.error(f"Error verifying password: {e}")
            return False
    
    @staticmethod
    def create_user(db: Session, user_data: UserCreate) -> User:
        """Crea un nuevo usuario"""
        # Verificar si el email ya existe
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            raise ValueError(f"User with email {user_data.email} already exists")
        
        # Crear usuario
        hashed_password = AuthService.hash_password(user_data.password)
        user = User(
            email=user_data.email,
            full_name=user_data.full_name,
            hashed_password=hashed_password,
            role=user_data.role
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        logger.info(f"Created user: {user.id} - {user.email} ({user.role.value})")
        return user
    
    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """Obtiene un usuario por email"""
        return db.query(User).filter(User.email == email).first()
    
    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
        """Obtiene un usuario por ID"""
        return db.query(User).filter(User.id == user_id).first()
    
    @staticmethod
    def authenticate_user(db: Session, login_data: LoginRequest) -> Optional[User]:
        """Autentica un usuario"""
        user = AuthService.get_user_by_email(db, login_data.email)
        
        if not user:
            return None
        
        if not user.is_active:
            return None
        
        if not AuthService.verify_password(login_data.password, user.hashed_password):
            return None
        
        # Actualizar último login
        user.last_login = datetime.now(timezone.utc)
        db.commit()
        
        return user
    
    @staticmethod
    def create_session_token() -> str:
        """Genera un token de sesión seguro"""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def create_session(db: Session, user_id: int, ip_address: Optional[str] = None,
                      user_agent: Optional[str] = None, expires_in_hours: int = 24) -> Session:
        """Crea una nueva sesión"""
        session_token = AuthService.create_session_token()
        expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)
        
        session = Session(
            user_id=user_id,
            session_token=session_token,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=expires_at
        )
        
        db.add(session)
        db.commit()
        db.refresh(session)
        
        logger.info(f"Created session for user {user_id}")
        return session
    
    @staticmethod
    def get_session_by_token(db: Session, session_token: str) -> Optional[Session]:
        """Obtiene una sesión por token"""
        session = db.query(Session).filter(Session.session_token == session_token).first()
        
        if not session:
            return None
        
        # Verificar expiración (usar timezone-aware datetime)
        if session.expires_at < datetime.now(timezone.utc):
            return None
        
        # Actualizar última actividad
        session.last_activity = datetime.now(timezone.utc)
        db.commit()
        
        return session
    
    @staticmethod
    def delete_session(db: Session, session_token: str) -> bool:
        """Elimina una sesión"""
        session = db.query(Session).filter(Session.session_token == session_token).first()
        
        if not session:
            return False
        
        db.delete(session)
        db.commit()
        
        logger.info(f"Deleted session {session.id}")
        return True
    
    @staticmethod
    def delete_user_sessions(db: Session, user_id: int) -> int:
        """Elimina todas las sesiones de un usuario"""
        deleted = db.query(Session).filter(Session.user_id == user_id).delete()
        db.commit()
        
        logger.info(f"Deleted {deleted} sessions for user {user_id}")
        return deleted
