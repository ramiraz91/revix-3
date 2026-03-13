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
from routes.logistica_routes import router as logistica_router
from routes.mobilesentrix_routes import router as mobilesentrix_router
from routes.utopya_routes import router as utopya_router
from routes.contabilidad_routes import router as contabilidad_router
from routes.kits_routes import router as kits_router
from routes.inteligencia_precios_routes import router as inteligencia_router
from routes.liquidaciones_routes import router as liquidaciones_router
from routes.web_publica_routes import router as web_publica_router
from routes.iso_routes import router as iso_router
from routes.peticiones_routes import router as peticiones_router
from routes.faqs_routes import router as faqs_router
from routes.apple_manuals_routes import router as apple_manuals_router
from routes.compras_routes import router as compras_router

# ==================== APP SETUP ====================
app = FastAPI(title="Mobile Repair CRM/ERP API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security headers middleware
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response

app.add_middleware(SecurityHeadersMiddleware)

# Performance monitoring middleware
from middleware.performance import PerformanceMiddleware, metrics, query_profiler
app.add_middleware(PerformanceMiddleware)

# Main API router
api_router = APIRouter(prefix="/api")

# Include extracted route modules
api_router.include_router(auth_router)
api_router.include_router(data_router)
api_router.include_router(agent_router)
api_router.include_router(ordenes_router)
api_router.include_router(admin_router)
api_router.include_router(insurama_router)
api_router.include_router(logistica_router)
api_router.include_router(mobilesentrix_router)
api_router.include_router(utopya_router)
api_router.include_router(contabilidad_router)
api_router.include_router(kits_router)
api_router.include_router(inteligencia_router)
api_router.include_router(liquidaciones_router)
api_router.include_router(web_publica_router)
api_router.include_router(iso_router)
api_router.include_router(peticiones_router)
api_router.include_router(faqs_router)
api_router.include_router(compras_router)
app.include_router(apple_manuals_router)  # No prefix, ya tiene /api/apple-manuals

# ==================== STATIC FILES ====================

@api_router.get("/uploads/{file_name}")
async def get_upload(file_name: str):
    file_path = UPLOAD_DIR / file_name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return FileResponse(str(file_path))

@api_router.post("/uploads")
async def upload_file(file: UploadFile = File(...)):
    file_ext = file.filename.split('.')[-1] if '.' in file.filename else 'bin'
    file_name = f"{str(uuid.uuid4())[:8]}.{file_ext}"
    file_path = UPLOAD_DIR / file_name
    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        await f.write(content)
    return {"file_name": file_name, "url": f"/api/uploads/{file_name}"}

# ==================== ROOT ====================

@api_router.get("/")
async def root():
    return {"message": "Mobile Repair CRM/ERP API"}

# ==================== CALENDARIO ====================

@api_router.get("/calendario/eventos")
async def listar_eventos_calendario(
    fecha_desde: Optional[str] = None, fecha_hasta: Optional[str] = None,
    usuario_id: Optional[str] = None, tipo: Optional[str] = None,
    user: dict = Depends(require_auth)
):
    query = {}
    conditions = []
    if fecha_desde:
        conditions.append({"fecha_inicio": {"$gte": fecha_desde}})
    if fecha_hasta:
        conditions.append({"fecha_inicio": {"$lte": fecha_hasta}})
    if usuario_id:
        conditions.append({"usuario_id": usuario_id})
    if tipo:
        conditions.append({"tipo": tipo})
    if user.get('role') == 'tecnico':
        conditions.append({"usuario_id": user['user_id']})
    if conditions:
        query = {"$and": conditions} if len(conditions) > 1 else conditions[0]
    return await db.calendario.find(query, {"_id": 0}).sort("fecha_inicio", 1).to_list(1000)

@api_router.post("/calendario/eventos")
async def crear_evento_calendario(evento: dict, user: dict = Depends(require_admin)):
    evento_obj = EventoCalendario(
        titulo=evento.get('titulo'), descripcion=evento.get('descripcion'),
        tipo=evento.get('tipo', TipoEvento.OTRO), fecha_inicio=evento.get('fecha_inicio'),
        fecha_fin=evento.get('fecha_fin'), todo_el_dia=evento.get('todo_el_dia', False),
        usuario_id=evento.get('usuario_id'), orden_id=evento.get('orden_id'),
        color=evento.get('color'), created_by=user['user_id']
    )
    doc = evento_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.calendario.insert_one(doc)
    doc.pop('_id', None)
    return doc

@api_router.put("/calendario/eventos/{evento_id}")
async def actualizar_evento_calendario(evento_id: str, evento: dict, user: dict = Depends(require_admin)):
    existing = await db.calendario.find_one({"id": evento_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    update_data = {k: v for k, v in evento.items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.calendario.update_one({"id": evento_id}, {"$set": update_data})
    return await db.calendario.find_one({"id": evento_id}, {"_id": 0})

@api_router.delete("/calendario/eventos/{evento_id}")
async def eliminar_evento_calendario(evento_id: str, user: dict = Depends(require_admin)):
    result = await db.calendario.delete_one({"id": evento_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    return {"message": "Evento eliminado"}

class _AsignarOrdenRequest(BaseModel):
    orden_id: str
    tecnico_id: str
    fecha_estimada: str

@api_router.post("/calendario/asignar-orden")
async def asignar_orden_tecnico(data: _AsignarOrdenRequest, user: dict = Depends(require_admin)):
    orden = await db.ordenes.find_one({"id": data.orden_id}, {"_id": 0})
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    tecnico = await db.users.find_one({"id": data.tecnico_id, "role": "tecnico"}, {"_id": 0})
    if not tecnico:
        raise HTTPException(status_code=404, detail="Técnico no encontrado")
    await db.ordenes.update_one({"id": data.orden_id}, {"$set": {"tecnico_asignado": data.tecnico_id, "fecha_estimada_reparacion": data.fecha_estimada, "updated_at": datetime.now(timezone.utc).isoformat()}})
    evento = EventoCalendario(titulo=f"Reparación: {orden['numero_orden']}", descripcion=f"Dispositivo: {orden['dispositivo']['modelo']} - {orden['dispositivo']['daños']}", tipo=TipoEvento.ORDEN_ASIGNADA, fecha_inicio=data.fecha_estimada, usuario_id=data.tecnico_id, orden_id=data.orden_id, color="#3b82f6", created_by=user['user_id'])
    doc = evento.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.calendario.insert_one(doc)
    doc.pop('_id', None)
    notificacion = Notificacion(tipo="orden_asignada", mensaje=f"Se te ha asignado la orden {orden['numero_orden']} para el {data.fecha_estimada}", orden_id=data.orden_id)
    notif_doc = notificacion.model_dump()
    notif_doc['created_at'] = notif_doc['created_at'].isoformat()
    notif_doc['usuario_destino'] = data.tecnico_id
    await db.notificaciones.insert_one(notif_doc)
    return {"message": "Orden asignada al técnico", "evento_id": doc.get('id')}

@api_router.get("/tecnicos/disponibilidad")
async def obtener_disponibilidad_tecnicos(fecha: str, user: dict = Depends(require_admin)):
    tecnicos = await db.users.find({"role": "tecnico", "activo": True}, {"_id": 0, "password_hash": 0}).to_list(100)
    resultado = []
    for tecnico in tecnicos:
        ordenes_asignadas = await db.calendario.count_documents({"usuario_id": tecnico['id'], "tipo": "orden_asignada", "fecha_inicio": {"$regex": f"^{fecha}"}})
        tiene_ausencia = await db.calendario.find_one({"usuario_id": tecnico['id'], "tipo": {"$in": ["vacaciones", "ausencia"]}, "fecha_inicio": {"$lte": fecha}, "fecha_fin": {"$gte": fecha}})
        resultado.append({"tecnico": {"id": tecnico['id'], "nombre": tecnico['nombre'], "apellidos": tecnico.get('apellidos', ''), "avatar_url": tecnico.get('avatar_url')}, "ordenes_asignadas": ordenes_asignadas, "disponible": not tiene_ausencia, "motivo_no_disponible": tiene_ausencia['tipo'] if tiene_ausencia else None})
    return resultado

# ==================== NOTIFICACIONES ====================

@api_router.get("/notificaciones", response_model=List[Notificacion])
async def listar_notificaciones(no_leidas: Optional[bool] = None):
    query = {"leida": False} if no_leidas else {}
    notificaciones = await db.notificaciones.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    for n in notificaciones:
        if isinstance(n.get('created_at'), str):
            n['created_at'] = datetime.fromisoformat(n['created_at'])
    return notificaciones

@api_router.patch("/notificaciones/{notificacion_id}/leer")
async def marcar_leida(notificacion_id: str):
    result = await db.notificaciones.update_one({"id": notificacion_id}, {"$set": {"leida": True}})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")
    return {"message": "Notificación marcada como leída"}

@api_router.delete("/notificaciones/{notificacion_id}")
async def eliminar_notificacion(notificacion_id: str):
    result = await db.notificaciones.delete_one({"id": notificacion_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")
    return {"message": "Notificación eliminada"}


@api_router.post("/notificaciones/eliminar-masivo")
async def eliminar_notificaciones_masivo(data: dict, user: dict = Depends(require_auth)):
    """Elimina múltiples notificaciones por sus IDs."""
    ids = data.get("ids", [])
    if not ids:
        raise HTTPException(status_code=400, detail="No se proporcionaron IDs")
    
    result = await db.notificaciones.delete_many({"id": {"$in": ids}})
    return {"eliminadas": result.deleted_count, "message": f"{result.deleted_count} notificaciones eliminadas"}


@api_router.post("/notificaciones/marcar-leidas-masivo")
async def marcar_leidas_masivo(data: dict, user: dict = Depends(require_auth)):
    """Marca múltiples notificaciones como leídas por sus IDs."""
    ids = data.get("ids", [])
    if not ids:
        raise HTTPException(status_code=400, detail="No se proporcionaron IDs")
    
    result = await db.notificaciones.update_many(
        {"id": {"$in": ids}},
        {"$set": {"leida": True}}
    )
    return {"modificadas": result.modified_count, "message": f"{result.modified_count} notificaciones marcadas como leídas"}


@api_router.patch("/notificaciones/marcar-leidas-orden/{orden_id}")
async def marcar_leidas_por_orden(orden_id: str):
    """Auto-mark all notifications linked to an order as read (when user views the order)."""
    result = await db.notificaciones.update_many(
        {"orden_id": orden_id, "leida": False},
        {"$set": {"leida": True}}
    )
    return {"marcadas": result.modified_count}

@api_router.post("/email/test")
async def test_smtp_email(data: dict, user: dict = Depends(require_master)):
    """Send a test email to verify SMTP configuration."""
    to = data.get('to', user.get('email', 'master@techrepair.local'))
    from services.email_service import send_email as smtp_send
    ok = smtp_send(
        to=to,
        subject="Revix - Test de configuración SMTP",
        titulo="Prueba de Email",
        contenido="<p>Si recibes este correo, la configuración SMTP está funcionando correctamente.</p>"
    )
    return {"success": ok, "to": to, "smtp_host": cfg.SMTP_HOST}

@api_router.get("/repuestos/buscar-sku/{sku}")
async def buscar_repuesto_por_sku(sku: str):
    """Search inventory by SKU/barcode for material scanning."""
    repuesto = await db.repuestos.find_one({"sku": sku}, {"_id": 0})
    if not repuesto:
        # Try partial match
        repuesto = await db.repuestos.find_one(
            {"sku": {"$regex": sku, "$options": "i"}}, {"_id": 0}
        )
    if not repuesto:
        raise HTTPException(status_code=404, detail=f"Repuesto con SKU '{sku}' no encontrado")
    if isinstance(repuesto.get('created_at'), str):
        repuesto['created_at'] = datetime.fromisoformat(repuesto['created_at'])
    if isinstance(repuesto.get('updated_at'), str):
        repuesto['updated_at'] = datetime.fromisoformat(repuesto['updated_at'])
    return repuesto


# ── Email Configuration ─────────────────────────────────

@api_router.get("/email-config")
async def get_email_config(user: dict = Depends(require_master)):
    config = await db.configuracion.find_one({"tipo": "email_config"}, {"_id": 0})
    if not config:
        return {"enabled": False, "demo_mode": True, "demo_email": "", "smtp_from": "Revix <notificaciones@revix.es>", "reply_to": "help@revix.es", "actions": {}}
    return config.get("datos", {})

@api_router.put("/email-config")
async def update_email_config(data: dict, user: dict = Depends(require_master)):
    await db.configuracion.update_one(
        {"tipo": "email_config"},
        {"$set": {"tipo": "email_config", "datos": data, "updated_at": datetime.now(timezone.utc).isoformat(), "updated_by": user.get("email", "sistema")}},
        upsert=True
    )
    return {"message": "Configuración de email actualizada"}

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




@api_router.post("/notificaciones/enviar")
async def enviar_notificacion_manual(data: dict, user: dict = Depends(require_admin)):
    orden_id = data.get('orden_id')
    tipo = data.get('tipo', 'sms')
    mensaje_personalizado = data.get('mensaje')
    orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    cliente = await db.clientes.find_one({"id": orden['cliente_id']}, {"_id": 0})
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    results = {}
    if tipo in ['sms', 'ambos'] and cliente.get('telefono'):
        results['sms'] = await send_sms(cliente['telefono'], mensaje_personalizado or f"TechRepair: Actualización de tu orden {orden['numero_orden']}")
    if tipo in ['email', 'ambos'] and cliente.get('email'):
        from helpers import generate_order_email_html
        html = generate_order_email_html(orden, cliente, mensaje_personalizado)
        results['email'] = await send_email(cliente['email'], f"Actualización - {orden['numero_orden']}", html)
    return {"message": "Notificación enviada", "resultados": results}

# ==================== DASHBOARD ====================

@api_router.get("/dashboard/stats")
async def obtener_estadisticas():
    ordenes_por_estado = {}
    for estado in OrderStatus:
        count = await db.ordenes.count_documents({"estado": estado.value})
        ordenes_por_estado[estado.value] = count
    total_ordenes = await db.ordenes.count_documents({})
    total_clientes = await db.clientes.count_documents({})
    total_repuestos = await db.repuestos.count_documents({})
    notificaciones_pendientes = await db.notificaciones.count_documents({"leida": False})
    now = datetime.now(timezone.utc)
    hace_30_dias = now - timedelta(days=30)
    hace_7_dias = now - timedelta(days=7)
    ordenes_ultimo_mes = await db.ordenes.count_documents({"created_at": {"$gte": hace_30_dias.isoformat()}})
    ordenes_ultima_semana = await db.ordenes.count_documents({"created_at": {"$gte": hace_7_dias.isoformat()}})
    ordenes_completadas = await db.ordenes.count_documents({"estado": "enviado"})
    ordenes_canceladas = await db.ordenes.count_documents({"estado": "cancelado"})
    tasa_completado = round((ordenes_completadas / total_ordenes * 100) if total_ordenes > 0 else 0, 1)
    ordenes_garantia_activas = await db.ordenes.count_documents({"estado": {"$nin": ["cancelado", "enviado"]}, "garantia_fecha_fin": {"$gte": now.isoformat()}})
    repuestos_bajo_stock = await db.repuestos.count_documents({"$expr": {"$lte": ["$stock", "$stock_minimo"]}})
    ordenes_bloqueadas = await db.ordenes.count_documents({"bloqueada": True})
    return {"total_ordenes": total_ordenes, "ordenes_por_estado": ordenes_por_estado, "total_clientes": total_clientes, "total_repuestos": total_repuestos, "notificaciones_pendientes": notificaciones_pendientes, "ordenes_ultimo_mes": ordenes_ultimo_mes, "ordenes_ultima_semana": ordenes_ultima_semana, "tasa_completado": tasa_completado, "ordenes_canceladas": ordenes_canceladas, "ordenes_garantia_activas": ordenes_garantia_activas, "repuestos_bajo_stock": repuestos_bajo_stock, "ordenes_bloqueadas": ordenes_bloqueadas}

@api_router.get("/dashboard/metricas-avanzadas")
async def obtener_metricas_avanzadas(user: dict = Depends(require_admin)):
    from collections import defaultdict
    now = datetime.now(timezone.utc)
    hace_30_dias = now - timedelta(days=30)
    hace_7_dias = now - timedelta(days=7)
    ordenes = await db.ordenes.find({}, {"_id": 0}).to_list(5000)
    ordenes_por_dia = defaultdict(int)
    for orden in ordenes:
        created = orden.get('created_at')
        if created:
            if isinstance(created, str):
                created = datetime.fromisoformat(created.replace('Z', '+00:00'))
            if created >= hace_30_dias:
                ordenes_por_dia[created.strftime('%Y-%m-%d')] += 1
    ordenes_por_estado = defaultdict(int)
    for orden in ordenes:
        ordenes_por_estado[orden.get('estado', 'unknown')] += 1
    total = len(ordenes)
    canceladas = len([o for o in ordenes if o.get('estado') == 'cancelado'])
    completadas = len([o for o in ordenes if o.get('estado') == 'enviado'])
    en_proceso = total - canceladas - completadas
    tiempos_reparacion = []
    for orden in ordenes:
        inicio, fin = orden.get('fecha_inicio_reparacion'), orden.get('fecha_fin_reparacion')
        if inicio and fin:
            if isinstance(inicio, str): inicio = datetime.fromisoformat(inicio.replace('Z', '+00:00'))
            if isinstance(fin, str): fin = datetime.fromisoformat(fin.replace('Z', '+00:00'))
            diff = (fin - inicio).total_seconds() / 3600
            if diff > 0: tiempos_reparacion.append(diff)
    promedio_reparacion = sum(tiempos_reparacion) / len(tiempos_reparacion) if tiempos_reparacion else 0
    tiempos_totales = []
    for orden in ordenes:
        created, enviado = orden.get('created_at'), orden.get('fecha_enviado')
        if created and enviado:
            if isinstance(created, str): created = datetime.fromisoformat(created.replace('Z', '+00:00'))
            if isinstance(enviado, str): enviado = datetime.fromisoformat(enviado.replace('Z', '+00:00'))
            diff = (enviado - created).total_seconds() / 3600
            if diff > 0: tiempos_totales.append(diff)
    promedio_total = sum(tiempos_totales) / len(tiempos_totales) if tiempos_totales else 0
    ordenes_garantia = len([o for o in ordenes if o.get('es_garantia')])
    ordenes_ultimos_7 = len([o for o in ordenes if o.get('created_at') and (datetime.fromisoformat(o['created_at'].replace('Z', '+00:00')) if isinstance(o['created_at'], str) else o['created_at']) >= hace_7_dias])
    repuestos_count = defaultdict(int)
    for orden in ordenes:
        for mat in orden.get('materiales', []):
            repuestos_count[mat.get('nombre', 'Unknown')] += mat.get('cantidad', 1)
    top_repuestos = sorted(repuestos_count.items(), key=lambda x: x[1], reverse=True)[:5]
    return {
        "ordenes_por_dia": [{"fecha": k, "ordenes": v} for k, v in sorted(ordenes_por_dia.items())],
        "ordenes_por_estado": [{"estado": k, "cantidad": v} for k, v in ordenes_por_estado.items()],
        "ratios": {"total": total, "completadas": completadas, "canceladas": canceladas, "en_proceso": en_proceso, "garantias": ordenes_garantia, "ratio_cancelacion": round((canceladas / total * 100) if total > 0 else 0, 1), "ratio_completado": round((completadas / total * 100) if total > 0 else 0, 1)},
        "tiempos": {"promedio_reparacion_horas": round(promedio_reparacion, 1), "promedio_total_horas": round(promedio_total, 1), "promedio_reparacion_dias": round(promedio_reparacion / 24, 1), "promedio_total_dias": round(promedio_total / 24, 1)},
        "comparativa": {"ultimos_7_dias": ordenes_ultimos_7, "total_30_dias": len([o for o in ordenes if o.get('created_at') and (datetime.fromisoformat(o['created_at'].replace('Z', '+00:00')) if isinstance(o['created_at'], str) else o['created_at']) >= hace_30_dias])},
        "top_repuestos": [{"nombre": r[0], "cantidad": r[1]} for r in top_repuestos]
    }

@api_router.get("/dashboard/alertas-stock")
async def obtener_alertas_stock(user: dict = Depends(require_admin)):
    repuestos = await db.repuestos.find({}, {"_id": 0}).to_list(1000)
    alertas = []
    for rep in repuestos:
        stock = rep.get('stock', 0)
        stock_minimo = rep.get('stock_minimo', 5)
        if stock <= stock_minimo:
            alertas.append({"id": rep.get('id'), "nombre": rep.get('nombre'), "stock": stock, "stock_minimo": stock_minimo, "nivel": "critico" if stock == 0 else "bajo", "proveedor_id": rep.get('proveedor_id')})
    alertas.sort(key=lambda x: (0 if x['nivel'] == 'critico' else 1, x['stock']))
    return {"alertas": alertas, "total_critico": len([a for a in alertas if a['nivel'] == 'critico']), "total_bajo": len([a for a in alertas if a['nivel'] == 'bajo'])}

@api_router.get("/dashboard/ordenes-compra-urgentes")
async def obtener_ordenes_compra_urgentes(user: dict = Depends(require_admin)):
    ordenes = await db.ordenes_compra.find({"estado": {"$in": ["pendiente", "aprobada"]}}, {"_id": 0}).sort("created_at", -1).to_list(50)
    for oc in ordenes:
        orden_trabajo = await db.ordenes.find_one({"id": oc.get('orden_trabajo_id')}, {"_id": 0, "numero_orden": 1, "dispositivo": 1})
        oc['orden_trabajo'] = {"numero_orden": orden_trabajo.get('numero_orden', 'N/A') if orden_trabajo else 'N/A', "dispositivo": orden_trabajo.get('dispositivo', {}).get('modelo', 'N/A') if orden_trabajo else 'N/A'}
    return {"total_pendientes": len([o for o in ordenes if o['estado'] == 'pendiente']), "ordenes": ordenes}

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
            {"$set": {"ultimo_consentimiento_seguimiento": consentimiento, "updated_at": now.isoformat()}},
        )
        consentimiento_registrado = True

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
            "codigo_seguimiento_salida": orden.get('codigo_seguimiento_salida'),
            "diagnostico_tecnico": orden.get('diagnostico_tecnico'),
            "numero_autorizacion": orden.get('numero_autorizacion'),
            "evidencias": orden.get('evidencias', []),
            "fechas": fechas,
            "cliente": {
                "nombre": cliente.get('nombre', ''),
            }
        },
        "textos_legales": textos,
        "consentimiento_registrado": consentimiento_registrado,
    }

@api_router.get("/seguimiento/{token}")
async def obtener_seguimiento_publico(token: str):
    orden = await db.ordenes.find_one({"token_seguimiento": token.upper()}, {"_id": 0})
    if not orden:
        raise HTTPException(status_code=404, detail="Código no válido")
    return {"numero_orden": orden['numero_orden'], "estado": orden['estado'], "dispositivo": {"modelo": orden['dispositivo']['modelo']}, "historial_estados": orden.get('historial_estados', [])}

# ==================== CONFIGURACIÓN SISTEMA ====================

@api_router.get("/configuracion/notificaciones")
async def obtener_config_notificaciones(user: dict = Depends(require_master)):
    return {"twilio_account_sid": cfg.TWILIO_ACCOUNT_SID or "", "twilio_phone_number": cfg.TWILIO_PHONE_NUMBER or "", "sendgrid_from_email": cfg.SENDGRID_FROM_EMAIL or "", "twilio_configurado": bool(cfg.twilio_client), "sendgrid_configurado": bool(cfg.sendgrid_client)}

@api_router.post("/configuracion/notificaciones")
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

@api_router.get("/configuracion/empresa")
async def obtener_config_empresa(user: dict = Depends(require_admin)):
    config = await db.configuracion.find_one({"tipo": "empresa"}, {"_id": 0})
    if not config:
        return EmpresaConfig().model_dump()
    return config.get("datos", EmpresaConfig().model_dump())

@api_router.get("/configuracion/empresa/publica")
async def obtener_config_empresa_publica():
    config = await db.configuracion.find_one({"tipo": "empresa"}, {"_id": 0})
    datos = config.get("datos", EmpresaConfig().model_dump()) if config else EmpresaConfig().model_dump()
    return {"nombre": datos.get("nombre", "Mi Empresa"), "logo": datos.get("logo", {}), "logo_url": datos.get("logo_url"), "textos_legales": datos.get("textos_legales", TextosLegales().model_dump()), "telefono": datos.get("telefono"), "email": datos.get("email"), "web": datos.get("web")}

@api_router.post("/configuracion/empresa/logo")
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

@api_router.post("/configuracion/empresa")
async def guardar_config_empresa(config: EmpresaConfig, user: dict = Depends(require_admin)):
    await db.configuracion.update_one({"tipo": "empresa"}, {"$set": {"tipo": "empresa", "datos": config.model_dump(), "updated_at": datetime.now(timezone.utc).isoformat(), "updated_by": user.get('email', 'sistema')}}, upsert=True)
    return {"message": "Configuración de empresa guardada", "datos": config.model_dump()}

# ==================== MÉTRICAS MASTER / ANALÍTICAS ====================

@api_router.get("/master/metricas-tecnicos")
async def obtener_metricas_tecnicos(user: dict = Depends(require_master)):
    tecnicos = await db.users.find({"role": "tecnico"}, {"_id": 0, "password_hash": 0}).to_list(100)
    metricas = []
    for t in tecnicos:
        ordenes = await db.ordenes.find({"tecnico_asignado": t['id']}, {"_id": 0}).to_list(1000)
        completadas = len([o for o in ordenes if o.get('estado') == 'enviado'])
        metricas.append({"tecnico_id": t['id'], "nombre": t['nombre'], "total_ordenes": len(ordenes), "completadas": completadas, "garantias": len([o for o in ordenes if o.get('es_garantia')]), "en_proceso": len([o for o in ordenes if o.get('estado') in ['en_taller', 'reparado', 'validacion']]), "irreparables": len([o for o in ordenes if o.get('estado') == 'irreparable']), "tasa_exito": round((completadas / len(ordenes) * 100) if ordenes else 0, 1)})
    return metricas

@api_router.get("/master/facturacion")
async def obtener_facturacion(user: dict = Depends(require_master), fecha_desde: Optional[str] = None, fecha_hasta: Optional[str] = None):
    query = {"estado": "enviado"}
    if fecha_desde:
        query["fecha_enviado"] = {"$gte": fecha_desde}
    if fecha_hasta:
        if "fecha_enviado" in query:
            query["fecha_enviado"]["$lte"] = fecha_hasta
        else:
            query["fecha_enviado"] = {"$lte": fecha_hasta}
    ordenes = await db.ordenes.find(query, {"_id": 0}).to_list(5000)
    config_empresa = await db.configuracion.find_one({"tipo": "empresa"}, {"_id": 0})
    iva_defecto = config_empresa.get("datos", {}).get("iva_por_defecto", 21.0) if config_empresa else 21.0
    total_materiales = sum(m.get('precio_unitario', 0) * m.get('cantidad', 1) for o in ordenes for m in o.get('materiales', []))
    subtotal = total_materiales
    iva = subtotal * (iva_defecto / 100)
    return {
        "periodo": {"desde": fecha_desde, "hasta": fecha_hasta},
        "ordenes_facturadas": len(ordenes),
        "desglose": {
            "materiales": round(total_materiales, 2),
            "mano_obra": 0,
            "subtotal": round(subtotal, 2),
            "iva_porcentaje": iva_defecto,
            "iva_importe": round(iva, 2),
            "total": round(subtotal + iva, 2),
        },
    }



def _parse_dt_safe(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            return None
    return None


@api_router.get("/master/iso/documentos")
async def obtener_iso_documentos(user: dict = Depends(require_master)):
    documentos = await db.iso_documentos.find({}, {"_id": 0}).sort("codigo", 1).to_list(500)
    return documentos


@api_router.post("/master/iso/documentos")
async def guardar_iso_documento(data: dict, user: dict = Depends(require_master)):
    codigo = (data.get("codigo") or "").strip().upper()
    titulo = (data.get("titulo") or "").strip()
    tipo = (data.get("tipo") or "").strip().lower()

    if not codigo or not titulo or tipo not in {"documento", "registro"}:
        raise HTTPException(status_code=400, detail="codigo, titulo y tipo(documento/registro) son obligatorios")

    now = datetime.now(timezone.utc).isoformat()
    existing = await db.iso_documentos.find_one({"codigo": codigo}, {"_id": 0})

    payload = {
        "codigo": codigo,
        "titulo": titulo,
        "tipo": tipo,
        "version": data.get("version") or "1.0",
        "estado": data.get("estado") or "vigente",
        "aprobado_por": data.get("aprobado_por") or user.get("email"),
        "retencion_anios": int(data.get("retencion_anios") or 3),
        "proceso": data.get("proceso") or "sgc",
        "clausulas_iso": data.get("clausulas_iso") or [],
        "observaciones": data.get("observaciones"),
        "updated_at": now,
        "updated_by": user.get("email"),
    }

    if existing:
        await db.iso_documentos.update_one({"codigo": codigo}, {"$set": payload})
    else:
        payload["created_at"] = now
        payload["created_by"] = user.get("email")
        await db.iso_documentos.insert_one(payload)

    return await db.iso_documentos.find_one({"codigo": codigo}, {"_id": 0})


@api_router.get("/master/iso/proveedores")
async def obtener_iso_proveedores(user: dict = Depends(require_master)):
    evaluaciones = await db.iso_proveedores_evaluacion.find({}, {"_id": 0}).sort("proveedor", 1).to_list(500)

    # Semillas mínimas para proveedores críticos ya usados por el negocio
    semillas = ["GLS", "MobileSentrix", "Utopya"]
    existentes = {e.get("proveedor") for e in evaluaciones}
    now = datetime.now(timezone.utc).isoformat()

    for nombre in semillas:
        if nombre not in existentes:
            doc = {
                "proveedor": nombre,
                "tipo": "logistica" if nombre == "GLS" else "recambios",
                "estado": "pendiente",
                "score": None,
                "ultima_evaluacion": None,
                "proxima_reevaluacion": None,
                "incidencias": 0,
                "comentarios": None,
                "created_at": now,
                "updated_at": now,
            }
            await db.iso_proveedores_evaluacion.insert_one(doc)
            evaluaciones.append(doc)

    cleaned = []
    for ev in evaluaciones:
        ev_clean = dict(ev)
        ev_clean.pop("_id", None)
        for key, value in list(ev_clean.items()):
            if isinstance(value, ObjectId):
                ev_clean[key] = str(value)
        cleaned.append(ev_clean)

    return sorted(cleaned, key=lambda x: x.get("proveedor", ""))


@api_router.post("/master/iso/proveedores/evaluar")
async def evaluar_iso_proveedor(data: dict, user: dict = Depends(require_master)):
    proveedor = (data.get("proveedor") or "").strip()
    if not proveedor:
        raise HTTPException(status_code=400, detail="proveedor es obligatorio")

    puntualidad = float(data.get("puntualidad") or 0)
    calidad = float(data.get("calidad") or 0)
    respuesta = float(data.get("respuesta") or 0)
    incidencias = float(data.get("incidencias") or 0)

    score = round((puntualidad + calidad + respuesta + (100 - incidencias)) / 4, 1)
    estado = "aprobado" if score >= 75 else "condicional" if score >= 60 else "bloqueado"

    now_dt = datetime.now(timezone.utc)
    now = now_dt.isoformat()
    proxima = (now_dt + timedelta(days=90)).date().isoformat()

    payload = {
        "proveedor": proveedor,
        "tipo": data.get("tipo") or "recambios",
        "puntualidad": puntualidad,
        "calidad": calidad,
        "respuesta": respuesta,
        "incidencias": incidencias,
        "score": score,
        "estado": estado,
        "ultima_evaluacion": now,
        "proxima_reevaluacion": data.get("proxima_reevaluacion") or proxima,
        "comentarios": data.get("comentarios"),
        "updated_at": now,
        "updated_by": user.get("email"),
    }

    await db.iso_proveedores_evaluacion.update_one(
        {"proveedor": proveedor},
        {"$set": payload, "$setOnInsert": {"created_at": now}},
        upsert=True,
    )
    return await db.iso_proveedores_evaluacion.find_one({"proveedor": proveedor}, {"_id": 0})


@api_router.get("/master/iso/kpis")
async def obtener_kpis_iso(user: dict = Depends(require_master)):
    ordenes = await db.ordenes.find({}, {"_id": 0}).to_list(10000)

    enviados = [o for o in ordenes if o.get("estado") == "enviado"]
    total_enviados = len(enviados)
    garantias = [o for o in ordenes if o.get("es_garantia")]
    total_garantias = len(garantias)

    retrabajo_pct = round((total_garantias / total_enviados * 100), 2) if total_enviados else 0
    reparaciones_sin_retrabajo_pct = round(100 - retrabajo_pct, 2) if total_enviados else 0

    tat_horas = []
    entregas_a_tiempo = 0
    entregas_con_sla = 0

    for o in enviados:
        created_at = _parse_dt_safe(o.get("created_at"))
        fecha_enviado = _parse_dt_safe(o.get("fecha_enviado"))
        if created_at and fecha_enviado:
            tat_horas.append((fecha_enviado - created_at).total_seconds() / 3600)

        fecha_estimada = _parse_dt_safe(o.get("fecha_estimada_entrega"))
        if fecha_estimada and fecha_enviado:
            entregas_con_sla += 1
            if fecha_enviado <= fecha_estimada:
                entregas_a_tiempo += 1

    tat_promedio_horas = round(sum(tat_horas) / len(tat_horas), 2) if tat_horas else None
    entregas_a_tiempo_pct = round((entregas_a_tiempo / entregas_con_sla) * 100, 2) if entregas_con_sla else None

    qc_fallos = len([o for o in ordenes if o.get("estado") == "validacion" and not (o.get("diagnostico_salida_realizado") and o.get("funciones_verificadas") and o.get("limpieza_realizada"))])
    first_pass_yield_pct = round(((total_enviados - total_garantias) / total_enviados) * 100, 2) if total_enviados else 0

    incidencias = await db.incidencias.find({}, {"_id": 0, "tipo": 1, "estado": 1}).to_list(5000)
    reclamaciones = [i for i in incidencias if i.get("tipo") == "reclamacion"]
    csat_proxy = round(max(0, 100 - (len(reclamaciones) / total_enviados * 100)), 2) if total_enviados else None

    proveedores = await db.iso_proveedores_evaluacion.find({}, {"_id": 0, "proveedor": 1, "score": 1, "estado": 1, "incidencias": 1}).to_list(200)

    return {
        "kpis": {
            "reparaciones_sin_retrabajo_pct": reparaciones_sin_retrabajo_pct,
            "tat_promedio_horas": tat_promedio_horas,
            "entregas_a_tiempo_pct": entregas_a_tiempo_pct,
            "qc_fallos": qc_fallos,
            "first_pass_yield_pct": first_pass_yield_pct,
            "devoluciones_garantias_pct": retrabajo_pct,
            "satisfaccion_cliente_proxy_pct": csat_proxy,
        },
        "proveedores": proveedores,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }



async def _collect_audit_pack_for_order(order_doc: dict) -> dict:
    orden_id = order_doc.get("id")
    eventos = await db.ot_event_log.find({"ot_id": orden_id}, {"_id": 0}).sort("created_at", 1).to_list(5000)
    consentimientos = await db.consentimientos_seguimiento.find({"orden_id": orden_id}, {"_id": 0}).sort("created_at", -1).to_list(200)
    incidencias = await db.incidencias.find({"orden_id": orden_id}, {"_id": 0}).sort("created_at", -1).to_list(200)

    return {
        "ot": {
            "id": order_doc.get("id"),
            "numero_orden": order_doc.get("numero_orden"),
            "numero_autorizacion": order_doc.get("numero_autorizacion"),
            "estado": order_doc.get("estado"),
            "cliente_id": order_doc.get("cliente_id"),
            "dispositivo": order_doc.get("dispositivo"),
            "created_at": order_doc.get("created_at"),
            "updated_at": order_doc.get("updated_at"),
            "historial_estados": order_doc.get("historial_estados", []),
            "ri": {
                "obligatoria": bool(order_doc.get("ri_obligatoria")),
                "completada": bool(order_doc.get("ri_completada")),
                "resultado": order_doc.get("ri_resultado"),
                "fecha": order_doc.get("ri_fecha"),
                "usuario": order_doc.get("ri_usuario"),
                "fotos_count": len(order_doc.get("ri_fotos_recepcion", []) or []),
            },
            "qc": {
                "diagnostico_salida_realizado": bool(order_doc.get("diagnostico_salida_realizado")),
                "funciones_verificadas": bool(order_doc.get("funciones_verificadas")),
                "limpieza_realizada": bool(order_doc.get("limpieza_realizada")),
            },
            "bateria": {
                "reemplazada": bool(order_doc.get("bateria_reemplazada")),
                "almacenamiento_temporal": bool(order_doc.get("bateria_almacenamiento_temporal")),
                "residuo_pendiente": bool(order_doc.get("bateria_residuo_pendiente")),
                "gestor": order_doc.get("bateria_gestor_autorizado"),
                "fecha_entrega_gestor": order_doc.get("bateria_fecha_entrega_gestor"),
            },
            "cpi": {
                "requiere_borrado": order_doc.get("cpi_requiere_borrado"),
                "metodo": order_doc.get("cpi_metodo"),
                "resultado": order_doc.get("cpi_resultado"),
                "fecha": order_doc.get("cpi_fecha"),
            },
            "flash": {
                "aplica": order_doc.get("flash_aplica"),
                "version": order_doc.get("flash_version"),
                "herramienta": order_doc.get("flash_herramienta"),
                "resultado": order_doc.get("flash_resultado"),
            },
            "evidencias_count": len(order_doc.get("evidencias", []) or []),
            "evidencias_tecnico_count": len(order_doc.get("evidencias_tecnico", []) or []),
        },
        "event_log": eventos,
        "consentimientos": consentimientos,
        "incidencias": incidencias,
    }


@api_router.get("/master/iso/audit-pack/ot/{orden_id}")
async def obtener_audit_pack_ot(orden_id: str, user: dict = Depends(require_master)):
    orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    if not orden:
        raise HTTPException(status_code=404, detail="OT no encontrada")
    pack = await _collect_audit_pack_for_order(orden)
    await _registrar_evento_seguridad(user, 'audit_pack_ot_export', {'orden_id': orden_id})
    return pack


@api_router.get("/master/iso/audit-pack/periodo")
async def obtener_audit_pack_periodo(
    user: dict = Depends(require_master),
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
):
    query = {}
    if fecha_desde or fecha_hasta:
        query["created_at"] = {}
        if fecha_desde:
            query["created_at"]["$gte"] = fecha_desde
        if fecha_hasta:
            query["created_at"]["$lte"] = fecha_hasta

    ordenes = await db.ordenes.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    items = []
    for o in ordenes:
        items.append(await _collect_audit_pack_for_order(o))

    payload = {
        "periodo": {"desde": fecha_desde, "hasta": fecha_hasta},
        "total_ots": len(items),
        "items": items,
    }
    await _registrar_evento_seguridad(user, 'audit_pack_periodo_export', {'desde': fecha_desde, 'hasta': fecha_hasta, 'total_ots': len(items)})
    return payload


@api_router.get("/master/iso/audit-pack/periodo/csv")
async def exportar_audit_pack_csv(
    user: dict = Depends(require_master),
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
):
    query = {}
    if fecha_desde or fecha_hasta:
        query["created_at"] = {}
        if fecha_desde:
            query["created_at"]["$gte"] = fecha_desde
        if fecha_hasta:
            query["created_at"]["$lte"] = fecha_hasta

    ordenes = await db.ordenes.find(query, {"_id": 0}).sort("created_at", -1).to_list(5000)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ot_id",
        "numero_orden",
        "estado",
        "created_at",
        "ri_completada",
        "ri_resultado",
        "qc_ok",
        "consentimientos",
        "eventos_auditoria",
        "incidencias",
        "capa_abiertas",
    ])

    for o in ordenes:
        orden_id = o.get("id")
        consent_count = await db.consentimientos_seguimiento.count_documents({"orden_id": orden_id})
        event_count = await db.ot_event_log.count_documents({"ot_id": orden_id})
        incidencias = await db.incidencias.find({"orden_id": orden_id}, {"_id": 0, "capa_estado": 1}).to_list(200)
        capa_abiertas = len([i for i in incidencias if i.get("capa_estado") in {"abierta", "en_progreso", "en_seguimiento"}])
        qc_ok = bool(o.get("diagnostico_salida_realizado") and o.get("funciones_verificadas") and o.get("limpieza_realizada"))

        writer.writerow([
            orden_id,
            o.get("numero_orden"),
            o.get("estado"),
            o.get("created_at"),
            bool(o.get("ri_completada")),
            o.get("ri_resultado"),
            qc_ok,
            consent_count,
            event_count,
            len(incidencias),
            capa_abiertas,
        ])

    csv_bytes = io.BytesIO(output.getvalue().encode("utf-8"))
    await _registrar_evento_seguridad(user, 'audit_pack_periodo_csv_export', {'desde': fecha_desde, 'hasta': fecha_hasta, 'total_ots': len(ordenes)})
    headers = {"Content-Disposition": "attachment; filename=audit_pack_periodo.csv"}
    return StreamingResponse(csv_bytes, media_type="text/csv", headers=headers)






@api_router.get('/master/iso/capa-dashboard')
async def obtener_dashboard_capa(user: dict = Depends(require_master)):
    capas = await db.capas.find({}, {'_id': 0}).to_list(5000)
    total = len(capas)
    por_estado = {}
    por_motivo = {}
    abiertas_antiguas = 0
    limite_antiguedad = datetime.now(timezone.utc) - timedelta(days=30)

    for c in capas:
        estado = c.get('estado') or 'abierta'
        por_estado[estado] = por_estado.get(estado, 0) + 1

        motivo = c.get('motivo_apertura') or 'sin_motivo'
        por_motivo[motivo] = por_motivo.get(motivo, 0) + 1

        created_at = _parse_dt_safe(c.get('created_at'))
        if estado in {'abierta', 'en_curso', 'implementada', 'en_seguimiento'} and created_at and created_at < limite_antiguedad:
            abiertas_antiguas += 1

    return {
        'total_capas': total,
        'por_estado': por_estado,
        'por_motivo': por_motivo,
        'abiertas_antiguedad_30d': abiertas_antiguas,
        'generated_at': datetime.now(timezone.utc).isoformat(),
    }

async def _registrar_evento_seguridad(user: dict, accion: str, detalle: dict):
    evento = {
        'id': str(uuid.uuid4()),
        'accion': accion,
        'usuario': user.get('email'),
        'role': user.get('role'),
        'detalle': detalle,
        'created_at': datetime.now(timezone.utc).isoformat(),
    }
    await db.seguridad_eventos.insert_one(evento)


@api_router.get("/master/iso/qa-config")
async def obtener_config_qa_iso(user: dict = Depends(require_master)):
    cfg = await db.iso_qa_config.find_one({'id': 'default'}, {'_id': 0})
    if not cfg:
        cfg = {
            'id': 'default',
            'porcentaje_diario': 10,
            'minimo_muestras': 1,
            'escalado_por_fallo_porcentaje': 20,
            'escalado_dias': 7,
            'escalado_hasta': None,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat(),
        }
        await db.iso_qa_config.insert_one(cfg)
    return cfg


@api_router.post("/master/iso/qa-config")
async def guardar_config_qa_iso(data: dict, user: dict = Depends(require_master)):
    cfg = await obtener_config_qa_iso(user)
    now = datetime.now(timezone.utc).isoformat()

    update = {
        'porcentaje_diario': int(data.get('porcentaje_diario', cfg.get('porcentaje_diario', 10))),
        'minimo_muestras': int(data.get('minimo_muestras', cfg.get('minimo_muestras', 1))),
        'escalado_por_fallo_porcentaje': int(data.get('escalado_por_fallo_porcentaje', cfg.get('escalado_por_fallo_porcentaje', 20))),
        'escalado_dias': int(data.get('escalado_dias', cfg.get('escalado_dias', 7))),
        'updated_at': now,
        'updated_by': user.get('email'),
    }

    await db.iso_qa_config.update_one({'id': 'default'}, {'$set': update}, upsert=True)
    return await db.iso_qa_config.find_one({'id': 'default'}, {'_id': 0})


@api_router.post("/master/iso/qa-muestreo/ejecutar")
async def ejecutar_muestreo_qa_iso(user: dict = Depends(require_master)):
    cfg = await obtener_config_qa_iso(user)
    now_dt = datetime.now(timezone.utc)
    hoy = now_dt.date().isoformat()

    porcentaje = int(cfg.get('porcentaje_diario', 10))
    escalado_hasta = cfg.get('escalado_hasta')
    if escalado_hasta:
        esc_dt = _parse_dt_safe(escalado_hasta)
        if esc_dt and esc_dt >= now_dt:
            porcentaje = int(cfg.get('escalado_por_fallo_porcentaje', 20))

    inicio_dia = f"{hoy}T00:00:00"
    ordenes = await db.ordenes.find(
        {
            'estado': {'$in': ['reparado', 'validacion', 'enviado']},
            'updated_at': {'$gte': inicio_dia},
        },
        {'_id': 0, 'id': 1, 'numero_orden': 1, 'estado': 1, 'updated_at': 1},
    ).to_list(5000)

    if not ordenes:
        return {'message': 'No hay OT candidatas hoy para muestreo QA', 'muestras': []}

    total = len(ordenes)
    minimo = max(1, int(cfg.get('minimo_muestras', 1)))
    tam_muestra = max(minimo, math.ceil((total * porcentaje) / 100))
    tam_muestra = min(tam_muestra, total)

    seleccionadas = random.sample(ordenes, tam_muestra)
    registros = []
    for o in seleccionadas:
        existente = await db.qa_muestreos.find_one({'ot_id': o.get('id'), 'fecha': hoy}, {'_id': 0})
        if existente:
            registros.append(existente)
            continue
        doc = {
            'id': str(uuid.uuid4()),
            'ot_id': o.get('id'),
            'numero_orden': o.get('numero_orden'),
            'fecha': hoy,
            'porcentaje_aplicado': porcentaje,
            'estado': 'pendiente_qa',
            'resultado': None,
            'hallazgos': None,
            'capa_id': None,
            'created_at': now_dt.isoformat(),
            'created_by': user.get('email'),
        }
        await db.qa_muestreos.insert_one(doc)
        doc.pop('_id', None)
        registros.append(doc)

    await _registrar_evento_seguridad(user, 'qa_muestreo_ejecutado', {'fecha': hoy, 'total': total, 'muestra': len(registros), 'porcentaje': porcentaje})

    return {
        'fecha': hoy,
        'total_candidatas': total,
        'tam_muestra': len(registros),
        'porcentaje_aplicado': porcentaje,
        'muestras': registros,
    }


@api_router.post('/master/iso/qa-muestreo/{muestreo_id}/resultado')
async def registrar_resultado_muestreo_qa(muestreo_id: str, data: dict, user: dict = Depends(require_master)):
    muestreo = await db.qa_muestreos.find_one({'id': muestreo_id}, {'_id': 0})
    if not muestreo:
        raise HTTPException(status_code=404, detail='Muestreo QA no encontrado')

    resultado = (data.get('resultado') or '').strip().lower()
    if resultado not in {'ok', 'fallo'}:
        raise HTTPException(status_code=400, detail='resultado debe ser ok o fallo')

    now_dt = datetime.now(timezone.utc)
    update = {
        'resultado': resultado,
        'estado': 'completado',
        'hallazgos': data.get('hallazgos'),
        'updated_at': now_dt.isoformat(),
        'updated_by': user.get('email'),
    }

    capa_id = None
    if resultado == 'fallo':
        cfg = await obtener_config_qa_iso(user)
        escalado_dias = int(cfg.get('escalado_dias', 7))
        escalado_hasta = (now_dt + timedelta(days=escalado_dias)).isoformat()
        await db.iso_qa_config.update_one({'id': 'default'}, {'$set': {'escalado_hasta': escalado_hasta, 'updated_at': now_dt.isoformat()}})

        capa_id = str(uuid.uuid4())
        capa_doc = {
            'id': capa_id,
            'origen': 'qa_muestreo',
            'ot_id': muestreo.get('ot_id'),
            'numero_orden': muestreo.get('numero_orden'),
            'estado': 'abierta',
            'motivo_apertura': 'fallo_qa_muestreo',
            'problema': data.get('hallazgos') or 'Fallo detectado en QA por muestreo',
            'created_at': now_dt.isoformat(),
            'updated_at': now_dt.isoformat(),
            'created_by': user.get('email'),
        }
        await db.capas.insert_one(capa_doc)
        update['capa_id'] = capa_id

    await db.qa_muestreos.update_one({'id': muestreo_id}, {'$set': update})

    await _registrar_evento_seguridad(user, 'qa_muestreo_resultado', {'muestreo_id': muestreo_id, 'resultado': resultado, 'capa_id': capa_id})

    return await db.qa_muestreos.find_one({'id': muestreo_id}, {'_id': 0})

@api_router.get("/master/iso/reporte-pdf")
async def exportar_reporte_iso_pdf(
    user: dict = Depends(require_master),
    orden_id: Optional[str] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
):
    query = {}

    if orden_id:
        query["id"] = orden_id

    if fecha_desde or fecha_hasta:
        query["created_at"] = {}
        if fecha_desde:
            query["created_at"]["$gte"] = fecha_desde
        if fecha_hasta:
            query["created_at"]["$lte"] = fecha_hasta

    ordenes = await db.ordenes.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 40

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(40, y, "Reporte ISO 9001 - Evidencias ERP")
    y -= 18
    pdf.setFont("Helvetica", 10)
    pdf.drawString(40, y, f"Generado por: {user.get('email')} | Fecha: {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')}")
    y -= 24

    if orden_id:
        pdf.drawString(40, y, f"Filtro OT: {orden_id}")
        y -= 14
    if fecha_desde or fecha_hasta:
        pdf.drawString(40, y, f"Rango: {fecha_desde or '-'} a {fecha_hasta or '-'}")
        y -= 18

    if not ordenes:
        pdf.drawString(40, y, "Sin resultados para los filtros aplicados")
    else:
        for o in ordenes:
            if y < 120:
                pdf.showPage()
                y = height - 40

            consent_count = await db.consentimientos_seguimiento.count_documents({"orden_id": o.get("id")})
            event_count = await db.ot_event_log.count_documents({"ot_id": o.get("id")})
            incidencia_nc = await db.incidencias.find_one(
                {"orden_id": o.get("id"), "$or": [{"es_no_conformidad": True}, {"tipo": {"$in": ["reclamacion", "garantia", "daño_transporte"]}}]},
                {"_id": 0, "numero_incidencia": 1, "capa_estado": 1, "capa_causa_raiz": 1, "capa_accion_correctiva": 1},
            )

            pdf.setFont("Helvetica-Bold", 10)
            pdf.drawString(40, y, f"OT {o.get('numero_orden')} ({o.get('estado')})")
            y -= 14
            pdf.setFont("Helvetica", 9)
            pdf.drawString(50, y, f"Cliente ID: {o.get('cliente_id')} | Creada: {o.get('created_at')} | Enviado: {o.get('fecha_enviado')}")
            y -= 12
            pdf.drawString(50, y, f"Consentimientos seguimiento: {consent_count} | EventLog: {event_count}")
            y -= 12
            pdf.drawString(50, y, f"RI: completada={bool(o.get('ri_completada'))} resultado={o.get('ri_resultado')}")
            y -= 12
            pdf.drawString(
                50,
                y,
                "Checklist recepción/QC: "
                f"recepcion={bool(o.get('recepcion_checklist_completo'))}, "
                f"diag_final={bool(o.get('diagnostico_salida_realizado'))}, "
                f"funciones={bool(o.get('funciones_verificadas'))}, "
                f"limpieza={bool(o.get('limpieza_realizada'))}",
            )
            y -= 12
            pdf.drawString(
                50,
                y,
                "Batería: "
                f"reemplazada={bool(o.get('bateria_reemplazada'))}, "
                f"almacenamiento={bool(o.get('bateria_almacenamiento_temporal'))}, "
                f"residuo_pendiente={bool(o.get('bateria_residuo_pendiente'))}",
            )
            y -= 12

            if incidencia_nc:
                pdf.drawString(
                    50,
                    y,
                    f"NC/CAPA: {incidencia_nc.get('numero_incidencia')} estado={incidencia_nc.get('capa_estado')}",
                )
                y -= 12
            else:
                pdf.drawString(50, y, "NC/CAPA: sin incidencia NC vinculada")
                y -= 12

            y -= 6

    pdf.save()
    buffer.seek(0)
    await _registrar_evento_seguridad(user, 'iso_reporte_pdf_export', {'orden_id': orden_id, 'desde': fecha_desde, 'hasta': fecha_hasta, 'total_ots': len(ordenes)})
    headers = {"Content-Disposition": "attachment; filename=reporte_iso_evidencias.pdf"}
    return StreamingResponse(buffer, media_type="application/pdf", headers=headers)



@api_router.get("/master/analiticas")
async def obtener_analiticas(user: dict = Depends(require_master)):
    """Panel de analíticas completo para master"""
    ordenes = await db.ordenes.find({}, {"_id": 0}).to_list(10000)

    # === MÉTRICAS FINANCIERAS ===
    total_gastos = 0  # Coste de materiales
    total_cobrado = 0  # Precio de venta de órdenes cerradas (enviado)
    total_pendiente_cobrar = 0  # Precio de venta de órdenes completadas pero no cerradas
    gastos_pendientes = 0  # Coste de órdenes no cerradas
    
    for o in ordenes:
        # Usar campos precalculados si existen
        if o.get('presupuesto_total') is not None:
            precio_venta_orden = o.get('presupuesto_total', 0)
            coste_orden = o.get('coste_total', 0)
        else:
            # Fallback: cálculo manual para órdenes antiguas
            materiales = o.get('materiales', [])
            coste_orden = sum(m.get('coste', 0) * m.get('cantidad', 1) for m in materiales)
            precio_venta_orden = sum(m.get('precio_unitario', 0) * m.get('cantidad', 1) for m in materiales)
        
        if o.get('estado') == 'enviado':
            # Orden cerrada
            total_gastos += coste_orden
            total_cobrado += precio_venta_orden
        elif o.get('estado') in ['reparado', 'validacion']:
            # Orden completada pero no cerrada (pendiente de cobrar)
            total_pendiente_cobrar += precio_venta_orden
            gastos_pendientes += coste_orden
        elif o.get('estado') in ['en_taller', 'recibida']:
            # Orden en proceso
            gastos_pendientes += coste_orden
    
    margen_beneficio = total_cobrado - total_gastos
    porcentaje_margen = round((margen_beneficio / total_cobrado * 100) if total_cobrado > 0 else 0, 1)

    # Ingresos por mes
    ingresos_por_mes = {}
    gastos_por_mes = {}
    for o in ordenes:
        if o.get('estado') == 'enviado':
            try:
                fecha = datetime.fromisoformat(o['created_at']) if isinstance(o['created_at'], str) else o['created_at']
                mes = fecha.strftime('%Y-%m')
                
                # Usar campos precalculados
                if o.get('presupuesto_total') is not None:
                    total_venta = o.get('presupuesto_total', 0)
                    total_coste = o.get('coste_total', 0)
                else:
                    materiales = o.get('materiales', [])
                    total_venta = sum(m.get('precio_unitario', 0) * m.get('cantidad', 1) for m in materiales)
                    total_coste = sum(m.get('coste', 0) * m.get('cantidad', 1) for m in materiales)
                
                ingresos_por_mes[mes] = ingresos_por_mes.get(mes, 0) + total_venta
                gastos_por_mes[mes] = gastos_por_mes.get(mes, 0) + total_coste
            except Exception:
                pass

    # Tiempo medio de reparación (en horas)
    tiempos_reparacion = []
    for o in ordenes:
        inicio = o.get('fecha_inicio_reparacion')
        fin = o.get('fecha_fin_reparacion')
        if inicio and fin:
            try:
                i = datetime.fromisoformat(inicio) if isinstance(inicio, str) else inicio
                f = datetime.fromisoformat(fin) if isinstance(fin, str) else fin
                tiempos_reparacion.append((f - i).total_seconds() / 3600)
            except Exception:
                pass
    tiempo_medio = round(sum(tiempos_reparacion) / len(tiempos_reparacion), 1) if tiempos_reparacion else 0

    # Ranking técnicos
    tecnicos = await db.users.find({"role": "tecnico", "activo": True}, {"_id": 0, "password_hash": 0}).to_list(100)
    ranking = []
    for t in tecnicos:
        t_ordenes = [o for o in ordenes if o.get('tecnico_asignado') == t['id']]
        completadas = len([o for o in t_ordenes if o.get('estado') == 'enviado'])
        ranking.append({"nombre": f"{t['nombre']} {t.get('apellidos', '')}", "total": len(t_ordenes), "completadas": completadas, "tasa": round((completadas / len(t_ordenes) * 100) if t_ordenes else 0, 1)})
    ranking.sort(key=lambda x: x['completadas'], reverse=True)

    # Distribución por estado
    dist_estado = {}
    for o in ordenes:
        est = o.get('estado', 'desconocido')
        dist_estado[est] = dist_estado.get(est, 0) + 1

    # Órdenes últimos 12 meses
    ordenes_por_mes = {}
    for o in ordenes:
        try:
            fecha = datetime.fromisoformat(o['created_at']) if isinstance(o['created_at'], str) else o['created_at']
            mes = fecha.strftime('%Y-%m')
            ordenes_por_mes[mes] = ordenes_por_mes.get(mes, 0) + 1
        except Exception:
            pass

    return {
        # Métricas financieras
        "finanzas": {
            "total_gastos": round(total_gastos, 2),
            "total_cobrado": round(total_cobrado, 2),
            "pendiente_cobrar": round(total_pendiente_cobrar, 2),
            "gastos_pendientes": round(gastos_pendientes, 2),
            "margen_beneficio": round(margen_beneficio, 2),
            "porcentaje_margen": porcentaje_margen,
        },
        "ingresos_por_mes": dict(sorted(ingresos_por_mes.items())[-12:]),
        "gastos_por_mes": dict(sorted(gastos_por_mes.items())[-12:]),
        "tiempo_medio_reparacion_horas": tiempo_medio,
        "ranking_tecnicos": ranking,
        "distribucion_estado": dist_estado,
        "ordenes_por_mes": dict(sorted(ordenes_por_mes.items())[-12:]),
        "total_ordenes": len(ordenes),
        "total_completadas": len([o for o in ordenes if o.get('estado') == 'enviado']),
        "total_en_proceso": len([o for o in ordenes if o.get('estado') in ['en_taller', 'reparado', 'validacion']]),
    }


@api_router.get("/master/finanzas")
async def obtener_finanzas(
    periodo: str = "mes",  # mes, semana, trimestre, año, custom
    fecha_inicio: str = None,
    fecha_fin: str = None,
    user: dict = Depends(require_master)
):
    """
    Panel financiero detallado con filtros por período.
    - Total a facturar (presupuestos aceptados)
    - Desglose por semana/mes
    - Proyecciones
    - Clasificación por estado de facturación
    """
    from datetime import timedelta
    
    ahora = datetime.now(timezone.utc)
    
    # Determinar rango de fechas según período
    if fecha_inicio and fecha_fin:
        inicio = datetime.fromisoformat(fecha_inicio.replace('Z', '+00:00'))
        fin = datetime.fromisoformat(fecha_fin.replace('Z', '+00:00'))
    elif periodo == "semana":
        inicio = ahora - timedelta(days=ahora.weekday())  # Lunes de esta semana
        inicio = inicio.replace(hour=0, minute=0, second=0, microsecond=0)
        fin = ahora
    elif periodo == "mes":
        inicio = ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        fin = ahora
    elif periodo == "trimestre":
        trimestre_mes = ((ahora.month - 1) // 3) * 3 + 1
        inicio = ahora.replace(month=trimestre_mes, day=1, hour=0, minute=0, second=0, microsecond=0)
        fin = ahora
    elif periodo == "año":
        inicio = ahora.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        fin = ahora
    else:  # Por defecto mes actual
        inicio = ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        fin = ahora
    
    # Obtener todas las órdenes del período
    ordenes = await db.ordenes.find({
        "created_at": {"$gte": inicio.isoformat(), "$lte": fin.isoformat()}
    }, {"_id": 0}).to_list(10000)
    
    # También obtener órdenes anteriores pendientes de facturar
    ordenes_pendientes_anteriores = await db.ordenes.find({
        "created_at": {"$lt": inicio.isoformat()},
        "estado": {"$in": ["reparado", "validacion", "en_taller", "recibida", "pendiente_recibir"]}
    }, {"_id": 0}).to_list(10000)
    
    # === CLASIFICACIÓN DE ÓRDENES ===
    facturado = []  # Órdenes cerradas (estado: enviado)
    pendiente_facturar = []  # Órdenes completadas pero no cerradas (reparado, validacion)
    en_proceso = []  # Órdenes en taller
    por_recibir = []  # Órdenes pendientes de recibir
    
    for o in ordenes:
        estado = o.get('estado', '')
        
        # Usar los campos precalculados, con fallback a cálculo manual si no existen
        if o.get('presupuesto_total') is not None:
            valor_orden = o.get('presupuesto_total', 0)
            coste_materiales = o.get('coste_total', 0)
            beneficio = o.get('beneficio_estimado', 0)
        else:
            # Fallback: calcular manualmente para órdenes antiguas
            materiales = o.get('materiales', [])
            precio_materiales = sum(m.get('precio_unitario', 0) * m.get('cantidad', 1) for m in materiales)
            coste_materiales = sum(m.get('coste', 0) * m.get('cantidad', 1) for m in materiales)
            
            presupuesto_enviado = o.get('presupuesto_enviado') or {}
            datos_portal = o.get('datos_portal') or {}
            precio_presupuesto = presupuesto_enviado.get('precio', 0) or datos_portal.get('price', 0)
            valor_orden = precio_presupuesto if precio_presupuesto > 0 else precio_materiales
            beneficio = valor_orden - coste_materiales
        
        dispositivo = o.get('dispositivo') or {}
        orden_data = {
            "id": o.get('id'),
            "numero_orden": o.get('numero_orden'),
            "estado": estado,
            "valor": valor_orden,
            "coste": coste_materiales,
            "beneficio": beneficio,
            "cliente": o.get('cliente_nombre', 'N/A'),
            "dispositivo": f"{dispositivo.get('marca', '')} {dispositivo.get('modelo', '')}".strip(),
            "fecha": o.get('created_at'),
            "origen": o.get('origen', 'directo')
        }
        
        if estado == 'enviado':
            facturado.append(orden_data)
        elif estado in ['reparado', 'validacion']:
            pendiente_facturar.append(orden_data)
        elif estado in ['en_taller', 'recibida']:
            en_proceso.append(orden_data)
        elif estado == 'pendiente_recibir':
            por_recibir.append(orden_data)
    
    # === TOTALES ===
    total_facturado = sum(o['valor'] for o in facturado)
    total_pendiente = sum(o['valor'] for o in pendiente_facturar)
    total_en_proceso = sum(o['valor'] for o in en_proceso)
    total_por_recibir = sum(o['valor'] for o in por_recibir)
    
    total_coste_facturado = sum(o['coste'] for o in facturado)
    total_coste_pendiente = sum(o['coste'] for o in pendiente_facturar)
    
    # === DESGLOSE POR SEMANA (últimas 4 semanas del período) ===
    semanas = {}
    for o in ordenes:
        try:
            fecha = datetime.fromisoformat(o['created_at']) if isinstance(o['created_at'], str) else o['created_at']
            semana_num = fecha.isocalendar()[1]
            semana_key = f"S{semana_num}"
            
            if semana_key not in semanas:
                semanas[semana_key] = {"ordenes": 0, "valor": 0, "facturado": 0, "pendiente": 0}
            
            materiales = o.get('materiales', [])
            pres_env = o.get('presupuesto_enviado') or {}
            precio = pres_env.get('precio', 0) or sum(m.get('precio_unitario', 0) * m.get('cantidad', 1) for m in materiales)
            
            semanas[semana_key]["ordenes"] += 1
            semanas[semana_key]["valor"] += precio
            
            if o.get('estado') == 'enviado':
                semanas[semana_key]["facturado"] += precio
            elif o.get('estado') in ['reparado', 'validacion']:
                semanas[semana_key]["pendiente"] += precio
        except Exception:
            pass
    
    # === PROYECCIÓN ===
    dias_transcurridos = (ahora - inicio).days + 1
    
    if periodo == "mes":
        dias_totales = 30
    elif periodo == "semana":
        dias_totales = 7
    elif periodo == "trimestre":
        dias_totales = 90
    elif periodo == "año":
        dias_totales = 365
    else:
        dias_totales = dias_transcurridos
    
    # Proyección basada en ritmo actual
    ritmo_diario = (total_facturado + total_pendiente + total_en_proceso) / dias_transcurridos if dias_transcurridos > 0 else 0
    proyeccion_periodo = ritmo_diario * dias_totales
    
    # Ticket medio
    ordenes_con_valor = [o for o in ordenes if (o.get('presupuesto_enviado') or {}).get('precio', 0) > 0 or sum(m.get('precio_unitario', 0) for m in o.get('materiales', []))]
    ticket_medio = (total_facturado + total_pendiente + total_en_proceso) / len(ordenes_con_valor) if ordenes_con_valor else 0
    
    # === COMPARATIVA CON PERÍODO ANTERIOR ===
    duracion_periodo = fin - inicio
    inicio_anterior = inicio - duracion_periodo
    fin_anterior = inicio
    
    ordenes_anterior = await db.ordenes.find({
        "created_at": {"$gte": inicio_anterior.isoformat(), "$lt": fin_anterior.isoformat()}
    }, {"_id": 0}).to_list(10000)
    
    total_anterior = 0
    for o in ordenes_anterior:
        materiales = o.get('materiales', [])
        pres_env_ant = o.get('presupuesto_enviado') or {}
        precio = pres_env_ant.get('precio', 0) or sum(m.get('precio_unitario', 0) * m.get('cantidad', 1) for m in materiales)
        total_anterior += precio
    
    variacion_porcentaje = round(((total_facturado + total_pendiente - total_anterior) / total_anterior * 100) if total_anterior > 0 else 0, 1)
    
    return {
        "periodo": {
            "tipo": periodo,
            "inicio": inicio.isoformat(),
            "fin": fin.isoformat(),
            "dias_transcurridos": dias_transcurridos,
            "dias_totales": dias_totales
        },
        "resumen": {
            "total_ordenes": len(ordenes),
            "total_a_facturar": round(total_facturado + total_pendiente + total_en_proceso + total_por_recibir, 2),
            "ya_facturado": round(total_facturado, 2),
            "pendiente_facturar": round(total_pendiente, 2),
            "en_proceso": round(total_en_proceso, 2),
            "por_recibir": round(total_por_recibir, 2),
            "ticket_medio": round(ticket_medio, 2),
        },
        "costes": {
            "total_costes": round(total_coste_facturado + total_coste_pendiente, 2),
            "costes_facturado": round(total_coste_facturado, 2),
            "costes_pendiente": round(total_coste_pendiente, 2),
        },
        "beneficio": {
            "beneficio_facturado": round(total_facturado - total_coste_facturado, 2),
            "beneficio_estimado_pendiente": round(total_pendiente - total_coste_pendiente, 2),
            "margen_porcentaje": round(((total_facturado - total_coste_facturado) / total_facturado * 100) if total_facturado > 0 else 0, 1),
        },
        "proyeccion": {
            "ritmo_diario": round(ritmo_diario, 2),
            "proyeccion_periodo": round(proyeccion_periodo, 2),
            "proyeccion_mensual": round(ritmo_diario * 30, 2),
            "proyeccion_anual": round(ritmo_diario * 365, 2),
        },
        "comparativa": {
            "periodo_anterior": round(total_anterior, 2),
            "variacion_porcentaje": variacion_porcentaje,
            "tendencia": "alza" if variacion_porcentaje > 0 else "baja" if variacion_porcentaje < 0 else "estable"
        },
        "desglose_semanal": dict(sorted(semanas.items())),
        "clasificacion": {
            "facturado": {"count": len(facturado), "total": round(total_facturado, 2), "ordenes": facturado[:10]},
            "pendiente_facturar": {"count": len(pendiente_facturar), "total": round(total_pendiente, 2), "ordenes": pendiente_facturar[:10]},
            "en_proceso": {"count": len(en_proceso), "total": round(total_en_proceso, 2), "ordenes": en_proceso[:10]},
            "por_recibir": {"count": len(por_recibir), "total": round(total_por_recibir, 2), "ordenes": por_recibir[:10]},
        },
        "pendientes_anteriores": {
            "count": len(ordenes_pendientes_anteriores),
            "total": round(sum(
                (o.get('presupuesto_enviado') or {}).get('precio', 0) or 
                sum(m.get('precio_unitario', 0) * m.get('cantidad', 1) for m in o.get('materiales', []))
                for o in ordenes_pendientes_anteriores
            ), 2)
        }
    }


# ==================== ASISTENTE IA ====================

try:
    from emergentintegrations.llm.chat import LlmChat, UserMessage
except ImportError:
    LlmChat = None
    UserMessage = None

class MejorarDiagnosticoRequest(BaseModel):
    diagnostico: str
    modelo_dispositivo: Optional[str] = None
    sintomas: Optional[str] = None

@api_router.post("/ia/mejorar-texto")
async def ia_mejorar_texto(request: IARequest, user: dict = Depends(require_auth)):
    if not EMERGENT_LLM_KEY or not LlmChat:
        raise HTTPException(status_code=500, detail="LLM no configurado")
    try:
        chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"mejorar-{user['user_id']}-{uuid.uuid4()}", system_message="Eres un asistente de redacción para un servicio técnico de reparación de móviles. Mejora textos haciéndolos más claros y profesionales. IMPORTANTE: Escribe en texto plano, sin markdown, sin asteriscos, sin negritas. Responde SOLO con el texto mejorado en español.").with_model("gemini", "gemini-3-flash-preview")
        prompt = f"Mejora el siguiente texto:\n\n{request.texto}"
        if request.contexto:
            prompt = f"Contexto: {request.contexto}\n\n{prompt}"
        response = await chat.send_message(UserMessage(text=prompt))
        return {"texto_mejorado": response, "original": request.texto}
    except Exception as e:
        logger.error(f"Error IA: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/ia/mejorar-diagnostico")
async def ia_mejorar_diagnostico(request: MejorarDiagnosticoRequest, user: dict = Depends(require_auth)):
    if not EMERGENT_LLM_KEY or not LlmChat:
        raise HTTPException(status_code=500, detail="LLM no configurado")
    try:
        ctx = ""
        if request.modelo_dispositivo:
            ctx += f"Dispositivo: {request.modelo_dispositivo}\n"
        if request.sintomas:
            ctx += f"Síntomas: {request.sintomas}\n"
        chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"diag-{user['user_id']}-{uuid.uuid4()}", system_message="Eres un técnico experto en reparación de móviles. Mejora diagnósticos para que sean claros y comprensibles. IMPORTANTE: Texto plano, sin markdown. Responde SOLO con el diagnóstico mejorado en español.").with_model("gemini", "gemini-3-flash-preview")
        response = await chat.send_message(UserMessage(text=f"{ctx}\nDIAGNÓSTICO ORIGINAL:\n{request.diagnostico}\n\nMejora este diagnóstico:"))
        return {"diagnostico_mejorado": response, "original": request.diagnostico}
    except Exception as e:
        logger.error(f"Error IA: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/ia/consulta")
async def ia_consulta(request: IAChatRequest, user: dict = Depends(require_auth)):
    if not EMERGENT_LLM_KEY or not LlmChat:
        raise HTTPException(status_code=500, detail="LLM no configurado")
    try:
        historial = await db.ia_chat_history.find({"session_id": request.session_id, "user_id": user['user_id']}).sort("created_at", 1).to_list(20)
        ctx = "\n".join([f"{'Usuario' if m['role']=='user' else 'Asistente'}: {m['content']}" for m in historial[-10:]])
        
        # System prompt completo del sistema NEXORA
        system_prompt = """Eres el asistente IA de NEXORA, un sistema CRM/ERP completo para servicios técnicos de reparación de telefonía móvil.

MÓDULOS DEL SISTEMA:
1. ÓRDENES DE TRABAJO (/ordenes): Crear, gestionar y seguir reparaciones. Estados: pendiente_recibir, recibida, en_taller, re_presupuestar, reparado, validacion, enviado, garantia, cancelado, reemplazo, irreparable.
2. CLIENTES (/clientes): Base de datos de clientes con historial de órdenes.
3. INVENTARIO (/inventario): Gestión de repuestos, stock y etiquetas con código de barras.
4. INSURAMA (/insurama): Integración con seguros vía Sumbroker. Polling automático cada 30 min para detectar nuevos siniestros.
5. PRE-REGISTROS (/pre-registros): Siniestros de Insurama pendientes de convertir en órdenes.
6. LOGÍSTICA (/logistica): Control de recogidas y envíos con alertas de retraso +48h.
7. PROVEEDORES (/proveedores): Gestión de proveedores de piezas.
8. ÓRDENES DE COMPRA (/ordenes-compra): Registro de compras de material.
9. USUARIOS (/usuarios): Roles: master, admin, tecnico.
10. NOTIFICACIONES: Sistema en tiempo real con WebSocket y popups.
11. SCANNER (/scanner): Lectura de QR/códigos de barras para cambio rápido de estado.
12. CALENDARIO (/calendario): Vista de órdenes por fecha.

FUNCIONES DE IA DISPONIBLES:
- Diagnósticos inteligentes basados en síntomas
- Mejora de textos y diagnósticos
- Consultas sobre el sistema

ACCESO A DATOS:
Puedo ayudarte a entender cómo usar cualquier módulo, explicar flujos de trabajo y responder preguntas sobre el sistema.

FORMATO: Responde siempre en español, texto plano sin markdown.

Historial de conversación:
""" + ctx
        
        chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"consulta-{user['user_id']}-{request.session_id}", system_message=system_prompt).with_model("gemini", "gemini-3-flash-preview")
        response = await chat.send_message(UserMessage(text=request.mensaje))
        now = datetime.now(timezone.utc).isoformat()
        await db.ia_chat_history.insert_many([{"session_id": request.session_id, "user_id": user['user_id'], "role": "user", "content": request.mensaje, "created_at": now}, {"session_id": request.session_id, "user_id": user['user_id'], "role": "assistant", "content": response, "created_at": now}])
        return {"respuesta": response, "session_id": request.session_id}
    except Exception as e:
        logger.error(f"Error IA: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/ia/historial/{session_id}")
async def ia_historial(session_id: str, user: dict = Depends(require_auth)):
    return await db.ia_chat_history.find({"session_id": session_id, "user_id": user['user_id']}, {"_id": 0}).sort("created_at", 1).to_list(100)

@api_router.delete("/ia/historial/{session_id}")
async def ia_limpiar_historial(session_id: str, user: dict = Depends(require_auth)):
    await db.ia_chat_history.delete_many({"session_id": session_id, "user_id": user['user_id']})
    return {"message": "Historial limpiado"}

@api_router.post("/ia/diagnostico")
async def ia_diagnostico(modelo: str, sintomas: str, user: dict = Depends(require_auth)):
    if not EMERGENT_LLM_KEY or not LlmChat:
        raise HTTPException(status_code=500, detail="LLM no configurado")
    try:
        chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"diagnostico-{user['user_id']}-{uuid.uuid4()}", system_message="Eres un técnico experto en reparación de móviles. Proporciona diagnósticos basados en síntomas. FORMATO: Texto plano, sin markdown. Español.").with_model("gemini", "gemini-3-flash-preview")
        response = await chat.send_message(UserMessage(text=f"Dispositivo: {modelo}\nSíntomas: {sintomas}\n\nProporciona diagnóstico."))
        return {"diagnostico": response, "modelo": modelo, "sintomas": sintomas}
    except Exception as e:
        logger.error(f"Error IA: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== RESTOS / DESPIECE ====================

@api_router.get("/restos")
async def listar_restos(
    estado: Optional[str] = None,
    tipo: Optional[str] = None,
    limit: int = 100,
    user: dict = Depends(require_admin)
):
    """Lista todos los dispositivos en restos/despiece"""
    query = {}
    if estado:
        query["estado"] = estado
    if tipo:
        query["tipo"] = tipo
    return await db.restos.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)

@api_router.get("/restos/{resto_id}")
async def obtener_resto(resto_id: str, user: dict = Depends(require_admin)):
    """Obtiene un resto específico por ID"""
    resto = await db.restos.find_one({"id": resto_id}, {"_id": 0})
    if not resto:
        raise HTTPException(status_code=404, detail="Resto no encontrado")
    # Añadir info de la orden original
    if resto.get('orden_id'):
        resto['orden_original'] = await db.ordenes.find_one({"id": resto['orden_id']}, {"_id": 0})
    return resto

@api_router.post("/restos")
async def crear_resto(data: dict, user: dict = Depends(require_admin)):
    """Crea un nuevo registro de resto/despiece"""
    from models import Resto
    resto = Resto(
        orden_id=data.get('orden_id', ''),
        numero_orden=data.get('numero_orden', ''),
        tipo=data.get('tipo', 'dispositivo_reemplazado'),
        modelo=data.get('modelo', ''),
        imei=data.get('imei'),
        color=data.get('color'),
        descripcion_daños=data.get('descripcion_daños'),
        ubicacion=data.get('ubicacion'),
        notas=data.get('notas'),
    )
    doc = resto.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    doc['fecha_recepcion'] = doc['fecha_recepcion'].isoformat()
    await db.restos.insert_one(doc)
    doc.pop('_id', None)
    
    # Log de auditoría
    from routes.ordenes_routes import log_audit
    await log_audit("resto", doc['id'], user, "resto_creado", f"Creado resto {doc['codigo_resto']} desde orden {data.get('numero_orden', 'N/A')}")
    
    return doc

@api_router.put("/restos/{resto_id}")
async def actualizar_resto(resto_id: str, data: dict, user: dict = Depends(require_admin)):
    """Actualiza un resto existente"""
    resto = await db.restos.find_one({"id": resto_id}, {"_id": 0})
    if not resto:
        raise HTTPException(status_code=404, detail="Resto no encontrado")
    
    update_data = {k: v for k, v in data.items() if v is not None and k not in ['id', 'codigo_resto', 'created_at']}
    update_data['updated_at'] = datetime.now(timezone.utc).isoformat()
    
    # Si cambia a clasificado o despiezado, actualizar fechas
    if data.get('estado') == 'clasificado' and resto.get('estado') != 'clasificado':
        update_data['fecha_clasificacion'] = datetime.now(timezone.utc).isoformat()
    if data.get('estado') == 'despiezado' and resto.get('estado') != 'despiezado':
        update_data['fecha_despiece'] = datetime.now(timezone.utc).isoformat()
    
    await db.restos.update_one({"id": resto_id}, {"$set": update_data})
    return await db.restos.find_one({"id": resto_id}, {"_id": 0})

@api_router.post("/restos/{resto_id}/piezas")
async def añadir_pieza_resto(resto_id: str, data: dict, user: dict = Depends(require_admin)):
    """Añade una pieza extraída a un resto"""
    resto = await db.restos.find_one({"id": resto_id}, {"_id": 0})
    if not resto:
        raise HTTPException(status_code=404, detail="Resto no encontrado")
    
    from models import PiezaResto
    pieza = PiezaResto(
        nombre=data.get('nombre', ''),
        estado=data.get('estado', 'bueno'),
        destino=data.get('destino'),
        codigo_inventario=data.get('codigo_inventario'),
        notas=data.get('notas'),
    )
    pieza_doc = pieza.model_dump()
    
    piezas_actuales = resto.get('piezas', [])
    piezas_actuales.append(pieza_doc)
    piezas_utiles = len([p for p in piezas_actuales if p.get('estado') in ['bueno', 'aceptable']])
    
    await db.restos.update_one({"id": resto_id}, {
        "$set": {
            "piezas": piezas_actuales,
            "piezas_utiles": piezas_utiles,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
    })
    
    return await db.restos.find_one({"id": resto_id}, {"_id": 0})

@api_router.delete("/restos/{resto_id}/piezas/{pieza_id}")
async def eliminar_pieza_resto(resto_id: str, pieza_id: str, user: dict = Depends(require_admin)):
    """Elimina una pieza de un resto"""
    resto = await db.restos.find_one({"id": resto_id}, {"_id": 0})
    if not resto:
        raise HTTPException(status_code=404, detail="Resto no encontrado")
    
    piezas = [p for p in resto.get('piezas', []) if p.get('id') != pieza_id]
    piezas_utiles = len([p for p in piezas if p.get('estado') in ['bueno', 'aceptable']])
    
    await db.restos.update_one({"id": resto_id}, {
        "$set": {
            "piezas": piezas,
            "piezas_utiles": piezas_utiles,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
    })
    
    return {"message": "Pieza eliminada"}

@api_router.post("/ordenes/{orden_id}/enviar-a-restos")
async def enviar_orden_a_restos(orden_id: str, data: dict, user: dict = Depends(require_admin)):
    """Envía el dispositivo de una orden a restos (usado cuando se reemplaza)"""
    orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    
    from models import Resto
    resto = Resto(
        orden_id=orden_id,
        numero_orden=orden['numero_orden'],
        tipo=data.get('tipo', 'dispositivo_reemplazado'),
        modelo=orden['dispositivo']['modelo'],
        imei=orden['dispositivo'].get('imei'),
        color=orden['dispositivo'].get('color'),
        descripcion_daños=orden['dispositivo'].get('daños'),
        ubicacion=data.get('ubicacion'),
        notas=data.get('notas', f"Dispositivo original de orden {orden['numero_orden']} - Reemplazado"),
    )
    doc = resto.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    doc['fecha_recepcion'] = doc['fecha_recepcion'].isoformat()
    await db.restos.insert_one(doc)
    doc.pop('_id', None)
    
    # Actualizar la orden con referencia al resto
    await db.ordenes.update_one({"id": orden_id}, {
        "$set": {
            "resto_id": doc['id'],
            "resto_codigo": doc['codigo_resto'],
            "dispositivo_enviado_a_restos": True,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
    })
    
    # Log de auditoría
    from routes.ordenes_routes import log_audit
    await log_audit("resto", doc['id'], user, "envio_a_restos", f"Dispositivo de orden {orden['numero_orden']} enviado a restos con código {doc['codigo_resto']}")
    
    return {
        "message": f"Dispositivo enviado a restos",
        "codigo_resto": doc['codigo_resto'],
        "resto": doc
    }

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

    # Log SMTP status
    if cfg.SMTP_CONFIGURED:
        logger.info("SMTP configurado: %s:%s", cfg.SMTP_HOST, cfg.SMTP_PORT)
    else:
        logger.warning("SMTP no configurado")

    # Database initialization - wrapped in try/except to not crash the server
    try:
        # Create default users
        from auth import hash_password as hp
        defaults = [
            {"id": "master-001", "email": "master@techrepair.local", "nombre": "Master Admin", "role": "master", "password_hash": hp("master123")},
            {"id": "admin-001", "email": "admin@techrepair.local", "nombre": "Admin Principal", "role": "admin", "password_hash": hp("admin123")},
            {"id": "tecnico-001", "email": "tecnico@techrepair.local", "nombre": "Técnico Demo", "role": "tecnico", "password_hash": hp("tecnico123")},
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

@app.on_event("shutdown")
async def shutdown_db_client():
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


