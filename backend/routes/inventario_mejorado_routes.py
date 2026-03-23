"""
inventario_mejorado_routes.py — Endpoints mejorados de inventario
Incluye:
  - Movimientos de stock con trazabilidad
  - Alertas de stock (crítico/bajo)
  - Valoración de inventario
  - Sugerencias de reposición
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, List
from datetime import datetime, timezone
from pydantic import BaseModel
from config import db, logger
from auth import require_auth, require_admin
from logic.inventory import GestorInventario, TipoMovimiento

router = APIRouter(prefix="/inventario", tags=["Inventario Mejorado"])


# ── Modelos Pydantic ──────────────────────────────────────────────────────────

class MovimientoStock(BaseModel):
    tipo: str  # entrada, salida, ajuste_mas, ajuste_menos, reserva, liberacion, devolucion
    cantidad: int
    referencia: Optional[str] = ""
    notas: Optional[str] = ""


class AlertaStock(BaseModel):
    repuesto_id: str
    nombre: str
    sku: Optional[str]
    stock: int
    stock_reservado: int
    stock_disponible: int
    stock_minimo: int
    nivel: str  # critico, bajo
    proveedor_id: Optional[str]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/{repuesto_id}/movimiento")
async def registrar_movimiento_stock(
    repuesto_id: str,
    movimiento: MovimientoStock,
    user: dict = Depends(require_auth)
):
    """
    Registra un movimiento de stock con trazabilidad completa.
    Tipos: entrada, salida, ajuste_mas, ajuste_menos, reserva, liberacion, devolucion
    """
    # Buscar repuesto
    repuesto = await db.repuestos.find_one({"id": repuesto_id}, {"_id": 0})
    if not repuesto:
        raise HTTPException(status_code=404, detail="Repuesto no encontrado")

    # Validar tipo de movimiento
    try:
        tipo = TipoMovimiento(movimiento.tipo)
    except ValueError:
        raise HTTPException(
            status_code=400, 
            detail=f"Tipo de movimiento inválido. Válidos: {[t.value for t in TipoMovimiento]}"
        )

    # Aplicar movimiento
    try:
        repuesto_actualizado = GestorInventario.registrar_movimiento(
            repuesto=repuesto,
            tipo=tipo,
            cantidad=movimiento.cantidad,
            usuario=user.get("email", user.get("user_id")),
            referencia=movimiento.referencia or "",
            notas=movimiento.notas or "",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Guardar en DB
    await db.repuestos.update_one(
        {"id": repuesto_id},
        {"$set": {
            "stock": repuesto_actualizado["stock"],
            "stock_reservado": repuesto_actualizado.get("stock_reservado", 0),
            "movimientos": repuesto_actualizado.get("movimientos", []),
            "updated_at": repuesto_actualizado["updated_at"],
        }}
    )

    logger.info(f"Movimiento de stock: {tipo.value} x{movimiento.cantidad} para {repuesto_id} por {user.get('email')}")

    return {
        "success": True,
        "repuesto_id": repuesto_id,
        "tipo": tipo.value,
        "cantidad": movimiento.cantidad,
        "stock_actual": repuesto_actualizado["stock"],
        "stock_reservado": repuesto_actualizado.get("stock_reservado", 0),
        "stock_disponible": GestorInventario.stock_disponible(repuesto_actualizado),
    }


@router.get("/{repuesto_id}/historial")
async def obtener_historial_movimientos(
    repuesto_id: str,
    limite: int = 50,
    user: dict = Depends(require_auth)
):
    """
    Obtiene el historial de movimientos de un repuesto.
    """
    repuesto = await db.repuestos.find_one({"id": repuesto_id}, {"_id": 0})
    if not repuesto:
        raise HTTPException(status_code=404, detail="Repuesto no encontrado")

    historial = GestorInventario.obtener_historial(repuesto, limite)

    return {
        "repuesto_id": repuesto_id,
        "nombre": repuesto.get("nombre"),
        "stock_actual": repuesto.get("stock", 0),
        "total_movimientos": len(repuesto.get("movimientos", [])),
        "historial": historial,
    }


@router.get("/alertas")
async def obtener_alertas_stock(user: dict = Depends(require_auth)):
    """
    Obtiene todos los repuestos con alertas de stock (crítico o bajo).
    Ordenados por urgencia: primero críticos, luego bajos.
    """
    # Obtener todos los repuestos con stock bajo o crítico
    repuestos = await db.repuestos.find(
        {},
        {"_id": 0, "id": 1, "nombre": 1, "sku": 1, "stock": 1, 
         "stock_reservado": 1, "stock_minimo": 1, "proveedor_id": 1}
    ).to_list(10000)

    alertas = GestorInventario.generar_alertas_inventario(repuestos)

    return {
        "total_alertas": len(alertas),
        "criticos": len([a for a in alertas if a["nivel"] == "critico"]),
        "bajos": len([a for a in alertas if a["nivel"] == "bajo"]),
        "alertas": alertas,
    }


@router.get("/valoracion")
async def obtener_valoracion_inventario(user: dict = Depends(require_admin)):
    """
    Calcula la valoración total del inventario (a coste y PVP).
    Solo disponible para admin/master.
    """
    repuestos = await db.repuestos.find(
        {},
        {"_id": 0, "id": 1, "nombre": 1, "stock": 1, "precio_compra": 1, "precio_venta": 1}
    ).to_list(10000)

    valoracion = GestorInventario.valorar_inventario(repuestos)

    return valoracion


@router.get("/sugerencias-reposicion")
async def obtener_sugerencias_reposicion(
    meses_cobertura: int = 2,
    user: dict = Depends(require_admin)
):
    """
    Sugiere cantidades a reponer basándose en el consumo histórico.
    Solo disponible para admin/master.
    """
    # Obtener repuestos con alertas o con historial de movimientos
    repuestos = await db.repuestos.find(
        {"$or": [
            {"$expr": {"$lte": ["$stock", {"$ifNull": ["$stock_minimo", 0]}]}},
            {"movimientos": {"$exists": True, "$ne": []}}
        ]},
        {"_id": 0}
    ).to_list(1000)

    sugerencias = []
    for repuesto in repuestos:
        sugerencia = GestorInventario.sugerir_reposicion(repuesto, meses_cobertura)
        if sugerencia["cantidad_sugerida"] > 0:
            sugerencias.append(sugerencia)

    # Ordenar por cantidad sugerida (mayor primero)
    sugerencias.sort(key=lambda x: x["cantidad_sugerida"], reverse=True)

    return {
        "meses_cobertura": meses_cobertura,
        "total_sugerencias": len(sugerencias),
        "sugerencias": sugerencias,
    }


@router.get("/{repuesto_id}/stock-disponible")
async def obtener_stock_disponible(
    repuesto_id: str,
    user: dict = Depends(require_auth)
):
    """
    Obtiene el stock disponible real de un repuesto (total - reservado).
    """
    repuesto = await db.repuestos.find_one({"id": repuesto_id}, {"_id": 0})
    if not repuesto:
        raise HTTPException(status_code=404, detail="Repuesto no encontrado")

    return {
        "repuesto_id": repuesto_id,
        "nombre": repuesto.get("nombre"),
        "stock_total": repuesto.get("stock", 0),
        "stock_reservado": repuesto.get("stock_reservado", 0),
        "stock_disponible": GestorInventario.stock_disponible(repuesto),
        "stock_minimo": repuesto.get("stock_minimo", 0),
        "nivel_alerta": GestorInventario.nivel_alerta(repuesto),
    }
