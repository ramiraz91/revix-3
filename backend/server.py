"""
CRM/ERP Mobile Repair Service - Main Server
Refactored: Models, Auth, Config and Helpers extracted to separate modules.
Routes split into: auth_routes, data_routes, and remaining routes in this file.
"""
from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone, timedelta
import uuid
import aiofiles
import zipfile
import io
import csv
import math
import random
import httpx
import logging
import os
from bson import ObjectId
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# Import from refactored modules
from config import db, UPLOAD_DIR, EMERGENT_LLM_KEY, FRONTEND_URL, logger
import config as cfg
from auth import require_auth, require_admin, require_master, hash_password
from models import (
    OrderStatus, UserRole, OrdenTrabajo, OrdenTrabajoCreate, MaterialOrden,
    Notificacion, MensajeOrdenCreate, EventoCalendario, TipoEvento,
    EmpresaConfig, TextosLegales, SeguimientoRequest,
    ConfiguracionNotificaciones, DiagnosticoRequest, IARequest, IAChatRequest,
    AsignarOrdenRequest, Resto, PiezaResto
)
from helpers import (
    generate_qr_code, generate_barcode, send_order_notification,
    send_sms, send_email, STATUS_MESSAGES, STATUS_EMOJIS
)

# Import route modules
from routes.auth_routes import router as auth_router
from routes.data_routes import router as data_router
from routes.agent_routes import router as agent_router
from routes.ordenes_routes import router as ordenes_router
from routes.admin_routes import router as admin_router
from routes.websocket_routes import router as ws_router
from routes.insurama_routes import router as insurama_router
from routes.insurama_ia_routes import router as insurama_ia_router
from routes.logistica_routes import router as logistica_router
from routes.contabilidad_routes import router as contabilidad_router
from routes.kits_routes import router as kits_router
from routes.inteligencia_precios_routes import router as inteligencia_router
from routes.liquidaciones_routes import router as liquidaciones_router
from routes.nuevas_ordenes_routes import router as nuevas_ordenes_router
from routes.web_publica_routes import router as web_publica_router
from routes.iso_routes import router as iso_router
from routes.peticiones_routes import router as peticiones_router
from routes.faqs_routes import router as faqs_router
from routes.apple_manuals_routes import router as apple_manuals_router
from routes.compras_routes import router as compras_router
from modules.gls.routes import router as gls_router
from routes.finanzas_routes import router as finanzas_router
from routes.inventario_mejorado_routes import router as inventario_mejorado_router
from routes.ordenes_mejorado_routes import router as ordenes_mejorado_router
from routes.print_routes import router as print_router
from routes.dashboard_routes import router as dashboard_router
from routes.master_routes import router as master_router
from routes.ia_routes import router as ia_router
from routes.restos_routes import router as restos_router
from routes.calendario_routes import router as calendario_router
from routes.notificaciones_routes import router as notificaciones_router
from routes.config_empresa_routes import router as config_empresa_router

# ==================== APP SETUP ====================
app = FastAPI(title="Mobile Repair CRM/ERP API")

# Middleware para forzar HTTPS en redirects
from starlette.middleware.base import BaseHTTPMiddleware

class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        # Si es un redirect (307, 308), forzar HTTPS en la Location
        if response.status_code in (307, 308) and "location" in response.headers:
            location = response.headers["location"]
            if location.startswith("http://"):
                response.headers["location"] = location.replace("http://", "https://", 1)
        return response

app.add_middleware(HTTPSRedirectMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        o.strip() for o in os.environ.get(
            "CORS_ORIGINS",
            "https://revix.es,https://www.revix.es,http://localhost:3000,http://127.0.0.1:3000"
        ).split(",") if o.strip()
    ] + ([os.environ.get("REACT_APP_BACKEND_URL")] if os.environ.get("REACT_APP_BACKEND_URL") else []),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Agent-Key"],
)

# Security headers middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "frame-ancestors 'none'"
        return response

app.add_middleware(SecurityHeadersMiddleware)

# Rate limiting middleware
from middleware.security import RateLimitMiddleware
app.add_middleware(RateLimitMiddleware)

# Performance monitoring middleware
from middleware.performance import PerformanceMiddleware, metrics, query_profiler
app.add_middleware(PerformanceMiddleware)

# Main API router
api_router = APIRouter(prefix="/api")

@api_router.get("/health")
async def api_health_check():
    """Health check endpoint via /api/health"""
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}

# Include extracted route modules
api_router.include_router(auth_router)
api_router.include_router(data_router)
api_router.include_router(agent_router)
api_router.include_router(ordenes_router)
api_router.include_router(admin_router)
api_router.include_router(insurama_router)
api_router.include_router(insurama_ia_router)
api_router.include_router(logistica_router)
api_router.include_router(contabilidad_router)
api_router.include_router(kits_router)
api_router.include_router(inteligencia_router)
api_router.include_router(liquidaciones_router)
api_router.include_router(nuevas_ordenes_router)
api_router.include_router(web_publica_router)
api_router.include_router(iso_router)
api_router.include_router(peticiones_router)
api_router.include_router(faqs_router)
api_router.include_router(compras_router)
api_router.include_router(finanzas_router)
api_router.include_router(gls_router)
api_router.include_router(inventario_mejorado_router)
api_router.include_router(ordenes_mejorado_router)
api_router.include_router(print_router)
api_router.include_router(dashboard_router)
api_router.include_router(master_router)
api_router.include_router(ia_router)
api_router.include_router(restos_router)
api_router.include_router(calendario_router)
api_router.include_router(notificaciones_router)
api_router.include_router(config_empresa_router)
app.include_router(apple_manuals_router)  # No prefix, ya tiene /api/apple-manuals

