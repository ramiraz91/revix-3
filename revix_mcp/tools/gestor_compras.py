"""
Tools del agente `gestor_compras` (#11).

Tools registradas:
  1. listar_compras_pendientes  (purchases:read)
  2. añadir_a_lista_compras     (inventory:write + purchases:write)
  3. generar_email_pedido       (purchases:read)
  4. marcar_recibido            (inventory:write + purchases:write)
  5. consultar_stock            (inventory:read)

Scopes del agente: inventory:read, inventory:write, purchases:read, purchases:write.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from ..auth import AgentIdentity, AuthError
from ._common import validate_input
from ._registry import ToolSpec, register


def _require_scopes(identity: AgentIdentity, *extras: str) -> None:
    for s in extras:
        if not identity.has_scope(s):
            raise AuthError(
                f'Scope requerido "{s}" no presente en agente "{identity.agent_id}"',
            )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ══════════════════════════════════════════════════════════════════════════════
# 1 · listar_compras_pendientes
# ══════════════════════════════════════════════════════════════════════════════

class ListarComprasPendientesInput(BaseModel):
    estado: Optional[str] = Field(None, description="pendiente|aprobado|pedido|recibido|cancelado")
    urgencia: Optional[str] = None
    proveedor_id: Optional[str] = None
    limit: int = Field(100, ge=1, le=500)


async def _listar_compras_pendientes_handler(
    db: AsyncIOMotorDatabase, identity: AgentIdentity, params: dict,
) -> dict:
    _require_scopes(identity, "purchases:read")
    p = validate_input(ListarComprasPendientesInput, params)

    q: dict = {}
    if p.estado:
        q["estado"] = p.estado
    else:
        q["estado"] = {"$in": ["pendiente", "aprobado"]}
    if p.urgencia:
        q["urgencia"] = p.urgencia
    if p.proveedor_id:
        q["proveedor_id"] = p.proveedor_id

    items = await db.lista_compras.find(
        q, {"_id": 0},
    ).sort("created_at", -1).limit(p.limit).to_list(p.limit)

    # Agrupar por proveedor + urgencia para vista "ejecutiva"
    por_proveedor: dict = {}
    por_urgencia: dict = {"critica": 0, "alta": 0, "normal": 0, "baja": 0}
    for it in items:
        pid = it.get("proveedor_id") or "_sin_proveedor_"
        if pid not in por_proveedor:
            por_proveedor[pid] = {
                "proveedor_id": it.get("proveedor_id"),
                "proveedor_nombre": it.get("proveedor_nombre") or "Sin proveedor",
                "items": 0,
                "total_estimado": 0.0,
            }
        por_proveedor[pid]["items"] += 1
        por_proveedor[pid]["total_estimado"] += (
            float(it.get("precio_estimado") or 0) * int(it.get("cantidad") or 0)
        )
        por_urgencia[it.get("urgencia", "normal")] = (
            por_urgencia.get(it.get("urgencia", "normal"), 0) + 1
        )

    return {
        "success": True,
        "total": len(items),
        "items": items,
        "por_urgencia": por_urgencia,
        "por_proveedor": list(por_proveedor.values()),
    }


register(ToolSpec(
    name="listar_compras_pendientes",
    description=(
        "Lista items de la lista de compras agrupados por proveedor y urgencia. "
        "Por defecto solo devuelve los abiertos (pendiente|aprobado). Útil para "
        "saber qué hay que pedir hoy."
    ),
    required_scope="purchases:read",
    input_schema={
        "type": "object",
        "properties": {
            "estado": {"type": "string"},
            "urgencia": {"type": "string"},
            "proveedor_id": {"type": "string"},
            "limit": {"type": "integer"},
        },
        "additionalProperties": False,
    },
    handler=_listar_compras_pendientes_handler,
))


# ══════════════════════════════════════════════════════════════════════════════
# 2 · añadir_a_lista_compras
# ══════════════════════════════════════════════════════════════════════════════

class AñadirListaInput(BaseModel):
    repuesto_id: Optional[str] = None
    repuesto_nombre: Optional[str] = None
    sku: Optional[str] = None
    cantidad: int = Field(1, ge=1, le=10000)
    urgencia: str = "normal"
    order_id_origen: Optional[str] = None
    proveedor_id: Optional[str] = None
    notas: Optional[str] = None


async def _añadir_a_lista_compras_handler(
    db: AsyncIOMotorDatabase, identity: AgentIdentity, params: dict,
) -> dict:
    _require_scopes(identity, "inventory:write", "purchases:write")
    p = validate_input(AñadirListaInput, params)
    if not p.repuesto_id and not p.repuesto_nombre:
        return {"success": False, "error": "missing_repuesto",
                "detail": "Debe indicar repuesto_id o repuesto_nombre."}

    from modules.compras.helpers import agregar_a_lista_compras, FUENTE_AGENTE
    try:
        item = await agregar_a_lista_compras(
            db,
            repuesto_id=p.repuesto_id,
            repuesto_nombre=p.repuesto_nombre,
            sku=p.sku,
            cantidad=p.cantidad,
            urgencia=p.urgencia,
            fuente=FUENTE_AGENTE,
            order_id=p.order_id_origen,
            proveedor_id=p.proveedor_id,
            notas=p.notas,
            creado_por=f"agent:{identity.agent_id}",
        )
        return {
            "success": True,
            "action": item.pop("_action", "created"),
            "item_id": item["id"],
            "repuesto_id": item.get("repuesto_id"),
            "repuesto_nombre": item.get("repuesto_nombre"),
            "cantidad": item.get("cantidad"),
            "urgencia": item.get("urgencia"),
            "estado": item.get("estado"),
        }
    except ValueError as exc:
        return {"success": False, "error": "invalid_input", "detail": str(exc)}


register(ToolSpec(
    name="añadir_a_lista_compras",
    description=(
        "Añade un repuesto a la lista de compras. Si el repuesto no existe en el "
        "inventario, lo crea automáticamente (categoría 'otros'). Idempotente: si "
        "ya existe un item abierto para ese repuesto, suma cantidad y registra la "
        "OT origen."
    ),
    required_scope="purchases:write",
    input_schema={
        "type": "object",
        "properties": {
            "repuesto_id": {"type": "string"},
            "repuesto_nombre": {"type": "string"},
            "sku": {"type": "string"},
            "cantidad": {"type": "integer", "minimum": 1, "maximum": 10000},
            "urgencia": {"type": "string", "enum": ["baja", "normal", "alta", "critica"]},
            "order_id_origen": {"type": "string"},
            "proveedor_id": {"type": "string"},
            "notas": {"type": "string"},
        },
        "additionalProperties": False,
    },
    handler=_añadir_a_lista_compras_handler,
))


# ══════════════════════════════════════════════════════════════════════════════
# 3 · generar_email_pedido
# ══════════════════════════════════════════════════════════════════════════════

class GenerarEmailPedidoInput(BaseModel):
    proveedor_id: str
    incluir_ids: Optional[list[str]] = None  # si None → todos los abiertos del proveedor


async def _generar_email_pedido_handler(
    db: AsyncIOMotorDatabase, identity: AgentIdentity, params: dict,
) -> dict:
    _require_scopes(identity, "purchases:read")
    p = validate_input(GenerarEmailPedidoInput, params)

    prov = await db.proveedores.find_one({"id": p.proveedor_id}, {"_id": 0})
    if not prov:
        return {"success": False, "error": "proveedor_no_encontrado"}

    q: dict = {"proveedor_id": p.proveedor_id, "estado": {"$in": ["pendiente", "aprobado"]}}
    if p.incluir_ids:
        q["id"] = {"$in": p.incluir_ids}
    items = await db.lista_compras.find(q, {"_id": 0}).to_list(length=None)
    if not items:
        return {"success": False, "error": "sin_items_pendientes",
                "proveedor_nombre": prov.get("nombre")}

    fecha_str = datetime.now(timezone.utc).strftime("%d/%m/%Y")
    asunto = f"Pedido Revix.es — {fecha_str}"
    lineas = ["Estimados " + (prov.get("nombre") or "proveedor") + ",", "",
              "Les realizamos el siguiente pedido:", ""]
    lineas.append(f"{'Ref':<18} {'Descripción':<40} {'Cant':<5} {'OTs':<25}")
    lineas.append("-" * 95)
    total = 0.0
    for it in items:
        ref = (it.get("repuesto_sku") or it.get("repuesto_id") or "")[:18]
        desc = (it.get("repuesto_nombre") or "")[:40]
        cant = int(it.get("cantidad") or 0)
        ots = ", ".join(it.get("ordenes_relacionadas") or [])[:25]
        total += float(it.get("precio_estimado") or 0) * cant
        lineas.append(f"{ref:<18} {desc:<40} {cant:<5} {ots:<25}")
    lineas += ["", "Rogamos confirmen disponibilidad y plazo de entrega.",
               "", "Un saludo,", "Revix.es"]

    return {
        "success": True,
        "proveedor": {
            "id": prov.get("id"), "nombre": prov.get("nombre"),
            "email": prov.get("email"),
        },
        "asunto": asunto,
        "cuerpo": "\n".join(lineas),
        "total_items": len(items),
        "total_estimado": round(total, 2),
        "items_ids": [it["id"] for it in items],
    }


register(ToolSpec(
    name="generar_email_pedido",
    description=(
        "Genera el cuerpo del email de pedido a un proveedor concreto. Devuelve "
        "asunto + cuerpo de texto plano listo para copiar/pegar. No envía emails."
    ),
    required_scope="purchases:read",
    input_schema={
        "type": "object",
        "properties": {
            "proveedor_id": {"type": "string"},
            "incluir_ids": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["proveedor_id"],
        "additionalProperties": False,
    },
    handler=_generar_email_pedido_handler,
))


# ══════════════════════════════════════════════════════════════════════════════
# 4 · marcar_recibido
# ══════════════════════════════════════════════════════════════════════════════

class MarcarRecibidoInput(BaseModel):
    purchase_id: str
    cantidad_recibida: Optional[int] = None
    precio_real: Optional[float] = None


async def _marcar_recibido_handler(
    db: AsyncIOMotorDatabase, identity: AgentIdentity, params: dict,
) -> dict:
    _require_scopes(identity, "inventory:write", "purchases:write")
    p = validate_input(MarcarRecibidoInput, params)

    item = await db.lista_compras.find_one({"id": p.purchase_id}, {"_id": 0})
    if not item:
        return {"success": False, "error": "item_no_encontrado"}
    if item["estado"] == "recibido":
        return {"success": False, "error": "ya_recibido"}
    cantidad = p.cantidad_recibida or int(item.get("cantidad") or 0)
    if cantidad < 1:
        return {"success": False, "error": "cantidad_invalida"}

    # Sumar stock
    if item.get("repuesto_id"):
        await db.repuestos.update_one(
            {"id": item["repuesto_id"]},
            {"$inc": {"stock": cantidad},
             "$set": {"updated_at": datetime.now(timezone.utc)}},
        )

    update = {
        "estado": "recibido", "cantidad_recibida": cantidad,
        "recibido_en": _now(), "recibido_por": f"agent:{identity.agent_id}",
        "updated_at": _now(),
    }
    if p.precio_real is not None:
        update["precio_real"] = float(p.precio_real)
    await db.lista_compras.update_one({"id": p.purchase_id}, {"$set": update})

    # Notificar OTs
    from modules.notificaciones.helper import create_notification
    notifs_creadas = 0
    for oid in item.get("ordenes_relacionadas") or []:
        try:
            await create_notification(
                db,
                categoria="GENERAL",
                tipo="llegada_repuesto",
                titulo=f"Repuesto recibido: {item.get('repuesto_nombre')}",
                mensaje=f"Llegó la pieza solicitada (cantidad: {cantidad}). Stock actualizado.",
                orden_id=oid,
                source="agent_gestor_compras",
                meta={
                    "lista_compras_id": p.purchase_id,
                    "repuesto_id": item.get("repuesto_id"),
                    "cantidad_recibida": cantidad,
                },
            )
            notifs_creadas += 1
        except Exception:
            pass

    return {
        "success": True,
        "item_id": p.purchase_id,
        "estado": "recibido",
        "cantidad_recibida": cantidad,
        "stock_actualizado": bool(item.get("repuesto_id")),
        "ordenes_notificadas": notifs_creadas,
    }


register(ToolSpec(
    name="marcar_recibido",
    description=(
        "Marca un item de la lista de compras como recibido. Suma `cantidad_recibida` "
        "al stock del repuesto y notifica a las OTs que esperaban esa pieza."
    ),
    required_scope="purchases:write",
    input_schema={
        "type": "object",
        "properties": {
            "purchase_id": {"type": "string"},
            "cantidad_recibida": {"type": "integer", "minimum": 1, "maximum": 10000},
            "precio_real": {"type": "number"},
        },
        "required": ["purchase_id"],
        "additionalProperties": False,
    },
    handler=_marcar_recibido_handler,
))


# ══════════════════════════════════════════════════════════════════════════════
# 5 · consultar_stock
# ══════════════════════════════════════════════════════════════════════════════

class ConsultarStockInput(BaseModel):
    referencia: Optional[str] = None
    descripcion: Optional[str] = None


async def _consultar_stock_handler(
    db: AsyncIOMotorDatabase, identity: AgentIdentity, params: dict,
) -> dict:
    _require_scopes(identity, "inventory:read")
    p = validate_input(ConsultarStockInput, params)
    if not p.referencia and not p.descripcion:
        return {"success": False, "error": "missing_input",
                "detail": "Indique al menos referencia o descripcion."}

    or_clauses: list[dict] = []
    if p.referencia:
        or_clauses += [{"sku": p.referencia}, {"sku_proveedor": p.referencia},
                       {"id": p.referencia},
                       {"codigo_barras": p.referencia}, {"ean": p.referencia}]
    if p.descripcion:
        or_clauses += [
            {"nombre": {"$regex": p.descripcion, "$options": "i"}},
            {"descripcion": {"$regex": p.descripcion, "$options": "i"}},
        ]
    repuestos = await db.repuestos.find(
        {"$or": or_clauses}, {"_id": 0},
    ).limit(20).to_list(20)

    items = []
    for r in repuestos:
        # OTs activas que necesitan esta pieza (vía lista_compras abierta)
        items_lista = await db.lista_compras.find(
            {"repuesto_id": r["id"], "estado": {"$in": ["pendiente", "aprobado"]}},
            {"_id": 0, "ordenes_relacionadas": 1},
        ).to_list(length=None)
        ots = []
        for it in items_lista:
            ots.extend(it.get("ordenes_relacionadas") or [])
        items.append({
            "id": r["id"],
            "nombre": r.get("nombre"),
            "sku": r.get("sku"),
            "stock": r.get("stock", 0),
            "stock_minimo": r.get("stock_minimo", 0),
            "bajo_minimo": (r.get("stock", 0) <= r.get("stock_minimo", 0)),
            "proveedor": r.get("proveedor"),
            "proveedor_id": r.get("proveedor_id"),
            "precio_compra": r.get("precio_compra"),
            "precio_venta": r.get("precio_venta"),
            "ots_que_la_necesitan": list(set(ots))[:20],
        })
    return {"success": True, "total": len(items), "items": items}


register(ToolSpec(
    name="consultar_stock",
    description=(
        "Consulta stock actual y mínimo de un repuesto por referencia (SKU/EAN/id) "
        "o descripción. Devuelve también las OTs que necesitan esa pieza."
    ),
    required_scope="inventory:read",
    input_schema={
        "type": "object",
        "properties": {
            "referencia": {"type": "string"},
            "descripcion": {"type": "string"},
        },
        "additionalProperties": False,
    },
    handler=_consultar_stock_handler,
))
