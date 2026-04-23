"""
Endpoints HTTP para logística (GLS Spain) — módulo v2.

Prefix: /api/logistica

Endpoints:
  POST /api/logistica/gls/crear-envio                    — crea etiqueta (con observaciones)
  GET  /api/logistica/gls/tracking/{codbarras}           — consulta tracking directo GLS
  GET  /api/logistica/gls/orden/{order_id}               — datos precarga + último envío
  POST /api/logistica/gls/actualizar-tracking/{codbarras} — refresca tracking desde GLS + BD
  POST /api/logistica/gls/abrir-incidencia               — crea incidencia manual vinculada
  GET  /api/logistica/gls/etiqueta/{codbarras}           — devuelve PDF cacheado
"""
from __future__ import annotations

import base64
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from config import db
from auth import require_auth

from modules.logistica.gls import (
    Destinatario, GLSClient, GLSError, Remitente,
)
from modules.logistica.state_mapper import (
    estado_color, friendly_estado, is_entregado, is_incidencia,
)

logger = logging.getLogger("gls.routes_logistica")

router = APIRouter(prefix="/logistica", tags=["Logística"])


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _build_remitente_from_env() -> Remitente:
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


def _is_preview() -> bool:
    return (os.environ.get("MCP_ENV", "").lower() == "preview")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _tracking_url(codbarras: str) -> str:
    return (f"https://www.gls-spain.es/es/ayuda/seguimiento-de-envio/"
            f"?match={codbarras}")


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


async def _get_orden(order_id: str) -> dict:
    orden = await db.ordenes.find_one(
        {"$or": [{"id": order_id}, {"numero_orden": order_id}]},
        {"_id": 0},
    )
    if not orden:
        raise HTTPException(404, f"Orden {order_id} no encontrada")
    return orden


# ──────────────────────────────────────────────────────────────────────────────
# Modelos API
# ──────────────────────────────────────────────────────────────────────────────

class CrearEnvioRequest(BaseModel):
    order_id: str = Field(..., min_length=1)
    peso_kg: float = Field(0.5, gt=0, le=40)  # default 0.5 kg (móvil típico)
    referencia: Optional[str] = None
    observaciones: Optional[str] = None
    # Overrides opcionales de destinatario (si el tramitador ajusta algo en el dialog)
    dest_nombre: Optional[str] = None
    dest_direccion: Optional[str] = None
    dest_poblacion: Optional[str] = None
    dest_provincia: Optional[str] = None
    dest_cp: Optional[str] = None
    dest_telefono: Optional[str] = None
    dest_movil: Optional[str] = None
    dest_email: Optional[str] = None


class EventoTrackingOut(BaseModel):
    fecha: str
    estado: str
    plaza: str
    codigo: str


class EnvioResumen(BaseModel):
    codbarras: str
    uid: str
    referencia: str
    peso_kg: float
    estado: str
    estado_codigo: str
    estado_cliente: str  # cliente-friendly
    estado_color: str
    incidencia: str
    fecha_entrega: str
    tracking_url: str
    creado_en: str
    ultima_actualizacion: str
    mock_preview: bool
    eventos: list[EventoTrackingOut]


class CrearEnvioResponse(BaseModel):
    success: bool
    codbarras: str
    uid: str
    referencia: str
    etiqueta_pdf_base64: str
    tracking_url: str
    mock_preview: bool


class DestinatarioPrefill(BaseModel):
    nombre: str
    direccion: str
    poblacion: str
    provincia: str
    cp: str
    telefono: str
    movil: str
    email: str
    observaciones: str


class OrdenGLSDetailResponse(BaseModel):
    order_id: str
    numero_orden: str
    destinatario: DestinatarioPrefill
    peso_kg_sugerido: float
    referencia_sugerida: str
    envios: list[EnvioResumen]  # vacío si nunca se creó etiqueta
    puede_crear_envio: bool


