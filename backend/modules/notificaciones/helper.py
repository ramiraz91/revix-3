"""
Helper central para creación de notificaciones con categorías.

Uso:
    from modules.notificaciones.helper import create_notification, CATEGORIAS

    await create_notification(
        db,
        categoria="LOGISTICA",
        tipo="gls_tracking_update",
        titulo="Envío en reparto",
        mensaje="OT OT-123 · En camino a tu domicilio",
        orden_id="...", usuario_destino="...",
        meta={"codbarras": "..."},
    )

La categoría es el eje del filtrado en el dashboard.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("notificaciones.helper")

# Catálogo oficial de categorías
CATEGORIAS = (
    "LOGISTICA",
    "INCIDENCIA_LOGISTICA",
    "COMUNICACION_INTERNA",
    "RECHAZO",
    "MODIFICACION",
    "INCIDENCIA",
    "GENERAL",
)

# Mapeo de tipo legacy → categoría, para notificaciones creadas antes del refactor
# que no lleven el campo `categoria`.
TIPO_A_CATEGORIA: dict[str, str] = {
    # Logística
    "gls_tracking_update":        "LOGISTICA",
    "gls_entregado":              "LOGISTICA",
    "gls_recogida_pendiente":     "LOGISTICA",
    "gls_envio_creado":           "LOGISTICA",
    # Incidencias logísticas
    "gls_incidencia":             "INCIDENCIA_LOGISTICA",
    "logistica_incidencia":       "INCIDENCIA_LOGISTICA",
    # Incidencias generales
    "incidencia_abierta":         "INCIDENCIA",
    "incidencia_agente":          "INCIDENCIA",
    # Rechazos
    "presupuesto_rechazado":      "RECHAZO",
    "aseguradora_rechazo":        "RECHAZO",
    "orden_rechazada":            "RECHAZO",
    # Modificaciones
    "orden_estado_cambiado":      "MODIFICACION",
    "orden_reasignada":           "MODIFICACION",
    "orden_precio_cambiado":      "MODIFICACION",
    # Comunicación interna
    "mensaje_admin":              "COMUNICACION_INTERNA",
    "mensaje_tecnico":            "COMUNICACION_INTERNA",
    # General
    "orden_reparada":             "GENERAL",
    "orden_asignada":             "GENERAL",
    "orden_desbloqueada":         "GENERAL",
    "material_añadido":           "GENERAL",
    "material_pendiente":         "GENERAL",
    "material_aprobado":          "GENERAL",
    "llegada_repuesto":           "GENERAL",
    "orden_completada":           "GENERAL",
    "presupuesto_aceptado":       "GENERAL",
    "mcp_interno":                "GENERAL",
}


def categoria_from_tipo(tipo: str, default: str = "GENERAL") -> str:
    """Devuelve la categoría canónica para un `tipo`. GENERAL si no lo conoce."""
    return TIPO_A_CATEGORIA.get(tipo or "", default)


async def create_notification(
    db,
    *,
    tipo: str,
    mensaje: str,
    categoria: Optional[str] = None,
    titulo: Optional[str] = None,
    orden_id: Optional[str] = None,
    usuario_destino: Optional[str] = None,
    source: Optional[str] = None,
    meta: Optional[dict] = None,
    skip_if_duplicate_minutes: Optional[int] = None,
) -> str:
    """
    Inserta una notificación en `db.notificaciones`.

    - `categoria` se infiere a partir de `tipo` si no se proporciona.
    - `skip_if_duplicate_minutes`: si >0, no inserta si hay otra notificación
      idéntica (mismo tipo+orden_id+usuario_destino) en los últimos N minutos.

    Devuelve el `id` creado (o el existente si se evitó duplicado).
    """
    cat = (categoria or categoria_from_tipo(tipo) or "GENERAL").upper()
    if cat not in CATEGORIAS:
        logger.warning("Categoría desconocida '%s', usando GENERAL", cat)
        cat = "GENERAL"

    now = datetime.now(timezone.utc)
    now_iso = now.isoformat(timespec="seconds")

    if skip_if_duplicate_minutes and skip_if_duplicate_minutes > 0:
        from datetime import timedelta
        cutoff = (now - timedelta(minutes=skip_if_duplicate_minutes)).isoformat(timespec="seconds")
        q = {"tipo": tipo, "created_at": {"$gte": cutoff}}
        if orden_id:
            q["orden_id"] = orden_id
        if usuario_destino:
            q["usuario_destino"] = usuario_destino
        existing = await db.notificaciones.find_one(q, {"_id": 0, "id": 1})
        if existing:
            return existing["id"]

    doc = {
        "id": str(uuid.uuid4()),
        "tipo": tipo,
        "categoria": cat,
        "titulo": titulo or "",
        "mensaje": mensaje,
        "orden_id": orden_id,
        "usuario_destino": usuario_destino,
        "leida": False,
        "meta": meta or {},
        "source": source or "sistema",
        "created_at": now_iso,
    }
    await db.notificaciones.insert_one(doc)
    return doc["id"]
