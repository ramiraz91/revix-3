"""
GLS Routes - FastAPI endpoints for GLS logistics module.
All routes prefixed with /api/gls/

MÓDULO LOGÍSTICO COMPLETO:
- CRUD de envíos, recogidas y devoluciones
- Etiquetas con cache persistente
- Tracking y eventos
- Sincronización automática
- Notificaciones al cliente
- Auditoría completa
"""
import base64
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from fastapi.responses import Response
from pydantic import BaseModel

from config import db
from auth import require_auth

from modules.gls.models import GLSConfigUpdate, GLSCreateShipment, GLSLabelFormat, GLSShipmentType
from modules.gls.state_mapper import GLS_SERVICES, GLS_SCHEDULES, STATE_BADGES
from modules.gls import shipment_service

router = APIRouter(prefix="/gls", tags=["GLS Logística"])


def _require_admin(user: dict):
    if user.get("role") not in ("admin", "master"):
        raise HTTPException(403, "Acceso restringido a administradores")


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/config")
async def get_gls_config(user: dict = Depends(require_auth)):
    """Get GLS configuration (admin only, UID NUNCA expuesto)."""
    _require_admin(user)
    config = await shipment_service.get_config(db)
    
    # PRIORIDAD 2: NUNCA exponer uid_cliente al frontend
    uid = config.get("uid_cliente", "")
    safe = {k: v for k, v in config.items() if k != "uid_cliente"}
    safe["uid_masked"] = f"{uid[:8]}...{uid[-4:]}" if len(uid) > 12 else ("***" if uid else "")
    safe["uid_configurado"] = bool(uid)
    
    return safe


@router.post("/config")
async def save_gls_config(data: GLSConfigUpdate, user: dict = Depends(require_auth)):
    """Save GLS configuration (admin only)."""
    _require_admin(user)
    await shipment_service.save_config(db, data.dict())
    return {"message": "Configuración GLS guardada"}


@router.get("/status")
async def get_gls_status(user: dict = Depends(require_auth)):
    """Check if GLS integration is active and properly configured."""
    is_active = await shipment_service.is_gls_active(db)
    return {"active": is_active}


# ═══════════════════════════════════════════════════════════════════════════════
# ENVÍOS (CRUD)
# ═══════════════════════════════════════════════════════════════════════════════

class CreateShipmentRequest(BaseModel):
    orden_id: str
    tipo: GLSShipmentType = GLSShipmentType.ENVIO
    dest_nombre: str
    dest_direccion: str
    dest_poblacion: str = ""
    dest_provincia: str = ""
    dest_cp: str
    dest_telefono: str = ""
    dest_email: str = ""
    dest_observaciones: str = ""
    bultos: int = 1
    peso: float = 1.0
    referencia: str = ""
    servicio: str = ""
    horario: str = ""
    formato_etiqueta: str = "PDF"
    skip_duplicate_check: bool = False
    notify_client: bool = False


@router.post("/envios")
async def crear_envio(data: CreateShipmentRequest, user: dict = Depends(require_auth)):
    """
    Create a GLS shipment (envio, recogida, or devolucion).
    
    - Validates data and checks for duplicates
    - Calls GLS SOAP API
    - Stores shipment and label in DB
    - Updates order with GLS reference
    - Optionally notifies client
    """
    _require_admin(user)
    result = await shipment_service.create_shipment(
        db, 
        data.dict(), 
        user.get("email", ""),
        skip_duplicate_check=data.skip_duplicate_check,
        notify_client=data.notify_client
    )
    if not result["success"]:
        status_code = 409 if result.get("duplicate") else 400
        raise HTTPException(status_code, result.get("error", "Error al crear envío GLS"))
    return result


@router.get("/envios")
async def listar_envios(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    search: Optional[str] = None,
    estado: Optional[str] = None,
    tipo: Optional[str] = None,
    orden_id: Optional[str] = None,
    es_final: Optional[bool] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    user: dict = Depends(require_auth),
):
    """List GLS shipments with filters and pagination."""
    filters = {}
    if search:
        filters["search"] = search
    if estado:
        filters["estado_interno"] = estado
    if tipo:
        filters["tipo"] = tipo
    if orden_id:
        filters["entidad_id"] = orden_id
    if es_final is not None:
        filters["es_final"] = es_final
    if fecha_desde:
        filters["fecha_desde"] = fecha_desde
    if fecha_hasta:
        filters["fecha_hasta"] = fecha_hasta

    return await shipment_service.list_shipments(db, filters, page, limit)


