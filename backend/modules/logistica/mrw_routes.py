"""
MRW — Endpoints de logística (crear envío, tracking, recogida) + config en BD.

Mirroring del patrón GLS. En MCP_ENV=preview usa mocks del cliente MRW.

Endpoints:
  POST /logistica/mrw/crear-envio
  GET  /logistica/mrw/orden/{order_id}
  POST /logistica/mrw/actualizar-tracking/{num_envio}
  POST /logistica/mrw/solicitar-recogida
  GET  /logistica/config/mrw
  POST /logistica/config/mrw/remitente
  POST /logistica/config/mrw/verify
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from config import db
from auth import require_auth, require_admin

from modules.logistica.mrw import (
    DestinatarioMRW, MRWClient, MRWError, RemitenteMRW, _tracking_url_mrw,
)

logger = logging.getLogger("mrw.logistica.routes")

router = APIRouter(prefix="/logistica", tags=["Logística · MRW"])

CONFIG_DOC_TIPO = "mrw"


# ══════════════════════════════════════════════════════════════════════════════
# Config helpers (BD > env)
# ══════════════════════════════════════════════════════════════════════════════

async def _get_config_doc() -> dict:
    return await db.configuracion.find_one(
        {"tipo": CONFIG_DOC_TIPO}, {"_id": 0},
    ) or {}


def _env_remitente() -> dict:
    return {
        "nombre": os.environ.get("MRW_REMITENTE_NOMBRE", ""),
        "direccion": os.environ.get("MRW_REMITENTE_DIRECCION", ""),
        "poblacion": os.environ.get("MRW_REMITENTE_POBLACION", ""),
        "provincia": os.environ.get("MRW_REMITENTE_PROVINCIA", ""),
        "cp": os.environ.get("MRW_REMITENTE_CP", ""),
        "telefono": os.environ.get("MRW_REMITENTE_TELEFONO", ""),
    }


async def _effective_remitente() -> dict:
    doc = await _get_config_doc()
    bd = (doc.get("remitente") or {}) if isinstance(doc.get("remitente"), dict) else {}
    env = _env_remitente()
    return {k: (bd.get(k) or env.get(k, "")) for k in env.keys()}


def _is_preview() -> bool:
    return os.environ.get("MCP_ENV", "").lower() == "preview"


async def _build_client() -> MRWClient:
    rem = await _effective_remitente()
    return MRWClient(
        franquicia=os.environ.get("MRW_FRANQUICIA", ""),
        abonado=os.environ.get("MRW_ABONADO", ""),
        departamento=os.environ.get("MRW_DEPARTAMENTO", "0"),
        usuario=os.environ.get("MRW_USUARIO", ""),
        password=os.environ.get("MRW_PASSWORD", ""),
        remitente=RemitenteMRW(**rem),
        url=os.environ.get("MRW_URL") or None,
        mcp_env=os.environ.get("MCP_ENV"),
    )


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


async def _get_orden(order_id: str) -> dict:
    orden = await db.ordenes.find_one(
        {"$or": [{"id": order_id}, {"numero_orden": order_id}]},
        {"_id": 0},
    )
    if not orden:
        raise HTTPException(404, f"Orden {order_id} no encontrada")
    return orden


async def _destinatario_desde_orden(orden: dict) -> DestinatarioMRW:
    cli = {}
    if orden.get("cliente_id"):
        cli = await db.clientes.find_one({"id": orden["cliente_id"]}, {"_id": 0}) or {}
    nombre = (f"{cli.get('nombre','').strip()} {cli.get('apellidos','').strip()}").strip()
    if not nombre:
        nombre = orden.get("cliente_nombre") or "Cliente"
    direccion = orden.get("direccion_envio") or cli.get("direccion", "")
    cp = orden.get("cp_envio") or cli.get("cp", "")
    poblacion = orden.get("poblacion_envio") or cli.get("poblacion", "")
    provincia = orden.get("provincia_envio") or cli.get("provincia", "")
    telefono = orden.get("telefono_envio") or cli.get("telefono", "")
    return DestinatarioMRW(
        nombre=nombre, direccion=direccion, cp=cp, poblacion=poblacion,
        provincia=provincia, telefono=telefono, email=cli.get("email", ""),
    )


# ══════════════════════════════════════════════════════════════════════════════
# Crear envío
# ══════════════════════════════════════════════════════════════════════════════

class CrearEnvioMRWRequest(BaseModel):
    order_id: str
    peso_kg: float = Field(0.5, gt=0, le=30)
    observaciones: str = ""
    referencia_usar_autorizacion: bool = True


class CrearEnvioMRWResponse(BaseModel):
    success: bool
    num_envio: str
    referencia: str
    etiqueta_pdf_base64: str
    tracking_url: str
    mock_preview: bool


@router.post("/mrw/crear-envio", response_model=CrearEnvioMRWResponse)
async def crear_envio_mrw(
    data: CrearEnvioMRWRequest, user: dict = Depends(require_admin),
):
    orden = await _get_orden(data.order_id)
    destinatario = await _destinatario_desde_orden(orden)
    referencia = (orden.get("numero_autorizacion")
                  if data.referencia_usar_autorizacion else None) \
        or orden.get("numero_orden") or orden.get("id", "")

    client = await _build_client()
    try:
        resultado = await client.crear_envio(
            order_id=orden["id"], destinatario=destinatario,
            peso=data.peso_kg, referencia=referencia,
        )
    except MRWError as exc:
        raise HTTPException(400, f"MRW: {exc}") from exc

    mock_preview = _is_preview()
    now = _now_iso()
    envio_doc = {
        "num_envio": resultado.num_envio,
        "referencia": resultado.referencia,
        "tracking_url": resultado.tracking_url or _tracking_url_mrw(resultado.num_envio),
        "peso_kg": data.peso_kg,
        "observaciones": data.observaciones,
        "destinatario_snapshot": {
            "nombre": destinatario.nombre, "direccion": destinatario.direccion,
            "cp": destinatario.cp, "poblacion": destinatario.poblacion,
            "provincia": destinatario.provincia, "telefono": destinatario.telefono,
        },
        "estado": "creado",
        "estado_actual": "RECOGIDO EN ORIGEN",
        "estado_codigo": "10",
        "eventos": [],
        "incidencia": "",
        "fecha_entrega": "",
        "mock_preview": mock_preview,
        "creado_en": now,
        "ultima_actualizacion": now,
        "creado_por": user.get("email", ""),
    }

    await db.ordenes.update_one(
        {"id": orden["id"]},
        {"$push": {"mrw_envios": envio_doc},
         "$set": {"updated_at": now}},
    )
    await db.mrw_etiquetas.insert_one({
        "num_envio": resultado.num_envio,
        "order_id": orden["id"],
        "referencia": resultado.referencia,
        "etiqueta_pdf_base64": resultado.etiqueta_pdf_base64,
        "mock_preview": mock_preview,
        "creado_en": now,
    })

    return CrearEnvioMRWResponse(
        success=True,
        num_envio=resultado.num_envio,
        referencia=resultado.referencia,
        etiqueta_pdf_base64=resultado.etiqueta_pdf_base64,
        tracking_url=envio_doc["tracking_url"],
        mock_preview=mock_preview,
    )


# ══════════════════════════════════════════════════════════════════════════════
# Orden MRW (envíos de una OT)
# ══════════════════════════════════════════════════════════════════════════════

class EnvioMRWResumen(BaseModel):
    num_envio: str
    referencia: str
    peso_kg: float
    estado: str
    estado_codigo: str
    incidencia: str
    fecha_entrega: str
    tracking_url: str
    creado_en: str
    ultima_actualizacion: str
    mock_preview: bool
    eventos: list[dict]


class OrdenMRWDetailResponse(BaseModel):
    order_id: str
    numero_orden: str
    envios: list[EnvioMRWResumen]


@router.get("/mrw/orden/{order_id}", response_model=OrdenMRWDetailResponse)
async def orden_mrw_detalle(order_id: str, user: dict = Depends(require_auth)):
    orden = await _get_orden(order_id)
    envios = [
        EnvioMRWResumen(
            num_envio=d.get("num_envio", ""),
            referencia=d.get("referencia", ""),
            peso_kg=float(d.get("peso_kg", 0.5)),
            estado=d.get("estado_actual", "creado"),
            estado_codigo=str(d.get("estado_codigo", "")),
            incidencia=d.get("incidencia", ""),
            fecha_entrega=d.get("fecha_entrega", ""),
            tracking_url=d.get("tracking_url", ""),
            creado_en=d.get("creado_en", ""),
            ultima_actualizacion=d.get("ultima_actualizacion",
                                       d.get("creado_en", "")),
            mock_preview=bool(d.get("mock_preview", False)),
            eventos=d.get("eventos", []),
        )
        for d in (orden.get("mrw_envios") or [])
    ]
    return OrdenMRWDetailResponse(
        order_id=orden["id"],
        numero_orden=orden.get("numero_orden", ""),
        envios=envios,
    )


# ══════════════════════════════════════════════════════════════════════════════
# Actualizar tracking MRW
# ══════════════════════════════════════════════════════════════════════════════

class ActualizarMRWResponse(BaseModel):
    success: bool
    num_envio: str
    estado_actual: str
    estado_codigo: str
    cambio_estado: bool
    mock_preview: bool


@router.post("/mrw/actualizar-tracking/{num_envio}",
             response_model=ActualizarMRWResponse)
async def actualizar_tracking_mrw(num_envio: str, user: dict = Depends(require_admin)):
    client = await _build_client()
    try:
        tr = await client.obtener_tracking(num_envio)
    except MRWError as exc:
        raise HTTPException(400, f"MRW: {exc}") from exc

    orden_doc = await db.ordenes.find_one(
        {"mrw_envios.num_envio": num_envio}, {"_id": 0, "id": 1, "mrw_envios": 1},
    )
    cambio = False
    if orden_doc:
        envio_previo = next(
            (e for e in orden_doc["mrw_envios"] if e.get("num_envio") == num_envio),
            None,
        )
        if envio_previo and envio_previo.get("estado_codigo") != tr.estado_codigo:
            cambio = True
        await db.ordenes.update_one(
            {"id": orden_doc["id"], "mrw_envios.num_envio": num_envio},
            {"$set": {
                "mrw_envios.$.estado_actual": tr.estado_actual,
                "mrw_envios.$.estado_codigo": tr.estado_codigo,
                "mrw_envios.$.incidencia": tr.incidencia,
                "mrw_envios.$.fecha_entrega": tr.fecha_entrega,
                "mrw_envios.$.eventos": [e.to_dict() for e in tr.eventos],
                "mrw_envios.$.ultima_actualizacion": _now_iso(),
                "updated_at": _now_iso(),
            }},
        )

    return ActualizarMRWResponse(
        success=True, num_envio=num_envio,
        estado_actual=tr.estado_actual, estado_codigo=tr.estado_codigo,
        cambio_estado=cambio, mock_preview=_is_preview(),
    )


# ══════════════════════════════════════════════════════════════════════════════
# Solicitar recogida (fuerte de MRW)
# ══════════════════════════════════════════════════════════════════════════════

class SolicitarRecogidaRequest(BaseModel):
    order_id: Optional[str] = None
    fecha_recogida: str  # YYYY-MM-DD
    peso_total_kg: float = Field(..., gt=0, le=500)
    num_bultos: int = Field(1, ge=1, le=50)
    observaciones: str = ""


class SolicitarRecogidaResponse(BaseModel):
    success: bool
    num_recogida: str
    fecha_recogida: str
    tracking_url: str
    mock_preview: bool
    order_id: Optional[str] = None


@router.post("/mrw/solicitar-recogida", response_model=SolicitarRecogidaResponse)
async def solicitar_recogida_mrw(
    data: SolicitarRecogidaRequest, user: dict = Depends(require_admin),
):
    client = await _build_client()
    referencia = data.order_id or f"RECOGIDA-{_now_iso()}"
    try:
        resultado = await client.solicitar_recogida(
            referencia=referencia,
            fecha_recogida=data.fecha_recogida,
            peso_total=data.peso_total_kg,
            num_bultos=data.num_bultos,
        )
    except MRWError as exc:
        raise HTTPException(400, f"MRW: {exc}") from exc

    now = _now_iso()
    rec_doc = {
        "num_recogida": resultado.num_recogida,
        "order_id": data.order_id,
        "referencia": referencia,
        "fecha_recogida": data.fecha_recogida,
        "peso_total_kg": data.peso_total_kg,
        "num_bultos": data.num_bultos,
        "observaciones": data.observaciones,
        "estado": "pendiente",
        "tracking_url": resultado.tracking_url,
        "mock_preview": _is_preview(),
        "creado_en": now,
        "creado_por": user.get("email", ""),
    }
    await db.mrw_recogidas.insert_one(rec_doc)
    if data.order_id:
        await db.ordenes.update_one(
            {"id": data.order_id},
            {"$push": {"mrw_recogidas": rec_doc},
             "$set": {"updated_at": now}},
        )

    return SolicitarRecogidaResponse(
        success=True, num_recogida=resultado.num_recogida,
        fecha_recogida=data.fecha_recogida,
        tracking_url=resultado.tracking_url,
        mock_preview=_is_preview(), order_id=data.order_id,
    )


# ══════════════════════════════════════════════════════════════════════════════
# Config MRW (mismo patrón que GLS)
# ══════════════════════════════════════════════════════════════════════════════

class RemitenteMRWModel(BaseModel):
    nombre: str = Field("", max_length=100)
    direccion: str = Field("", max_length=200)
    poblacion: str = Field("", max_length=100)
    provincia: str = Field("", max_length=100)
    cp: str = Field("", max_length=10)
    telefono: str = Field("", max_length=25)


def _mask(v: str, keep: int = 4) -> str:
    if not v:
        return ""
    if len(v) <= keep:
        return "•" * len(v)
    return ("•" * (len(v) - keep)) + v[-keep:]


class ConfigMRWResponse(BaseModel):
    entorno: str
    franquicia_masked: str
    abonado_masked: str
    usuario_masked: str
    credenciales_set: bool
    remitente: RemitenteMRWModel
    remitente_source: dict
    stats_mes: dict
    ultimo_envio: dict
    mrw_url: str
    updated_at: Optional[str] = None
    updated_by: Optional[str] = None


async def _stats_mes_mrw() -> dict:
    now = datetime.now(timezone.utc)
    mes_inicio = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
    total = await db.ordenes.aggregate([
        {"$match": {"mrw_envios.creado_en": {"$gte": mes_inicio}}},
        {"$unwind": "$mrw_envios"},
        {"$match": {"mrw_envios.creado_en": {"$gte": mes_inicio}}},
        {"$count": "n"},
    ]).to_list(1)
    inc = await db.ordenes.aggregate([
        {"$match": {"mrw_envios.creado_en": {"$gte": mes_inicio}}},
        {"$unwind": "$mrw_envios"},
        {"$match": {"mrw_envios.creado_en": {"$gte": mes_inicio},
                    "mrw_envios.incidencia": {"$exists": True, "$ne": ""}}},
        {"$count": "n"},
    ]).to_list(1)
    recogidas = await db.mrw_recogidas.count_documents({"estado": "pendiente"})
    return {
        "envios_mes": total[0]["n"] if total else 0,
        "incidencias_mes": inc[0]["n"] if inc else 0,
        "recogidas_pendientes": recogidas,
    }


async def _ultimo_envio_mrw() -> dict:
    r = await db.ordenes.aggregate([
        {"$match": {"mrw_envios": {"$exists": True, "$ne": []}}},
        {"$unwind": "$mrw_envios"},
        {"$sort": {"mrw_envios.creado_en": -1}},
        {"$limit": 1},
        {"$project": {
            "_id": 0, "numero_orden": 1,
            "num_envio": "$mrw_envios.num_envio",
            "creado_en": "$mrw_envios.creado_en",
            "tracking_url": "$mrw_envios.tracking_url",
        }},
    ]).to_list(1)
    return r[0] if r else {}


@router.get("/config/mrw", response_model=ConfigMRWResponse)
async def config_mrw_get(user: dict = Depends(require_admin)):
    doc = await _get_config_doc()
    env = _env_remitente()
    bd = doc.get("remitente") or {}
    efec = {k: (bd.get(k) or env.get(k, "")) for k in env.keys()}
    source = {
        k: ("bd" if bd.get(k) else "env" if env.get(k) else "")
        for k in env.keys()
    }
    franq = os.environ.get("MRW_FRANQUICIA", "")
    abonado = os.environ.get("MRW_ABONADO", "")
    usuario = os.environ.get("MRW_USUARIO", "")
    stats = await _stats_mes_mrw()
    ultimo = await _ultimo_envio_mrw()
    return ConfigMRWResponse(
        entorno="preview" if _is_preview() else "production",
        franquicia_masked=_mask(franq, 2),
        abonado_masked=_mask(abonado, 3),
        usuario_masked=_mask(usuario, 3),
        credenciales_set=bool(franq and abonado and usuario),
        remitente=RemitenteMRWModel(**efec),
        remitente_source=source,
        stats_mes=stats,
        ultimo_envio=ultimo,
        mrw_url=os.environ.get("MRW_URL", ""),
        updated_at=doc.get("updated_at"),
        updated_by=doc.get("updated_by"),
    )


@router.post("/config/mrw/remitente", response_model=ConfigMRWResponse)
async def config_mrw_set_remitente(
    remitente: RemitenteMRWModel, user: dict = Depends(require_admin),
):
    now = _now_iso()
    await db.configuracion.update_one(
        {"tipo": CONFIG_DOC_TIPO},
        {"$set": {
            "tipo": CONFIG_DOC_TIPO,
            "remitente": remitente.model_dump(),
            "updated_at": now, "updated_by": user.get("email", "sistema"),
        }},
        upsert=True,
    )
    return await config_mrw_get(user)


class VerifyMRWResponse(BaseModel):
    ok: bool
    preview: bool
    mensaje: str


@router.post("/config/mrw/verify", response_model=VerifyMRWResponse)
async def config_mrw_verify(user: dict = Depends(require_admin)):
    if _is_preview():
        return VerifyMRWResponse(
            ok=True, preview=True,
            mensaje="Preview: credenciales no contactadas. Mock activo.",
        )
    if not all([
        os.environ.get("MRW_FRANQUICIA"),
        os.environ.get("MRW_ABONADO"),
        os.environ.get("MRW_USUARIO"),
        os.environ.get("MRW_PASSWORD"),
    ]):
        return VerifyMRWResponse(
            ok=False, preview=False,
            mensaje="Faltan credenciales MRW en entorno.",
        )
    return VerifyMRWResponse(
        ok=True, preview=False,
        mensaje="Credenciales presentes. MRW real aún no implementa verify.",
    )
