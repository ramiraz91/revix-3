"""
GLS Logistics API Routes.
Endpoints for: config, create shipments/pickups, labels, tracking, cancel.
"""
import logging
import base64
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional
from config import db
from auth import require_auth, require_master

from services.gls_service import (
    crear_envio, crear_recogida, obtener_etiqueta, obtener_etiqueta_recogida,
    consultar_envio, anular_envio, SERVICIOS_GLS, HORARIOS_GLS
)

logger = logging.getLogger("gls_routes")
router = APIRouter(prefix="/gls", tags=["gls"])

COLLECTION = "configuracion"
CONFIG_TIPO = "gls_config"


# ─── Helpers ──────────────────────────────────────────────

async def _get_gls_config() -> dict:
    doc = await db.configuracion.find_one({"tipo": CONFIG_TIPO}, {"_id": 0})
    return doc.get("datos", {}) if doc else {}


async def _require_gls_active():
    cfg = await _get_gls_config()
    if not cfg.get("activo"):
        raise HTTPException(status_code=400, detail="Integración GLS no está activada")
    if not cfg.get("uid_cliente"):
        raise HTTPException(status_code=400, detail="UID de cliente GLS no configurado")
    return cfg


# ─── Config endpoints ────────────────────────────────────

@router.get("/config")
async def get_gls_config(user: dict = Depends(require_master)):
    cfg = await _get_gls_config()
    return {
        "activo": cfg.get("activo", False),
        "uid_cliente": cfg.get("uid_cliente", ""),
        "remitente": cfg.get("remitente", {
            "nombre": "revix.es",
            "direccion": "Julio alarcon 8, Local",
            "poblacion": "Cordoba",
            "cp": "14007",
            "telefono": "604319223",
            "nif": "31018296J"
        }),
        "servicio_defecto": cfg.get("servicio_defecto", "1"),
        "horario_defecto": cfg.get("horario_defecto", "18"),
        "portes_defecto": cfg.get("portes_defecto", "P"),
        "formato_etiqueta": cfg.get("formato_etiqueta", "PDF"),
        "polling_activo": cfg.get("polling_activo", False),
        "polling_intervalo_horas": cfg.get("polling_intervalo_horas", 4),
        "servicios_disponibles": SERVICIOS_GLS,
        "horarios_disponibles": HORARIOS_GLS,
    }


class GLSConfigPayload(BaseModel):
    activo: bool = False
    uid_cliente: str = ""
    remitente: dict = {}
    servicio_defecto: str = "1"
    horario_defecto: str = "18"
    portes_defecto: str = "P"
    formato_etiqueta: str = "PDF"
    polling_activo: bool = False
    polling_intervalo_horas: int = 4


@router.post("/config")
async def save_gls_config(payload: GLSConfigPayload, user: dict = Depends(require_master)):
    data = payload.dict()
    await db.configuracion.update_one(
        {"tipo": CONFIG_TIPO},
        {"$set": {
            "tipo": CONFIG_TIPO,
            "datos": data,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "updated_by": user.get("email", "sistema")
        }},
        upsert=True
    )
    return {"success": True, "message": "Configuración GLS guardada"}


# ─── Shipment creation ───────────────────────────────────

class CrearEnvioPayload(BaseModel):
    orden_id: str
    nombre_dst: str
    direccion_dst: str
    poblacion_dst: str
    cp_dst: str
    telefono_dst: str = ""
    email_dst: str = ""
    nif_dst: str = ""
    observaciones: str = ""
    servicio: str = ""
    horario: str = ""
    bultos: str = "1"
    peso: str = "1"
    portes: str = ""
    reembolso: str = "0"
    pais_dst: str = "ES"