@router.get("/envios/{shipment_id}")
async def detalle_envio(
    shipment_id: str, 
    raw: bool = False, 
    user: dict = Depends(require_auth)
):
    """Get full shipment detail including events and logs."""
    include_raw = raw and user.get("role") in ("admin", "master")
    detail = await shipment_service.get_shipment_detail(db, shipment_id, include_raw)
    if not detail:
        raise HTTPException(404, "Envío no encontrado")
    return detail


@router.delete("/envios/{shipment_id}")
async def anular_envio(
    shipment_id: str, 
    motivo: str = Query("", description="Motivo de anulación"),
    user: dict = Depends(require_auth)
):
    """Cancel/annul a GLS shipment."""
    _require_admin(user)
    result = await shipment_service.cancel_shipment(db, shipment_id, user.get("email", ""), motivo)
    if not result["success"]:
        raise HTTPException(400, result.get("error"))
    return {"message": "Envío anulado"}


# ═══════════════════════════════════════════════════════════════════════════════
# VERIFICACIÓN DE DUPLICADOS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/check-duplicate/{orden_id}/{tipo}")
async def check_duplicate(
    orden_id: str,
    tipo: str,
    user: dict = Depends(require_auth)
):
    """Check if there's already an active shipment of this type for the order."""
    existing = await shipment_service.check_duplicate_shipment(db, orden_id, tipo)
    return {
        "has_duplicate": existing is not None,
        "existing_shipment": existing
    }


# ═══════════════════════════════════════════════════════════════════════════════
# ETIQUETAS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/etiqueta/{shipment_id}")
async def descargar_etiqueta(
    shipment_id: str,
    formato: GLSLabelFormat = GLSLabelFormat.PDF,
    force_refresh: bool = Query(False, description="Forzar descarga desde GLS ignorando cache"),
    user: dict = Depends(require_auth),
):
    """
    Download label for a specific shipment.
    Uses cached version if available, unless force_refresh is True.
    """
    result = await shipment_service.get_label(db, shipment_id, force_refresh=force_refresh)
    if not result.get("success") or not result.get("labels"):
        raise HTTPException(404, result.get("error", "Etiqueta no disponible"))

    label_b64 = result["labels"][0]
    label_bytes = base64.b64decode(label_b64)

    content_types = {
        "PDF": "application/pdf",
        "PNG": "image/png",
        "JPG": "image/jpeg",
        "EPL": "application/octet-stream",
        "DPL": "application/octet-stream",
        "XML": "application/xml",
    }
    ct = content_types.get(formato.value, "application/octet-stream")
    ext = formato.value.lower()

    headers = {
        "Content-Disposition": f'attachment; filename="etiqueta_gls_{shipment_id[:8]}.{ext}"',
        "X-Label-Cached": "true" if result.get("cached") else "false"
    }

    return Response(content=label_bytes, media_type=ct, headers=headers)


