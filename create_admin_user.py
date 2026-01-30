"""
Script para crear un usuario administrador inicial
"""

import sys
from database import SessionLocal
from models.user import User, UserRole
from services.auth_service import AuthService
import getpass

def create_admin():
    """Crea un usuario administrador"""
    db = SessionLocal()
    
    try:
        print("=" * 50)
        print("Crear Usuario Administrador")
        print("=" * 50)
        
        # Solicitar información
        email = input("Email: ").strip()
        if not email:
            print("❌ Email es requerido")
            return
        
        # Verificar si el usuario ya existe
        existing = AuthService.get_user_by_email(db, email)
        if existing:
            print(f"❌ El usuario con email {email} ya existe")
            return
        
        full_name = input("Nombre completo: ").strip()
        if not full_name:
            print("❌ Nombre completo es requerido")
            return
        
        password = getpass.getpass("Contraseña: ")
        if not password or len(password) < 6:
            print("❌ La contraseña debe tener al menos 6 caracteres")
            return
        
        password_confirm = getpass.getpass("Confirmar contraseña: ")
        if password != password_confirm:
            print("❌ Las contraseñas no coinciden")
            return
        
        # Crear usuario
        from schemas.auth import UserCreate
        
        user_data = UserCreate(
            email=email,
            full_name=full_name,
            password=password,
            role=UserRole.ADMINISTRATOR
        )
        
        user = AuthService.create_user(db, user_data)
        
        print("\n✅ Usuario administrador creado exitosamente!")
        print(f"   ID: {user.id}")
        print(f"   Email: {user.email}")
        print(f"   Nombre: {user.full_name}")
        print(f"   Rol: {user.role.value}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    create_admin()
