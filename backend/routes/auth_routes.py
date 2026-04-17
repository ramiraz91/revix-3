from fastapi import APIRouter, HTTPException, Depends, Request
from typing import Optional
from datetime import datetime, timezone, timedelta
from config import db, FRONTEND_URL
from auth import require_auth, require_admin, require_master, hash_password, verify_password, create_token
from models import User, UserCreate, UserUpdate, UserLogin, TokenResponse, UserRole
from helpers import send_email
import secrets
import logging
from pydantic import BaseModel
from collections import defaultdict
import time

logger = logging.getLogger(__name__)
router = APIRouter()

# ==================== RATE LIMITING (en memoria) ====================

# {ip: [timestamps_of_failed_attempts]}
_login_attempts: dict = defaultdict(list)
# {ip: blocked_until_timestamp}
_blocked_ips: dict = {}
# {email: [timestamps]}
_email_attempts: dict = defaultdict(list)
# {email: blocked_until}
_blocked_emails: dict = {}

MAX_ATTEMPTS = 5          # intentos antes de bloqueo
BLOCK_DURATION = 900      # segundos (15 min)
WINDOW = 600              # ventana de 10 min para contar intentos


def _check_rate_limit(ip: str, email: str):
    """Lanza 429 si la IP o el email están bloqueados o han superado el límite"""
    now = time.time()

    # Verificar bloqueo activo por IP
    if ip in _blocked_ips:
        remaining = int(_blocked_ips[ip] - now)
        if remaining > 0:
            raise HTTPException(
                status_code=429,
                detail=f"Demasiados intentos fallidos. Espera {remaining // 60 + 1} minuto(s) antes de volver a intentarlo.",
                headers={"Retry-After": str(remaining)}
            )
        else:
            del _blocked_ips[ip]
            _login_attempts[ip] = []

    # Verificar bloqueo activo por email
    if email in _blocked_emails:
        remaining = int(_blocked_emails[email] - now)
        if remaining > 0:
            raise HTTPException(
                status_code=429,
                detail=f"Cuenta temporalmente bloqueada por seguridad. Espera {remaining // 60 + 1} minuto(s) o recupera tu contraseña.",
                headers={"Retry-After": str(remaining)}
            )
        else:
            del _blocked_emails[email]
            _email_attempts[email] = []

    # Limpiar intentos fuera de la ventana
    _login_attempts[ip] = [t for t in _login_attempts[ip] if now - t < WINDOW]
    _email_attempts[email] = [t for t in _email_attempts[email] if now - t < WINDOW]


def _record_failed_attempt(ip: str, email: str):
    """Registra un intento fallido y bloquea si supera el límite"""
    now = time.time()
    _login_attempts[ip].append(now)
    _email_attempts[email].append(now)

    if len(_login_attempts[ip]) >= MAX_ATTEMPTS:
        _blocked_ips[ip] = now + BLOCK_DURATION

    if len(_email_attempts[email]) >= MAX_ATTEMPTS:
        _blocked_emails[email] = now + BLOCK_DURATION


def _clear_attempts(ip: str, email: str):
    """Limpia los intentos tras login exitoso"""
    _login_attempts.pop(ip, None)
    _email_attempts.pop(email, None)


def _attempts_remaining(ip: str, email: str) -> int:
    now = time.time()
    ip_count = len([t for t in _login_attempts.get(ip, []) if now - t < WINDOW])
    email_count = len([t for t in _email_attempts.get(email, []) if now - t < WINDOW])
    return max(0, MAX_ATTEMPTS - max(ip_count, email_count) - 1)


# ==================== AUTH ====================

# ==================== AUTH ====================

@router.post("/auth/register", response_model=TokenResponse)
async def register(user: UserCreate, current_user: dict = Depends(require_admin)):
    existing = await db.users.find_one({"email": user.email.lower()})
    if existing:
        raise HTTPException(status_code=400, detail="El email ya está registrado")
    user_obj = User(**user.model_dump(exclude={"password"}))
    user_obj.email = user.email.lower()
    doc = user_obj.model_dump()
    doc['password_hash'] = hash_password(user.password)
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    await db.users.insert_one(doc)
    token = create_token(user_obj.id, user_obj.email, user_obj.role.value)
    return {"token": token, "user": {"id": user_obj.id, "email": user_obj.email, "nombre": user_obj.nombre, "apellidos": user_obj.apellidos, "role": user_obj.role.value}}