@router.get("/etiqueta-por-codigo/{codigo}")
async def descargar_etiqueta_por_codigo(
    codigo: str,
    formato: GLSLabelFormat = GLSLabelFormat.PDF,
    user: dict = Depends(require_auth),
):
    """Download label by barcode/reference (for reprint without shipment_id)."""
    result = await shipment_service.get_label_by_code(db, codigo, formato.value)
    if not result.get("success") or not result.get("labels"):
        raise HTTPException(404, result.get("error", "Etiqueta no disponible"))

    label_b64 = result["labels"][0]
    label_bytes = base64.b64decode(label_b64)

    ct = "application/pdf" if formato == GLSLabelFormat.PDF else "application/octet-stream"
    ext = formato.value.lower()
    return Response(
        content=label_bytes,
        media_type=ct,
        headers={"Content-Disposition": f'attachment; filename="etiqueta_gls_{codigo}.{ext}"'}
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TRACKING
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/tracking-url/{codbarras}")
async def obtener_url_tracking(codbarras: str):
    """Get GLS tracking URL for a barcode (public, no auth required for customer sharing)."""
    url = shipment_service.get_tracking_url(codbarras)
    if not url:
        raise HTTPException(400, "Código de barras inválido")
    return {"tracking_url": url, "codbarras": codbarras}


@router.get("/tracking/{shipment_id}")
async def consultar_tracking(
    shipment_id: str, 
    notify: bool = Query(False, description="Notificar al cliente si hay cambios"),
    user: dict = Depends(require_auth)
):
    """Get full tracking for a shipment and update DB."""
    result = await shipment_service.get_tracking(db, shipment_id, notify_on_change=notify)
    if not result.get("success"):
        raise HTTPException(400, result.get("error", "No se pudo obtener tracking"))
    return result


@router.get("/tracking-por-codigo/{codigo}")
async def consultar_tracking_por_codigo(codigo: str, user: dict = Depends(require_auth)):
    """Get tracking by barcode/reference (quick lookup without updating DB)."""
    config = await shipment_service.get_config(db)
    uid = config.get("uid_cliente", "")
    if not uid:
        raise HTTPException(400, "GLS no configurado")

    from modules.gls.soap_client import get_exp_cli
    result = await get_exp_cli(uid, codigo)
    if not result.get("success"):
        raise HTTPException(404, "Envío no encontrado en GLS")
    return result


@router.get("/eventos/{shipment_id}")
async def obtener_eventos(shipment_id: str, user: dict = Depends(require_auth)):
    """Get tracking events timeline for a shipment."""
    events = await db.gls_tracking_events.find(
        {"shipment_id": shipment_id}, {"_id": 0}
    ).sort("fecha_evento", -1).to_list(200)
    return {"events": events, "total": len(events)}


# ═══════════════════════════════════════════════════════════════════════════════
# SINCRONIZACIÓN
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/sync")
async def sync_manual(
    notify: bool = Query(False, description="Notificar a clientes si hay cambios"),
    user: dict = Depends(require_auth)
):
    """Trigger manual sync of all active (non-final) shipments."""
    _require_admin(user)
    stats = await shipment_service.sync_shipments(db, notify_on_change=notify)
    return stats


@router.post("/sync/{shipment_id}")
async def sync_single(
    shipment_id: str, 
    notify: bool = Query(False, description="Notificar al cliente si hay cambios"),
    user: dict = Depends(require_auth)
):
    """Sync a single shipment."""
    result = await shipment_service.get_tracking(db, shipment_id, notify_on_change=notify)
    return {
        "success": result.get("success", False), 
        "tracking": result,
        "state_changed": result.get("state_changed", False)
    }


@router.post("/sync-orden/{orden_id}")
async def sync_orden(orden_id: str, user: dict = Depends(require_auth)):
    """Sync all shipments for a specific order."""
    result = await shipment_service.sync_orden_shipments(db, orden_id)
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# NOTIFICACIONES
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/notificar/{shipment_id}")
async def notificar_cliente(
    shipment_id: str,
    tipo: str = Query("tracking", description="Tipo de notificación: tracking, creacion"),
    user: dict = Depends(require_auth)
):
    """Manually trigger client notification for a shipment."""
    _require_admin(user)
    result = await shipment_service.notify_client(db, shipment_id, tipo)
    if not result["success"]:
        raise HTTPException(400, result.get("error"))
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# DATOS MAESTROS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/maestros")
async def get_maestros(user: dict = Depends(require_auth)):
    """Return GLS reference data (services, schedules, state badges)."""
    return {
        "servicios": GLS_SERVICES,
        "horarios": GLS_SCHEDULES,
        "estados": STATE_BADGES,
        "tipos_envio": [
            {"value": "envio", "label": "Envío"},
            {"value": "recogida", "label": "Recogida"},
            {"value": "devolucion", "label": "Devolución"},
        ]
    }


# ═══════════════════════════════════════════════════════════════════════════════
# LOGS Y AUDITORÍA
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/logs/{shipment_id}")
async def get_logs(shipment_id: str, user: dict = Depends(require_auth)):
    """Get integration logs for a shipment (admin only)."""
    _require_admin(user)
    logs = await db.gls_logs.find(
        {"shipment_id": shipment_id}, {"_id": 0}
    ).sort("fecha", -1).to_list(100)
    return {"logs": logs, "total": len(logs)}


@router.get("/logs/orden/{orden_id}")
async def get_orden_logs(orden_id: str, user: dict = Depends(require_auth)):
    """Get all GLS logs for an order (admin only)."""
    _require_admin(user)
    logs = await db.gls_logs.find(
        {"orden_id": orden_id}, {"_id": 0}
    ).sort("fecha", -1).to_list(200)
    return {"logs": logs, "total": len(logs)}


# ═══════════════════════════════════════════════════════════════════════════════
# INTEGRACIÓN CON ÓRDENES
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/orden/{orden_id}")
async def get_orden_logistics(orden_id: str, user: dict = Depends(require_auth)):
    """
    Get complete logistics data for an order.
    Includes all shipments organized by type, events, and history.
    """
    return await shipment_service.get_orden_logistics(db, orden_id)
