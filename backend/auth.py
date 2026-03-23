from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
import jwt
import bcrypt
from config import security, JWT_SECRET, JWT_ALGORITHM, db
from models import UserRole

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

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        return None
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")

async def require_auth(credentials: HTTPAuthorizationCredentials = Depends(security)):
    user = await get_current_user(credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Autenticación requerida")
    return user

async def require_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    user = await require_auth(credentials)
    if user.get("role") not in [UserRole.ADMIN.value, UserRole.MASTER.value]:
        raise HTTPException(status_code=403, detail="Acceso denegado. Se requiere rol de administrador")
    return user

async def require_master(credentials: HTTPAuthorizationCredentials = Depends(security)):
    user = await require_auth(credentials)
    if user.get("role") != UserRole.MASTER.value:
        raise HTTPException(status_code=403, detail="Acceso denegado. Se requiere rol master")
    return user

async def require_tecnico(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Solo técnicos pueden ejecutar acciones técnicas de certificación (RI, CPI, QC, diagnóstico)."""
    user = await require_auth(credentials)
    if user.get("role") != UserRole.TECNICO.value:
        raise HTTPException(
            status_code=403,
            detail="Acción restringida: solo el técnico puede completar esta sección (RI, CPI, Diagnóstico, QC)"
        )
    return user