@app.get("/api/debug-connection")
async def debug_connection_public():
    """Debug público: muestra info básica de conexión a BD (sin datos sensibles)."""
    import os
    result = {
        "db_name_configured": os.environ.get('DB_NAME', 'NOT SET'),
        "mongo_host": "hidden",
    }
    try:
        mongo_url = os.environ.get('MONGO_URL', '')
        if '@' in mongo_url:
            result["mongo_host"] = mongo_url.split('@')[-1].split('/')[0].split('?')[0]
        if '/production' in mongo_url:
            result["has_production_in_url"] = True
        else:
            result["has_production_in_url"] = False
    except:
        pass
    try:
        from config import db as current_db
        result["db_actual_name"] = current_db.name
        count = await current_db.users.count_documents({})
        result["users_count"] = count
        result["db_connected"] = True
        # Listar emails de usuarios (sin datos sensibles)
        users = []
        async for u in current_db.users.find({}, {"_id": 0, "email": 1, "role": 1}):
            users.append(f"{u.get('email')} ({u.get('role')})")
        result["users"] = users
    except Exception as e:
        result["db_connected"] = False
        result["db_error"] = str(e)[:200]
    return result

@app.post("/api/debug-login")
async def debug_login_test(data: dict):
    """Debug: prueba el login y muestra diagnóstico detallado."""
    import bcrypt
    from config import db as current_db
    
    email = data.get("email", "").lower().strip()
    password = data.get("password", "")
    
    result = {
        "email_received": email,
        "password_length": len(password),
    }
    
    # Buscar usuario
    user = await current_db.users.find_one({"email": email}, {"_id": 0})
    
    if not user:
        result["user_found"] = False
        result["error"] = "Usuario no encontrado"
        return result
    
    result["user_found"] = True
    result["user_role"] = user.get("role")
    result["user_activo"] = user.get("activo")
    result["has_password_hash"] = bool(user.get("password_hash"))
    result["hash_prefix"] = user.get("password_hash", "")[:20] + "..." if user.get("password_hash") else "N/A"
    
    # Verificar contraseña
    try:
        stored_hash = user.get("password_hash", "")
        password_ok = bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8'))
        result["password_valid"] = password_ok
    except Exception as e:
        result["password_valid"] = False
        result["bcrypt_error"] = str(e)[:100]
    
    return result

@app.get("/api/emergency/debug-db")
async def emergency_debug_db(secret: str = ""):
    """Debug: muestra configuracion de BD."""
    import os, subprocess
    key = os.environ.get('EMERGENCY_ACCESS_KEY', '')
    if not secret or secret != key:
        raise HTTPException(403, "Clave incorrecta")
    mongo_url = os.environ.get('MONGO_URL', 'NOT SET')
    db_name_env = os.environ.get('DB_NAME', 'NOT SET')
    host = mongo_url.split('@')[-1].split('/')[0] if '@' in mongo_url else mongo_url[:60]
    user = mongo_url.split('://')[1].split(':')[0] if '://' in mongo_url else 'N/A'
    env_file_mongo = "NOT IN FILE"
    env_file_db = "NOT IN FILE"
    try:
        for p in ['/app/backend/.env', '.env']:
            try:
                with open(p) as f:
                    for line in f:
                        if line.startswith('MONGO_URL'):
                            env_file_mongo = line.strip()[:80]
                        if line.startswith('DB_NAME'):
                            env_file_db = line.strip()[:80]
                break
            except:
                pass
    except:
        pass
    result = {
        "mongo_host": host,
        "mongo_user": user,
        "db_name_env": db_name_env,
        "env_file_mongo": env_file_mongo,
        "env_file_db": env_file_db,
    }
    try:
        from config import db as current_db
        result["db_actual"] = current_db.name
        count = await current_db.users.count_documents({})
        result["users_count"] = count
        result["db_connected"] = True
    except Exception as e:
        result["db_connected"] = False
        result["db_error"] = str(e)[:300]
    return result

@app.get("/health")
async def root_health_check():
    """Health check endpoint for Emergent deployment (no auth, root level)"""
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}

