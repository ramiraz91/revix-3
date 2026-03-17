"""
GLS State Mapper & Business Events.
Central mapping between GLS status codes and internal CRM states.
Triggers business actions on state changes.
"""
import logging
from datetime import datetime, timezone

logger = logging.getLogger("gls_mapper")

# ─── GLS Status Codes → Internal States ──────────────────
# Source: GLS documentation ES-GLS-Maestros_V2
GLS_STATUS_MAP = {
    # Grabado / Alta
    "0": {"estado": "grabado", "descripcion": "Expedición grabada", "final": False},
    "1": {"estado": "grabado", "descripcion": "Datos recibidos", "final": False},
    # Recogida
    "2": {"estado": "recogido", "descripcion": "Recogido en origen", "final": False},
    "3": {"estado": "en_transito", "descripcion": "En tránsito", "final": False},
    # En delegación
    "4": {"estado": "en_delegacion", "descripcion": "En delegación destino", "final": False},
    "5": {"estado": "en_reparto", "descripcion": "En reparto", "final": False},
    # Entrega
    "6": {"estado": "entregado", "descripcion": "Entregado", "final": True},
    "7": {"estado": "entregado_parcial", "descripcion": "Entregado parcialmente", "final": True},
    # Incidencias
    "8": {"estado": "incidencia", "descripcion": "Incidencia en entrega", "final": False},
    "9": {"estado": "ausente", "descripcion": "Ausente", "final": False},
    "10": {"estado": "direccion_incorrecta", "descripcion": "Dirección incorrecta", "final": False},
    "11": {"estado": "rehusado", "descripcion": "Rehusado por destinatario", "final": False},
    # Devolución
    "12": {"estado": "devolucion_transito", "descripcion": "En devolución - tránsito", "final": False},
    "13": {"estado": "devuelto", "descripcion": "Devuelto a remitente", "final": True},
    # Cancelación
    "14": {"estado": "anulado", "descripcion": "Anulado", "final": True},
    "15": {"estado": "cancelado", "descripcion": "Cancelado", "final": True},
    # Almacenaje
    "20": {"estado": "en_almacen", "descripcion": "En almacén GLS", "final": False},
}

# Reverse: internal state → badge style
ESTADO_BADGE = {
    "grabado": {"color": "blue", "label": "Grabado"},
    "recogido": {"color": "cyan", "label": "Recogido"},
    "en_transito": {"color": "amber", "label": "En Tránsito"},
    "en_delegacion": {"color": "orange", "label": "En Delegación"},
    "en_reparto": {"color": "purple", "label": "En Reparto"},
    "entregado": {"color": "green", "label": "Entregado"},
    "entregado_parcial": {"color": "green", "label": "Entregado Parcial"},
    "incidencia": {"color": "red", "label": "Incidencia"},
    "ausente": {"color": "red", "label": "Ausente"},
    "direccion_incorrecta": {"color": "red", "label": "Dir. Incorrecta"},
    "rehusado": {"color": "red", "label": "Rehusado"},
    "devolucion_transito": {"color": "orange", "label": "Devolución Tránsito"},
    "devuelto": {"color": "slate", "label": "Devuelto"},
    "anulado": {"color": "slate", "label": "Anulado"},
    "cancelado": {"color": "slate", "label": "Cancelado"},
    "en_almacen": {"color": "yellow", "label": "En Almacén"},
    "desconocido": {"color": "gray", "label": "Desconocido"},
}

# States that are final (no more sync needed)
ESTADOS_FINALES = {k for k, v in GLS_STATUS_MAP.items() if v.get("final")}
ESTADOS_INTERNOS_FINALES = {"entregado", "entregado_parcial", "devuelto", "anulado", "cancelado"}

# States that require attention (incidencias)
ESTADOS_INCIDENCIA = {"incidencia", "ausente", "direccion_incorrecta", "rehusado"}

# Map GLS state → CRM order state
GLS_TO_ORDER_STATE = {
    "recogido": "recibida",
    "en_transito": None,  # No change
    "en_reparto": None,
    "entregado": "entregado",
    "devuelto": None,
    "incidencia": None,  # Create internal task instead
}


def map_gls_status(codigo_gls: str) -> dict:
    """Map a GLS status code to internal state."""
    codigo = str(codigo_gls).strip()
    mapped = GLS_STATUS_MAP.get(codigo)
    if mapped:
        return {**mapped, "codigo_gls": codigo}
    return {"estado": "desconocido", "descripcion": f"Código GLS: {codigo}", "final": False, "codigo_gls": codigo}


def is_final_state(estado_interno: str) -> bool:
    return estado_interno in ESTADOS_INTERNOS_FINALES


def is_incidencia(estado_interno: str) -> bool:
    return estado_interno in ESTADOS_INCIDENCIA


def get_badge_info(estado_interno: str) -> dict:
    return ESTADO_BADGE.get(estado_interno, ESTADO_BADGE["desconocido"])


async def process_state_change(db, envio_doc: dict, old_state: str, new_state: str, tracking_data: dict = None):
    """
    Process business logic when a GLS shipment state changes.
    Creates notifications, updates order state, logs events.
    """
    envio_id = envio_doc.get("id", "")
    orden_id = envio_doc.get("entidad_origen_id", "")
    
    if old_state == new_state:
        return

    logger.info(f"GLS state change: {envio_id} [{old_state}] → [{new_state}]")

    # 1. Update order state if applicable
    order_state = GLS_TO_ORDER_STATE.get(new_state)
    if order_state and orden_id:
        await db.ordenes.update_one(
            {"id": orden_id},
            {"$set": {"estado": order_state, "updated_at": datetime.now(timezone.utc).isoformat()},
             "$push": {"historial_estados": {
                 "estado": order_state,
                 "fecha": datetime.now(timezone.utc).isoformat(),
                 "usuario": "sistema_gls",
                 "notas": f"Actualizado automáticamente por GLS: {new_state}"
             }}}
        )
        logger.info(f"Order {orden_id} state updated to {order_state} via GLS")

    # 2. Store delivery proof if entregado
    if new_state == "entregado" and tracking_data:
        entrega_data = {
            "entrega_fecha": tracking_data.get("fecha", ""),
            "entrega_receptor": tracking_data.get("nombre_dst", ""),
        }
        await db.gls_envios.update_one(
            {"id": envio_id},
            {"$set": entrega_data}
        )

    # 3. Create notification for incidencias
    if is_incidencia(new_state):
        import uuid
        await db.notificaciones.insert_one({
            "id": str(uuid.uuid4()),
            "tipo": "incidencia_gls",
            "titulo": f"Incidencia GLS: {get_badge_info(new_state)['label']}",
            "mensaje": f"Envío {envio_doc.get('gls_codbarras', '')} - Orden {envio_doc.get('referencia_interna', '')}",
            "codigo_siniestro": orden_id,
            "orden_id": orden_id,
            "urgente": True,
            "popup": True,
            "leida": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        })

    # 4. Log the state change
    await _log_event(db, envio_id, "state_change", f"{old_state} → {new_state}")


async def _log_event(db, envio_id: str, tipo: str, detalle: str, error: str = ""):
    """Log integration event."""
    import uuid
    await db.gls_logs.insert_one({
        "id": str(uuid.uuid4()),
        "envio_id": envio_id,
        "tipo_operacion": tipo,
        "detalle": detalle,
        "error": error,
        "fecha": datetime.now(timezone.utc).isoformat()
    })
