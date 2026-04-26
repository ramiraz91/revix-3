"""
Scheduler diario de Lista de Compras.
- Cada 600s comprueba si toca enviar el resumen.
- Hora target: 17:00 UTC.
- Sólo envía 1 vez por día (control con flag en colección `compras_daily_sent`).
- Genera email + notificación PROVEEDORES para todos los admins.
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("compras.scheduler")

CHECK_INTERVAL = 600  # 10 min
TARGET_HOUR_UTC = 17
EMAIL_DESTINATARIO = "ramirez91@gmail.com"

_task: Optional[asyncio.Task] = None
_running = False


async def _enviar_resumen():
    from config import db
    from modules.notificaciones.helper import create_notification
    from email_service import send_email_async, _safe_public_url

    items = await db.lista_compras.find(
        {"estado": "pendiente"},  # solo pendientes (no aprobados/pedidos)
        {"_id": 0},
    ).sort("urgencia", -1).to_list(length=None)

    if not items:
        logger.info("Compras daily: 0 items pendientes, skip email")
    
    # Agrupar por proveedor
    grupos: dict = {}
    urgencia_count = {"critica": 0, "alta": 0, "normal": 0, "baja": 0}
    for it in items:
        pid = it.get("proveedor_id") or "_sin_proveedor_"
        grupos.setdefault(pid, {
            "proveedor_id": it.get("proveedor_id"),
            "proveedor_nombre": it.get("proveedor_nombre") or "Sin proveedor",
            "items": [],
            "total": 0.0,
        })
        grupos[pid]["items"].append(it)
        grupos[pid]["total"] += float(it.get("precio_estimado") or 0) * int(it.get("cantidad") or 0)
        urgencia_count[it.get("urgencia", "normal")] = urgencia_count.get(it.get("urgencia", "normal"), 0) + 1

    base_url = _safe_public_url(os.environ.get("FRONTEND_URL"))
    panel_url = f"{base_url}/crm/compras"

    # Notificación para TODOS los admins
    try:
        admins = await db.users.find(
            {"role": {"$in": ["master", "admin"]}, "is_active": {"$ne": False}},
            {"_id": 0, "id": 1, "email": 1},
        ).to_list(length=None)
        msg = (
            f"Hay {len(items)} repuesto(s) pendientes de pedir "
            f"({urgencia_count['critica']} crítico, {urgencia_count['alta']} alta, "
            f"{urgencia_count['normal']} normal). Revisa la lista y aprueba el pedido."
        )
        for adm in admins:
            await create_notification(
                db,
                categoria="PROVEEDORES",
                tipo="compras_resumen_diario",
                titulo=f"Resumen diario de compras · {len(items)} items pendientes",
                mensaje=msg,
                user_id=adm.get("id"),
                source="compras_scheduler",
                meta={
                    "total_items": len(items),
                    "urgencias": urgencia_count,
                    "proveedores": len(grupos),
                    "url_panel": panel_url,
                },
            )
    except Exception as exc:
        logger.warning("No pude crear notificaciones de resumen: %s", exc)

    if not items:
        return  # sin items, no email

    # Email
    rows_html = []
    rows_text = []
    for grupo in grupos.values():
        rows_html.append(
            f"<h3 style='margin-top:18px;color:#1e40af'>{grupo['proveedor_nombre']} "
            f"<span style='color:#64748b;font-size:13px'>({len(grupo['items'])} items)</span></h3>"
            f"<table border='1' cellpadding='6' cellspacing='0' style='border-collapse:collapse;font-family:sans-serif;font-size:13px'>"
            f"<thead><tr style='background:#f1f5f9'>"
            f"<th>Ref</th><th>Pieza</th><th>Cant</th><th>Urg</th><th>OTs</th></tr></thead><tbody>"
        )
        rows_text.append(f"\n{grupo['proveedor_nombre']} ({len(grupo['items'])} items):")
        for it in grupo["items"]:
            ots = ",".join(it.get("ordenes_relacionadas") or []) or "-"
            urg = it.get("urgencia", "normal").upper()
            ref = it.get("repuesto_sku") or it.get("repuesto_id", "")[:10]
            rows_html.append(
                f"<tr><td>{ref}</td><td>{it.get('repuesto_nombre','')}</td>"
                f"<td style='text-align:center'>{it.get('cantidad')}</td>"
                f"<td>{urg}</td><td style='font-size:11px'>{ots}</td></tr>"
            )
            rows_text.append(f"  · {it.get('repuesto_nombre')} x{it.get('cantidad')} [{urg}] OTs:{ots}")
        rows_html.append("</tbody></table>")

    cuerpo_html = (
        f"<h2 style='color:#1e40af'>📦 Resumen diario de compras pendientes</h2>"
        f"<p style='font-size:14px'>"
        f"<strong>{len(items)}</strong> items pendientes de pedir, "
        f"agrupados en <strong>{len(grupos)}</strong> proveedor(es). "
        f"Revisa el panel para aprobar y enviar pedidos:</p>"
        f"<p><a href='{panel_url}' style='display:inline-block;background:#1e40af;color:white;"
        f"padding:8px 14px;border-radius:6px;text-decoration:none'>Abrir lista de compras →</a></p>"
        f"<p style='font-size:13px'>Urgencias: 🔴 {urgencia_count['critica']} crítica · "
        f"🟠 {urgencia_count['alta']} alta · 🟡 {urgencia_count['normal']} normal · "
        f"🟢 {urgencia_count['baja']} baja</p>"
        f"<hr>{''.join(rows_html)}"
        f"<hr><p style='font-size:11px;color:#64748b'>"
        f"Email automático de Revix.es — generado a las {datetime.now(timezone.utc).strftime('%H:%M UTC del %d/%m/%Y')}</p>"
    )
    cuerpo_text = (
        f"Resumen diario de compras pendientes\n\n"
        f"{len(items)} items en {len(grupos)} proveedor(es).\n"
        f"Urgencias: critica={urgencia_count['critica']}, alta={urgencia_count['alta']}, "
        f"normal={urgencia_count['normal']}, baja={urgencia_count['baja']}.\n"
        + "\n".join(rows_text)
        + f"\n\nPanel: {panel_url}"
    )

    try:
        await send_email_async(
            to_email=EMAIL_DESTINATARIO,
            subject=f"📦 Compras pendientes · {len(items)} items · {datetime.now(timezone.utc).strftime('%d/%m/%Y')}",
            html_content=cuerpo_html,
            text_content=cuerpo_text,
        )
        logger.info("Compras daily email enviado a %s (%s items)",
                    EMAIL_DESTINATARIO, len(items))
    except Exception as exc:
        logger.error("Error enviando email compras daily: %s", exc)


async def _ya_enviado_hoy() -> bool:
    """Idempotencia diaria — colección compras_daily_sent."""
    from config import db
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return bool(await db.compras_daily_sent.find_one({"date": today}))


async def _marcar_enviado():
    from config import db
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    await db.compras_daily_sent.update_one(
        {"date": today},
        {"$set": {"date": today, "enviado_en": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )


async def _loop():
    global _running
    _running = True
    await asyncio.sleep(180)  # delay startup
    while _running:
        try:
            now = datetime.now(timezone.utc)
            if now.hour == TARGET_HOUR_UTC and not await _ya_enviado_hoy():
                await _enviar_resumen()
                await _marcar_enviado()
        except Exception as exc:
            logger.error("Compras daily scheduler error: %s", exc)
        await asyncio.sleep(CHECK_INTERVAL)


def start_compras_daily_scheduler() -> None:
    global _task
    if _task and not _task.done():
        return
    loop = asyncio.get_event_loop()
    _task = loop.create_task(_loop())
    logger.info("Compras daily scheduler arrancado (target %s:00 UTC)", TARGET_HOUR_UTC)


def stop_compras_daily_scheduler() -> None:
    global _running
    _running = False
    if _task and not _task.done():
        _task.cancel()