@app.get("/api/emergency/reset-password")
async def emergency_reset_password(secret: str = "", email: str = "", new_password: str = ""):
    """Endpoint de emergencia para resetear contraseña. Requiere EMERGENCY_ACCESS_KEY."""
    import os, bcrypt
    key = os.environ.get('EMERGENCY_ACCESS_KEY', '')
    if not secret or secret != key:
        raise HTTPException(403, "Clave de emergencia incorrecta")
    if not email or not new_password:
        raise HTTPException(400, "email y new_password son obligatorios")
    user = await db.users.find_one({"email": email}, {"_id": 0, "id": 1})
    if not user:
        return {"error": f"Usuario {email} no encontrado"}
    hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    await db.users.update_one({"email": email}, {"$set": {"password_hash": hashed, "activo": True}})
    return {"ok": True, "email": email}

@app.get("/api/emergency/list-users")
async def emergency_list_users(secret: str = ""):
    """Lista usuarios. Requiere EMERGENCY_ACCESS_KEY."""
    import os
    key = os.environ.get('EMERGENCY_ACCESS_KEY', '')
    if not secret or secret != key:
        raise HTTPException(403, "Clave de emergencia incorrecta")
    users = await db.users.find({}, {"_id": 0, "email": 1, "role": 1, "nombre": 1, "activo": 1}).to_list(50)
    return {"users": users}

@app.get("/api/emergency/db-diagnostic")
async def emergency_db_diagnostic(secret: str = ""):
    """Diagnostico: muestra DB actual y busca datos en otras BDs del mismo cluster."""
    import os
    from motor.motor_asyncio import AsyncIOMotorClient as TempClient
    key = os.environ.get('EMERGENCY_ACCESS_KEY', '')
    if not secret or secret != key:
        raise HTTPException(403, "Clave de emergencia incorrecta")
    
    mongo_url = os.environ.get('MONGO_URL', '')
    current_db = os.environ.get('DB_NAME', '')
    
    result = {
        "current_mongo_host": mongo_url.split('@')[-1].split('/')[0] if '@' in mongo_url else mongo_url[:50],
        "current_db_name": current_db,
        "current_db_users": await db.users.count_documents({}),
        "current_db_ordenes": await db.ordenes.count_documents({}),
        "current_db_clientes": await db.clientes.count_documents({}),
        "other_databases": []
    }
    
    try:
        temp_client = TempClient(mongo_url, serverSelectionTimeoutMS=15000)
        db_names = await temp_client.list_database_names()
        for name in [d for d in db_names if d not in ('admin', 'local', 'config')]:
            temp_db = temp_client[name]
            cols = await temp_db.list_collection_names()
            info = {"name": name, "collections": len(cols)}
            for col in ['users', 'ordenes', 'clientes', 'pre_registros', 'repuestos']:
                if col in cols:
                    info[col] = await temp_db[col].count_documents({})
            if any(info.get(c, 0) > 0 for c in ['users', 'ordenes', 'clientes', 'pre_registros']):
                result["other_databases"].append(info)
        temp_client.close()
    except Exception as e:
        result["error_listing_dbs"] = str(e)[:300]
    
    return result

@app.get("/api/emergency/switch-db")
async def emergency_switch_db(secret: str = "", target_db: str = ""):
    """Cambia la BD activa en caliente (temporal hasta reinicio)."""
    import os
    key = os.environ.get('EMERGENCY_ACCESS_KEY', '')
    if not secret or secret != key:
        raise HTTPException(403, "Clave de emergencia incorrecta")
    if not target_db:
        raise HTTPException(400, "target_db es obligatorio")
    from config import client as mongo_client
    import config
    config.db = mongo_client[target_db]
    new_users = await config.db.users.count_documents({})
    new_ordenes = await config.db.ordenes.count_documents({})
    new_clientes = await config.db.clientes.count_documents({})
    return {"switched_to": target_db, "users": new_users, "ordenes": new_ordenes, "clientes": new_clientes}


@app.post("/api/emergency/scan-cluster")
async def emergency_scan_cluster(data: dict, secret: str = ""):
    """Escanea un cluster MongoDB específico para encontrar bases de datos con órdenes."""
    import os
    from motor.motor_asyncio import AsyncIOMotorClient as TempClient
    key = os.environ.get('EMERGENCY_ACCESS_KEY', '')
    if not secret or secret != key:
        raise HTTPException(403, "Clave de emergencia incorrecta")
    
    target_url = data.get("mongo_url", "")
    if not target_url:
        raise HTTPException(400, "mongo_url es obligatorio en el body")
    
    result = {
        "cluster_host": target_url.split('@')[-1].split('/')[0] if '@' in target_url else target_url[:50],
        "databases_found": [],
        "database_with_most_ordenes": None,
        "max_ordenes": 0
    }
    
    try:
        temp_client = TempClient(target_url, serverSelectionTimeoutMS=20000)
        db_names = await temp_client.list_database_names()
        
        for name in [d for d in db_names if d not in ('admin', 'local', 'config')]:
            temp_db = temp_client[name]
            cols = await temp_db.list_collection_names()
            info = {"name": name, "collections": len(cols), "collection_names": cols[:10]}
            
            for col in ['users', 'ordenes', 'clientes', 'pre_registros', 'repuestos']:
                if col in cols:
                    info[col] = await temp_db[col].count_documents({})
            
            result["databases_found"].append(info)
            
            ordenes_count = info.get('ordenes', 0)
            if ordenes_count > result["max_ordenes"]:
                result["max_ordenes"] = ordenes_count
                result["database_with_most_ordenes"] = name
        
        temp_client.close()
        
    except Exception as e:
        result["error"] = str(e)[:500]
    
    return result

