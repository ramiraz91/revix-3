"""
GLS Routes - FastAPI endpoints for GLS logistics module.
All routes prefixed with /api/gls/
"""
import base64
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from config import db
from auth import require_auth

from modules.gls.models import GLSConfigUpdate, GLSCreateShipment, GLSLabelFormat
from modules.gls.state_mapper import GLS_SERVICES, GLS_SCHEDULES, STATE_BADGES
from modules.gls import shipment_service

router = APIRouter(prefix="/gls", tags=["GLS Logística"])


def _require_admin(user: dict):
    if user.get("role") not in ("admin", "master"):
        raise HTTPException(403, "Acceso restringido a administradores")


# ─── CONFIG ──────────────────────────

@router.get("/config")
async def get_gls_config(user: dict = Depends(require_auth)):
    _require_admin(user)
    config = await shipment_service.get_config(db)
    # Never expose uid_cliente to frontend fully
    safe = {**config}
    uid = safe.get("uid_cliente", "")
    safe["uid_masked"] = f"{uid[:8]}...{uid[-4:]}" if len(uid) > 12 else ("***" if uid else "")
    return safe


@router.post("/config")
async def save_gls_config(data: GLSConfigUpdate, user: dict = Depends(require_auth)):
    _require_admin(user)
    await shipment_service.save_config(db, data.dict())
    return {"message": "Configuración GLS guardada"}


# ─── SHIPMENTS (CRUD) ──────────────────────────

@router.post("/envios")
async def crear_envio(data: GLSCreateShipment, user: dict = Depends(require_auth)):
    _require_admin(user)
    result = await shipment_service.create_shipment(db, data.dict(), user.get("email", ""))
    if not result["success"]:
        raise HTTPException(400, result.get("error", "Error al crear envío GLS"))
    return result


@router.get("/envios")
async def listar_envios(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    search: Optional[str] = None,
    estado: Optional[str] = None,
    tipo: Optional[str] = None,
    orden_id: Optional[str] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    user: dict = Depends(require_auth),
):
    filters = {}
    if search:
        filters["search"] = search
    if estado:
        filters["estado_interno"] = estado
    if tipo:
        filters["tipo"] = tipo
    if orden_id:
        filters["entidad_id"] = orden_id
    if fecha_desde:
        filters["fecha_desde"] = fecha_desde
    if fecha_hasta:
        filters["fecha_hasta"] = fecha_hasta

    return await shipment_service.list_shipments(db, filters, page, limit)


@router.get("/envios/{shipment_id}")
async def detalle_envio(shipment_id: str, raw: bool = False, user: dict = Depends(require_auth)):
    include_raw = raw and user.get("role") in ("admin", "master")
    detail = await shipment_service.get_shipment_detail(db, shipment_id, include_raw)
    if not detail:
        raise HTTPException(404, "Envío no encontrado")
    return detail


@router.delete("/envios/{shipment_id}")
async def anular_envio(shipment_id: str, user: dict = Depends(require_auth)):
    _require_admin(user)
    result = await shipment_service.cancel_shipment(db, shipment_id, user.get("email", ""))
    if not result["success"]:
        raise HTTPException(400, result.get("error"))
    return {"message": "Envío anulado"}


# ─── LABELS ──────────────────────────

@router.get("/etiqueta/{shipment_id}")
async def descargar_etiqueta(
    shipment_id: str,
    formato: GLSLabelFormat = GLSLabelFormat.PDF,
    user: dict = Depends(require_auth),
):
    """Download label for a specific shipment."""
    result = await shipment_service.get_label(db, shipment_id)
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

    return Response(
        content=label_bytes,
        media_type=ct,
        headers={"Content-Disposition": f'attachment; filename="etiqueta_gls_{shipment_id[:8]}.{ext}"'}
    )


@router.get("/etiqueta-por-codigo/{codigo}")
async def descargar_etiqueta_por_codigo(
    codigo: str,
    formato: GLSLabelFormat = GLSLabelFormat.PDF,
    user: dict = Depends(require_auth),
):
    """Download label by barcode/reference (for reprint)."""
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


# ─── TRACKING ──────────────────────────

@router.get("/tracking-url/{codbarras}")
async def obtener_url_tracking(codbarras: str):
    """Get GLS tracking URL for a barcode (public, no auth required for customer sharing)."""
    from modules.gls.shipment_service import get_tracking_url
    url = get_tracking_url(codbarras)
    if not url:
        raise HTTPException(400, "Código de barras inválido")
    return {"tracking_url": url, "codbarras": codbarras}


@router.get("/tracking/{shipment_id}")
async def consultar_tracking(shipment_id: str, user: dict = Depends(require_auth)):
    """Get full tracking for a shipment."""
    result = await shipment_service.get_tracking(db, shipment_id)
    if not result.get("success"):
        raise HTTPException(400, result.get("error", "No se pudo obtener tracking"))
    
    # Añadir tracking_url al resultado
    from modules.gls.shipment_service import get_tracking_url
    codbarras = result.get("shipment", {}).get("gls_codbarras", "")
    result["tracking_url"] = get_tracking_url(codbarras)
    
    return result


@router.get("/tracking-por-codigo/{codigo}")
async def consultar_tracking_por_codigo(codigo: str, user: dict = Depends(require_auth)):
    """Get tracking by barcode/reference (quick lookup)."""
    config = await shipment_service.get_config(db)
    uid = config.get("uid_cliente", "")
    if not uid:
        raise HTTPException(400, "GLS no configurado")

    from modules.gls.soap_client import get_exp_cli
    from modules.gls.state_mapper import map_gls_state
    result = await get_exp_cli(uid, codigo)
    if not result.get("success"):
        raise HTTPException(404, "Envío no encontrado en GLS")
    return result


# ─── SYNC ──────────────────────────

@router.post("/sync")
async def sync_manual(user: dict = Depends(require_auth)):
    """Trigger manual sync of all active shipments."""
    _require_admin(user)
    stats = await shipment_service.sync_shipments(db)
    return stats


@router.post("/sync/{shipment_id}")
async def sync_single(shipment_id: str, user: dict = Depends(require_auth)):
    """Sync a single shipment."""
    _require_admin(user)
    result = await shipment_service.get_tracking(db, shipment_id)
    return {"success": result.get("success", False), "tracking": result}


# ─── MAESTROS / REFERENCE DATA ──────────────────────────

@router.get("/maestros")
async def get_maestros(user: dict = Depends(require_auth)):
    """Return GLS reference data (services, schedules, state badges)."""
    return {
        "servicios": GLS_SERVICES,
        "horarios": GLS_SCHEDULES,
        "estados": STATE_BADGES,
    }


# ─── LOGS ──────────────────────────

@router.get("/logs/{shipment_id}")
async def get_logs(shipment_id: str, user: dict = Depends(require_auth)):
    """Get integration logs for a shipment."""
    _require_admin(user)
    logs = await db.gls_logs.find(
        {"shipment_id": shipment_id}, {"_id": 0}
    ).sort("fecha", -1).to_list(100)
    return logs
