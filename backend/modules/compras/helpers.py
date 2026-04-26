"""
Compras · Helpers compartidos.

Funciones core reutilizadas por:
  - Endpoints REST (`routes/lista_compras_routes.py`).
  - Hook al asignar materiales a OT.
  - Hook al actualizar stock (stock <= mínimo).
  - Tool MCP `gestor_compras.añadir_a_lista_compras`.

Modelo `lista_compras` (colección):
{
  id: str (uuid),
  repuesto_id: str | None,
  repuesto_nombre: str,
  repuesto_sku: str | None,
  cantidad: int,
  urgencia: 'baja' | 'normal' | 'alta' | 'critica',
  estado: 'pendiente' | 'aprobado' | 'pedido' | 'recibido' | 'cancelado',
  ordenes_relacionadas: list[str]      # IDs de OT que necesitan esta pieza
  proveedor_id: str | None,
  proveedor_nombre: str | None,
  precio_estimado: float,
  fuente: 'auto_stock_minimo' | 'auto_triador' | 'auto_material_ot' | 'manual' | 'agente',
  notas: str | None,
  created_at, updated_at, created_by, ...,
  aprobado_en: str | None, aprobado_por: str | None,
  pedido_en: str | None, pedido_por: str | None,
  recibido_en: str | None, recibido_por: str | None,
  cantidad_recibida: int = 0,
}
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger("compras.helpers")

URGENCIAS = ("baja", "normal", "alta", "critica")
ESTADOS = ("pendiente", "aprobado", "pedido", "recibido", "cancelado")
ESTADOS_ABIERTOS = ("pendiente", "aprobado")

FUENTE_AUTO_STOCK = "auto_stock_minimo"
FUENTE_AUTO_TRIADOR = "auto_triador"
FUENTE_AUTO_MATERIAL = "auto_material_ot"
FUENTE_MANUAL = "manual"
FUENTE_AGENTE = "agente"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ──────────────────────────────────────────────────────────────────────────
# 1) Auto-crear repuesto en inventario si no existe
# ──────────────────────────────────────────────────────────────────────────

async def get_or_create_repuesto(
    db: AsyncIOMotorDatabase,
    nombre: str,
    *,
    sku: Optional[str] = None,
    categoria: str = "otros",
    proveedor_id: Optional[str] = None,
    precio_compra: float = 0.0,
    precio_venta: float = 0.0,
    creado_por: str = "auto",
    stock_inicial: int = 0,
    stock_minimo: int = 1,
) -> dict:
    """
    Busca un repuesto por nombre exacto (case-insensitive) o SKU.
    Si no existe, lo crea con los datos mínimos.
    Devuelve el documento (con _id excluido).
    """
    nombre_n = (nombre or "").strip()
    if not nombre_n:
        raise ValueError("nombre vacío")

    # 1. Buscar exacto case-insensitive por nombre
    q: dict = {"nombre": {"$regex": f"^{nombre_n}$", "$options": "i"}}
    if sku:
        q = {"$or": [q, {"sku": sku}, {"sku_proveedor": sku}]}
    existing = await db.repuestos.find_one(q, {"_id": 0})
    if existing:
        return existing

    # 2. Crear nuevo
    proveedor_nombre = None
    if proveedor_id:
        prov = await db.proveedores.find_one(
            {"id": proveedor_id}, {"_id": 0, "nombre": 1},
        )
        proveedor_nombre = prov.get("nombre") if prov else None

    doc = {
        "id": str(uuid.uuid4()),
        "nombre": nombre_n,
        "categoria": categoria,
        "sku": sku,
        "stock": stock_inicial,
        "stock_minimo": stock_minimo,
        "precio_compra": precio_compra,
        "precio_venta": precio_venta,
        "proveedor_id": proveedor_id,
        "proveedor": proveedor_nombre,
        "creado_por": creado_por,
        "auto_creado": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    await db.repuestos.insert_one(doc)
    logger.info("Repuesto auto-creado: %s (id=%s, por=%s)",
                nombre_n, doc["id"], creado_por)
    # Quitar _id que insert_one añade in-place
    return {k: v for k, v in doc.items() if k != "_id"}


# ──────────────────────────────────────────────────────────────────────────
# 2) Añadir / actualizar item en lista de compras (con dedupe)
# ──────────────────────────────────────────────────────────────────────────

URGENCIA_RANK = {"baja": 0, "normal": 1, "alta": 2, "critica": 3}


async def agregar_a_lista_compras(
    db: AsyncIOMotorDatabase,
    *,
    repuesto_id: Optional[str] = None,
    repuesto_nombre: Optional[str] = None,
    sku: Optional[str] = None,
    cantidad: int = 1,
    urgencia: str = "normal",
    fuente: str = FUENTE_MANUAL,
    order_id: Optional[str] = None,
    proveedor_id: Optional[str] = None,
    precio_estimado: Optional[float] = None,
    notas: Optional[str] = None,
    creado_por: str = "system",
) -> dict:
    """
    Añade a lista de compras. Idempotente:
      - Si ya existe un item ABIERTO (pendiente/aprobado) para el mismo repuesto_id
        → suma cantidad, agrega order_id a `ordenes_relacionadas`, sube urgencia
          si la nueva es mayor.
      - Si no existe → crea nuevo.

    Si no se pasa repuesto_id pero sí nombre, intenta resolver por nombre exacto;
    si tampoco existe en inventario, lo auto-crea (categoría "otros").

    Devuelve el item de la lista (creado o actualizado) con flag `_action`:
      - "created"
      - "updated"
    """
    if urgencia not in URGENCIAS:
        urgencia = "normal"
    cantidad = max(1, int(cantidad or 1))

    # Resolver / crear repuesto
    repuesto = None
    if repuesto_id:
        repuesto = await db.repuestos.find_one({"id": repuesto_id}, {"_id": 0})
    if not repuesto and repuesto_nombre:
        repuesto = await get_or_create_repuesto(
            db, repuesto_nombre, sku=sku, creado_por=creado_por,
            proveedor_id=proveedor_id,
        )
    if not repuesto:
        raise ValueError("Debe proveer repuesto_id o repuesto_nombre")

    rid = repuesto["id"]
    proveedor_id_eff = proveedor_id or repuesto.get("proveedor_id")
    proveedor_nombre = None
    if proveedor_id_eff:
        prov = await db.proveedores.find_one(
            {"id": proveedor_id_eff}, {"_id": 0, "nombre": 1},
        )
        proveedor_nombre = prov.get("nombre") if prov else repuesto.get("proveedor")
    else:
        proveedor_nombre = repuesto.get("proveedor")

    precio = (
        float(precio_estimado) if precio_estimado is not None
        else float(repuesto.get("precio_compra") or 0)
    )

    # Buscar item abierto duplicado
    existing = await db.lista_compras.find_one(
        {"repuesto_id": rid, "estado": {"$in": list(ESTADOS_ABIERTOS)}},
        {"_id": 0},
    )

    now = _now()
    if existing:
        # Actualizar cantidad + ordenes + urgencia (mayor) + última actualización
        new_cantidad = int(existing.get("cantidad") or 0) + cantidad
        ords = list(existing.get("ordenes_relacionadas") or [])
        if order_id and order_id not in ords:
            ords.append(order_id)
        prev_urg = existing.get("urgencia", "normal")
        new_urg = (
            urgencia if URGENCIA_RANK.get(urgencia, 1) > URGENCIA_RANK.get(prev_urg, 1)
            else prev_urg
        )
        update = {
            "cantidad": new_cantidad,
            "ordenes_relacionadas": ords,
            "urgencia": new_urg,
            "updated_at": now,
        }
        if not existing.get("proveedor_id") and proveedor_id_eff:
            update["proveedor_id"] = proveedor_id_eff
            update["proveedor_nombre"] = proveedor_nombre
        await db.lista_compras.update_one(
            {"id": existing["id"]}, {"$set": update},
        )
        existing.update(update)
        existing["_action"] = "updated"
        return existing

    # Crear nuevo
    doc = {
        "id": str(uuid.uuid4()),
        "repuesto_id": rid,
        "repuesto_nombre": repuesto.get("nombre"),
        "repuesto_sku": repuesto.get("sku") or repuesto.get("sku_proveedor"),
        "cantidad": cantidad,
        "cantidad_recibida": 0,
        "urgencia": urgencia,
        "estado": "pendiente",
        "ordenes_relacionadas": [order_id] if order_id else [],
        "proveedor_id": proveedor_id_eff,
        "proveedor_nombre": proveedor_nombre,
        "precio_estimado": precio,
        "fuente": fuente,
        "notas": notas,
        "created_at": now,
        "updated_at": now,
        "created_by": creado_por,
    }
    await db.lista_compras.insert_one(doc)
    return {**{k: v for k, v in doc.items() if k != "_id"}, "_action": "created"}


# ──────────────────────────────────────────────────────────────────────────
# 3) Hook: stock <= mínimo → añade auto a lista
# ──────────────────────────────────────────────────────────────────────────

async def trigger_alerta_stock_minimo(
    db: AsyncIOMotorDatabase, repuesto: dict,
) -> Optional[dict]:
    """
    Si el repuesto tiene stock <= stock_minimo, añade auto a lista de compras
    (urgencia 'alta' si stock=0, 'normal' si entre 1 y mínimo).
    Idempotente: si ya hay item abierto, no duplica (suma 0 vía update interno
    pero devuelve el existente).
    """
    stock = int(repuesto.get("stock") or 0)
    minimo = int(repuesto.get("stock_minimo") or 0)
    if minimo <= 0 or stock > minimo:
        return None

    # Si ya hay item abierto para este repuesto, no añadir más cantidad.
    existing = await db.lista_compras.find_one(
        {"repuesto_id": repuesto["id"], "estado": {"$in": list(ESTADOS_ABIERTOS)}},
        {"_id": 0},
    )
    if existing:
        # Subir urgencia si pasamos a stock=0
        if stock == 0 and existing.get("urgencia") != "critica":
            await db.lista_compras.update_one(
                {"id": existing["id"]},
                {"$set": {"urgencia": "alta" if existing["urgencia"] == "normal" else existing["urgencia"],
                          "updated_at": _now()}},
            )
        return existing

    cantidad = max(minimo - stock, 1) if minimo > stock else 1
    urgencia = "alta" if stock == 0 else "normal"
    return await agregar_a_lista_compras(
        db,
        repuesto_id=repuesto["id"],
        cantidad=cantidad,
        urgencia=urgencia,
        fuente=FUENTE_AUTO_STOCK,
        creado_por="system_stock_check",
    )
