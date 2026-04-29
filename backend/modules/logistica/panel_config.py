"""
Panel de Logística + Ajustes GLS — extiende /api/logistica con:

Panel dashboard:
  GET  /api/logistica/panel/resumen         — contadores globales
  GET  /api/logistica/panel/envios          — listado filtrado y paginado
  POST /api/logistica/panel/actualizar-todos — refresca tracking de activos (manual)
  GET  /api/logistica/panel/export-csv      — exporta envíos filtrados en CSV

Ajustes GLS:
  GET  /api/logistica/config/gls            — config efectiva (BD ∪ env)
  POST /api/logistica/config/gls/remitente  — guarda remitente en BD
  POST /api/logistica/config/gls/polling    — guarda intervalo polling en BD
  POST /api/logistica/config/gls/verify     — ping a GLS (preview: mock OK)

La colección `configuracion` se usa con `{"tipo": "gls"}`. No tocamos `.env`.
"""
from __future__ import annotations

import csv
import io
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from config import db
from auth import require_auth, require_admin

from modules.logistica.gls import GLSClient, GLSError, Remitente
from modules.logistica.state_mapper import (
    estado_color, friendly_estado, interno_estado, is_entregado, is_incidencia,
)

logger = logging.getLogger("gls.logistica.panel")

# Se monta bajo el mismo prefix que el router principal (/logistica)
router = APIRouter(prefix="/logistica", tags=["Logística · Panel y Config"])

CONFIG_DOC_TIPO = "gls"


# ══════════════════════════════════════════════════════════════════════════════
# Helpers de configuración (BD > env)
# ══════════════════════════════════════════════════════════════════════════════

async def _get_config_doc() -> dict:
    doc = await db.configuracion.find_one(
        {"tipo": CONFIG_DOC_TIPO}, {"_id": 0},
    )
    return doc or {}


def _env_remitente() -> dict:
    return {
        "nombre": os.environ.get("GLS_REMITENTE_NOMBRE", ""),
        "direccion": os.environ.get("GLS_REMITENTE_DIRECCION", ""),
        "poblacion": os.environ.get("GLS_REMITENTE_POBLACION", ""),
        "provincia": os.environ.get("GLS_REMITENTE_PROVINCIA", ""),
        "cp": os.environ.get("GLS_REMITENTE_CP", ""),
        "telefono": os.environ.get("GLS_REMITENTE_TELEFONO", ""),
        "pais": os.environ.get("GLS_REMITENTE_PAIS", "34"),
    }


async def _effective_remitente() -> dict:
    """Remitente efectivo: BD > env. Siempre devuelve los 7 campos."""
    doc = await _get_config_doc()
    bd = (doc.get("remitente") or {}) if isinstance(doc.get("remitente"), dict) else {}
    env = _env_remitente()
    return {k: (bd.get(k) or env.get(k, "")) for k in env.keys()}


async def _effective_polling_hours() -> float:
    doc = await _get_config_doc()
    try:
        v = float(doc.get("polling_hours") or os.environ.get("GLS_POLLING_INTERVAL_HOURS", "4"))
        return max(0.25, v)
    except (TypeError, ValueError):
        return 4.0


async def _build_client_from_bd() -> GLSClient:
    rem = await _effective_remitente()
    return GLSClient(
        uid_cliente=os.environ.get("GLS_UID_CLIENTE", ""),
        remitente=Remitente(**rem),
        url=os.environ.get("GLS_URL") or None,
        mcp_env=os.environ.get("MCP_ENV"),
    )


def _is_preview() -> bool:
    return os.environ.get("MCP_ENV", "").lower() == "preview"


def _mask_uid(uid: str) -> str:
    if not uid:
        return ""
    if len(uid) <= 8:
        return "•" * len(uid)
    return ("•" * (len(uid) - 8)) + uid[-8:]


# ══════════════════════════════════════════════════════════════════════════════
# PANEL · Resumen
# ══════════════════════════════════════════════════════════════════════════════

class PanelResumenResponse(BaseModel):
    envios_activos: int
    entregados_hoy: int
    incidencias_activas: int
    recogidas_pendientes: int  # MRW: 0 hasta que haya integración
    total_envios_mes: int


