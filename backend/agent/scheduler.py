"""
Background scheduler: Runs the Insurama polling loop and consolidation processor.
Uses asyncio tasks managed by FastAPI lifespan.
"""
import asyncio
from datetime import datetime, timezone
from typing import Optional
from config import db, logger
from agent.email_client import IMAPClient
from agent.processor import process_email, process_consolidated_events, log_agent
from agent.crypto import decrypt_value
from agent.insurama_poller import poll_insurama_budgets

_task: Optional[asyncio.Task] = None
_running = False
POLL_INTERVAL_DEFAULT = 1800  # 30 minutes


async def get_agent_config() -> Optional[dict]:
    config = await db.configuracion.find_one({"tipo": "agent_config"}, {"_id": 0})
    return config.get('datos', {}) if config else None


async def poll_cycle():
    """Single poll cycle: poll Insurama API directly, then consolidate pending events."""
    cfg = await get_agent_config()
    if not cfg:
        return

    # PRIMARY: Poll Insurama/Sumbroker API directly
    try:
        result = await poll_insurama_budgets()
        if result.get("action") == "error":
            logger.warning(f"Insurama polling failed: {result.get('error')}")
    except Exception as e:
        await log_agent("error_insurama_polling", "error", "error", error=str(e))

    # FALLBACK: Also process emails if IMAP is configured
    if cfg.get('imap_host') and cfg.get('imap_user') and cfg.get('email_fallback', True):
        imap_pass = cfg.get('imap_password', '')
        try:
            imap_pass = decrypt_value(imap_pass)
        except Exception:
            pass

        client = IMAPClient(
            host=cfg['imap_host'],
            port=int(cfg.get('imap_port', 993)),
            user=cfg['imap_user'],
            password=imap_pass,
            use_ssl=cfg.get('imap_ssl', True),
            folder=cfg.get('imap_folder', 'INBOX')
        )

        try:
            last_uid = cfg.get('last_processed_uid')
            messages = client.fetch_unseen(since_uid=last_uid)

            if messages:
                code_pattern = cfg.get('codigo_pattern')
                for msg in messages:
                    try:
                        result = await process_email(msg, code_pattern)
                        logger.info(f"Processed email: {result.get('action')} "
                                    f"code={result.get('codigo', 'N/A')}")
                    except Exception as e:
                        await log_agent("error_procesando_email", "error", "error",
                                        email_id=msg.message_id, error=str(e))

                max_uid = max(m.uid for m in messages)
                await db.configuracion.update_one(
                    {"tipo": "agent_config"},
                    {"$set": {
                        "datos.last_processed_uid": max_uid,
                        "datos.last_poll": datetime.now(timezone.utc).isoformat()
                    }}
                )
        except Exception as e:
            await log_agent("error_poll_cycle", "error", "error", error=str(e))
        finally:
            client.disconnect()

    # Process consolidated events (accept/reject windows from email)
    try:
        results = await process_consolidated_events()
        for r in results:
            logger.info(f"Consolidated: {r.get('action')} code={r.get('codigo', 'N/A')}")
    except Exception as e:
        await log_agent("error_consolidation", "error", "error", error=str(e))


async def _poll_loop():
    global _running
    _running = True
    await log_agent("agente_iniciado", "ok", "info")

    while _running:
        try:
            cfg = await get_agent_config()
            interval = int(cfg.get('poll_interval', POLL_INTERVAL_DEFAULT)) if cfg else POLL_INTERVAL_DEFAULT
            estado = cfg.get('estado', 'pausado') if cfg else 'pausado'

            if estado == 'activo':
                await poll_cycle()
            else:
                logger.debug("Agent paused, skipping poll cycle")

            await asyncio.sleep(interval)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Agent loop error: {e}")
            await asyncio.sleep(60)

    await log_agent("agente_detenido", "ok", "info")


def start_agent():
    global _task
    if _task and not _task.done():
        return False
    _task = asyncio.create_task(_poll_loop())
    return True


def stop_agent():
    global _running, _task
    _running = False
    if _task:
        _task.cancel()
        _task = None
    return True


def is_agent_running() -> bool:
    return _running and _task is not None and not _task.done()