# ==================== STATIC FILES ====================

@api_router.get("/uploads/{file_name}")
async def get_upload(file_name: str):
    file_path = UPLOAD_DIR / file_name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return FileResponse(str(file_path))

@api_router.post("/uploads")
async def upload_file(file: UploadFile = File(...)):
    file_name = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = UPLOAD_DIR / file_name
    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        await f.write(content)
    return {"url": f"/api/uploads/{file_name}", "filename": file_name}

# ==================== ROOT ====================

@api_router.get("/")
async def root():
    return {"message": "Mobile Repair CRM/ERP API", "version": "2.0"}

# ── Budget Simulation (Presupuesto) ─────────────────────

class PresupuestoRequest(BaseModel):
    codigo_siniestro: str
    precio: float
    notas: str = ""

@api_router.post("/agente/simular-presupuesto/{codigo}")
async def simular_solicitud_presupuesto(codigo: str, user: dict = Depends(require_master)):
    """
    Simulate a new service request from the provider:
    1. Fetch data from Sumbroker API
    2. Create a pre-registro with all provider data
    3. Set status to 'pendiente_presupuesto'
    """
    from agent.processor import scrape_portal_data
    results = {"codigo": codigo, "steps": []}

    # Step 1: Fetch portal data
    datos_portal = await scrape_portal_data(codigo)
    if not datos_portal:
        raise HTTPException(status_code=404, detail=f"No se encontraron datos en el portal para {codigo}")
    results["steps"].append({"step": 1, "action": "datos_portal_obtenidos", "device": f"{datos_portal.get('device_brand', '')} {datos_portal.get('device_model', '')}".strip(), "client": datos_portal.get("client_full_name"), "damage": datos_portal.get("damage_type_text")})

    # Step 2: Create/update pre-registro
    existing = await db.pre_registros.find_one({"codigo_siniestro": codigo}, {"_id": 0})
    if existing:
        await db.pre_registros.update_one(
            {"codigo_siniestro": codigo},
            {"$set": {"estado": "pendiente_presupuesto", "datos_portal": datos_portal, "updated_at": datetime.now(timezone.utc).isoformat()}}
        )
        pre_id = existing["id"]
    else:
        from models import PreRegistro
        pre = PreRegistro(
            codigo_siniestro=codigo,
            email_from=datos_portal.get("client_email", ""),
            email_subject=f"Nuevo Siniestro {codigo}: {datos_portal.get('damage_type_text', '')}",
            estado="pendiente_presupuesto",
        )
        doc = pre.model_dump()
        doc["created_at"] = doc["created_at"].isoformat()
        doc["updated_at"] = doc["updated_at"].isoformat()
        doc["datos_portal"] = datos_portal
        doc["cliente_nombre"] = datos_portal.get("client_full_name", "")
        doc["cliente_telefono"] = datos_portal.get("client_phone", "")
        doc["cliente_email"] = datos_portal.get("client_email", "")
        doc["dispositivo"] = f"{datos_portal.get('device_brand', '')} {datos_portal.get('device_model', '')}".strip()
        doc["tipo_dano"] = datos_portal.get("damage_type_text", "")
        await db.pre_registros.insert_one(doc)
        pre_id = pre.id
    results["steps"].append({"step": 2, "action": "pre_registro_creado", "pre_id": pre_id, "estado": "pendiente_presupuesto"})

    # Step 3: Create notification for admin
    notif = Notificacion(
        tipo="solicitud_presupuesto",
        mensaje=f"Solicitud de presupuesto para siniestro {codigo} — {datos_portal.get('damage_type_text', '')} ({datos_portal.get('device_brand', '')} {datos_portal.get('device_model', '')})",
        orden_id="",
        severidad="warning",
    )
    notif_doc = notif.model_dump()
    notif_doc["created_at"] = notif_doc["created_at"].isoformat()
    notif_doc["pre_registro_id"] = pre_id
    notif_doc["codigo_siniestro"] = codigo
    await db.notificaciones.insert_one(notif_doc)
    results["steps"].append({"step": 3, "action": "notificacion_presupuesto_creada"})

    results["success"] = True
    results["message"] = f"Solicitud de presupuesto creada para {codigo}. Pre-registro en estado 'pendiente_presupuesto'."
    return results

