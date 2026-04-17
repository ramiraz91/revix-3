"""
Rutas de Configuración del sistema y Empresa.
Extraído de server.py durante refactorización.
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from datetime import datetime, timezone
import os
import uuid
import aiofiles

from config import db, UPLOAD_DIR, logger
import config as cfg
from auth import require_auth, require_admin, require_master
from models import ConfiguracionNotificaciones, EmpresaConfig, TextosLegales

router = APIRouter(tags=["configuracion"])

@router.get("/configuracion/notificaciones")
async def obtener_config_notificaciones(user: dict = Depends(require_master)):
    return {"twilio_account_sid": cfg.TWILIO_ACCOUNT_SID or "", "twilio_phone_number": cfg.TWILIO_PHONE_NUMBER or "", "sendgrid_from_email": cfg.SENDGRID_FROM_EMAIL or "", "twilio_configurado": bool(cfg.twilio_client), "sendgrid_configurado": bool(cfg.sendgrid_client)}

@router.post("/configuracion/notificaciones")
async def guardar_config_notificaciones(config: ConfiguracionNotificaciones, user: dict = Depends(require_master)):
    if config.twilio_account_sid and config.twilio_auth_token:
        try:
            from twilio.rest import Client as TwilioClient
            cfg.twilio_client = TwilioClient(config.twilio_account_sid, config.twilio_auth_token)
            cfg.TWILIO_ACCOUNT_SID = config.twilio_account_sid
            cfg.TWILIO_AUTH_TOKEN = config.twilio_auth_token
            if config.twilio_phone_number:
                cfg.TWILIO_PHONE_NUMBER = config.twilio_phone_number
        except Exception as e:
            logger.error(f"Error configurando Twilio: {e}")
    if config.sendgrid_api_key:
        try:
            from sendgrid import SendGridAPIClient
            cfg.sendgrid_client = SendGridAPIClient(config.sendgrid_api_key)
            cfg.SENDGRID_API_KEY = config.sendgrid_api_key
            if config.sendgrid_from_email:
                cfg.SENDGRID_FROM_EMAIL = config.sendgrid_from_email
        except Exception as e:
            logger.error(f"Error configurando SendGrid: {e}")
    return {"message": "Configuración de notificaciones actualizada"}

# ==================== EMPRESA Y CONFIGURACIÓN ====================

@router.get("/configuracion/empresa")
async def obtener_config_empresa(user: dict = Depends(require_admin)):
    config = await db.configuracion.find_one({"tipo": "empresa"}, {"_id": 0})
    if not config:
        return EmpresaConfig().model_dump()
    return config.get("datos", EmpresaConfig().model_dump())

@router.get("/configuracion/empresa/publica")
async def obtener_config_empresa_publica():
    config = await db.configuracion.find_one({"tipo": "empresa"}, {"_id": 0})
    datos = config.get("datos", EmpresaConfig().model_dump()) if config else EmpresaConfig().model_dump()
    return {"nombre": datos.get("nombre", "Mi Empresa"), "logo": datos.get("logo", {}), "logo_url": datos.get("logo_url"), "textos_legales": datos.get("textos_legales", TextosLegales().model_dump()), "telefono": datos.get("telefono"), "email": datos.get("email"), "web": datos.get("web")}

@router.post("/configuracion/empresa/logo")
async def subir_logo_empresa(file: UploadFile = File(...), user: dict = Depends(require_admin)):
    allowed_types = ['image/png', 'image/jpeg', 'image/jpg', 'image/webp', 'image/svg+xml']
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Formato no soportado. Use PNG, JPEG, WebP o SVG.")
    file_ext = file.filename.split('.')[-1] if '.' in file.filename else 'png'
    file_name = f"logo_empresa_{str(uuid.uuid4())[:8]}.{file_ext}"
    file_path = UPLOAD_DIR / file_name
    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        await f.write(content)
    config = await db.configuracion.find_one({"tipo": "empresa"}, {"_id": 0})
    datos = config.get("datos", EmpresaConfig().model_dump()) if config else EmpresaConfig().model_dump()
    if "logo" not in datos:
        datos["logo"] = {}
    datos["logo"]["url"] = file_name
    datos["logo_url"] = file_name
    await db.configuracion.update_one({"tipo": "empresa"}, {"$set": {"tipo": "empresa", "datos": datos, "updated_at": datetime.now(timezone.utc).isoformat(), "updated_by": user.get('email', 'sistema')}}, upsert=True)
    return {"message": "Logo subido correctamente", "file_name": file_name}

@router.post("/configuracion/empresa")
async def guardar_config_empresa(config: EmpresaConfig, user: dict = Depends(require_admin)):
    await db.configuracion.update_one({"tipo": "empresa"}, {"$set": {"tipo": "empresa", "datos": config.model_dump(), "updated_at": datetime.now(timezone.utc).isoformat(), "updated_by": user.get('email', 'sistema')}}, upsert=True)
    return {"message": "Configuración de empresa guardada", "datos": config.model_dump()}