@router.get("/panel/resumen", response_model=PanelResumenResponse)
async def panel_resumen(user: dict = Depends(require_auth)):
    now = datetime.now(timezone.utc)
    hoy_inicio = now.replace(hour=0, minute=0, second=0, microsecond=0)
    mes_inicio = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    pipeline_base_gls = [
        {"$match": {"gls_envios": {"$exists": True, "$ne": []}}},
        {"$unwind": "$gls_envios"},
    ]
    pipeline_base_mrw = [
        {"$match": {"mrw_envios": {"$exists": True, "$ne": []}}},
        {"$unwind": "$mrw_envios"},
    ]

    # Activos GLS + MRW
    activos_gls = await db.ordenes.aggregate(pipeline_base_gls + [
        {"$match": {
            "$and": [
                {"gls_envios.estado_codigo": {"$nin": ["7", "11"]}},
                {"gls_envios.estado_actual": {"$not": {"$regex": "^ENTREGADO", "$options": "i"}}},
            ],
        }},
        {"$count": "n"},
    ]).to_list(1)
    activos_mrw = await db.ordenes.aggregate(pipeline_base_mrw + [
        {"$match": {
            "$and": [
                {"mrw_envios.estado_actual": {"$not": {"$regex": "^ENTREGADO", "$options": "i"}}},
                {"mrw_envios.estado_codigo": {"$nin": ["60"]}},  # 60 = entregado MRW
            ],
        }},
        {"$count": "n"},
    ]).to_list(1)

    # Entregados hoy
    entregados_gls = await db.ordenes.aggregate(pipeline_base_gls + [
        {"$match": {
            "$or": [
                {"gls_envios.estado_codigo": "7"},
                {"gls_envios.estado_actual": {"$regex": "^ENTREGADO", "$options": "i"}},
            ],
            "gls_envios.ultima_actualizacion": {"$gte": hoy_inicio.isoformat()},
        }},
        {"$count": "n"},
    ]).to_list(1)
    entregados_mrw = await db.ordenes.aggregate(pipeline_base_mrw + [
        {"$match": {
            "$or": [
                {"mrw_envios.estado_codigo": "60"},
                {"mrw_envios.estado_actual": {"$regex": "^ENTREGADO", "$options": "i"}},
            ],
            "mrw_envios.ultima_actualizacion": {"$gte": hoy_inicio.isoformat()},
        }},
        {"$count": "n"},
    ]).to_list(1)

    # Incidencias
    incid_gls = await db.ordenes.aggregate(pipeline_base_gls + [
        {"$match": {
            "gls_envios.incidencia": {"$exists": True, "$ne": ""},
            "gls_envios.estado_codigo": {"$nin": ["7"]},
        }},
        {"$count": "n"},
    ]).to_list(1)
    incid_mrw = await db.ordenes.aggregate(pipeline_base_mrw + [
        {"$match": {
            "mrw_envios.incidencia": {"$exists": True, "$ne": ""},
            "mrw_envios.estado_codigo": {"$nin": ["60"]},
        }},
        {"$count": "n"},
    ]).to_list(1)

    # Total envíos mes (GLS + MRW)
    total_gls_mes = await db.ordenes.aggregate(pipeline_base_gls + [
        {"$match": {"gls_envios.creado_en": {"$gte": mes_inicio.isoformat()}}},
        {"$count": "n"},
    ]).to_list(1)
    total_mrw_mes = await db.ordenes.aggregate(pipeline_base_mrw + [
        {"$match": {"mrw_envios.creado_en": {"$gte": mes_inicio.isoformat()}}},
        {"$count": "n"},
    ]).to_list(1)

    recogidas_pend = await db.mrw_recogidas.count_documents({"estado": "pendiente"})

    def _n(r):
        return r[0]["n"] if r else 0

    return PanelResumenResponse(
        envios_activos=_n(activos_gls) + _n(activos_mrw),
        entregados_hoy=_n(entregados_gls) + _n(entregados_mrw),
        incidencias_activas=_n(incid_gls) + _n(incid_mrw),
        recogidas_pendientes=recogidas_pend,
        total_envios_mes=_n(total_gls_mes) + _n(total_mrw_mes),
    )


# ══════════════════════════════════════════════════════════════════════════════
# PANEL · Listado envíos
# ══════════════════════════════════════════════════════════════════════════════