@api_router.post("/agente/emitir-presupuesto")
async def emitir_presupuesto(data: PresupuestoRequest, user: dict = Depends(require_master)):
    """
    Register the budget response for a pre-registro.
    The actual budget is submitted via the Sumbroker web portal (API),
    NOT sent by email. This endpoint only records the response internally
    and updates the pre-registro state.
    """
    codigo = data.codigo_siniestro
    pre_reg = await db.pre_registros.find_one({"codigo_siniestro": codigo}, {"_id": 0})
    if not pre_reg:
        raise HTTPException(status_code=404, detail=f"Pre-registro no encontrado para {codigo}")

    results = {"codigo": codigo, "steps": []}

    # Step 1: Update pre-registro with budget data (internal record)
    await db.pre_registros.update_one(
        {"codigo_siniestro": codigo},
        {"$set": {
            "estado": "presupuesto_emitido",
            "presupuesto_precio": data.precio,
            "presupuesto_notas": data.notas,
            "presupuesto_emitido_por": user.get("email", "sistema"),
            "presupuesto_fecha": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }}
    )
    results["steps"].append({"step": 1, "action": "presupuesto_registrado", "precio": data.precio})

    # Step 2: Create internal notification for tracking
    notif = Notificacion(
        tipo="presupuesto_emitido",
        mensaje=f"Presupuesto emitido para {codigo}: {data.precio}€ — Pendiente respuesta del proveedor.",
        orden_id="",
        severidad="info",
    )
    notif_doc = notif.model_dump()
    notif_doc["created_at"] = notif_doc["created_at"].isoformat()
    notif_doc["codigo_siniestro"] = codigo
    await db.notificaciones.insert_one(notif_doc)
    results["steps"].append({"step": 2, "action": "notificacion_interna_creada"})

    # Step 3: Log
    from agent.processor import log_agent
    await log_agent("presupuesto_emitido", "ok", "info", codigo=codigo,
                    detalles={"precio": data.precio, "nota": "Respuesta enviada vía portal web proveedor"})

    results["success"] = True
    results["message"] = f"Presupuesto de {data.precio}€ registrado para {codigo}. Pendiente respuesta del proveedor vía email."
    return results







# ==================== SEGUIMIENTO PÚBLICO ====================

@api_router.post("/seguimiento/verificar")
async def verificar_seguimiento(request: SeguimientoRequest, request_http: Request):
    orden = await db.ordenes.find_one({"token_seguimiento": request.token.upper()}, {"_id": 0})
    if not orden:
        raise HTTPException(status_code=404, detail="Código de seguimiento no válido")
    cliente = await db.clientes.find_one({"id": orden['cliente_id']}, {"_id": 0})
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    telefono_clean = ''.join(filter(str.isdigit, request.telefono))
    cliente_telefono_clean = ''.join(filter(str.isdigit, cliente.get('telefono', '')))
    if telefono_clean[-6:] != cliente_telefono_clean[-6:]:
        raise HTTPException(status_code=401, detail="Los últimos 6 dígitos del teléfono no coinciden")
    config_empresa = await db.configuracion.find_one({"tipo": "empresa"}, {"_id": 0})
    textos = config_empresa.get("datos", {}).get("textos_legales", TextosLegales().model_dump()) if config_empresa else TextosLegales().model_dump()

    consentimiento_registrado = False
    # Check if client already accepted legal texts for this token
    consentimiento_previo = await db.consentimientos_seguimiento.find_one(
        {"token": request.token.upper(), "acepta_condiciones": True, "acepta_rgpd": True},
        {"_id": 0}
    )
    ya_acepto = bool(consentimiento_previo)
    
    if request.acepta_condiciones or request.acepta_rgpd:
        now = datetime.now(timezone.utc)
        telefono_mask = f"***{telefono_clean[-6:]}" if telefono_clean else "***"
        consentimiento = {
            "id": str(uuid.uuid4()),
            "orden_id": orden.get("id"),
            "token": request.token.upper(),
            "telefono_mask": telefono_mask,
            "acepta_condiciones": bool(request.acepta_condiciones),
            "acepta_rgpd": bool(request.acepta_rgpd),
            "ip": request_http.client.host if request_http.client else None,
            "user_agent": request_http.headers.get("user-agent"),
            "created_at": now.isoformat(),
        }
        await db.consentimientos_seguimiento.insert_one(consentimiento)
        await db.ordenes.update_one(
            {"id": orden.get("id")},
            {"$set": {"consentimiento_legal": True, "ultimo_consentimiento_seguimiento": consentimiento, "updated_at": now.isoformat()}},
        )
        consentimiento_registrado = True
        ya_acepto = True

    # Extraer fechas del historial de estados
    fechas = {
        "creacion": orden.get('created_at'),
    }
    for hist in orden.get('historial_estados', []):
        estado = hist.get('estado')
        fecha = hist.get('fecha')
        if estado == 'recibida':
            fechas['recibida'] = fecha
        elif estado == 'en_taller':
            fechas['inicio_reparacion'] = fecha
        elif estado == 'reparado':
            fechas['fin_reparacion'] = fecha
        elif estado == 'enviado':
            fechas['enviado'] = fecha

    # Fetch GLS logistics data for client view
    logistics_data = {"recogida": None, "envio": None}
    try:
        gls_shipments_cursor = db.gls_shipments.find(
            {"entidad_id": orden.get("id")},
            {"_id": 0, "raw_request": 0, "raw_response": 0, "tracking_json": 0, "label_base64": 0}
        ).sort("created_at", -1)
        gls_shipments = await gls_shipments_cursor.to_list(20)
        for s in gls_shipments:
            tipo = s.get("tipo", "")
            slot = "recogida" if tipo == "recogida" else "envio"
            if logistics_data[slot] is None:
                logistics_data[slot] = {
                    "codbarras": s.get("gls_codbarras", ""),
                    "tracking_url": s.get("tracking_url", "https://www.gls-spain.es/es/ayuda/seguimiento-de-envio/"),
                    "tracking_source": s.get("tracking_source", "fallback"),
                    "estado": s.get("estado_interno", ""),
                    "estado_texto": s.get("estado_gls_texto", ""),
                    "es_final": s.get("es_final", False),
                    "fecha_creacion": s.get("created_at", ""),
                    "entrega_receptor": s.get("entrega_receptor"),
                    "entrega_fecha": s.get("entrega_fecha"),
                    "incidencia_texto": s.get("incidencia_texto"),
                }
    except Exception:
        pass

    # Consolidar todas las fuentes de fotos en un solo array
    # Normalizar: las fotos pueden ser strings (URLs) o objetos {src, tipo}
    todas_las_fotos = []
    fotos_vistas = set()  # Para tracking de duplicados por URL
    
    for campo_fotos in ['fotos', 'evidencias', 'fotos_antes', 'fotos_despues', 'fotos_portal']:
        fotos_campo = orden.get(campo_fotos, [])
        if isinstance(fotos_campo, list):
            for foto in fotos_campo:
                # Extraer la URL real para comparar duplicados
                if isinstance(foto, dict):
                    url = foto.get('src', '')
                else:
                    url = foto if isinstance(foto, str) else ''
                
                if url and url not in fotos_vistas:
                    fotos_vistas.add(url)
                    todas_las_fotos.append(foto)
    
    fotos_unicas = todas_las_fotos

    return {
        "orden": {
            "numero_orden": orden['numero_orden'],
            "estado": orden['estado'],
            "dispositivo": orden['dispositivo'],
            "created_at": orden.get('created_at'),
            "historial_estados": orden.get('historial_estados', []),
            "agencia_envio": orden.get('agencia_envio'),
            "codigo_recogida_entrada": orden.get('codigo_recogida_entrada'),
            "codigo_recogida_salida": orden.get('codigo_recogida_salida'),
            "codigo_seguimiento_salida": orden.get('codigo_seguimiento_salida') or orden.get('codigo_recogida_salida'),
            "diagnostico_tecnico": orden.get('diagnostico_tecnico'),
            "numero_autorizacion": orden.get('numero_autorizacion'),
            "evidencias": orden.get('evidencias', []),
            "fotos": fotos_unicas,
            "descripcion_problema": orden.get('descripcion_problema', ''),
            "fechas": fechas,
            "cliente": {
                "nombre": cliente.get('nombre', ''),
            },
            "logistics": logistics_data,
        },
        "textos_legales": textos,
        "consentimiento_registrado": consentimiento_registrado,
        "ya_acepto_legal": ya_acepto,
    }

