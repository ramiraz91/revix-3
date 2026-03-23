"""
ordenes_mejorado_routes.py — Endpoints mejorados de órdenes
Incluye:
  - Historial de estados con trazabilidad
  - Alertas de retraso
  - Cálculo de costes
  - Gestión de materiales mejorada
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, List
from datetime import datetime, timezone
from pydantic import BaseModel
from config import db, logger
from auth import require_auth, require_admin
from logic.orders import GestorOrdenes, EstadoOrden, TRANSICIONES_VALIDAS

router = APIRouter(prefix="/ordenes-v2", tags=["Órdenes Mejoradas"])


# ── Modelos Pydantic ──────────────────────────────────────────────────────────

class CambioEstado(BaseModel):
    nuevo_estado: str
    motivo: Optional[str] = ""
    validar_transicion: Optional[bool] = True


class MaterialOrden(BaseModel):
    repuesto_id: str
    nombre: str
    cantidad: int
    precio_unitario: float
    es_tecnico: Optional[bool] = False


class AprobacionMateriales(BaseModel):
    accion: str  # aprobar, rechazar
    motivo: Optional[str] = ""


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/estados-validos")
async def obtener_estados_validos(user: dict = Depends(require_auth)):
    """
    Devuelve la máquina de estados con todas las transiciones válidas.
    """
    transiciones = {}
    for estado, siguientes in TRANSICIONES_VALIDAS.items():
        transiciones[estado.value] = [s.value for s in siguientes]

    return {
        "estados": [e.value for e in EstadoOrden],
        "transiciones": transiciones,
    }


@router.get("/{orden_id}/transiciones-disponibles")
async def obtener_transiciones_disponibles(
    orden_id: str,
    user: dict = Depends(require_auth)
):
    """
    Devuelve los estados a los que puede transicionar una orden específica.
    """
    orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0, "estado": 1, "numero_orden": 1})
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")

    estado_actual = orden.get("estado", "pendiente_recibir")
    
    try:
        estado_enum = EstadoOrden(estado_actual)
        siguientes = TRANSICIONES_VALIDAS.get(estado_enum, [])
        transiciones = [s.value for s in siguientes]
    except ValueError:
        transiciones = []

    return {
        "orden_id": orden_id,
        "numero_orden": orden.get("numero_orden"),
        "estado_actual": estado_actual,
        "transiciones_disponibles": transiciones,
    }


@router.patch("/{orden_id}/estado-mejorado")
async def cambiar_estado_mejorado(
    orden_id: str,
    cambio: CambioEstado,
    user: dict = Depends(require_auth)
):
    """
    Cambia el estado de una orden con validación de máquina de estados
    y registro en historial.
    """
    orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")

    try:
        orden_actualizada = GestorOrdenes.cambiar_estado(
            orden=orden,
            nuevo_estado=cambio.nuevo_estado,
            usuario=user.get("email", user.get("user_id")),
            motivo=cambio.motivo or "",
            validar=cambio.validar_transicion,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Guardar en DB
    await db.ordenes.update_one(
        {"id": orden_id},
        {"$set": {
            "estado": orden_actualizada["estado"],
            "historial_estados": orden_actualizada.get("historial_estados", []),
            "updated_at": orden_actualizada["updated_at"],
        }}
    )

    logger.info(f"Cambio de estado: {orden.get('estado')} → {cambio.nuevo_estado} para orden {orden_id}")

    return {
        "success": True,
        "orden_id": orden_id,
        "estado_anterior": orden.get("estado"),
        "estado_nuevo": orden_actualizada["estado"],
        "historial": orden_actualizada.get("historial_estados", [])[-1] if orden_actualizada.get("historial_estados") else None,
    }


@router.get("/{orden_id}/historial-estados")
async def obtener_historial_estados(
    orden_id: str,
    user: dict = Depends(require_auth)
):
    """
    Obtiene el historial completo de cambios de estado de una orden.
    """
    orden = await db.ordenes.find_one(
        {"id": orden_id},
        {"_id": 0, "id": 1, "numero_orden": 1, "estado": 1, "historial_estados": 1, "created_at": 1}
    )
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")

    return {
        "orden_id": orden_id,
        "numero_orden": orden.get("numero_orden"),
        "estado_actual": orden.get("estado"),
        "historial": orden.get("historial_estados", []),
        "created_at": orden.get("created_at"),
    }


@router.post("/{orden_id}/materiales-mejorado")
async def añadir_material_mejorado(
    orden_id: str,
    material: MaterialOrden,
    user: dict = Depends(require_auth)
):
    """
    Añade un material a la orden con gestión de bloqueo automático.
    Si es_tecnico=True, la orden se bloquea hasta aprobación.
    """
    orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")

    material_dict = {
        "repuesto_id": material.repuesto_id,
        "nombre": material.nombre,
        "cantidad": material.cantidad,
        "precio_unitario": material.precio_unitario,
    }

    es_tecnico = material.es_tecnico or user.get("role") == "tecnico"

    orden_actualizada = GestorOrdenes.añadir_material(
        orden=orden,
        material=material_dict,
        usuario=user.get("email", user.get("user_id")),
        es_tecnico=es_tecnico,
    )

    # Guardar en DB
    await db.ordenes.update_one(
        {"id": orden_id},
        {"$set": {
            "materiales": orden_actualizada.get("materiales", []),
            "bloqueada": orden_actualizada.get("bloqueada", False),
            "motivo_bloqueo": orden_actualizada.get("motivo_bloqueo"),
            "bloqueada_desde": orden_actualizada.get("bloqueada_desde"),
            "updated_at": orden_actualizada["updated_at"],
        }}
    )

    return {
        "success": True,
        "orden_id": orden_id,
        "material_añadido": material_dict,
        "bloqueada": orden_actualizada.get("bloqueada", False),
        "motivo_bloqueo": orden_actualizada.get("motivo_bloqueo"),
        "total_materiales": len(orden_actualizada.get("materiales", [])),
    }


@router.post("/{orden_id}/aprobar-materiales-mejorado")
async def gestionar_materiales_pendientes(
    orden_id: str,
    accion: AprobacionMateriales,
    user: dict = Depends(require_admin)
):
    """
    Aprueba o rechaza los materiales pendientes de una orden.
    Solo admin/master.
    """
    orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")

    try:
        if accion.accion == "aprobar":
            orden_actualizada = GestorOrdenes.aprobar_materiales(
                orden=orden,
                admin_usuario=user.get("email", user.get("user_id")),
            )
        elif accion.accion == "rechazar":
            if not accion.motivo:
                raise HTTPException(status_code=400, detail="Se requiere motivo para rechazar materiales")
            orden_actualizada = GestorOrdenes.rechazar_materiales(
                orden=orden,
                admin_usuario=user.get("email", user.get("user_id")),
                motivo=accion.motivo,
            )
        else:
            raise HTTPException(status_code=400, detail="Acción inválida. Use 'aprobar' o 'rechazar'")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Guardar en DB
    update_fields = {
        "materiales": orden_actualizada.get("materiales", []),
        "bloqueada": orden_actualizada.get("bloqueada", False),
        "motivo_bloqueo": orden_actualizada.get("motivo_bloqueo"),
        "updated_at": orden_actualizada["updated_at"],
    }
    if accion.accion == "rechazar":
        update_fields["rechazo_info"] = orden_actualizada.get("rechazo_info")

    await db.ordenes.update_one({"id": orden_id}, {"$set": update_fields})

    logger.info(f"Materiales {accion.accion}dos para orden {orden_id} por {user.get('email')}")

    return {
        "success": True,
        "orden_id": orden_id,
        "accion": accion.accion,
        "bloqueada": orden_actualizada.get("bloqueada", False),
    }


@router.get("/{orden_id}/coste")
async def calcular_coste_orden(
    orden_id: str,
    user: dict = Depends(require_auth)
):
    """
    Calcula el desglose de costes de una orden (materiales + mano de obra + IVA).
    """
    orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")

    orden_con_coste = GestorOrdenes.calcular_coste_total(orden)

    return {
        "orden_id": orden_id,
        "numero_orden": orden.get("numero_orden"),
        "coste_desglose": orden_con_coste.get("coste_desglose", {}),
    }


@router.get("/alertas-retraso")
async def obtener_ordenes_retrasadas(user: dict = Depends(require_auth)):
    """
    Obtiene todas las órdenes que llevan más tiempo del esperado en su estado actual.
    """
    # Obtener órdenes activas (no finalizadas)
    ordenes = await db.ordenes.find(
        {"estado": {"$nin": ["enviado", "cancelado", "garantia"]}},
        {"_id": 0, "id": 1, "numero_orden": 1, "estado": 1, "updated_at": 1, "created_at": 1}
    ).to_list(1000)

    retrasadas = GestorOrdenes.obtener_ordenes_retrasadas(ordenes)

    return {
        "total_ordenes_activas": len(ordenes),
        "total_retrasadas": len(retrasadas),
        "ordenes_retrasadas": retrasadas,
    }


@router.get("/{orden_id}/alerta-retraso")
async def verificar_alerta_retraso(
    orden_id: str,
    user: dict = Depends(require_auth)
):
    """
    Verifica si una orden específica tiene alerta de retraso.
    """
    orden = await db.ordenes.find_one(
        {"id": orden_id},
        {"_id": 0, "id": 1, "numero_orden": 1, "estado": 1, "updated_at": 1, "created_at": 1}
    )
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")

    alerta = GestorOrdenes.calcular_alerta_retraso(orden)

    return {
        "orden_id": orden_id,
        "numero_orden": orden.get("numero_orden"),
        "estado": orden.get("estado"),
        "tiene_alerta": alerta is not None,
        "alerta": alerta,
    }
