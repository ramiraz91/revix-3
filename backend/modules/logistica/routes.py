"""
Endpoints HTTP para logística (GLS Spain).

Prefix: /api/logistica

Endpoints:
  POST /api/logistica/gls/crear-envio
  GET  /api/logistica/gls/tracking/{codbarras}
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from config import db
from auth import require_auth

from modules.logistica.gls import (
    Destinatario, GLSClient, GLSError, Remitente,
)

logger = logging.getLogger("gls.routes_logistica")

router = APIRouter(prefix="/logistica", tags=["Logística"])


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _build_remitente_from_env() -> Remitente:
    """Remitente (origen) construido desde variables de entorno."""
    return Remitente(
        nombre=os.environ.get("GLS_REMITENTE_NOMBRE", "REVIX TALLER"),
        direccion=os.environ.get("GLS_REMITENTE_DIRECCION", ""),
        poblacion=os.environ.get("GLS_REMITENTE_POBLACION", ""),
        provincia=os.environ.get("GLS_REMITENTE_PROVINCIA", ""),
        cp=os.environ.get("GLS_REMITENTE_CP", ""),
        telefono=os.environ.get("GLS_REMITENTE_TELEFONO", ""),
        pais=os.environ.get("GLS_REMITENTE_PAIS", "34"),
    )


def _build_gls_client() -> GLSClient:
    return GLSClient(
        uid_cliente=os.environ.get("GLS_UID_CLIENTE", ""),
        remitente=_build_remitente_from_env(),
        url=os.environ.get("GLS_URL") or None,
        mcp_env=os.environ.get("MCP_ENV"),
    )


async def _destinatario_desde_orden(orden: dict) -> Destinatario:
    cliente_id = orden.get("cliente_id")
    cliente: dict = {}
    if cliente_id:
        cliente = await db.clientes.find_one({"id": cliente_id}, {"_id": 0}) or {}

    nombre = (f"{cliente.get('nombre','').strip()} "
              f"{cliente.get('apellidos','').strip()}").strip()
    if not nombre:
        nombre = orden.get("cliente_nombre") or "Cliente"

    return Destinatario(
        nombre=nombre[:60],
        direccion=cliente.get("direccion") or orden.get("direccion", ""),
        poblacion=cliente.get("ciudad") or "",
        provincia=cliente.get("provincia") or "",
        cp=str(cliente.get("codigo_postal") or orden.get("codigo_postal") or "").strip(),
        telefono=str(cliente.get("telefono") or "").strip(),
        movil=str(cliente.get("movil") or cliente.get("telefono") or "").strip(),
        email=cliente.get("email") or "",
        observaciones=f"OT {orden.get('numero_orden','')}",
    )


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/logistica/gls/crear-envio
# ──────────────────────────────────────────────────────────────────────────────

class CrearEnvioRequest(BaseModel):
    order_id: str = Field(..., min_length=1)
    peso_kg: float = Field(1.0, gt=0, le=40)
    referencia: Optional[str] = None  # Si no, se usa numero_orden


class CrearEnvioResponse(BaseModel):
    success: bool
    codbarras: str
    uid: str
    referencia: str
    etiqueta_pdf_base64: str
    tracking_url: str
    mock_preview: bool


@router.post("/gls/crear-envio", response_model=CrearEnvioResponse)
async def crear_envio_gls(
    data: CrearEnvioRequest, user: dict = Depends(require_auth),
):
    """
    Crea una etiqueta GLS para una orden.

    Flujo:
      1. Carga la orden por id o numero_orden.
      2. Resuelve datos destinatario desde la orden + cliente.
      3. Llama a GLS (o mock si MCP_ENV=preview).
      4. Persiste codbarras + uid + etiqueta en la orden (campo `gls_envios[]`).
    """
    orden = await db.ordenes.find_one(
        {"$or": [{"id": data.order_id}, {"numero_orden": data.order_id}]},
        {"_id": 0},
    )
    if not orden:
        raise HTTPException(404, f"Orden {data.order_id} no encontrada")

    destinatario = await _destinatario_desde_orden(orden)
    if not destinatario.direccion or not destinatario.cp:
        raise HTTPException(
            400,
            "Destinatario incompleto: falta dirección o código postal en la orden/cliente.",
        )
    if not (destinatario.cp.isdigit() and len(destinatario.cp) == 5):
        raise HTTPException(400, f"Código postal inválido: '{destinatario.cp}'")

    client = _build_gls_client()
    referencia = data.referencia or orden.get("numero_orden") or orden.get("id", "")

    try:
        resultado = await client.crear_envio(
            order_id=orden.get("id", data.order_id),
            destinatario=destinatario,
            peso=data.peso_kg,
            referencia=referencia,
        )
    except GLSError as exc:
        logger.error("GLS rechazó envío orden=%s: %s", data.order_id, exc)
        raise HTTPException(400, f"GLS: {exc}") from exc

    # Persistir en la orden
    tracking_url = (
        f"https://www.gls-spain.es/es/ayuda/seguimiento-de-envio/"
        f"?match={resultado.codbarras}"
    )
    mock_preview = (os.environ.get("MCP_ENV", "").lower() == "preview")

    envio_doc = {
        "codbarras": resultado.codbarras,
        "uid": resultado.uid,
        "referencia": resultado.referencia,
        "tracking_url": tracking_url,
        "peso_kg": data.peso_kg,
        "estado": "creado",
        "mock_preview": mock_preview,
        "creado_en": _now_iso(),
        "creado_por": user.get("email", ""),
    }

    await db.ordenes.update_one(
        {"id": orden.get("id")},
        {"$push": {"gls_envios": envio_doc},
         "$set": {"updated_at": _now_iso()}},
    )

    # Guardar también la etiqueta (para reimpresión) en su propia colección
    await db.gls_etiquetas.insert_one({
        "codbarras": resultado.codbarras,
        "order_id": orden.get("id"),
        "referencia": resultado.referencia,
        "etiqueta_pdf_base64": resultado.etiqueta_pdf_base64,
        "mock_preview": mock_preview,
        "creado_en": _now_iso(),
    })

    return CrearEnvioResponse(
        success=True,
        codbarras=resultado.codbarras,
        uid=resultado.uid,
        referencia=resultado.referencia,
        etiqueta_pdf_base64=resultado.etiqueta_pdf_base64,
        tracking_url=tracking_url,
        mock_preview=mock_preview,
    )


# ──────────────────────────────────────────────────────────────────────────────
# GET /api/logistica/gls/tracking/{codbarras}
# ──────────────────────────────────────────────────────────────────────────────

class EventoTrackingOut(BaseModel):
    fecha: str
    estado: str
    plaza: str
    codigo: str


class TrackingResponse(BaseModel):
    success: bool
    codbarras: str
    estado_actual: str
    estado_codigo: str
    fecha_entrega: str
    incidencia: str
    eventos: list[EventoTrackingOut]
    tracking_url: str
    mock_preview: bool


@router.get("/gls/tracking/{codbarras}", response_model=TrackingResponse)
async def tracking_gls(codbarras: str, user: dict = Depends(require_auth)):
    client = _build_gls_client()
    try:
        tracking = await client.obtener_tracking(codbarras)
    except GLSError as exc:
        raise HTTPException(400, f"GLS: {exc}") from exc

    if not tracking.success:
        raise HTTPException(404, f"Envío {codbarras} no encontrado en GLS")

    return TrackingResponse(
        success=True,
        codbarras=tracking.codbarras,
        estado_actual=tracking.estado_actual,
        estado_codigo=tracking.estado_codigo,
        fecha_entrega=tracking.fecha_entrega,
        incidencia=tracking.incidencia,
        eventos=[EventoTrackingOut(**e.to_dict()) for e in tracking.eventos],
        tracking_url=(
            f"https://www.gls-spain.es/es/ayuda/seguimiento-de-envio/"
            f"?match={tracking.codbarras}"
        ),
        mock_preview=(os.environ.get("MCP_ENV", "").lower() == "preview"),
    )