class RecuperarCredencialesRequest(BaseModel):
    email: Optional[str] = None
    dni: Optional[str] = None
    telefono: Optional[str] = None
    codigo_postal: Optional[str] = None

@api_router.post("/seguimiento/recuperar")
async def recuperar_credenciales_seguimiento(request: RecuperarCredencialesRequest):
    """Recuperar credenciales de seguimiento verificando datos del cliente."""
    if not request.email and not request.telefono:
        raise HTTPException(status_code=400, detail="Debes proporcionar email o teléfono")
    
    # Build query to find client
    query = {"$and": []}
    if request.email:
        query["$and"].append({"email": {"$regex": f"^{request.email.strip()}$", "$options": "i"}})
    if request.telefono:
        tel_clean = ''.join(filter(str.isdigit, request.telefono))
        if len(tel_clean) >= 6:
            query["$and"].append({"telefono": {"$regex": tel_clean[-6:]}})
    if request.dni:
        query["$and"].append({"dni": {"$regex": f"^{request.dni.strip()}$", "$options": "i"}})
    
    if not query["$and"]:
        raise HTTPException(status_code=400, detail="Datos insuficientes")
    
    cliente = await db.clientes.find_one(query, {"_id": 0})
    if not cliente:
        raise HTTPException(status_code=404, detail="No se encontraron datos. Verifica tu información.")
    
    # Find orders for this client
    ordenes = await db.ordenes.find(
        {"cliente_id": cliente.get("id"), "token_seguimiento": {"$exists": True, "$ne": ""}},
        {"_id": 0, "numero_orden": 1, "token_seguimiento": 1, "estado": 1, "dispositivo": 1}
    ).sort("created_at", -1).to_list(10)
    
    if not ordenes:
        raise HTTPException(status_code=404, detail="No se encontraron órdenes activas para estos datos")
    
    # Send email with tracking credentials
    if cliente.get("email"):
        from services.email_service import send_email as smtp_send
        
        ordenes_html = ""
        for o in ordenes:
            link = f"https://revix.es/consulta?codigo={o.get('token_seguimiento', '')}"
            ordenes_html += f"""<tr>
                <td style="padding:8px;border:1px solid #e2e8f0;">{o.get('numero_orden','')}</td>
                <td style="padding:8px;border:1px solid #e2e8f0;">{o.get('dispositivo',{}).get('modelo','')}</td>
                <td style="padding:8px;border:1px solid #e2e8f0;font-family:monospace;font-weight:bold;">{o.get('token_seguimiento','')}</td>
                <td style="padding:8px;border:1px solid #e2e8f0;"><a href="{link}" style="color:#2563eb;">Ver estado</a></td>
            </tr>"""
        
        contenido = f"""<p>Hola {cliente.get('nombre','')},</p>
        <p>Has solicitado recuperar tus credenciales de seguimiento. Aquí tienes tus órdenes:</p>
        <table style="width:100%;border-collapse:collapse;margin:15px 0;">
            <tr style="background:#f8fafc;">
                <th style="padding:8px;border:1px solid #e2e8f0;text-align:left;">Orden</th>
                <th style="padding:8px;border:1px solid #e2e8f0;text-align:left;">Dispositivo</th>
                <th style="padding:8px;border:1px solid #e2e8f0;text-align:left;">Código</th>
                <th style="padding:8px;border:1px solid #e2e8f0;text-align:left;">Enlace</th>
            </tr>
            {ordenes_html}
        </table>
        <p>Usa el código junto con tu número de teléfono para acceder al portal de seguimiento.</p>"""
        
        smtp_send(
            to=cliente["email"],
            subject="Revix - Recuperación de credenciales de seguimiento",
            titulo="Tus credenciales de seguimiento",
            contenido=contenido
        )
    
    return {"message": f"Credenciales enviadas a {email_mask}"}