class AbrirIncidenciaRequest(BaseModel):
    order_id: str
    codbarras: str
    titulo: Optional[str] = None
    descripcion: str = Field(..., min_length=3)
    severidad: str = Field("media", pattern="^(baja|media|alta|critica)$")


# ──────────────────────────────────────────────────────────────────────────────
# Constructor envío resumen (a partir de doc almacenado en ordenes.gls_envios[])
# ──────────────────────────────────────────────────────────────────────────────

def _envio_doc_to_resumen(doc: dict) -> EnvioResumen:
    estado = doc.get("estado_actual") or doc.get("estado") or ""
    codigo = str(doc.get("estado_codigo") or "")
    eventos = [
        EventoTrackingOut(
            fecha=e.get("fecha", ""), estado=e.get("estado", ""),
            plaza=e.get("plaza", ""), codigo=str(e.get("codigo", "")),
        )
        for e in (doc.get("eventos") or [])
    ]
    return EnvioResumen(
        codbarras=doc.get("codbarras", ""),
        uid=doc.get("uid", ""),
        referencia=doc.get("referencia", ""),
        peso_kg=float(doc.get("peso_kg", 0.5)),
        estado=estado,
        estado_codigo=codigo,
        estado_cliente=friendly_estado(estado, codigo),
        estado_color=estado_color(estado, codigo),
        incidencia=doc.get("incidencia", ""),
        fecha_entrega=doc.get("fecha_entrega", ""),
        tracking_url=doc.get("tracking_url") or _tracking_url(doc.get("codbarras", "")),
        creado_en=doc.get("creado_en", ""),
        ultima_actualizacion=doc.get("ultima_actualizacion", doc.get("creado_en", "")),
        mock_preview=bool(doc.get("mock_preview", False)),
        eventos=eventos,
    )