class PanelEnvioRow(BaseModel):
    order_id: str
    numero_orden: str
    numero_autorizacion: str = ""
    cliente_nombre: str = ""
    cliente_telefono: str = ""
    transportista: str  # "GLS" | "MRW"
    codbarras: str
    referencia: str = ""
    estado_interno: str
    estado_codigo: str = ""
    estado_color: str
    tiene_incidencia: bool
    incidencia: str = ""
    creado_en: str
    ultima_actualizacion: str
    tracking_url: str
    mock_preview: bool = False


class PanelEnviosResponse(BaseModel):
    total: int
    page: int
    page_size: int
    pages: int
    items: list[PanelEnvioRow]


def _envio_filter_matches(envio: dict, transportista: str, estado: Optional[str],
                          solo_incidencias: bool) -> bool:
    # transportista: por ahora solo GLS. MRW reservado.
    if transportista not in ("", "GLS", "MRW"):
        return False
    estado_actual = (envio.get("estado_actual") or "").upper()
    codigo = str(envio.get("estado_codigo") or "")

    if solo_incidencias:
        if not (envio.get("incidencia") or is_incidencia(estado_actual)):
            return False

    if estado:
        e = estado.upper()
        if e == "ACTIVO":
            # no entregado
            if is_entregado(estado_actual, codigo):
                return False
        elif e == "ENTREGADO":
            if not is_entregado(estado_actual, codigo):
                return False
        elif e == "INCIDENCIA":
            if not (envio.get("incidencia") or is_incidencia(estado_actual)):
                return False
        else:
            # coincidencia textual
            if e not in estado_actual:
                return False

    return True