# ==================== INCLUDE ROUTER & STARTUP ====================

app.include_router(api_router)

@app.on_event("startup")
async def create_default_users():
    # Init Twilio
    if cfg.TWILIO_ACCOUNT_SID and cfg.TWILIO_AUTH_TOKEN:
        try:
            from twilio.rest import Client as TwilioClient
            cfg.twilio_client = TwilioClient(cfg.TWILIO_ACCOUNT_SID, cfg.TWILIO_AUTH_TOKEN)
            logger.info("Twilio configurado")
        except Exception as e:
            logger.warning(f"Twilio no disponible: {e}")

    # Init SendGrid
    if cfg.SENDGRID_API_KEY:
        try:
            from sendgrid import SendGridAPIClient
            cfg.sendgrid_client = SendGridAPIClient(cfg.SENDGRID_API_KEY)
            logger.info("SendGrid configurado")
        except Exception as e:
            logger.warning(f"SendGrid no disponible: {e}")

    # Log Resend status
    if cfg.RESEND_CONFIGURED:
        logger.info("Resend configurado: %s", cfg.SENDER_EMAIL)
    else:
        logger.warning("Resend no configurado - falta RESEND_API_KEY")

    # FRONTEND_URL forzado a producción en config.py — no sobreescribir


    # Crear/verificar indices de MongoDB (idempotente)
    try:
        from scripts.create_indexes import safe_index
        await safe_index(db.ordenes, "id", unique=True, name="idx_ordenes_id")
        await safe_index(db.ordenes, [("estado", 1), ("created_at", -1)], name="idx_ordenes_estado_fecha")
        await safe_index(db.ordenes, "numero_autorizacion", name="idx_ordenes_auth", sparse=True)
        await safe_index(db.ordenes, "token_seguimiento", name="idx_ordenes_token")
        await safe_index(db.clientes, "id", unique=True, name="idx_clientes_id")
        await safe_index(db.users, "email", unique=True, name="idx_users_email")
        await safe_index(db.print_jobs, "job_id", unique=True, name="idx_pj_jobid")
        await safe_index(db.print_jobs, "status", name="idx_pj_status")
        logger.info("Indices MongoDB verificados")
    except Exception as e:
        logger.warning(f"Error creando indices: {e}")

    # Database initialization - wrapped in try/except to not crash the server
    try:
        # Create default users
        from auth import hash_password as hp
        defaults = [
            {"id": "master-001", "email": "master@revix.es", "nombre": "Master Admin", "role": "master", "password_hash": hp("RevixMaster2026!")},
            {"id": "admin-001", "email": "admin@techrepair.local", "nombre": "Admin Principal", "role": "admin", "password_hash": hp("Admin2026!")},
            {"id": "tecnico-001", "email": "tecnico@techrepair.local", "nombre": "Técnico Demo", "role": "tecnico", "password_hash": hp("Tecnico2026!")},
        ]
        for u in defaults:
            existing = await db.users.find_one({"email": u["email"]})
            if not existing:
                doc = {**u, "activo": True, "created_at": datetime.now(timezone.utc).isoformat(), "updated_at": datetime.now(timezone.utc).isoformat()}
                await db.users.insert_one(doc)
                logger.info(f"Usuario creado: {u['email']}")

        await db.ordenes.create_index("numero_orden", unique=True)
        await db.ordenes.create_index("estado")
        await db.ordenes.create_index("cliente_id")
        await db.ordenes.create_index("token_seguimiento")
        await db.clientes.create_index("telefono")
        await db.clientes.create_index("dni")
        await db.pre_registros.create_index("codigo_siniestro", unique=True)
        await db.agent_idempotency.create_index("key", unique=True)
        await db.notificaciones_externas.create_index("codigo_siniestro")
        await db.notificaciones_externas.create_index("orden_id")
        
        # Índice para logs de auditoría
        await db.audit_logs.create_index([("entidad", 1), ("entidad_id", 1)])
        await db.audit_logs.create_index("usuario_email")
        await db.audit_logs.create_index([("created_at", -1)])
        
        # Índice para alertas SLA
        await db.alertas_sla.create_index("orden_id")
        await db.alertas_sla.create_index([("created_at", -1)])

        # Índices para GLS
        await db.gls_envios.create_index("entidad_origen_id")
        await db.gls_envios.create_index("gls_codbarras")
        await db.gls_envios.create_index("estado_interno")
        await db.gls_envios.create_index([("created_at", -1)])
        await db.gls_tracking_events.create_index("envio_id")
        await db.gls_logs.create_index("envio_id")
        
        logger.info("Database indexes created successfully")
    except Exception as e:
        logger.error(f"Error during database initialization (server will continue): {e}")

    # Start email agent if configured
    try:
        from agent.scheduler import start_agent
        agent_config = await db.configuracion.find_one({"tipo": "agent_config"}, {"_id": 0})
        if agent_config and agent_config.get('datos', {}).get('estado') == 'activo':
            start_agent()
            logger.info("Email agent started")
    except Exception as e:
        logger.warning(f"Could not start email agent: {e}")

    # Start GLS sync scheduler
    try:
        from modules.gls.sync_service import start_gls_sync
        start_gls_sync(db)
        logger.info("GLS sync scheduler started")
    except Exception as e:
        logger.warning(f"Could not start GLS sync scheduler: {e}")