# ──────────────────────────────────────────────────────────────────────────────
# POST /gls/crear-envio
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/gls/crear-envio", response_model=CrearEnvioResponse)
async def crear_envio_gls(
    data: CrearEnvioRequest, user: dict = Depends(require_auth),
):
    orden = await _get_orden(data.order_id)

    # Destinatario: base de BD + overrides del request
    destinatario = await _destinatario_desde_orden(orden)

    def _apply(field: str, override_val: Optional[str]) -> None:
        if override_val is not None and override_val.strip():
            setattr(destinatario, field, override_val.strip())

    _apply("nombre", data.dest_nombre)
    _apply("direccion", data.dest_direccion)
    _apply("poblacion", data.dest_poblacion)
    _apply("provincia", data.dest_provincia)
    _apply("cp", data.dest_cp)
    _apply("telefono", data.dest_telefono)
    _apply("movil", data.dest_movil)
    _apply("email", data.dest_email)
    if data.observaciones is not None:
        destinatario.observaciones = data.observaciones.strip() or destinatario.observaciones

    # Validaciones
    if not destinatario.direccion or not destinatario.cp:
        raise HTTPException(400, "Destinatario incompleto: falta dirección o CP.")
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

    tracking_url = _tracking_url(resultado.codbarras)
    mock_preview = _is_preview()
    now = _now_iso()

    envio_doc = {
        "codbarras": resultado.codbarras,
        "uid": resultado.uid,
        "referencia": resultado.referencia,
        "tracking_url": tracking_url,
        "peso_kg": data.peso_kg,
        "observaciones": data.observaciones or "",
        "destinatario_snapshot": {
            "nombre": destinatario.nombre,
            "direccion": destinatario.direccion,
            "cp": destinatario.cp,
            "poblacion": destinatario.poblacion,
            "provincia": destinatario.provincia,
            "telefono": destinatario.telefono,
            "email": destinatario.email,
        },
        "estado": "creado",
        "estado_actual": "RECIBIDA INFORMACION",
        "estado_codigo": "0",
        "eventos": [],
        "incidencia": "",
        "fecha_entrega": "",
        "mock_preview": mock_preview,
        "creado_en": now,
        "ultima_actualizacion": now,
        "creado_por": user.get("email", ""),
    }

    await db.ordenes.update_one(
        {"id": orden.get("id")},
        {"$push": {"gls_envios": envio_doc},
         "$set": {"updated_at": now}},
    )

    # Guardar también la etiqueta (para reimpresión)
    await db.gls_etiquetas.insert_one({
        "codbarras": resultado.codbarras,
        "order_id": orden.get("id"),
        "referencia": resultado.referencia,
        "etiqueta_pdf_base64": resultado.etiqueta_pdf_base64,
        "mock_preview": mock_preview,
        "creado_en": now,
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
# GET /gls/orden/{order_id} — datos precarga + lista de envíos con tracking
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/gls/orden/{order_id}", response_model=OrdenGLSDetailResponse)
async def orden_gls_detalle(order_id: str, user: dict = Depends(require_auth)):
    orden = await _get_orden(order_id)
    destinatario = await _destinatario_desde_orden(orden)

    envios = [
        _envio_doc_to_resumen(d)
        for d in (orden.get("gls_envios") or [])
    ]

    return OrdenGLSDetailResponse(
        order_id=orden.get("id", order_id),
        numero_orden=orden.get("numero_orden", ""),
        destinatario=DestinatarioPrefill(
            nombre=destinatario.nombre,
            direccion=destinatario.direccion,
            poblacion=destinatario.poblacion,
            provincia=destinatario.provincia,
            cp=destinatario.cp,
            telefono=destinatario.telefono,
            movil=destinatario.movil,
            email=destinatario.email,
            observaciones=destinatario.observaciones,
        ),
        peso_kg_sugerido=0.5,
        referencia_sugerida=orden.get("numero_orden", ""),
        envios=envios,
        puede_crear_envio=bool(destinatario.direccion and destinatario.cp),
    )


# ──────────────────────────────────────────────────────────────────────────────
# GET /gls/tracking/{codbarras}  (consulta directa, sin persistir)
# ──────────────────────────────────────────────────────────────────────────────

class TrackingDirectResponse(BaseModel):
    success: bool
    codbarras: str
    estado_actual: str
    estado_codigo: str
    estado_cliente: str
    estado_color: str
    fecha_entrega: str
    incidencia: str
    eventos: list[EventoTrackingOut]
    tracking_url: str
    mock_preview: bool


@router.get("/gls/tracking/{codbarras}", response_model=TrackingDirectResponse)
async def tracking_gls(codbarras: str, user: dict = Depends(require_auth)):
    client = _build_gls_client()
    try:
        tracking = await client.obtener_tracking(codbarras)
    except GLSError as exc:
        raise HTTPException(400, f"GLS: {exc}") from exc
    if not tracking.success:
        raise HTTPException(404, f"Envío {codbarras} no encontrado en GLS")

    return TrackingDirectResponse(
        success=True,
        codbarras=tracking.codbarras,
        estado_actual=tracking.estado_actual,
        estado_codigo=tracking.estado_codigo,
        estado_cliente=friendly_estado(tracking.estado_actual, tracking.estado_codigo),
        estado_color=estado_color(tracking.estado_actual, tracking.estado_codigo),
        fecha_entrega=tracking.fecha_entrega,
        incidencia=tracking.incidencia,
        eventos=[EventoTrackingOut(**e.to_dict()) for e in tracking.eventos],
        tracking_url=_tracking_url(tracking.codbarras),
        mock_preview=_is_preview(),
    )


# ──────────────────────────────────────────────────────────────────────────────
# POST /gls/actualizar-tracking/{codbarras}
# Consulta GLS, actualiza `ordenes.gls_envios[]`, aplica side-effects:
#   - si entregado → estado de la orden pasa a "enviado" si procede
#   - si incidencia → crea incidencia automática
#   - crea notificación interna si cambia estado
# ──────────────────────────────────────────────────────────────────────────────

class ActualizarTrackingResponse(BaseModel):
    success: bool
    codbarras: str
    estado_cambio: bool
    envio: EnvioResumen
    orden_estado_actualizado: bool = False
    incidencia_creada: Optional[str] = None
    notificacion_creada: Optional[str] = None


@router.post("/gls/actualizar-tracking/{codbarras}",
             response_model=ActualizarTrackingResponse)
async def actualizar_tracking(
    codbarras: str, user: dict = Depends(require_auth),
):
    # Buscar orden que contenga ese codbarras
    orden = await db.ordenes.find_one(
        {"gls_envios.codbarras": codbarras}, {"_id": 0},
    )
    if not orden:
        raise HTTPException(404, f"Ningún envío con codbarras={codbarras}")

    client = _build_gls_client()
    try:
        tracking = await client.obtener_tracking(codbarras)
    except GLSError as exc:
        raise HTTPException(400, f"GLS: {exc}") from exc

    side_effects = await _apply_tracking_update(
        orden=orden, codbarras=codbarras, tracking=tracking,
        source=f"manual:{user.get('email','')}",
    )

    # Devolver estado actualizado
    orden2 = await db.ordenes.find_one({"id": orden["id"]}, {"_id": 0})
    envio_doc = next(
        (e for e in (orden2.get("gls_envios") or []) if e.get("codbarras") == codbarras),
        None,
    )
    return ActualizarTrackingResponse(
        success=True,
        codbarras=codbarras,
        estado_cambio=side_effects["estado_cambio"],
        envio=_envio_doc_to_resumen(envio_doc or {}),
        orden_estado_actualizado=side_effects["orden_estado_actualizado"],
        incidencia_creada=side_effects.get("incidencia_id"),
        notificacion_creada=side_effects.get("notificacion_id"),
    )


async def _apply_tracking_update(
    *, orden: dict, codbarras: str, tracking, source: str,
) -> dict:
    """
    Aplica el tracking obtenido sobre `ordenes.gls_envios[].codbarras==codbarras`.

    Returns dict: {estado_cambio, orden_estado_actualizado, incidencia_id, notificacion_id}
    """
    envio_prev = next(
        (e for e in (orden.get("gls_envios") or []) if e.get("codbarras") == codbarras),
        None,
    )
    estado_anterior = (envio_prev or {}).get("estado_actual", "")
    nuevo_estado = tracking.estado_actual or estado_anterior
    codigo_nuevo = tracking.estado_codigo or ""
    incidencia_texto = tracking.incidencia or ""

    # Detectar incidencia incluso en el texto del último evento
    ultimo_evento = tracking.eventos[-1] if tracking.eventos else None
    if ultimo_evento and is_incidencia(ultimo_evento.estado):
        if not incidencia_texto:
            incidencia_texto = ultimo_evento.estado

    estado_cambio = (nuevo_estado != estado_anterior)
    now = _now_iso()

    # Persistir actualización del envío (update positional)
    await db.ordenes.update_one(
        {"id": orden["id"], "gls_envios.codbarras": codbarras},
        {"$set": {
            "gls_envios.$.estado_actual": nuevo_estado,
            "gls_envios.$.estado_codigo": codigo_nuevo,
            "gls_envios.$.eventos": [e.to_dict() for e in tracking.eventos],
            "gls_envios.$.incidencia": incidencia_texto,
            "gls_envios.$.fecha_entrega": tracking.fecha_entrega or "",
            "gls_envios.$.ultima_actualizacion": now,
            "updated_at": now,
        }},
    )

    result = {
        "estado_cambio": estado_cambio,
        "orden_estado_actualizado": False,
        "incidencia_id": None,
        "notificacion_id": None,
    }

    # Side-effect 1 · si entregado y la orden aún no está en 'enviado'/'entregado'
    if is_entregado(nuevo_estado, codigo_nuevo):
        estado_orden_actual = (orden.get("estado") or "").lower()
        if estado_orden_actual not in {"enviado", "entregado", "cerrada"}:
            await db.ordenes.update_one(
                {"id": orden["id"]},
                {"$set": {
                    "estado": "enviado",
                    "fecha_enviado": orden.get("fecha_enviado") or now,
                    "updated_at": now,
                },
                "$push": {
                    "historial_estados": {
                        "estado": "enviado",
                        "fecha": now,
                        "usuario": "sistema",
                        "nota": f"GLS entregado · codbarras {codbarras}",
                    },
                }},
            )
            result["orden_estado_actualizado"] = True

    # Side-effect 2 · si hay incidencia crítica, crear incidencia
    if is_incidencia(nuevo_estado) or (incidencia_texto and is_incidencia(incidencia_texto)):
        # Evitar duplicar: buscar incidencia abierta del mismo codbarras
        existing = await db.incidencias.find_one(
            {"orden_id": orden["id"], "tipo": "logistica_gls",
             "codbarras": codbarras, "estado": {"$in": ["abierta", "en_proceso"]}},
            {"_id": 0, "id": 1},
        )
        if not existing:
            inc_id = str(uuid.uuid4())
            await db.incidencias.insert_one({
                "id": inc_id,
                "orden_id": orden["id"],
                "codbarras": codbarras,
                "tipo": "logistica_gls",
                "severidad": "alta",
                "titulo": f"Incidencia envío GLS · {codbarras}",
                "descripcion": incidencia_texto or nuevo_estado,
                "estado": "abierta",
                "reportada_por": "sistema",
                "created_at": now,
                "source": source,
            })
            result["incidencia_id"] = inc_id

    # Side-effect 3 · notificación al tramitador si hay cambio
    if estado_cambio:
        notif_id = str(uuid.uuid4())
        destinatario_email = (orden.get("tecnico_asignado")
                              or orden.get("created_by")
                              or "")
        await db.notificaciones.insert_one({
            "id": notif_id,
            "tipo": "gls_tracking_update",
            "orden_id": orden["id"],
            "usuario_destino": destinatario_email,
            "mensaje": (
                f"OT {orden.get('numero_orden','')} · envío GLS {codbarras}: "
                f"{friendly_estado(nuevo_estado, codigo_nuevo)}"
            ),
            "leida": False,
            "created_at": now,
            "source": source,
        })
        result["notificacion_id"] = notif_id

    return result


# ──────────────────────────────────────────────────────────────────────────────
# POST /gls/abrir-incidencia
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/gls/abrir-incidencia")
async def abrir_incidencia(
    data: AbrirIncidenciaRequest, user: dict = Depends(require_auth),
):
    orden = await _get_orden(data.order_id)
    now = _now_iso()
    inc_id = str(uuid.uuid4())
    doc = {
        "id": inc_id,
        "orden_id": orden["id"],
        "codbarras": data.codbarras,
        "tipo": "logistica_gls",
        "severidad": data.severidad,
        "titulo": data.titulo or f"Incidencia envío GLS · {data.codbarras}",
        "descripcion": data.descripcion,
        "estado": "abierta",
        "reportada_por": user.get("email", ""),
        "created_at": now,
        "source": "manual",
    }
    await db.incidencias.insert_one(doc)
    return {"success": True, "incidencia_id": inc_id}


# ──────────────────────────────────────────────────────────────────────────────
# GET /gls/etiqueta/{codbarras}  (re-descargar PDF desde cache)
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/gls/etiqueta/{codbarras}")
async def descargar_etiqueta(codbarras: str, user: dict = Depends(require_auth)):
    etiqueta = await db.gls_etiquetas.find_one(
        {"codbarras": codbarras}, {"_id": 0},
        sort=[("creado_en", -1)],
    )
    if not etiqueta:
        raise HTTPException(404, f"Etiqueta {codbarras} no encontrada")
    try:
        pdf_bytes = base64.b64decode(etiqueta["etiqueta_pdf_base64"])
    except Exception as exc:
        raise HTTPException(500, f"Etiqueta corrupta: {exc}") from exc
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="etiqueta-{codbarras}.pdf"'},
    )