@router.get("/panel/envios", response_model=PanelEnviosResponse)
async def panel_listar_envios(
    estado: Optional[str] = Query(None, description="ACTIVO|ENTREGADO|INCIDENCIA|texto"),
    transportista: str = Query("", description="GLS|MRW|vacío=todos"),
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    solo_incidencias: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    user: dict = Depends(require_auth),
):
    # Query base: órdenes con gls_envios O mrw_envios no vacío
    query: dict = {
        "$or": [
            {"gls_envios": {"$exists": True, "$ne": []}},
            {"mrw_envios": {"$exists": True, "$ne": []}},
        ],
    }
    if fecha_desde or fecha_hasta:
        rng: dict = {}
        if fecha_desde:
            rng["$gte"] = fecha_desde
        if fecha_hasta:
            rng["$lte"] = fecha_hasta
        # No podemos filtrar ambos a la vez con el mismo key, aplicamos en memoria.

    proj = {
        "_id": 0, "id": 1, "numero_orden": 1, "numero_autorizacion": 1,
        "cliente_id": 1, "gls_envios": 1, "mrw_envios": 1,
    }
    ordenes = await db.ordenes.find(query, proj).sort("updated_at", -1).to_list(5000)

    cliente_ids = {o["cliente_id"] for o in ordenes if o.get("cliente_id")}
    clientes_map: dict = {}
    if cliente_ids:
        async for c in db.clientes.find({"id": {"$in": list(cliente_ids)}},
                                        {"_id": 0, "id": 1, "nombre": 1,
                                         "apellidos": 1, "telefono": 1}):
            clientes_map[c["id"]] = c

    rows: list[PanelEnvioRow] = []
    for o in ordenes:
        cli = clientes_map.get(o.get("cliente_id")) or {}
        nombre = (f"{cli.get('nombre','')} {cli.get('apellidos','')}").strip()

        # ── GLS ──
        for envio in (o.get("gls_envios") or []):
            if not envio.get("codbarras"):
                continue
            # En producción ocultamos completamente los envíos preview/mock
            # para no confundir al admin ni al cliente
            if envio.get("mock_preview") and not _is_preview():
                continue
            if not _envio_filter_matches(envio, transportista or "", estado, solo_incidencias):
                continue
            if fecha_desde and (envio.get("creado_en", "") < fecha_desde):
                continue
            if fecha_hasta and (envio.get("creado_en", "") > fecha_hasta):
                continue
            if transportista and transportista.upper() not in ("GLS", ""):
                continue
            estado_actual = envio.get("estado_actual") or ""
            codigo = str(envio.get("estado_codigo") or "")
            incidencia = envio.get("incidencia") or ""
            rows.append(PanelEnvioRow(
                order_id=o["id"],
                numero_orden=o.get("numero_orden", ""),
                numero_autorizacion=o.get("numero_autorizacion") or "",
                cliente_nombre=nombre, cliente_telefono=cli.get("telefono", ""),
                transportista="GLS",
                codbarras=envio["codbarras"],
                referencia=envio.get("referencia", ""),
                estado_interno=interno_estado(estado_actual, codigo, incidencia),
                estado_codigo=codigo,
                estado_color=estado_color(estado_actual, codigo),
                tiene_incidencia=bool(incidencia) or is_incidencia(estado_actual),
                incidencia=incidencia,
                creado_en=envio.get("creado_en", ""),
                ultima_actualizacion=envio.get("ultima_actualizacion",
                                               envio.get("creado_en", "")),
                tracking_url=envio.get("tracking_url", ""),
                mock_preview=bool(envio.get("mock_preview", False)),
            ))

        # ── MRW ──
        if transportista and transportista.upper() not in ("MRW", ""):
            continue
        for envio in (o.get("mrw_envios") or []):
            if not envio.get("num_envio"):
                continue
            # En producción ocultamos envíos preview/mock
            if envio.get("mock_preview") and not _is_preview():
                continue
            if fecha_desde and (envio.get("creado_en", "") < fecha_desde):
                continue
            if fecha_hasta and (envio.get("creado_en", "") > fecha_hasta):
                continue
            estado_actual = envio.get("estado_actual") or ""
            codigo = str(envio.get("estado_codigo") or "")
            incidencia = envio.get("incidencia") or ""
            entregado_mrw = codigo == "60" or estado_actual.upper().startswith("ENTREGADO")
            if solo_incidencias and not incidencia:
                continue
            if estado:
                e = estado.upper()
                if e == "ACTIVO" and entregado_mrw:
                    continue
                if e == "ENTREGADO" and not entregado_mrw:
                    continue
                if e == "INCIDENCIA" and not incidencia:
                    continue
                if e not in ("ACTIVO", "ENTREGADO", "INCIDENCIA") and e not in estado_actual.upper():
                    continue
            rows.append(PanelEnvioRow(
                order_id=o["id"],
                numero_orden=o.get("numero_orden", ""),
                numero_autorizacion=o.get("numero_autorizacion") or "",
                cliente_nombre=nombre, cliente_telefono=cli.get("telefono", ""),
                transportista="MRW",
                codbarras=envio["num_envio"],  # reutilizamos el campo como identificador
                referencia=envio.get("referencia", ""),
                estado_interno=estado_actual or "creado",
                estado_codigo=codigo,
                estado_color=("green" if entregado_mrw
                              else "red" if incidencia else "blue"),
                tiene_incidencia=bool(incidencia),
                incidencia=incidencia,
                creado_en=envio.get("creado_en", ""),
                ultima_actualizacion=envio.get("ultima_actualizacion",
                                               envio.get("creado_en", "")),
                tracking_url=envio.get("tracking_url", ""),
                mock_preview=bool(envio.get("mock_preview", False)),
            ))

    rows.sort(key=lambda r: r.ultima_actualizacion or r.creado_en, reverse=True)

    total = len(rows)
    start = (page - 1) * page_size
    end = start + page_size
    page_rows = rows[start:end]
    pages = (total + page_size - 1) // page_size if page_size else 1

    return PanelEnviosResponse(
        total=total, page=page, page_size=page_size, pages=max(1, pages),
        items=page_rows,
    )


# ══════════════════════════════════════════════════════════════════════════════
# PANEL · Actualizar todos (manual)
# ══════════════════════════════════════════════════════════════════════════════

class ActualizarTodosResponse(BaseModel):
    ok: bool
    procesados: int
    cambios_estado: int
    incidencias: int
    entregas: int
    errores: int
    preview: bool


@router.post("/panel/actualizar-todos", response_model=ActualizarTodosResponse)
async def panel_actualizar_todos(user: dict = Depends(require_admin)):
    from modules.logistica.scheduler import _run_once  # reuse
    client = await _build_client_from_bd()
    stats = await _run_once(db, client)
    return ActualizarTodosResponse(
        ok=True, preview=_is_preview(),
        procesados=stats.get("procesados", 0),
        cambios_estado=stats.get("cambios_estado", 0),
        incidencias=stats.get("incidencias", 0),
        entregas=stats.get("entregas", 0),
        errores=stats.get("errores", 0),
    )


