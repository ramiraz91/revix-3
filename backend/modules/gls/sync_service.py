"""
GLS Sync Service - Background polling for tracking updates.
Follows GLS recommendation: sync 4-5 times/day, only non-final shipments.
"""
import asyncio
import logging
from datetime import datetime, timezone

logger = logging.getLogger("gls.sync")
_sync_task = None


async def _run_sync_cycle(db):
    """Execute one sync cycle."""
    from modules.gls.shipment_service import sync_shipments, get_config

    config = await get_config(db)
    if not config.get("activo") or not config.get("polling_activo"):
        return

    logger.info("GLS sync cycle starting...")
    stats = await sync_shipments(db)
    logger.info(f"GLS sync complete: {stats}")


async def _sync_loop(db):
    """Main loop: run sync at configured interval."""
    while True:
        try:
            from modules.gls.shipment_service import get_config
            config = await get_config(db)
            if config.get("activo") and config.get("polling_activo"):
                interval = config.get("polling_intervalo_horas", 4) * 3600
                await _run_sync_cycle(db)
                await asyncio.sleep(interval)
            else:
                await asyncio.sleep(300)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"GLS sync loop error: {e}")
            await asyncio.sleep(300)


def start_gls_sync(db):
    """Start the background sync task."""
    global _sync_task
    if _sync_task and not _sync_task.done():
        return
    _sync_task = asyncio.ensure_future(_sync_loop(db))
    logger.info("GLS sync scheduler started")


def stop_gls_sync():
    """Stop the background sync task."""
    global _sync_task
    if _sync_task and not _sync_task.done():
        _sync_task.cancel()
        logger.info("GLS sync scheduler stopped")
