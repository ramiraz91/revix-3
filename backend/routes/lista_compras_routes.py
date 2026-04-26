"""
Endpoints REST de la Lista de Compras (separado del módulo de facturas).

Rutas (todas bajo /api/compras/lista):
  GET  /lista                    → Listado con filtros
  GET  /lista/resumen            → Counts por estado/urgencia/proveedor
  POST /lista                    → Añadir item (manual/agente)
  POST /lista/aprobar            → Aprobar selección [ids]
  POST /lista/{id}/marcar-pedido → Pasa a estado "pedido" (con email opcional)
  POST /lista/{id}/marcar-recibido → Pasa a "recibido" + suma stock
  POST /lista/{id}/cancelar      → Cancela item
  GET  /lista/email-pedido/{proveedor_id} → Genera email plantilla por proveedor
  POST /lista/scan-stock-minimo  → Fuerza barrido stock<=mínimo
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth import require_admin, require_auth
from config import db
from modules.compras.helpers import (
    ESTADOS, ESTADOS_ABIERTOS, URGENCIAS, FUENTE_AGENTE,
    FUENTE_AUTO_STOCK, FUENTE_MANUAL,
    agregar_a_lista_compras,
    trigger_alerta_stock_minimo,
)
from modules.notificaciones.helper import create_notification

router = APIRouter(prefix="/compras/lista", tags=["Compras · Lista"])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ════════════════════════════════════════════════════════════════════════════
# GET /lista
# ════════════════════════════════════════════════════════════════════════════
@router.get("")
async def listar_items(
    estado: Optional[str] = None,
    urgencia: Optional[str] = None,
    proveedor_id: Optional[str] = None,
    solo_abiertos: bool = False,
    limit: int = 200,
    user: dict = Depends(require_auth),
):
    """Lista items de la lista de compras con filtros."""
    q: dict = {}
    if estado:
        if estado not in ESTADOS:
            raise HTTPException(400, f"estado inválido. Permitidos: {ESTADOS}")
        q["estado"] = estado
    if solo_abiertos:
        q["estado"] = {"$in": list(ESTADOS_ABIERTOS)}
    if urgencia:
        if urgencia not in URGENCIAS:
            raise HTTPException(400, f"urgencia inválida. Permitidas: {URGENCIAS}")
        q["urgencia"] = urgencia
    if proveedor_id:
        q["proveedor_id"] = proveedor_id

    items = await db.lista_compras.find(
        q, {"_id": 0},
    ).sort("created_at", -1).limit(min(limit, 500)).to_list(min(limit, 500))
    return {"total": len(items), "items": items}


# ════════════════════════════════════════════════════════════════════════════
# GET /lista/resumen
# ════════════════════════════════════════════════════════════════════════════
@router.get("/resumen")
async def resumen(user: dict = Depends(require_auth)):
    """Conteos para dashboard."""
    estados_counts = {e: 0 for e in ESTADOS}
    urgencias_counts = {u: 0 for u in URGENCIAS}
    proveedores_pendientes: dict = {}

    async for doc in db.lista_compras.find(
        {"estado": {"$in": list(ESTADOS_ABIERTOS)}},
        {"_id": 0, "estado": 1, "urgencia": 1, "proveedor_id": 1,
         "proveedor_nombre": 1},
    ):
        estados_counts[doc.get("estado", "pendiente")] = (
            estados_counts.get(doc.get("estado", "pendiente"), 0) + 1
        )
        urgencias_counts[doc.get("urgencia", "normal")] = (
            urgencias_counts.get(doc.get("urgencia", "normal"), 0) + 1
        )
        pid = doc.get("proveedor_id") or "_sin_proveedor_"
        if pid not in proveedores_pendientes:
            proveedores_pendientes[pid] = {
                "proveedor_id": doc.get("proveedor_id"),
                "proveedor_nombre": doc.get("proveedor_nombre") or "Sin proveedor",
                "items": 0,
            }
        proveedores_pendientes[pid]["items"] += 1

    pedidos_total = await db.lista_compras.count_documents({"estado": "pedido"})
    return {
        "estados": estados_counts,
        "urgencias": urgencias_counts,
        "proveedores_pendientes": list(proveedores_pendientes.values()),
        "total_abiertos": sum(estados_counts[e] for e in ESTADOS_ABIERTOS),
        "total_pedidos": pedidos_total,
    }


# ════════════════════════════════════════════════════════════════════════════
# POST /lista — añadir item (manual)
# ════════════════════════════════════════════════════════════════════════════
class AddItemRequest(BaseModel):
    repuesto_id: Optional[str] = None
    repuesto_nombre: Optional[str] = None
    sku: Optional[str] = None
    cantidad: int = Field(1, ge=1, le=10000)
    urgencia: str = "normal"
    proveedor_id: Optional[str] = None
    precio_estimado: Optional[float] = None
    order_id: Optional[str] = None
    notas: Optional[str] = None


@router.post("")
async def add_item(payload: AddItemRequest, user: dict = Depends(require_auth)):
    if not payload.repuesto_id and not payload.repuesto_nombre:
        raise HTTPException(400, "Debe indicar repuesto_id o repuesto_nombre")
    try:
        item = await agregar_a_lista_compras(
            db,
            repuesto_id=payload.repuesto_id,
            repuesto_nombre=payload.repuesto_nombre,
            sku=payload.sku,
            cantidad=payload.cantidad,
            urgencia=payload.urgencia,
            fuente=FUENTE_MANUAL,
            order_id=payload.order_id,
            proveedor_id=payload.proveedor_id,
            precio_estimado=payload.precio_estimado,
            notas=payload.notas,
            creado_por=user.get("email", "manual"),
        )
        return {"ok": True, "item": item}
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


# ════════════════════════════════════════════════════════════════════════════
# POST /lista/aprobar — solo master/admin
# ════════════════════════════════════════════════════════════════════════════
class AprobarRequest(BaseModel):
    ids: list[str]


@router.post("/aprobar")
async def aprobar_seleccion(
    payload: AprobarRequest, user: dict = Depends(require_admin),
):
    if not payload.ids:
        raise HTTPException(400, "ids vacío")
    role = user.get("role") or user.get("rol")
    if role not in ("master", "admin"):
        raise HTTPException(403, "Solo master/admin puede aprobar")
    now = _now()
    res = await db.lista_compras.update_many(
        {"id": {"$in": payload.ids}, "estado": "pendiente"},
        {"$set": {
            "estado": "aprobado",
            "aprobado_en": now,
            "aprobado_por": user.get("email", ""),
            "updated_at": now,
        }},
    )
    return {"ok": True, "aprobadas": res.modified_count, "ids": payload.ids}


# ════════════════════════════════════════════════════════════════════════════
# POST /lista/{id}/marcar-pedido
# ════════════════════════════════════════════════════════════════════════════
@router.post("/{item_id}/marcar-pedido")
async def marcar_pedido(item_id: str, user: dict = Depends(require_admin)):
    item = await db.lista_compras.find_one({"id": item_id}, {"_id": 0})
    if not item:
        raise HTTPException(404, "Item no encontrado")
    if item["estado"] not in ("pendiente", "aprobado"):
        raise HTTPException(400, f"Estado {item['estado']} no permite pasar a pedido")
    now = _now()
    await db.lista_compras.update_one(
        {"id": item_id},
        {"$set": {"estado": "pedido", "pedido_en": now,
                  "pedido_por": user.get("email", ""), "updated_at": now}},
    )
    return {"ok": True, "id": item_id, "estado": "pedido"}


# ════════════════════════════════════════════════════════════════════════════
# POST /lista/{id}/marcar-recibido — actualiza stock + notifica OTs
# ════════════════════════════════════════════════════════════════════════════
class MarcarRecibidoRequest(BaseModel):
    cantidad_recibida: Optional[int] = None  # default = cantidad pedida
    precio_real: Optional[float] = None


@router.post("/{item_id}/marcar-recibido")
async def marcar_recibido(
    item_id: str, payload: MarcarRecibidoRequest = MarcarRecibidoRequest(),
    user: dict = Depends(require_admin),
):
    item = await db.lista_compras.find_one({"id": item_id}, {"_id": 0})
    if not item:
        raise HTTPException(404, "Item no encontrado")
    if item["estado"] == "recibido":
        raise HTTPException(400, "Ya estaba marcado como recibido")
    cantidad = payload.cantidad_recibida or int(item.get("cantidad") or 0)
    if cantidad < 1:
        raise HTTPException(400, "cantidad_recibida debe ser >= 1")

    # 1) Sumar stock al repuesto
    if item.get("repuesto_id"):
        await db.repuestos.update_one(
            {"id": item["repuesto_id"]},
            {"$inc": {"stock": cantidad},
             "$set": {"updated_at": datetime.now(timezone.utc)}},
        )

    # 2) Marcar item recibido
    now = _now()
    update = {
        "estado": "recibido", "cantidad_recibida": cantidad,
        "recibido_en": now, "recibido_por": user.get("email", ""),
        "updated_at": now,
    }
    if payload.precio_real is not None:
        update["precio_real"] = float(payload.precio_real)
    await db.lista_compras.update_one({"id": item_id}, {"$set": update})

    # 3) Notificar a las OTs que esperaban esta pieza
    for oid in item.get("ordenes_relacionadas") or []:
        try:
            await create_notification(
                db,
                categoria="GENERAL",
                tipo="llegada_repuesto",
                titulo=f"Repuesto recibido: {item.get('repuesto_nombre')}",
                mensaje=(
                    f"Llegó el repuesto solicitado para esta OT (cantidad: {cantidad}). "
                    f"Stock actualizado."
                ),
                orden_id=oid,
                source="compras_lista",
                meta={
                    "lista_compras_id": item_id,
                    "repuesto_id": item.get("repuesto_id"),
                    "cantidad_recibida": cantidad,
                },
            )
        except Exception:
            pass

    return {"ok": True, "id": item_id, "estado": "recibido",
            "cantidad_recibida": cantidad}


# ════════════════════════════════════════════════════════════════════════════
# POST /lista/{id}/cancelar
# ════════════════════════════════════════════════════════════════════════════
@router.post("/{item_id}/cancelar")
async def cancelar(item_id: str, user: dict = Depends(require_admin)):
    item = await db.lista_compras.find_one({"id": item_id}, {"_id": 0})
    if not item:
        raise HTTPException(404, "Item no encontrado")
    if item["estado"] == "recibido":
        raise HTTPException(400, "No se puede cancelar un item ya recibido")
    await db.lista_compras.update_one(
        {"id": item_id},
        {"$set": {"estado": "cancelado", "updated_at": _now(),
                  "cancelado_por": user.get("email", "")}},
    )
    return {"ok": True, "id": item_id, "estado": "cancelado"}


# ════════════════════════════════════════════════════════════════════════════
# GET /lista/email-pedido/{proveedor_id}
# ════════════════════════════════════════════════════════════════════════════
@router.get("/email-pedido/{proveedor_id}")
async def email_pedido(
    proveedor_id: str,
    incluir_estados: str = "pendiente,aprobado",
    user: dict = Depends(require_auth),
):
    """Genera email plantilla agrupado por proveedor."""
    estados_l = [e.strip() for e in incluir_estados.split(",") if e.strip() in ESTADOS]
    if not estados_l:
        estados_l = ["pendiente", "aprobado"]

    prov = await db.proveedores.find_one(
        {"id": proveedor_id}, {"_id": 0},
    )
    if not prov:
        raise HTTPException(404, "Proveedor no encontrado")

    items = await db.lista_compras.find(
        {"proveedor_id": proveedor_id, "estado": {"$in": estados_l}},
        {"_id": 0},
    ).to_list(length=None)

    if not items:
        return {
            "ok": False,
            "reason": "sin_items_pendientes",
            "proveedor": prov,
            "items": [],
        }

    # Asunto + cuerpo
    fecha_str = datetime.now(timezone.utc).strftime("%d/%m/%Y")
    asunto = f"Pedido Revix.es — {fecha_str}"

    # Tabla en plain text + HTML
    lineas_txt = ["Estimados " + (prov.get("nombre") or "proveedor") + ",", "",
                  "Les realizamos el siguiente pedido:", ""]
    lineas_txt.append(f"{'Ref':<18} {'Descripción':<40} {'Cant':<6} {'OTs':<25}")
    lineas_txt.append("-" * 95)
    rows_html = []
    total_estim = 0.0
    for it in items:
        ref = (it.get("repuesto_sku") or it.get("repuesto_id") or "")[:18]
        desc = (it.get("repuesto_nombre") or "")[:40]
        cant = it.get("cantidad", 0)
        ots = ", ".join(it.get("ordenes_relacionadas") or [])[:25]
        precio_unit = float(it.get("precio_estimado") or 0)
        total_estim += precio_unit * (cant or 0)
        lineas_txt.append(f"{ref:<18} {desc:<40} {cant:<6} {ots:<25}")
        rows_html.append(
            f"<tr><td>{ref}</td><td>{desc}</td><td style='text-align:center'>{cant}</td>"
            f"<td>{ots}</td></tr>"
        )

    lineas_txt += [
        "",
        "Rogamos confirmen disponibilidad y plazo de entrega.",
        "",
        "Un saludo,",
        "Revix.es",
    ]
    cuerpo_text = "\n".join(lineas_txt)

    cuerpo_html = (
        f"<p>Estimados {prov.get('nombre') or 'proveedor'},</p>"
        f"<p>Les realizamos el siguiente pedido:</p>"
        f"<table border='1' cellpadding='6' cellspacing='0' "
        f"style='border-collapse:collapse;font-family:sans-serif'>"
        f"<thead><tr style='background:#f1f5f9'>"
        f"<th>Ref</th><th>Descripción</th><th>Cant</th><th>OTs</th></tr></thead>"
        f"<tbody>{''.join(rows_html)}</tbody></table>"
        f"<p>Rogamos confirmen disponibilidad y plazo de entrega.</p>"
        f"<p>Un saludo,<br><strong>Revix.es</strong></p>"
    )

    return {
        "ok": True,
        "proveedor": {
            "id": prov.get("id"), "nombre": prov.get("nombre"),
            "email": prov.get("email"), "telefono": prov.get("telefono"),
        },
        "asunto": asunto,
        "cuerpo_text": cuerpo_text,
        "cuerpo_html": cuerpo_html,
        "items": items,
        "total_items": len(items),
        "total_estimado": round(total_estim, 2),
    }


# ════════════════════════════════════════════════════════════════════════════
# POST /lista/scan-stock-minimo — barrido manual
# ════════════════════════════════════════════════════════════════════════════
@router.post("/scan-stock-minimo")
async def scan_stock_minimo(user: dict = Depends(require_admin)):
    """Recorre repuestos con stock <= mínimo y los agrega a la lista (idempotente)."""
    cursor = db.repuestos.find(
        {"$expr": {"$lte": ["$stock", {"$ifNull": ["$stock_minimo", 0]}]},
         "stock_minimo": {"$gt": 0}},
        {"_id": 0},
    )
    creados = 0
    actualizados = 0
    async for r in cursor:
        item = await trigger_alerta_stock_minimo(db, r)
        if not item:
            continue
        if item.get("_action") == "created":
            creados += 1
        else:
            actualizados += 1
    return {"ok": True, "creados": creados, "actualizados": actualizados}