# ══════════════════════════════════════════════════════════════════════════════
# PANEL · Export CSV
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/panel/export-csv")
async def panel_export_csv(
    estado: Optional[str] = None,
    transportista: str = "",
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    solo_incidencias: bool = False,
    user: dict = Depends(require_auth),
):
    # Reusar la lógica del listado
    resp: PanelEnviosResponse = await panel_listar_envios(
        estado=estado, transportista=transportista,
        fecha_desde=fecha_desde, fecha_hasta=fecha_hasta,
        solo_incidencias=solo_incidencias,
        page=1, page_size=5000, user=user,
    )

    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";")
    writer.writerow([
        "numero_orden", "numero_autorizacion", "cliente", "telefono",
        "transportista", "codbarras", "referencia", "estado_interno",
        "estado_codigo", "incidencia", "creado_en", "ultima_actualizacion",
        "tracking_url",
    ])
    for r in resp.items:
        writer.writerow([
            r.numero_orden, r.numero_autorizacion, r.cliente_nombre,
            r.cliente_telefono, r.transportista, r.codbarras, r.referencia,
            r.estado_interno, r.estado_codigo,
            r.incidencia, r.creado_en, r.ultima_actualizacion, r.tracking_url,
        ])
    buf.seek(0)
    data = buf.getvalue().encode("utf-8-sig")  # BOM para Excel
    filename = f"logistica-envios-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M')}.csv"
    return StreamingResponse(
        iter([data]), media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ══════════════════════════════════════════════════════════════════════════════
# AJUSTES GLS · Leer config
# ══════════════════════════════════════════════════════════════════════════════

class RemitenteModel(BaseModel):
    nombre: str = Field("", max_length=100)
    direccion: str = Field("", max_length=200)
    poblacion: str = Field("", max_length=100)
    provincia: str = Field("", max_length=100)
    cp: str = Field("", max_length=10)
    telefono: str = Field("", max_length=25)
    pais: str = Field("34", max_length=4)


class ConfigGLSResponse(BaseModel):
    entorno: str  # "preview" | "production"
    uid_cliente_masked: str
    uid_cliente_set: bool
    remitente: RemitenteModel
    remitente_source: dict  # por campo: "bd" | "env" | ""
    polling_hours: float
    stats_mes: dict
    ultimo_envio: dict
    gls_url: str
    updated_at: Optional[str] = None
    updated_by: Optional[str] = None


async def _stats_mes() -> dict:
    now = datetime.now(timezone.utc)
    mes_inicio = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    total = await db.ordenes.aggregate([
        {"$match": {"gls_envios.creado_en": {"$gte": mes_inicio.isoformat()}}},
        {"$unwind": "$gls_envios"},
        {"$match": {"gls_envios.creado_en": {"$gte": mes_inicio.isoformat()}}},
        {"$count": "n"},
    ]).to_list(1)
    incidencias = await db.ordenes.aggregate([
        {"$match": {"gls_envios.creado_en": {"$gte": mes_inicio.isoformat()}}},
        {"$unwind": "$gls_envios"},
        {"$match": {
            "gls_envios.creado_en": {"$gte": mes_inicio.isoformat()},
            "gls_envios.incidencia": {"$exists": True, "$ne": ""},
        }},
        {"$count": "n"},
    ]).to_list(1)
    return {
        "envios_mes": total[0]["n"] if total else 0,
        "incidencias_mes": incidencias[0]["n"] if incidencias else 0,
    }


async def _ultimo_envio() -> dict:
    r = await db.ordenes.aggregate([
        {"$match": {"gls_envios": {"$exists": True, "$ne": []}}},
        {"$unwind": "$gls_envios"},
        {"$sort": {"gls_envios.creado_en": -1}},
        {"$limit": 1},
        {"$project": {
            "_id": 0, "numero_orden": 1,
            "codbarras": "$gls_envios.codbarras",
            "creado_en": "$gls_envios.creado_en",
            "tracking_url": "$gls_envios.tracking_url",
        }},
    ]).to_list(1)
    return r[0] if r else {}


@router.get("/config/gls", response_model=ConfigGLSResponse)
async def config_gls_get(user: dict = Depends(require_admin)):
    doc = await _get_config_doc()
    env = _env_remitente()
    bd = doc.get("remitente") or {}
    efectivo = {k: (bd.get(k) or env.get(k, "")) for k in env.keys()}
    source = {}
    for k in env.keys():
        if bd.get(k):
            source[k] = "bd"
        elif env.get(k):
            source[k] = "env"
        else:
            source[k] = ""

    uid = os.environ.get("GLS_UID_CLIENTE", "") or ""
    stats = await _stats_mes()
    ultimo = await _ultimo_envio()

    return ConfigGLSResponse(
        entorno="preview" if _is_preview() else "production",
        uid_cliente_masked=_mask_uid(uid),
        uid_cliente_set=bool(uid),
        remitente=RemitenteModel(**efectivo),
        remitente_source=source,
        polling_hours=await _effective_polling_hours(),
        stats_mes=stats,
        ultimo_envio=ultimo,
        gls_url=os.environ.get("GLS_URL", ""),
        updated_at=doc.get("updated_at"),
        updated_by=doc.get("updated_by"),
    )


# ══════════════════════════════════════════════════════════════════════════════
# AJUSTES GLS · Guardar remitente
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/config/gls/remitente", response_model=ConfigGLSResponse)
async def config_gls_set_remitente(
    remitente: RemitenteModel, user: dict = Depends(require_admin),
):
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    await db.configuracion.update_one(
        {"tipo": CONFIG_DOC_TIPO},
        {"$set": {
            "tipo": CONFIG_DOC_TIPO,
            "remitente": remitente.model_dump(),
            "updated_at": now,
            "updated_by": user.get("email", "sistema"),
        }},
        upsert=True,
    )
    return await config_gls_get(user)


class PollingPayload(BaseModel):
    polling_hours: float = Field(..., ge=0.25, le=48.0)


@router.post("/config/gls/polling", response_model=ConfigGLSResponse)
async def config_gls_set_polling(
    payload: PollingPayload, user: dict = Depends(require_admin),
):
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    await db.configuracion.update_one(
        {"tipo": CONFIG_DOC_TIPO},
        {"$set": {
            "tipo": CONFIG_DOC_TIPO,
            "polling_hours": float(payload.polling_hours),
            "updated_at": now,
            "updated_by": user.get("email", "sistema"),
        }},
        upsert=True,
    )
    return await config_gls_get(user)


# ══════════════════════════════════════════════════════════════════════════════
# AJUSTES GLS · Verificar conexión
# ══════════════════════════════════════════════════════════════════════════════

class VerifyResponse(BaseModel):
    ok: bool
    preview: bool
    mensaje: str
    detalle: Optional[str] = None


@router.post("/config/gls/verify", response_model=VerifyResponse)
async def config_gls_verify(user: dict = Depends(require_admin)):
    if _is_preview():
        return VerifyResponse(
            ok=True, preview=True,
            mensaje="Preview: credenciales no contactadas. Mock activo.",
            detalle="MCP_ENV=preview",
        )
    uid = os.environ.get("GLS_UID_CLIENTE", "")
    if not uid:
        return VerifyResponse(
            ok=False, preview=False,
            mensaje="Falta GLS_UID_CLIENTE en entorno.",
        )
    client = await _build_client_from_bd()
    # Consulta tracking de un codbarras ficticio → si responde (aunque sea error de codbarras),
    # sabemos que las credenciales son válidas.
    try:
        await client.obtener_tracking("0000000000000")
        return VerifyResponse(
            ok=True, preview=False,
            mensaje="Conexión con GLS verificada.",
        )
    except GLSError as exc:
        # Algunos errores indican credenciales válidas (ej: codbarras no existe).
        text = str(exc).lower()
        if any(k in text for k in ("autenticac", "unauth", "forbidden", "401", "403")):
            return VerifyResponse(
                ok=False, preview=False,
                mensaje="Credenciales GLS inválidas.",
                detalle=str(exc),
            )
        return VerifyResponse(
            ok=True, preview=False,
            mensaje="Conexión operativa (codbarras de prueba no encontrado, esperable).",
            detalle=str(exc),
        )
    except Exception as exc:  # noqa: BLE001
        return VerifyResponse(
            ok=False, preview=False,
            mensaje="Error de red o servicio.",
            detalle=str(exc),
        )
