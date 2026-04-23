"""
Resumen diario de logística por email.

Cada día a las 08:00 UTC se envía un email con:
  - Envíos activos (no entregados)
  - Incidencias nuevas en las últimas 24h
  - Entregas del día anterior

Destino: `LOGISTICA_DAILY_EMAIL` (default `ramirez91@gmail.com`).

Idempotencia: en la colección `mcp_daily_runs` se registra la fecha de envío;
no se envía dos veces el mismo día.

Endpoint manual:
  POST /api/logistica/panel/enviar-resumen-diario → fuerza el envío (incluso si ya se envió hoy).
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from config import db
from auth import require_admin
from email_service import send_email_async

from modules.logistica.state_mapper import is_entregado, is_incidencia

logger = logging.getLogger("gls.logistica.daily_summary")

router = APIRouter(prefix="/logistica", tags=["Logística · Resumen diario"])

DAILY_RUNS_COLLECTION = "mcp_daily_runs"
RUN_KEY = "logistica_daily_summary"
DEFAULT_TO = "ramirez91@gmail.com"
DEFAULT_HOUR_UTC = 8  # 08:00 UTC


# ══════════════════════════════════════════════════════════════════════════════
# Helpers de consulta
# ══════════════════════════════════════════════════════════════════════════════

async def _compute_summary(now: Optional[datetime] = None) -> dict:
    now = now or datetime.now(timezone.utc)
    hace_24h = (now - timedelta(hours=24)).isoformat()
    ayer_inicio = (now - timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0,
    ).isoformat()
    ayer_fin = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()

    pipeline_base = [
        {"$match": {"gls_envios": {"$exists": True, "$ne": []}}},
        {"$unwind": "$gls_envios"},
    ]

    # Envíos activos (no entregados)
    activos = await db.ordenes.aggregate(pipeline_base + [
        {"$match": {
            "gls_envios.estado_codigo": {"$nin": ["7", "11"]},
            "gls_envios.estado_actual": {"$not": {"$regex": "^ENTREGADO", "$options": "i"}},
        }},
        {"$count": "n"},
    ]).to_list(1)

    # Incidencias nuevas últimas 24h
    incidencias = await db.ordenes.aggregate(pipeline_base + [
        {"$match": {
            "gls_envios.incidencia": {"$exists": True, "$ne": ""},
            "gls_envios.ultima_actualizacion": {"$gte": hace_24h},
        }},
        {"$project": {
            "_id": 0, "numero_orden": 1,
            "codbarras": "$gls_envios.codbarras",
            "incidencia": "$gls_envios.incidencia",
            "ultima_actualizacion": "$gls_envios.ultima_actualizacion",
        }},
        {"$limit": 50},
    ]).to_list(50)

    # Entregas de ayer (ventana 00:00-24:00 del día anterior en UTC)
    entregas = await db.ordenes.aggregate(pipeline_base + [
        {"$match": {
            "$or": [
                {"gls_envios.estado_codigo": "7"},
                {"gls_envios.estado_actual": {"$regex": "^ENTREGADO", "$options": "i"}},
            ],
            "gls_envios.ultima_actualizacion": {"$gte": ayer_inicio, "$lt": ayer_fin},
        }},
        {"$project": {
            "_id": 0, "numero_orden": 1,
            "codbarras": "$gls_envios.codbarras",
            "ultima_actualizacion": "$gls_envios.ultima_actualizacion",
        }},
        {"$limit": 50},
    ]).to_list(50)

    return {
        "fecha": now.strftime("%d/%m/%Y"),
        "envios_activos": activos[0]["n"] if activos else 0,
        "incidencias_24h": len(incidencias),
        "entregas_ayer": len(entregas),
        "incidencias_detalle": incidencias,
        "entregas_detalle": entregas,
    }


def _render_html(summary: dict) -> str:
    def _fmt(iso: str) -> str:
        try:
            d = datetime.fromisoformat(iso.replace("Z", "+00:00"))
            return d.strftime("%d/%m %H:%M")
        except Exception:
            return iso or "—"

    inc_rows = "".join(
        f'<tr><td style="padding:4px 8px;border-bottom:1px solid #eee"><b>{i["numero_orden"]}</b></td>'
        f'<td style="padding:4px 8px;border-bottom:1px solid #eee;font-family:monospace">{i["codbarras"]}</td>'
        f'<td style="padding:4px 8px;border-bottom:1px solid #eee;color:#b91c1c">{i["incidencia"]}</td>'
        f'<td style="padding:4px 8px;border-bottom:1px solid #eee;color:#666;font-size:12px">{_fmt(i["ultima_actualizacion"])}</td></tr>'
        for i in summary["incidencias_detalle"][:10]
    ) or '<tr><td colspan="4" style="padding:8px;color:#16a34a">Sin incidencias nuevas ✅</td></tr>'

    ent_rows = "".join(
        f'<tr><td style="padding:4px 8px;border-bottom:1px solid #eee"><b>{e["numero_orden"]}</b></td>'
        f'<td style="padding:4px 8px;border-bottom:1px solid #eee;font-family:monospace">{e["codbarras"]}</td>'
        f'<td style="padding:4px 8px;border-bottom:1px solid #eee;color:#666;font-size:12px">{_fmt(e["ultima_actualizacion"])}</td></tr>'
        for e in summary["entregas_detalle"][:10]
    ) or '<tr><td colspan="3" style="padding:8px;color:#666">Sin entregas ayer</td></tr>'

    return f"""
    <div style="font-family:system-ui,sans-serif;color:#111">
      <p>Resumen logística del <b>{summary['fecha']}</b>:</p>
      <div style="display:flex;gap:12px;margin:16px 0">
        <div style="flex:1;padding:12px;background:#eff6ff;border-radius:8px">
          <div style="font-size:24px;font-weight:bold;color:#1d4ed8">{summary['envios_activos']}</div>
          <div style="font-size:12px;color:#1e40af">Envíos activos</div>
        </div>
        <div style="flex:1;padding:12px;background:#fef2f2;border-radius:8px">
          <div style="font-size:24px;font-weight:bold;color:#b91c1c">{summary['incidencias_24h']}</div>
          <div style="font-size:12px;color:#991b1b">Incidencias 24h</div>
        </div>
        <div style="flex:1;padding:12px;background:#f0fdf4;border-radius:8px">
          <div style="font-size:24px;font-weight:bold;color:#16a34a">{summary['entregas_ayer']}</div>
          <div style="font-size:12px;color:#15803d">Entregas ayer</div>
        </div>
      </div>
      <h3 style="margin:20px 0 8px">🚨 Incidencias nuevas (24h)</h3>
      <table style="width:100%;border-collapse:collapse;font-size:14px">
        <thead><tr style="background:#f3f4f6"><th style="padding:6px 8px;text-align:left">OT</th><th style="padding:6px 8px;text-align:left">Codbarras</th><th style="padding:6px 8px;text-align:left">Incidencia</th><th style="padding:6px 8px;text-align:left">Actualizado</th></tr></thead>
        <tbody>{inc_rows}</tbody>
      </table>
      <h3 style="margin:20px 0 8px">✅ Entregas ayer</h3>
      <table style="width:100%;border-collapse:collapse;font-size:14px">
        <thead><tr style="background:#f3f4f6"><th style="padding:6px 8px;text-align:left">OT</th><th style="padding:6px 8px;text-align:left">Codbarras</th><th style="padding:6px 8px;text-align:left">Entregado</th></tr></thead>
        <tbody>{ent_rows}</tbody>
      </table>
    </div>
    """


async def send_daily_summary(*, force: bool = False) -> dict:
    """Envía el resumen. Si force=False, no re-envía el mismo día."""
    now = datetime.now(timezone.utc)
    today_key = now.strftime("%Y-%m-%d")
    to = os.environ.get("LOGISTICA_DAILY_EMAIL", DEFAULT_TO)

    if not force:
        prev = await db[DAILY_RUNS_COLLECTION].find_one(
            {"key": RUN_KEY, "date": today_key}, {"_id": 0},
        )
        if prev and prev.get("sent"):
            return {"sent": False, "reason": "already_sent_today",
                    "date": today_key, "to": to}

    summary = await _compute_summary(now)
    html_body = _render_html(summary)
    subject = f"Revix · Resumen logística {summary['fecha']}"

    ok = await send_email_async(
        to=to, subject=subject,
        titulo="Resumen diario de logística",
        contenido=html_body,
        link_url=os.environ.get("FRONTEND_URL", "https://revix.es") + "/crm/logistica",
        link_text="Abrir panel de logística",
    )

    await db[DAILY_RUNS_COLLECTION].update_one(
        {"key": RUN_KEY, "date": today_key},
        {"$set": {
            "key": RUN_KEY, "date": today_key,
            "sent": bool(ok), "to": to,
            "sent_at": now.isoformat(timespec="seconds"),
            "summary": {
                "envios_activos": summary["envios_activos"],
                "incidencias_24h": summary["incidencias_24h"],
                "entregas_ayer": summary["entregas_ayer"],
            },
        }},
        upsert=True,
    )
    logger.info("Resumen diario logística enviado=%s a %s (%s)", ok, to, today_key)
    return {
        "sent": bool(ok), "date": today_key, "to": to,
        "summary": summary,
    }


# ══════════════════════════════════════════════════════════════════════════════
# Scheduler: revisa cada 10 min si es >= 08:00 UTC y no se envió hoy
# ══════════════════════════════════════════════════════════════════════════════

_task: Optional[asyncio.Task] = None
_stop_event: Optional[asyncio.Event] = None


async def _loop(interval_seconds: int, stop_event: asyncio.Event) -> None:
    logger.info("Daily summary scheduler arrancado (check cada %ss, envío 08:00 UTC)",
                interval_seconds)
    # Espera inicial para que la app termine de levantar
    try:
        await asyncio.wait_for(stop_event.wait(), timeout=120)
        return
    except asyncio.TimeoutError:
        pass

    while not stop_event.is_set():
        try:
            now = datetime.now(timezone.utc)
            if now.hour >= DEFAULT_HOUR_UTC:
                today_key = now.strftime("%Y-%m-%d")
                prev = await db[DAILY_RUNS_COLLECTION].find_one(
                    {"key": RUN_KEY, "date": today_key}, {"_id": 0, "sent": 1},
                )
                if not (prev and prev.get("sent")):
                    await send_daily_summary(force=False)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Error en daily summary loop: %s", exc)

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval_seconds)
        except asyncio.TimeoutError:
            continue


def start_daily_summary_scheduler(interval_seconds: int = 600) -> None:
    global _task, _stop_event
    if _task and not _task.done():
        return
    _stop_event = asyncio.Event()
    _task = asyncio.create_task(_loop(interval_seconds, _stop_event))


def stop_daily_summary_scheduler() -> None:
    global _task, _stop_event
    if _stop_event:
        _stop_event.set()
    _task = None


# ══════════════════════════════════════════════════════════════════════════════
# Endpoint manual
# ══════════════════════════════════════════════════════════════════════════════

class DailySummaryResponse(BaseModel):
    sent: bool
    date: str
    to: str
    forced: bool = False
    reason: Optional[str] = None
    summary: Optional[dict] = None


@router.post("/panel/enviar-resumen-diario", response_model=DailySummaryResponse)
async def enviar_resumen_manual(
    force: bool = True, user: dict = Depends(require_admin),
):
    """
    Fuerza el envío del resumen diario al email configurado.
    Por defecto force=true (ignora si ya se envió hoy).
    """
    result = await send_daily_summary(force=force)
    return DailySummaryResponse(
        sent=result["sent"],
        date=result["date"],
        to=result["to"],
        forced=force,
        reason=result.get("reason"),
        summary=result.get("summary"),
    )
