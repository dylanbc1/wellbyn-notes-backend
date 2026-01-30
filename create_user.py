"""
Script para crear un usuario nuevo (doctor o administrador)
Uso: python create_user.py <email> <nombre_completo> <contraseña> [rol]
Rol puede ser: doctor o administrator (por defecto: doctor)
"""

import sys
from database import SessionLocal
from models.user import User, UserRole
from services.auth_service import AuthService
from schemas.auth import UserCreate


def create_user(email: str, full_name: str, password: str, role: str = "doctor"):
    """Crea un usuario nuevo"""
    db = SessionLocal()
    
    try:
        # Validar rol
        if role.lower() == "administrator" or role.lower() == "admin":
            user_role = UserRole.ADMINISTRATOR
        elif role.lower() == "doctor" or role.lower() == "doctor":
            user_role = UserRole.DOCTOR
        else:
            print(f"❌ Rol inválido: {role}. Usa 'doctor' o 'administrator'")
            return False
        
        # Validar contraseña
        if len(password) < 6:
            print("❌ La contraseña debe tener al menos 6 caracteres")
            return False
        
        # Verificar si el usuario ya existe
        existing = AuthService.get_user_by_email(db, email)
        if existing:
            print(f"❌ El usuario con email {email} ya existe")
            return False
        
        # Crear usuario
        user_data = UserCreate(
            email=email,
            full_name=full_name,
            password=password,
            role=user_role
        )
        
        user = AuthService.create_user(db, user_data)
        
        print("\n✅ Usuario creado exitosamente!")
        print(f"   ID: {user.id}")
        print(f"   Email: {user.email}")
        print(f"   Nombre: {user.full_name}")
        print(f"   Rol: {user.role.value}")
        print(f"   Activo: {user.is_active}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("=" * 60)
        print("Crear Usuario")
        print("=" * 60)
        print("\nUso:")
        print("  python create_user.py <email> <nombre_completo> <contraseña> [rol]")
        print("\nEjemplos:")
        print("  python create_user.py doctor@example.com 'Dr. Juan Pérez' miPassword123")
        print("  python create_user.py admin@example.com 'Admin Usuario' miPassword123 administrator")
        print("\nRoles disponibles: doctor (por defecto) o administrator")
        sys.exit(1)
    
    email = sys.argv[1]
    full_name = sys.argv[2]
    password = sys.argv[3]
    role = sys.argv[4] if len(sys.argv) > 4 else "doctor"
    
    success = create_user(email, full_name, password, role)
    sys.exit(0 if success else 1)