@router.post("/envio")
async def crear_envio_gls(payload: CrearEnvioPayload, user: dict = Depends(require_auth)):
    cfg = await _require_gls_active()
    
    envio_data = payload.dict()
    envio_data["servicio"] = envio_data["servicio"] or cfg.get("servicio_defecto", "1")
    envio_data["horario"] = envio_data["horario"] or cfg.get("horario_defecto", "18")
    envio_data["portes"] = envio_data["portes"] or cfg.get("portes_defecto", "P")
    envio_data["referencia"] = payload.orden_id

    result = await crear_envio(cfg, envio_data)

    if result.get("success"):
        # Save to order
        gls_envio = {
            "id": str(uuid.uuid4()),
            "tipo": "envio",
            "codbarras": result["codbarras"],
            "uid_envio": result.get("uid_envio", ""),
            "referencia": payload.orden_id,
            "servicio": envio_data["servicio"],
            "nombre_dst": payload.nombre_dst,
            "cp_dst": payload.cp_dst,
            "estado_gls": "grabado",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "created_by": user.get("email", "sistema"),
        }
        await db.ordenes.update_one(
            {"id": payload.orden_id},
            {
                "$push": {"gls_envios": gls_envio},
                "$set": {
                    "codigo_recogida_salida": result["codbarras"],
                    "agencia_envio": "GLS",
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        return {**result, "gls_envio": gls_envio}
    
    return result


class CrearRecogidaPayload(BaseModel):
    orden_id: str
    nombre_org: str
    direccion_org: str
    poblacion_org: str
    cp_org: str
    telefono_org: str = ""
    observaciones: str = ""
    servicio: str = ""
    horario: str = ""
    bultos: str = "1"
    peso: str = "1"
    fecha: str = ""


@router.post("/recogida")
async def crear_recogida_gls(payload: CrearRecogidaPayload, user: dict = Depends(require_auth)):
    cfg = await _require_gls_active()
    
    rec_data = payload.dict()
    rec_data["servicio"] = rec_data["servicio"] or cfg.get("servicio_defecto", "1")
    rec_data["horario"] = rec_data["horario"] or cfg.get("horario_defecto", "18")
    rec_data["referencia"] = payload.orden_id
    if not rec_data["fecha"]:
        rec_data["fecha"] = datetime.now(timezone.utc).strftime("%d/%m/%Y")

    result = await crear_recogida(cfg, rec_data)

    if result.get("success"):
        gls_recogida = {
            "id": str(uuid.uuid4()),
            "tipo": "recogida",
            "codbarras": result["codbarras"],
            "uid_envio": result.get("uid_envio", ""),
            "referencia": payload.orden_id,
            "servicio": rec_data["servicio"],
            "nombre_org": payload.nombre_org,
            "cp_org": payload.cp_org,
            "estado_gls": "grabado",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "created_by": user.get("email", "sistema"),
        }
        await db.ordenes.update_one(
            {"id": payload.orden_id},
            {
                "$push": {"gls_envios": gls_recogida},
                "$set": {
                    "codigo_recogida_entrada": result["codbarras"],
                    "agencia_envio": "GLS",
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        return {**result, "gls_envio": gls_recogida}
    
    return result


# ─── Labels ──────────────────────────────────────────────

@router.get("/etiqueta/{referencia}")
async def descargar_etiqueta(referencia: str, tipo: str = "PDF", user: dict = Depends(require_auth)):
    cfg = await _require_gls_active()
    result = await obtener_etiqueta(cfg["uid_cliente"], referencia, tipo)
    
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Error obteniendo etiqueta"))
    
    label_bytes = base64.b64decode(result["etiqueta_base64"])
    ext = tipo.lower()
    return Response(
        content=label_bytes,
        media_type=result["content_type"],
        headers={"Content-Disposition": f"attachment; filename=etiqueta_{referencia}.{ext}"}
    )


@router.get("/etiqueta-recogida/{referencia}")
async def descargar_etiqueta_recogida(referencia: str, tipo: str = "PDF", user: dict = Depends(require_auth)):
    cfg = await _require_gls_active()
    result = await obtener_etiqueta_recogida(cfg["uid_cliente"], referencia, tipo)
    
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Error obteniendo etiqueta"))
    
    label_bytes = base64.b64decode(result["etiqueta_base64"])
    ext = tipo.lower()
    return Response(
        content=label_bytes,
        media_type=result["content_type"],
        headers={"Content-Disposition": f"attachment; filename=etiqueta_recogida_{referencia}.{ext}"}
    )


# ─── Tracking ────────────────────────────────────────────

@router.get("/tracking/{referencia}")
async def consultar_tracking(referencia: str, user: dict = Depends(require_auth)):
    cfg = await _require_gls_active()
    result = await consultar_envio(cfg["uid_cliente"], referencia)
    
    if result.get("success"):
        # Update order with latest tracking
        await db.ordenes.update_one(
            {"id": referencia},
            {"$set": {
                "gls_ultimo_tracking": result,
                "gls_tracking_updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
    return result


@router.post("/tracking/poll")
async def poll_tracking_all(user: dict = Depends(require_master)):
    """Poll tracking for all orders with active GLS shipments."""
    cfg = await _require_gls_active()
    uid = cfg["uid_cliente"]
    
    ordenes = await db.ordenes.find(
        {"gls_envios": {"$exists": True, "$ne": []}, "estado": {"$nin": ["entregado", "cancelado", "irreparable"]}},
        {"_id": 0, "id": 1, "gls_envios": 1, "numero_orden": 1}
    ).to_list(200)
    
    updated = 0
    errors = 0
    for orden in ordenes:
        for envio in (orden.get("gls_envios") or []):
            ref = envio.get("referencia") or orden["id"]
            try:
                result = await consultar_envio(uid, ref)
                if result.get("success"):
                    await db.ordenes.update_one(
                        {"id": orden["id"]},
                        {"$set": {
                            "gls_ultimo_tracking": result,
                            "gls_tracking_updated_at": datetime.now(timezone.utc).isoformat()
                        }}
                    )
                    updated += 1
            except Exception as e:
                logger.error(f"Error polling tracking {ref}: {e}")
                errors += 1
    
    return {"success": True, "updated": updated, "errors": errors, "total": len(ordenes)}


# ─── Cancel ──────────────────────────────────────────────

@router.post("/anular/{referencia}")
async def anular_envio_gls(referencia: str, user: dict = Depends(require_auth)):
    cfg = await _require_gls_active()
    result = await anular_envio(cfg["uid_cliente"], referencia)
    
    if result.get("success"):
        await db.ordenes.update_one(
            {"gls_envios.referencia": referencia},
            {"$set": {"gls_envios.$.estado_gls": "anulado"}}
        )
    return result


# ─── Maestros ─────────────────────────────────────────────

@router.get("/servicios")
async def listar_servicios(user: dict = Depends(require_auth)):
    return {"servicios": SERVICIOS_GLS, "horarios": HORARIOS_GLS}