@app.on_event("shutdown")
async def shutdown_db_client():
    from modules.gls.sync_service import stop_gls_sync
    stop_gls_sync()
    cfg.client.close()


# ==================== PERFORMANCE METRICS ENDPOINTS ====================

@api_router.get("/metrics/performance")
async def get_performance_metrics(user: dict = Depends(require_master)):
    """Get full performance report - MASTER only"""
    return metrics.get_full_report()

@api_router.get("/metrics/slow-endpoints")
async def get_slow_endpoints(limit: int = 20, user: dict = Depends(require_admin)):
    """Get top slow endpoints by p95 latency"""
    return {
        "endpoints": metrics.get_top_slow_endpoints(limit),
        "slow_requests": metrics.get_slow_queries_log(50)
    }

@api_router.get("/metrics/slow-queries")
async def get_slow_db_queries(user: dict = Depends(require_master)):
    """Get slow database queries"""
    return {
        "query_stats": query_profiler.get_query_stats(),
        "recent_slow": query_profiler.get_slow_queries(50)
    }

@api_router.get("/health")
async def health_check():
    """Health check endpoint (no auth)"""
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}

# ==================== ENDPOINT TEMPORAL PARA CREAR USUARIOS ====================
@api_router.get("/setup/init-users")
async def init_users_endpoint(secret: str = ""):
    """
    Endpoint temporal para crear usuarios en producción.
    Usar UNA VEZ y luego eliminar este endpoint.
    URL: /api/setup/init-users?secret=revix-setup-2026-init
    """
    # Clave secreta para evitar uso no autorizado
    if secret != "revix-setup-2026-init":
        raise HTTPException(status_code=403, detail="Clave incorrecta. Usa: ?secret=revix-setup-2026-init")
    
    from auth import hash_password as hp
    
    created = []
    
    # Usuarios a crear
    users_to_create = [
        {
            "id": "master-ramiraz",
            "email": "ramiraz91@gmail.com",
            "nombre": "Administrador Master",
            "role": "master",
            "password_hash": hp("temp123"),
            "activo": True
        },
        {
            "id": "admin-001",
            "email": "admin@techrepair.local",
            "nombre": "Admin Principal",
            "role": "admin",
            "password_hash": hp("Admin2026!"),
            "activo": True
        },
        {
            "id": "tecnico-001",
            "email": "tecnico@techrepair.local",
            "nombre": "Técnico Demo",
            "role": "tecnico",
            "password_hash": hp("Tecnico2026!"),
            "activo": True
        },
    ]
    
    for u in users_to_create:
        existing = await db.users.find_one({"email": u["email"]})
        if existing:
            # Actualizar contraseña del usuario existente
            await db.users.update_one(
                {"email": u["email"]},
                {"$set": {"password_hash": u["password_hash"], "activo": True}}
            )
            created.append(f"Actualizado: {u['email']}")
        else:
            doc = {
                **u,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            await db.users.insert_one(doc)
            created.append(f"Creado: {u['email']}")
    
    return {
        "success": True,
        "message": "Usuarios inicializados correctamente",
        "usuarios": created
    }


