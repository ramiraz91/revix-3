"""
Scheduler de polling GLS cada N horas.

Recorre `ordenes.gls_envios[]` cuyos envíos NO están entregados ni marcados
como cerrados y llama a `_apply_tracking_update` (routes_logistica) para
refrescar el estado y disparar los side-effects (cambio de estado de la OT,
creación de incidencia automática, notificación al tramitador).

Config:
  GLS_POLLING_INTERVAL_HOURS  (default 4)
  MCP_ENV=preview             → no llama a GLS, usa mocks del GLSClient
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from modules.logistica.gls import GLSClient, GLSError
from modules.logistica.routes import (
    _apply_tracking_update, _build_gls_client,
)
from modules.logistica.state_mapper import is_entregado

logger = logging.getLogger("gls.logistica.scheduler")

_task: Optional[asyncio.Task] = None
_stop_event: Optional[asyncio.Event] = None


async def _run_once(db: AsyncIOMotorDatabase, client: GLSClient) -> dict:
    """Una iteración: actualiza todos los envíos pendientes. Devuelve estadísticas."""
    stats = {"procesados": 0, "cambios_estado": 0,
             "incidencias": 0, "entregas": 0, "errores": 0}

    # Envíos candidatos: todos los gls_envios que NO estén entregados
    # ni marcados como mock desactualizado.
    cursor = db.ordenes.find(
        {"gls_envios": {"$exists": True, "$ne": []}},
        {"_id": 0, "id": 1, "numero_orden": 1, "estado": 1,
         "tecnico_asignado": 1, "created_by": 1, "gls_envios": 1},
    )

    async for orden in cursor:
        envios = orden.get("gls_envios") or []
        for envio in envios:
            codbarras = envio.get("codbarras")
            if not codbarras:
                continue
            estado = envio.get("estado_actual", "")
            codigo = str(envio.get("estado_codigo", ""))
            if is_entregado(estado, codigo):
                continue  # ya entregado, skip
            try:
                tracking = await client.obtener_tracking(codbarras)
            except GLSError as exc:
                logger.warning("GLS error en polling codbarras=%s: %s", codbarras, exc)
                stats["errores"] += 1
                continue
            stats["procesados"] += 1
            try:
                effects = await _apply_tracking_update(
                    orden=orden, codbarras=codbarras, tracking=tracking,
                    source="scheduler:polling",
                )
                if effects.get("estado_cambio"):
                    stats["cambios_estado"] += 1
                if effects.get("incidencia_id"):
                    stats["incidencias"] += 1
                if effects.get("orden_estado_actualizado"):
                    stats["entregas"] += 1
            except Exception as exc:
                logger.exception("Error aplicando tracking %s: %s", codbarras, exc)
                stats["errores"] += 1

    return stats


async def _polling_loop(db: AsyncIOMotorDatabase, interval_seconds: int,
                        stop_event: asyncio.Event) -> None:
    logger.info("GLS logistica scheduler iniciado (interval=%ss)", interval_seconds)
    # Pequeño retraso inicial para que el backend esté completamente arriba
    try:
        await asyncio.wait_for(stop_event.wait(), timeout=60)
        return  # stop antes del primer tick
    except asyncio.TimeoutError:
        pass

    while not stop_event.is_set():
        started = datetime.now(timezone.utc)
        try:
            client = _build_gls_client()
            stats = await _run_once(db, client)
            logger.info("GLS logistica polling tick: %s", stats)
        except Exception as exc:
            logger.exception("Error en polling tick: %s", exc)

        elapsed = (datetime.now(timezone.utc) - started).total_seconds()
        wait = max(1, interval_seconds - int(elapsed))
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=wait)
        except asyncio.TimeoutError:
            continue


def start_logistica_scheduler(db: AsyncIOMotorDatabase) -> None:
    """Arranca el loop. Intervalo desde GLS_POLLING_INTERVAL_HOURS (default 4h)."""
    global _task, _stop_event
    if _task and not _task.done():
        return
    hours = float(os.environ.get("GLS_POLLING_INTERVAL_HOURS", "4"))
    interval_seconds = max(60, int(hours * 3600))
    _stop_event = asyncio.Event()
    _task = asyncio.create_task(_polling_loop(db, interval_seconds, _stop_event))


def stop_logistica_scheduler() -> None:
    global _task, _stop_event
    if _stop_event:
        _stop_event.set()
    _task = None
