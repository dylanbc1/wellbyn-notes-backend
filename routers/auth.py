"""
Endpoints de autenticación
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import Optional
import logging

from database import get_db
from schemas.auth import UserCreate, UserResponse, LoginRequest, LoginResponse, SessionResponse, PublicRegisterRequest
from services.auth_service import AuthService
from models.user import User, Session

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

logger = logging.getLogger(__name__)


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Dependency para obtener el usuario actual"""
    # Obtener token de sesión del header o cookie
    session_token = None
    
    # Intentar obtener de header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        session_token = auth_header.split(" ")[1]
    else:
        # Intentar obtener de cookie
        session_token = request.cookies.get("session_token")
    
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Obtener sesión
    session = AuthService.get_session_by_token(db, session_token)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    
    # Obtener usuario
    user = AuthService.get_user_by_id(db, session.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    
    return user


def get_current_administrator(current_user: User = Depends(get_current_user)) -> User:
    """Dependency para verificar que el usuario es administrador"""
    from models.user import UserRole
    
    if current_user.role != UserRole.ADMINISTRATOR:
        raise HTTPException(status_code=403, detail="Administrator access required")
    
    return current_user


@router.post("/register", response_model=UserResponse, status_code=201)
def register_user(
    user_data: PublicRegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Registro público de nuevo usuario
    
    Crea un nuevo usuario con rol DOCTOR por defecto
    """
    try:
        # Convertir PublicRegisterRequest a UserCreate con role DOCTOR
        from models.user import UserRole
        user_create = UserCreate(
            email=user_data.email,
            full_name=user_data.full_name,
            password=user_data.password,
            role=UserRole.DOCTOR
        )
        user = AuthService.create_user(db, user_create)
        return user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login", response_model=LoginResponse)
def login(
    login_data: LoginRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Inicia sesión y crea una sesión
    """
    # Autenticar usuario
    user = AuthService.authenticate_user(db, login_data)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Crear sesión
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    
    session = AuthService.create_session(
        db,
        user.id,
        ip_address=ip_address,
        user_agent=user_agent,
        expires_in_hours=24
    )
    
    return {
        "access_token": session.session_token,
        "token_type": "bearer",
        "user": user,
        "expires_in": 24 * 60 * 60  # 24 horas en segundos
    }


@router.post("/logout")
def logout(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Cierra sesión eliminando el token de sesión
    """
    session_token = None
    
    # Intentar obtener de header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        session_token = auth_header.split(" ")[1]
    else:
        # Intentar obtener de cookie
        session_token = request.cookies.get("session_token")
    
    if session_token:
        AuthService.delete_session(db, session_token)
    
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene información del usuario actual
    """
    return current_user


@router.get("/sessions", response_model=list[SessionResponse])
def get_my_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtiene todas las sesiones activas del usuario actual
    """
    from datetime import datetime, timezone
    
    # Obtener todas las sesiones del usuario
    sessions = db.query(Session).filter(
        Session.user_id == current_user.id
    ).all()
    
    # Filtrar sesiones expiradas (usar timezone-aware datetime)
    active_sessions = [s for s in sessions if s.expires_at > datetime.now(timezone.utc)]
    
    return active_sessions