@router.post("/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin, request: Request):
    ip = request.client.host if request.client else "unknown"
    email = credentials.email.lower()
    
    logger.info(f"Login attempt for email: {email}")

    # Rate limit check
    _check_rate_limit(ip, email)

    user = await db.users.find_one({"email": email}, {"_id": 0})
    if not user:
        _record_failed_attempt(ip, email)
        from middleware.security import security_logger
        security_logger.log_failed_login(ip, email)
        remaining = _attempts_remaining(ip, email)
        raise HTTPException(
            status_code=401,
            detail=f"Email o contraseña incorrectos.{f' Te quedan {remaining} intento(s) antes del bloqueo temporal.' if remaining <= 2 else ''}"
        )
    if not user.get('activo', True):
        raise HTTPException(status_code=401, detail="Usuario desactivado. Contacta con el administrador.")
    
    stored_hash = user.get('password_hash', '')
    password_ok = verify_password(credentials.password, stored_hash)
    
    if not password_ok:
        _record_failed_attempt(ip, email)
        from middleware.security import security_logger
        security_logger.log_failed_login(ip, email)
        remaining = _attempts_remaining(ip, email)
        raise HTTPException(
            status_code=401,
            detail=f"Email o contraseña incorrectos.{f' Te quedan {remaining} intento(s) antes del bloqueo temporal.' if remaining <= 2 else ''}"
        )

    _clear_attempts(ip, email)
    
    # Log de seguridad
    from middleware.security import security_logger
    security_logger.log_successful_login(ip, email)
    
    token = create_token(user['id'], user['email'], user['role'])
    return {"token": token, "user": {"id": user['id'], "email": user['email'], "nombre": user['nombre'], "apellidos": user.get('apellidos', ''), "role": user['role'], "avatar_url": user.get('avatar_url')}}

@router.get("/auth/me")
async def get_me(user: dict = Depends(require_auth)):
    db_user = await db.users.find_one({"id": user['user_id']}, {"_id": 0, "password_hash": 0})
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return db_user

@router.get("/auth/users")
async def list_users(user: dict = Depends(require_admin)):
    users = await db.users.find({}, {"_id": 0, "password_hash": 0}).to_list(100)
    return users

# ==================== USUARIOS CRUD ====================

@router.get("/usuarios")
async def listar_usuarios(role: Optional[str] = None, activo: Optional[bool] = None, search: Optional[str] = None, user: dict = Depends(require_admin)):
    query = {}
    conditions = []
    if role:
        conditions.append({"role": role})
    if activo is not None:
        conditions.append({"activo": activo})
    if search:
        conditions.append({"$or": [{"nombre": {"$regex": search, "$options": "i"}}, {"apellidos": {"$regex": search, "$options": "i"}}, {"email": {"$regex": search, "$options": "i"}}, {"ficha.dni": {"$regex": search, "$options": "i"}}]})
    if conditions:
        query = {"$and": conditions} if len(conditions) > 1 else conditions[0]
    users = await db.users.find(query, {"_id": 0, "password_hash": 0}).to_list(500)
    return users

@router.get("/usuarios/{usuario_id}")
async def obtener_usuario(usuario_id: str, user: dict = Depends(require_admin)):
    usuario = await db.users.find_one({"id": usuario_id}, {"_id": 0, "password_hash": 0})
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return usuario

@router.post("/usuarios")
async def crear_usuario(usuario: UserCreate, user: dict = Depends(require_admin)):
    existing = await db.users.find_one({"email": usuario.email.lower()})
    if existing:
        raise HTTPException(status_code=400, detail="El email ya está registrado")
    
    # Si no se proporciona contraseña, generar una automática
    import secrets
    import string
    
    password_to_use = usuario.password
    password_generated = False
    
    if not password_to_use or password_to_use.strip() == "" or password_to_use == "auto":
        # Generar contraseña segura de 12 caracteres
        alphabet = string.ascii_letters + string.digits + "!@#$%"
        password_to_use = ''.join(secrets.choice(alphabet) for _ in range(12))
        password_generated = True
    
    user_obj = User(**usuario.model_dump(exclude={"password"}))
    user_obj.email = usuario.email.lower()
    doc = user_obj.model_dump()
    doc['password_hash'] = hash_password(password_to_use)
    doc['password_temporal'] = password_generated
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    await db.users.insert_one(doc)
    
    # Si se generó contraseña automática, enviar por email
    if password_generated:
        try:
            html_content = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="text-align: center; margin-bottom: 30px;">
                    <h1 style="color: #0055FF; margin: 0;">REVIX</h1>
                    <p style="color: #666; margin: 5px 0;">Sistema de Gestión</p>
                </div>
                
                <h2 style="color: #333;">¡Bienvenido/a al equipo!</h2>
                
                <p>Hola <strong>{usuario.nombre}</strong>,</p>
                
                <p>Se ha creado tu cuenta en el sistema de gestión de Revix. A continuación encontrarás tus credenciales de acceso:</p>
                
                <div style="background: #f5f5f5; border-radius: 8px; padding: 20px; margin: 20px 0;">
                    <p style="margin: 5px 0;"><strong>Email:</strong> {usuario.email.lower()}</p>
                    <p style="margin: 5px 0;"><strong>Contraseña temporal:</strong> <code style="background: #e0e0e0; padding: 2px 8px; border-radius: 4px;">{password_to_use}</code></p>
                </div>
                
                <p style="color: #e74c3c;"><strong>⚠️ Importante:</strong> Te recomendamos cambiar esta contraseña temporal en tu primer acceso.</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="https://revix.es/crm/login" style="background: #0055FF; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; font-weight: bold;">
                        Acceder al Sistema
                    </a>
                </div>
                
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                
                <p style="color: #999; font-size: 12px; text-align: center;">
                    Este email fue enviado automáticamente por el sistema de gestión de Revix.<br>
                    Si tienes alguna duda, contacta con tu administrador.
                </p>
            </div>
            """
            await send_email(usuario.email.lower(), "Bienvenido a Revix - Tus credenciales de acceso", html_content)
            logger.info(f"Email de bienvenida enviado a {usuario.email}")
        except Exception as e:
            logger.error(f"Error enviando email de bienvenida a {usuario.email}: {e}")
    
    doc.pop('password_hash', None)
    doc.pop('_id', None)
    return {**doc, "password_enviada": password_generated}

@router.put("/usuarios/{usuario_id}")
async def actualizar_usuario(usuario_id: str, data: UserUpdate, user: dict = Depends(require_admin)):
    existing = await db.users.find_one({"id": usuario_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    update_data = {}
    if data.email is not None:
        email_check = await db.users.find_one({"email": data.email.lower(), "id": {"$ne": usuario_id}})
        if email_check:
            raise HTTPException(status_code=400, detail="El email ya está en uso")
        update_data["email"] = data.email.lower()
    if data.nombre is not None:
        update_data["nombre"] = data.nombre
    if data.apellidos is not None:
        update_data["apellidos"] = data.apellidos
    if data.role is not None:
        update_data["role"] = data.role.value
    if data.activo is not None:
        update_data["activo"] = data.activo
    if data.avatar_url is not None:
        update_data["avatar_url"] = data.avatar_url
    if data.ficha is not None:
        update_data["ficha"] = data.ficha.model_dump()
    if data.info_laboral is not None:
        update_data["info_laboral"] = data.info_laboral.model_dump()
    if data.password is not None and data.password.strip():
        update_data["password_hash"] = hash_password(data.password)
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.users.update_one({"id": usuario_id}, {"$set": update_data})
    updated = await db.users.find_one({"id": usuario_id}, {"_id": 0, "password_hash": 0})
    return updated

@router.delete("/usuarios/{usuario_id}")
async def eliminar_usuario(usuario_id: str, user: dict = Depends(require_master)):
    if user['user_id'] == usuario_id:
        raise HTTPException(status_code=400, detail="No puedes eliminarte a ti mismo")
    result = await db.users.delete_one({"id": usuario_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return {"message": "Usuario eliminado"}

@router.patch("/usuarios/{usuario_id}/toggle-activo")
async def toggle_usuario_activo(usuario_id: str, user: dict = Depends(require_admin)):
    existing = await db.users.find_one({"id": usuario_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    nuevo_estado = not existing.get('activo', True)
    await db.users.update_one({"id": usuario_id}, {"$set": {"activo": nuevo_estado, "updated_at": datetime.now(timezone.utc).isoformat()}})
    return {"message": f"Usuario {'activado' if nuevo_estado else 'desactivado'}", "activo": nuevo_estado}


# ==================== GESTIÓN DE CONTRASEÑA ====================


class PasswordChangeRequest(BaseModel):
    nueva_password: str


@router.patch("/usuarios/{usuario_id}/cambiar-password")
async def cambiar_password_usuario(usuario_id: str, data: PasswordChangeRequest, user: dict = Depends(require_master)):
    """Master cambia directamente la contraseña de un usuario"""
    if len(data.nueva_password) < 6:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 6 caracteres")
    existing = await db.users.find_one({"id": usuario_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    await db.users.update_one(
        {"id": usuario_id},
        {"$set": {"password_hash": hash_password(data.nueva_password), "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    return {"message": f"Contraseña de {existing.get('nombre')} actualizada correctamente"}


@router.post("/usuarios/{usuario_id}/enviar-reset-password")
async def enviar_reset_password(usuario_id: str, user: dict = Depends(require_master)):
    """Genera una contraseña temporal y la envía por email al trabajador"""
    existing = await db.users.find_one({"id": usuario_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Generar contraseña temporal legible
    temp_password = secrets.token_urlsafe(10)

    # Actualizar en BD
    await db.users.update_one(
        {"id": usuario_id},
        {"$set": {
            "password_hash": hash_password(temp_password),
            "password_temporal": True,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )

    # Enviar email al trabajador
    email_enviado = False
    try:
        from services.email_service import send_email
        from config import FRONTEND_URL
        nombre = existing.get('nombre', 'Trabajador')
        send_email(
            to=existing['email'],
            subject="Restablecimiento de contraseña — Revix",
            titulo=f"Nueva contraseña temporal, {nombre}",
            contenido=f"""
                <p>El administrador ha generado una nueva contraseña temporal para tu cuenta.</p>
                <p><strong>Email:</strong> {existing['email']}</p>
                <p><strong>Contraseña temporal:</strong> <code style="background:#f1f5f9;padding:4px 10px;border-radius:4px;font-size:16px;letter-spacing:1px">{temp_password}</code></p>
                <p style="color:#64748b;font-size:13px;margin-top:16px;">Por seguridad, te recomendamos cambiar esta contraseña desde tu perfil en cuanto accedas al sistema.</p>
            """,
            link_url="https://revix.es/crm/login",
            link_text="Acceder al sistema"
        )
        email_enviado = True
    except Exception as e:
        logger.warning(f"No se pudo enviar email de reset: {e}")

    return {
        "message": "Contraseña temporal generada" + (" y enviada por email" if email_enviado else " (email no enviado)"),
        "email_enviado": email_enviado,
        "email_destino": existing['email']
    }


# ==================== RECUPERACIÓN DE CONTRASEÑA (usuarios web) ====================

class RecuperarPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    token: str
    nueva_password: str


@router.post("/auth/recuperar-password")
async def solicitar_recuperacion(data: RecuperarPasswordRequest, request: Request):
    """Envía email con link de recuperación. Siempre responde igual para no revelar si el email existe."""
    ip = request.client.host if request.client else "unknown"
    email = data.email.lower().strip()

    # Rate limit básico por IP para evitar enumeración de emails
    _email_attempts[f"recovery:{ip}"] = [t for t in _email_attempts.get(f"recovery:{ip}", []) if time.time() - t < 3600]
    if len(_email_attempts[f"recovery:{ip}"]) >= 10:
        raise HTTPException(status_code=429, detail="Demasiadas solicitudes. Espera un rato.")
    _email_attempts[f"recovery:{ip}"].append(time.time())

    user = await db.users.find_one({"email": email}, {"_id": 0})
    if user and user.get('activo', True):
        # Generar token seguro de 1 hora
        reset_token = secrets.token_urlsafe(32)
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

        await db.password_reset_tokens.insert_one({
            "token": reset_token,
            "email": email,
            "user_id": user['id'],
            "expires_at": expires_at,
            "used": False
        })

        try:
            from services.email_service import send_email
            from config import FRONTEND_URL
            reset_url = f"https://revix.es/crm/reset-password?token={reset_token}"
            send_email(
                to=email,
                subject="Recuperación de contraseña — Revix",
                titulo=f"Recupera el acceso, {user.get('nombre', '')}",
                contenido="""
                    <p>Hemos recibido una solicitud para restablecer la contraseña de tu cuenta.</p>
                    <p>Haz clic en el botón para crear una nueva contraseña. El enlace es válido durante <strong>1 hora</strong>.</p>
                    <p style="color:#64748b;font-size:13px;margin-top:16px;">Si no solicitaste este cambio, puedes ignorar este email con total seguridad.</p>
                """,
                link_url=reset_url,
                link_text="Restablecer contraseña"
            )
        except Exception as e:
            logger.warning(f"No se pudo enviar email de recuperación: {e}")

    # Siempre devolver la misma respuesta
    return {"message": "Si el email está registrado, recibirás un enlace de recuperación en breve."}


@router.post("/auth/reset-password")
async def reset_password(data: ResetPasswordRequest):
    """Aplica la nueva contraseña usando el token de recuperación."""
    if len(data.nueva_password) < 6:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 6 caracteres")

    record = await db.password_reset_tokens.find_one({"token": data.token}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=400, detail="Enlace inválido o ya utilizado")
    if record.get("used"):
        raise HTTPException(status_code=400, detail="Este enlace ya ha sido utilizado")

    # Verificar expiración
    expires_at = datetime.fromisoformat(record["expires_at"].replace("Z", "+00:00"))
    if datetime.now(timezone.utc) > expires_at:
        raise HTTPException(status_code=400, detail="El enlace ha caducado. Solicita uno nuevo.")

    # Actualizar contraseña
    await db.users.update_one(
        {"id": record["user_id"]},
        {"$set": {
            "password_hash": hash_password(data.nueva_password),
            "password_temporal": False,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )

    # Marcar token como usado
    await db.password_reset_tokens.update_one({"token": data.token}, {"$set": {"used": True}})

    return {"message": "Contraseña actualizada correctamente. Ya puedes iniciar sesión."}


@router.get("/auth/verificar-token-reset")
async def verificar_token_reset(token: str):
    """Verifica si un token de recuperación es válido (para el frontend)."""
    record = await db.password_reset_tokens.find_one({"token": token}, {"_id": 0})
    if not record or record.get("used"):
        return {"valido": False, "motivo": "Enlace inválido o ya utilizado"}
    expires_at = datetime.fromisoformat(record["expires_at"].replace("Z", "+00:00"))
    if datetime.now(timezone.utc) > expires_at:
        return {"valido": False, "motivo": "El enlace ha caducado"}
    return {"valido": True, "email": record["email"]}



# ==================== ENDPOINT DE EMERGENCIA ====================
# Este endpoint permite crear/resetear un usuario master cuando no hay acceso
# Protegido por una clave secreta que debe configurarse en .env

class EmergencyUserCreate(BaseModel):
    emergency_key: str
    email: str
    password: str
    nombre: str = "Master"
    apellidos: str = "Admin"

@router.post("/auth/emergency-access")
async def crear_usuario_emergencia(data: EmergencyUserCreate):
    """
    Endpoint de emergencia para crear/resetear usuario master.
    Requiere EMERGENCY_ACCESS_KEY en el .env del backend.
    
    IMPORTANTE: Desactivar o cambiar la clave después de usar.
    """
    import os
    
    # Verificar clave de emergencia
    emergency_key = os.environ.get("EMERGENCY_ACCESS_KEY")
    if not emergency_key:
        raise HTTPException(status_code=403, detail="Acceso de emergencia no configurado")
    
    if data.emergency_key != emergency_key:
        logger.warning(f"Intento de acceso de emergencia fallido para: {data.email}")
        raise HTTPException(status_code=403, detail="Clave de emergencia incorrecta")
    
    # Hashear la contraseña
    password_hash = hash_password(data.password)
    
    # Verificar si el usuario ya existe
    existing_user = await db.users.find_one({"email": data.email})
    
    if existing_user:
        # Actualizar contraseña del usuario existente
        await db.users.update_one(
            {"email": data.email},
            {
                "$set": {
                    "password_hash": password_hash,
                    "activo": True,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        logger.info(f"Contraseña reseteada por emergencia para: {data.email}")
        return {
            "message": "Contraseña actualizada correctamente",
            "email": data.email,
            "action": "password_reset"
        }
    else:
        # Crear nuevo usuario master
        import uuid
        new_user = {
            "id": str(uuid.uuid4()),
            "email": data.email,
            "password_hash": password_hash,
            "nombre": data.nombre,
            "apellidos": data.apellidos,
            "role": "master",
            "activo": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await db.users.insert_one(new_user)
        logger.info(f"Usuario master creado por emergencia: {data.email}")
        return {
            "message": "Usuario master creado correctamente",
            "email": data.email,
            "role": "master",
            "action": "user_created"
        }
