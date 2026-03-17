"""
GLS Background Sync Scheduler.
Periodically polls GLS API for tracking updates on active shipments.
Integrates with the existing scheduler pattern.
"""
import asyncio
import logging
from datetime import datetime, timezone

logger = logging.getLogger("gls_sync")

_sync_task = None


async def _run_gls_sync():
    """Execute one sync cycle for all non-final GLS shipments."""
    from config import db
    from services.gls_soap_client import get_exp_cli
    from services.gls_state_mapper import map_gls_status, process_state_change

    # Get GLS config
    doc = await db.configuracion.find_one({"tipo": "gls_config"}, {"_id": 0})
    cfg = doc.get("datos", {}) if doc else {}

    if not cfg.get("activo") or not cfg.get("polling_activo") or not cfg.get("uid_cliente"):
        return

    uid = cfg["uid_cliente"]
    final_states = {"entregado", "entregado_parcial", "devuelto", "anulado", "cancelado", "error"}

    envios = await db.gls_envios.find(
        {"estado_interno": {"$nin": list(final_states)}},
        {"_id": 0, "id": 1, "referencia_interna": 1, "estado_interno": 1, "entidad_origen_id": 1}
    ).to_list(500)

    if not envios:
        return

    updated, errors = 0, 0
    for envio in envios:
        ref = envio.get("referencia_interna") or envio.get("entidad_origen_id", "")
        if not ref:
            continue
        try:
            result = await get_exp_cli(uid, ref)
            if not result.get("success"):
                errors += 1
                continue

            old_state = envio.get("estado_interno", "grabado")
            mapped = map_gls_status(result.get("codestado", ""))
            new_state = mapped["estado"]

            up = {
                "estado_interno": new_state,
                "estado_gls_codigo": result.get("codestado", ""),
                "estado_gls_texto": result.get("estado", ""),
                "fecha_ultima_sync": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            if result.get("entrega_fecha"):
                up["entrega_fecha"] = result["entrega_fecha"]
            if result.get("nombre_receptor"):
                up["entrega_receptor"] = result["nombre_receptor"]
            if result.get("dni_receptor"):
                up["entrega_dni"] = result["dni_receptor"]
            if result.get("incidencia"):
                up["incidencia_texto"] = result["incidencia"]

            await db.gls_envios.update_one({"id": envio["id"]}, {"$set": up})

            if old_state != new_state:
                await process_state_change(db, envio, old_state, new_state, result)
                await db.ordenes.update_one(
                    {"gls_envios.id": envio["id"]},
                    {"$set": {"gls_envios.$.estado_gls": new_state}}
                )
            updated += 1
        except Exception as e:
            logger.error(f"GLS sync error for {ref}: {e}")
            errors += 1

        # Small delay between API calls to avoid rate limiting
        await asyncio.sleep(0.5)

    logger.info(f"GLS sync complete: {updated} updated, {errors} errors, {len(envios)} total")


async def _sync_loop():
    """Main loop that runs sync at the configured interval."""
    from config import db

    while True:
        try:
            doc = await db.configuracion.find_one({"tipo": "gls_config"}, {"_id": 0})
            cfg = doc.get("datos", {}) if doc else {}

            if cfg.get("activo") and cfg.get("polling_activo"):
                interval_hours = cfg.get("polling_intervalo_horas", 4)
                await _run_gls_sync()
                await asyncio.sleep(interval_hours * 3600)
            else:
                # Check again in 5 minutes if polling is disabled
                await asyncio.sleep(300)
        except Exception as e:
            logger.error(f"GLS sync loop error: {e}")
            await asyncio.sleep(300)


def start_gls_sync():
    """Start the GLS sync background task."""
    global _sync_task
    if _sync_task and not _sync_task.done():
        return
    _sync_task = asyncio.ensure_future(_sync_loop())
    logger.info("GLS sync scheduler started")


def stop_gls_sync():
    """Stop the GLS sync background task."""
    global _sync_task
    if _sync_task and not _sync_task.done():
        _sync_task.cancel()
        logger.info("GLS sync scheduler stopped")
