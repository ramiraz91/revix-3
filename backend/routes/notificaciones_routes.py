"""
Rutas de Notificaciones y configuración de Email.
Extraído de server.py durante refactorización.
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, List
from datetime import datetime, timezone

from config import db, logger
import config as cfg
from auth import require_auth, require_admin, require_master
from models import Notificacion
from helpers import send_email

router = APIRouter(tags=["notificaciones"])

@router.get("/notificaciones", response_model=List[Notificacion])
async def listar_notificaciones(no_leidas: Optional[bool] = None):
    query = {"leida": False} if no_leidas else {}
    notificaciones = await db.notificaciones.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    for n in notificaciones:
        if isinstance(n.get('created_at'), str):
            n['created_at'] = datetime.fromisoformat(n['created_at'])
    return notificaciones

@router.patch("/notificaciones/{notificacion_id}/leer")
async def marcar_leida(notificacion_id: str):
    result = await db.notificaciones.update_one({"id": notificacion_id}, {"$set": {"leida": True}})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")
    return {"message": "Notificación marcada como leída"}

@router.delete("/notificaciones/{notificacion_id}")
async def eliminar_notificacion(notificacion_id: str):
    result = await db.notificaciones.delete_one({"id": notificacion_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")
    return {"message": "Notificación eliminada"}


@router.post("/notificaciones/eliminar-masivo")
async def eliminar_notificaciones_masivo(data: dict, user: dict = Depends(require_auth)):
    """Elimina múltiples notificaciones por sus IDs."""
    ids = data.get("ids", [])
    if not ids:
        raise HTTPException(status_code=400, detail="No se proporcionaron IDs")
    
    result = await db.notificaciones.delete_many({"id": {"$in": ids}})
    return {"eliminadas": result.deleted_count, "message": f"{result.deleted_count} notificaciones eliminadas"}


@router.post("/notificaciones/marcar-leidas-masivo")
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


@router.patch("/notificaciones/marcar-leidas-orden/{orden_id}")
async def marcar_leidas_por_orden(orden_id: str):
    """Auto-mark all notifications linked to an order as read (when user views the order)."""
    result = await db.notificaciones.update_many(
        {"orden_id": orden_id, "leida": False},
        {"$set": {"leida": True}}
    )
    return {"marcadas": result.modified_count}

@router.post("/email/test")
async def test_resend_email(data: dict, user: dict = Depends(require_master)):
    """Send a test email to verify Resend configuration."""
    to = data.get('to', user.get('email', 'master@revix.es'))
    from services.email_service import send_email as resend_send
    ok = resend_send(
        to=to,
        subject="Revix - Test de configuracion Resend",
        titulo="Prueba de Email",
        contenido="<p>Si recibes este correo, la configuracion de Resend esta funcionando correctamente.</p>"
    )
    return {"success": ok, "to": to, "provider": "resend", "sender": cfg.SENDER_EMAIL}

@router.get("/resend-config")
async def get_resend_config(user: dict = Depends(require_master)):
    """Get current email (Resend) configuration."""
    return {
        "provider": "resend",
        "sender_email": cfg.SENDER_EMAIL or "",
        "api_key_configured": bool(cfg.RESEND_API_KEY),
        "api_key_prefix": cfg.RESEND_API_KEY[:10] + "..." if cfg.RESEND_API_KEY else "",
        "configured": cfg.RESEND_CONFIGURED,
    }

@router.get("/repuestos/buscar-sku/{sku}")
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

@router.get("/email-config")
async def get_email_config(user: dict = Depends(require_master)):
    config = await db.configuracion.find_one({"tipo": "email_config"}, {"_id": 0})
    if not config:
        return {"enabled": False, "demo_mode": True, "demo_email": "", "smtp_from": "Revix <notificaciones@revix.es>", "reply_to": "help@revix.es", "actions": {}}
    return config.get("datos", {})

@router.put("/email-config")
async def update_email_config(data: dict, user: dict = Depends(require_master)):
    await db.configuracion.update_one(
        {"tipo": "email_config"},
        {"$set": {"tipo": "email_config", "datos": data, "updated_at": datetime.now(timezone.utc).isoformat(), "updated_by": user.get("email", "sistema")}},
        upsert=True
    )
    return {"message": "Configuración de email actualizada"}

# ── Budget Simulation (Presupuesto) ─────────────────────

