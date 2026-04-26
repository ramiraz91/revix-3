"""
Tools del agente `call_center` (Fase 4 · Cara al cliente).

Tools registradas:
  1. buscar_orden_por_cliente   (customers:read + orders:read)
  2. obtener_historial_comunicacion (customers:read)
  3. enviar_mensaje_portal      (comm:write)
  4. escalar_a_humano           (comm:escalate)

Reglas de seguridad:
  - SIN scopes: finance:*, orders:write, insurance:*
  - Idempotency obligatoria en operaciones de escritura.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from ..auth import AgentIdentity, AuthError
from ._common import validate_input
from ._registry import ToolSpec, register


def _require(identity: AgentIdentity, *scopes: str) -> None:
    for s in scopes:
        if not identity.has_scope(s):
            raise AuthError(
                f'Scope requerido "{s}" no presente en agente "{identity.agent_id}"',
            )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ══════════════════════════════════════════════════════════════════════════════
# 1 · buscar_orden_por_cliente
# ══════════════════════════════════════════════════════════════════════════════

class BuscarOrdenClienteInput(BaseModel):
    cliente_id: Optional[str] = None
    email: Optional[str] = None
    estado: Optional[str] = Field(
        None,
        description="Filtro por estado (recepcion, en_taller, listo, entregado, …)",
    )
    limit: int = Field(20, ge=1, le=100)


async def _buscar_orden_por_cliente_handler(
    db: AsyncIOMotorDatabase, identity: AgentIdentity, params: dict,
) -> dict:
    _require(identity, "customers:read", "orders:read")
    p = validate_input(BuscarOrdenClienteInput, params)
    if not p.cliente_id and not p.email:
        return {"success": False, "error": "missing_input",
                "detail": "Indique cliente_id o email."}

    cli = None
    if p.cliente_id:
        cli = await db.clientes.find_one({"id": p.cliente_id}, {"_id": 0})
    if not cli and p.email:
        cli = await db.clientes.find_one(
            {"email": {"$regex": f"^{p.email}$", "$options": "i"}},
            {"_id": 0},
        )
    if not cli:
        return {"success": False, "error": "cliente_no_encontrado"}

    q: dict = {"cliente_id": cli["id"]}
    if p.estado:
        q["estado"] = p.estado

    cursor = db.ordenes.find(
        q,
        {"_id": 0, "id": 1, "numero_orden": 1, "estado": 1, "estado_actual": 1,
         "dispositivo": 1, "marca": 1, "modelo": 1, "averia": 1,
         "fecha_estimada_entrega": 1, "fecha_creacion": 1, "fecha_actualizacion": 1,
         "tecnico_asignado": 1, "numero_autorizacion": 1, "precio_total": 1},
    ).sort("fecha_creacion", -1).limit(p.limit)

    ordenes = await cursor.to_list(p.limit)
    return {
        "success": True,
        "cliente": {"id": cli["id"], "nombre": cli.get("nombre"),
                    "apellidos": cli.get("apellidos"), "email": cli.get("email"),
                    "telefono": cli.get("telefono")},
        "total": len(ordenes),
        "ordenes": ordenes,
    }


register(ToolSpec(
    name="buscar_orden_por_cliente",
    description="Devuelve las órdenes de un cliente (por id o email) con estado actual y fechas.",
    required_scope="orders:read",
    input_schema={
        "type": "object",
        "properties": {
            "cliente_id": {"type": "string"},
            "email": {"type": "string"},
            "estado": {"type": "string"},
            "limit": {"type": "integer"},
        },
        "additionalProperties": False,
    },
    handler=_buscar_orden_por_cliente_handler,
))


# ══════════════════════════════════════════════════════════════════════════════
# 2 · obtener_historial_comunicacion
# ══════════════════════════════════════════════════════════════════════════════

class HistorialComunicacionInput(BaseModel):
    cliente_id: str
    limit: int = Field(50, ge=1, le=200)


async def _obtener_historial_comunicacion_handler(
    db: AsyncIOMotorDatabase, identity: AgentIdentity, params: dict,
) -> dict:
    _require(identity, "customers:read")
    p = validate_input(HistorialComunicacionInput, params)
    cli = await db.clientes.find_one({"id": p.cliente_id}, {"_id": 0})
    if not cli:
        return {"success": False, "error": "cliente_no_encontrado"}

    # IDs de órdenes del cliente
    ordenes_ids = [
        o["id"] async for o in db.ordenes.find(
            {"cliente_id": p.cliente_id}, {"_id": 0, "id": 1},
        )
    ]

    # Mensajes (portal_messages, comunicaciones, notificaciones)
    eventos = []
    # 1) Mensajes del portal cliente
    async for m in db.portal_messages.find(
        {"$or": [{"cliente_id": p.cliente_id},
                 {"orden_id": {"$in": ordenes_ids}}]},
        {"_id": 0},
    ).sort("created_at", -1).limit(p.limit):
        eventos.append({
            "tipo": "mensaje_portal",
            "fecha": m.get("created_at"),
            "direccion": m.get("direccion") or "saliente",
            "asunto": m.get("asunto") or m.get("tipo"),
            "contenido": (m.get("mensaje") or m.get("contenido") or "")[:300],
            "orden_id": m.get("orden_id"),
            "autor": m.get("autor") or m.get("user_email"),
        })

    # 2) Notificaciones dirigidas al cliente
    async for n in db.notificaciones.find(
        {"$or": [{"cliente_id": p.cliente_id},
                 {"orden_id": {"$in": ordenes_ids}}]},
        {"_id": 0},
    ).sort("created_at", -1).limit(p.limit):
        eventos.append({
            "tipo": f"notif_{n.get('tipo','generica')}",
            "fecha": n.get("created_at"),
            "direccion": "saliente",
            "asunto": n.get("titulo"),
            "contenido": (n.get("mensaje") or "")[:300],
            "orden_id": n.get("orden_id"),
            "autor": n.get("source") or "sistema",
        })

    # 3) Llamadas registradas en logs (si existe colección)
    try:
        async for c in db.llamadas_log.find(
            {"cliente_id": p.cliente_id}, {"_id": 0},
        ).sort("fecha", -1).limit(p.limit):
            eventos.append({
                "tipo": "llamada",
                "fecha": c.get("fecha"),
                "direccion": c.get("direccion") or "entrante",
                "asunto": c.get("motivo"),
                "contenido": (c.get("notas") or "")[:300],
                "orden_id": c.get("orden_id"),
                "autor": c.get("operador"),
            })
    except Exception:
        pass

    # Ordenar por fecha desc
    eventos.sort(key=lambda e: str(e.get("fecha") or ""), reverse=True)
    return {"success": True, "cliente_id": p.cliente_id,
            "total": len(eventos), "eventos": eventos[: p.limit]}


register(ToolSpec(
    name="obtener_historial_comunicacion",
    description="Mensajes, llamadas y notificaciones de un cliente cronológicamente.",
    required_scope="customers:read",
    input_schema={
        "type": "object",
        "properties": {
            "cliente_id": {"type": "string"},
            "limit": {"type": "integer"},
        },
        "required": ["cliente_id"],
        "additionalProperties": False,
    },
    handler=_obtener_historial_comunicacion_handler,
))


# ══════════════════════════════════════════════════════════════════════════════
# 3 · enviar_mensaje_portal
# ══════════════════════════════════════════════════════════════════════════════

class EnviarMensajePortalInput(BaseModel):
    cliente_id: str
    order_id: Optional[str] = None
    mensaje: str = Field(..., min_length=1, max_length=2000)
    tipo: str = Field("informativo", pattern="^(informativo|respuesta|solicitud_info)$")
    idempotency_key: str = Field(..., min_length=8, max_length=64)


async def _enviar_mensaje_portal_handler(
    db: AsyncIOMotorDatabase, identity: AgentIdentity, params: dict,
) -> dict:
    _require(identity, "comm:write")
    p = validate_input(EnviarMensajePortalInput, params)

    # Idempotencia
    existing = await db.portal_messages.find_one(
        {"idempotency_key": p.idempotency_key}, {"_id": 0, "id": 1},
    )
    if existing:
        return {"success": True, "deduped": True, "message_id": existing["id"]}

    cli = await db.clientes.find_one({"id": p.cliente_id}, {"_id": 0, "id": 1})
    if not cli:
        return {"success": False, "error": "cliente_no_encontrado"}
    if p.order_id:
        ord_doc = await db.ordenes.find_one({"id": p.order_id}, {"_id": 0, "id": 1})
        if not ord_doc:
            return {"success": False, "error": "orden_no_encontrada"}

    msg = {
        "id": str(uuid.uuid4()),
        "cliente_id": p.cliente_id,
        "orden_id": p.order_id,
        "tipo": p.tipo,
        "direccion": "saliente",
        "mensaje": p.mensaje,
        "autor": f"agent:{identity.agent_id}",
        "idempotency_key": p.idempotency_key,
        "leido": False,
        "created_at": _now(),
    }
    await db.portal_messages.insert_one(msg)

    # Notificación al cliente — siempre que tengamos orden_id (si no, guardamos el msg igual)
    try:
        from modules.notificaciones.helper import create_notification
        await create_notification(
            db,
            categoria="COMUNICACION_INTERNA",
            tipo="mensaje_admin",
            titulo="Nuevo mensaje del taller",
            mensaje=p.mensaje[:200],
            cliente_id=p.cliente_id,
            orden_id=p.order_id,
            source=f"agent:{identity.agent_id}",
        )
    except Exception:
        pass

    return {"success": True, "deduped": False, "message_id": msg["id"]}


register(ToolSpec(
    name="enviar_mensaje_portal",
    description="Envía un mensaje al cliente en el portal. Idempotente por idempotency_key.",
    required_scope="comm:write",
    input_schema={
        "type": "object",
        "properties": {
            "cliente_id": {"type": "string"},
            "order_id": {"type": "string"},
            "mensaje": {"type": "string", "maxLength": 2000},
            "tipo": {"type": "string", "enum": ["informativo", "respuesta", "solicitud_info"]},
            "idempotency_key": {"type": "string"},
        },
        "required": ["cliente_id", "mensaje", "idempotency_key"],
        "additionalProperties": False,
    },
    handler=_enviar_mensaje_portal_handler,
))


# ══════════════════════════════════════════════════════════════════════════════
# 4 · escalar_a_humano
# ══════════════════════════════════════════════════════════════════════════════

ESCALATION_SLA = {
    "normal": "2 horas laborables",
    "alta":   "30 minutos",
}


class EscalarHumanoInput(BaseModel):
    cliente_id: str
    motivo_escalado: str = Field(..., min_length=10, max_length=500)
    resumen_conversacion: str = Field(..., min_length=10, max_length=2000)
    urgencia: str = Field("normal", pattern="^(normal|alta)$")
    order_id: Optional[str] = None


async def _escalar_a_humano_handler(
    db: AsyncIOMotorDatabase, identity: AgentIdentity, params: dict,
) -> dict:
    _require(identity, "comm:escalate")
    p = validate_input(EscalarHumanoInput, params)

    ticket = {
        "id": str(uuid.uuid4()),
        "cliente_id": p.cliente_id,
        "orden_id": p.order_id,
        "motivo": p.motivo_escalado,
        "resumen_conversacion": p.resumen_conversacion,
        "urgencia": p.urgencia,
        "estado": "abierto",
        "abierto_por_agente": identity.agent_id,
        "created_at": _now(),
        "sla_response": ESCALATION_SLA.get(p.urgencia, "indeterminado"),
    }
    await db.escalation_tickets.insert_one(ticket)

    # Notificación a TODOS los admins
    try:
        from modules.notificaciones.helper import create_notification
        admins = [u async for u in db.users.find(
            {"role": {"$in": ["master", "admin"]}, "is_active": {"$ne": False}},
            {"_id": 0, "id": 1},
        )]
        msg_resumen = (
            f"Cliente requiere atención humana ({p.urgencia.upper()}). "
            f"Motivo: {p.motivo_escalado[:120]}"
        )
        for adm in admins:
            await create_notification(
                db,
                categoria="INCIDENCIA",
                tipo="incidencia_agente",
                titulo=f"⚠️ Escalado de Call Center · urgencia {p.urgencia}",
                mensaje=msg_resumen,
                user_id=adm.get("id"),
                cliente_id=p.cliente_id,
                orden_id=p.order_id,
                source=f"agent:{identity.agent_id}",
                meta={"escalation_ticket_id": ticket["id"], "urgencia": p.urgencia},
            )
    except Exception:
        pass

    return {
        "success": True,
        "ticket_escalado_id": ticket["id"],
        "tiempo_estimado_respuesta": ESCALATION_SLA.get(p.urgencia, "indeterminado"),
        "urgencia": p.urgencia,
    }


register(ToolSpec(
    name="escalar_a_humano",
    description=(
        "Escala la conversación a un humano admin. OBLIGATORIO cuando: cliente "
        "expresa frustración intensa, amenaza con acciones legales, pide hablar "
        "con responsable, o reclamación de garantía sin resolver tras 2 interacciones."
    ),
    required_scope="comm:escalate",
    input_schema={
        "type": "object",
        "properties": {
            "cliente_id": {"type": "string"},
            "motivo_escalado": {"type": "string", "minLength": 10},
            "resumen_conversacion": {"type": "string", "minLength": 10},
            "urgencia": {"type": "string", "enum": ["normal", "alta"]},
            "order_id": {"type": "string"},
        },
        "required": ["cliente_id", "motivo_escalado", "resumen_conversacion"],
        "additionalProperties": False,
    },
    handler=_escalar_a_humano_handler,
))
