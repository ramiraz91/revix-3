from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
import jwt
import bcrypt
from config import security, JWT_SECRET, JWT_ALGORITHM, db
from models import UserRole
from typing import Optional

# Usuario master por defecto - LOGIN DESHABILITADO
DEFAULT_MASTER_USER = {
    "user_id": "auto-master",
    "email": "master@revix.es",
    "role": "master"
}

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

def create_token(user_id: str, email: str, role: str) -> str:
    from datetime import datetime, timezone
    payload = {
        "user_id": user_id,
        "email": email,
        "role": role,
        "exp": datetime.now(timezone.utc).timestamp() + 86400 * 7
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    # Sin token -> devolver usuario master por defecto
    if not credentials:
        return DEFAULT_MASTER_USER
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        # Token expirado -> devolver usuario master por defecto
        return DEFAULT_MASTER_USER
    except jwt.InvalidTokenError:
        # Token inválido -> devolver usuario master por defecto
        return DEFAULT_MASTER_USER

async def require_auth(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    # LOGIN DESHABILITADO - Siempre devuelve usuario master
    user = await get_current_user(credentials)
    return user if user else DEFAULT_MASTER_USER

async def require_admin(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    # LOGIN DESHABILITADO - Siempre permite acceso admin
    user = await get_current_user(credentials)
    return user if user else DEFAULT_MASTER_USER

async def require_master(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    # LOGIN DESHABILITADO - Siempre permite acceso master
    user = await get_current_user(credentials)
    return user if user else DEFAULT_MASTER_USER

async def require_tecnico(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """Solo técnicos pueden ejecutar acciones técnicas de certificación (RI, CPI, QC, diagnóstico)."""
    # LOGIN DESHABILITADO - Permitir acceso
    user = await get_current_user(credentials)
    return user if user else DEFAULT_MASTER_USER
