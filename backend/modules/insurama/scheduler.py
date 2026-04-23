"""
Scheduler Insurama Inbox — polling cada 6h para detectar observaciones,
cambios de estado y cambios de precio en presupuestos Sumbroker.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from modules.insurama.inbox import check_all_active

logger = logging.getLogger("insurama.inbox.scheduler")

INTERVAL_SECONDS = 6 * 60 * 60  # 6 horas

_task: Optional[asyncio.Task] = None
_running = False


async def _loop():
    global _running
    _running = True
    # Pequeño delay para no solapar con startup de otros schedulers
    await asyncio.sleep(120)
    while _running:
        try:
            stats = await check_all_active()
            logger.info(
                "Insurama inbox sweep · ordenes=%s ok=%s cambios=%s notificaciones=%s primera=%s errores=%s",
                stats.get("total"), stats.get("ok"), stats.get("cambios"),
                stats.get("notificaciones"), stats.get("primera_revision"),
                stats.get("errores"),
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("Insurama inbox sweep error: %s", exc)
        await asyncio.sleep(INTERVAL_SECONDS)


def start_insurama_inbox_scheduler() -> None:
    """Arranca el loop (una vez)."""
    global _task
    if _task and not _task.done():
        return
    loop = asyncio.get_event_loop()
    _task = loop.create_task(_loop())
    logger.info("Insurama inbox scheduler arrancado (cada %ss)", INTERVAL_SECONDS)


def stop_insurama_inbox_scheduler() -> None:
    global _running
    _running = False
    if _task and not _task.done():
        _task.cancel()
