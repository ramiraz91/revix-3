"""
Inbox Insurama — detección de cambios en observaciones, estado y precio.

Estrategia:
  - Por cada orden con `origen.fuente="insurama"` (o `numero_autorizacion` + presupuesto
    Sumbroker), mantenemos un snapshot en la colección `insurama_snapshots`.
  - Cada 6h (scheduler) o bajo demanda (POST /refresh), consultamos Sumbroker y
    comparamos con el snapshot previo:
      · Observaciones nuevas → notificación tipo `insurama_mensaje` por cada una.
      · Cambio de estado del siniestro → `insurama_estado_cambio`.
      · Cambio de precio del presupuesto → `insurama_precio_cambio`.
  - Actualizamos el snapshot con el estado actual.
  - Categoría siempre `PROVEEDORES`.

Estructura del snapshot (colección `insurama_snapshots`):
  {
    order_id: str,
    codigo_siniestro: str,
    budget_id: int,
    observaciones_hashes: list[str],   # SHA1 de (fecha|user|texto) vistas
    estado_codigo: int | None,
    estado_texto: str,
    importe: float | None,
    ultima_revision: ISO8601,
    actor_ultima: str,
  }
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from config import db
from auth import require_admin
from modules.notificaciones.helper import create_notification

logger = logging.getLogger("insurama.inbox")

router = APIRouter(prefix="/insurama/inbox", tags=["Insurama · Inbox"])

SNAPSHOTS = "insurama_snapshots"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _hash_obs(o: dict) -> str:
    """Hash canónico de una observación."""
    parts = [
        str(o.get("id") or ""),
        str(o.get("created_at") or o.get("date") or ""),
        str(o.get("user_name") or o.get("user", {}).get("name") or ""),
        (o.get("text") or o.get("observation") or "").strip()[:500],
    ]
    return hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()


def _pick_obs_text(o: dict) -> str:
    return (o.get("text") or o.get("observation") or "").strip()


def _pick_obs_user(o: dict) -> str:
    return (
        o.get("user_name")
        or (o.get("user") or {}).get("name")
        or (o.get("user") or {}).get("email")
        or "Insurama"
    )


def _pick_obs_date(o: dict) -> str:
    return o.get("created_at") or o.get("date") or _now_iso()


async def _get_client():
    from routes.insurama_routes import get_sumbroker_client
    try:
        return await get_sumbroker_client()
    except Exception as exc:  # noqa: BLE001
        logger.warning("No se pudo crear cliente Sumbroker: %s", exc)
        return None


# ── DETECCIÓN ───────────────────────────────────────────────────────────────

async def check_orden(orden: dict, actor: str = "scheduler") -> dict:
    """
    Comprueba cambios de Insurama para una orden concreta.
    Devuelve dict con contadores y lista de notificaciones creadas.
    """
    order_id = orden.get("id")
    codigo = (orden.get("numero_autorizacion") or "").strip()
    if not order_id or not codigo:
        return {"ok": False, "reason": "sin_autorizacion", "changes": 0,
                "notificaciones": []}

    client = await _get_client()
    if not client:
        return {"ok": False, "reason": "no_credentials", "changes": 0,
                "notificaciones": []}

    # 1. Obtener presupuesto y observaciones
    try:
        budget = await client.find_budget_by_service_code(codigo)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "reason": f"fetch_budget: {exc!s}"[:200],
                "changes": 0, "notificaciones": []}
    if not budget:
        return {"ok": False, "reason": "budget_no_encontrado", "changes": 0,
                "notificaciones": []}

    budget_id = budget.get("id")
    try:
        observaciones = await client.get_observations(budget_id) if budget_id else []
    except Exception as exc:  # noqa: BLE001
        logger.warning("get_observations fallo (%s): %s", codigo, exc)
        observaciones = []

    estado_codigo = budget.get("status") or budget.get("state")
    estado_texto = budget.get("status_name") or budget.get("state_name") or ""
    importe = budget.get("total_amount") or budget.get("total") or budget.get("amount")
    try:
        importe = float(importe) if importe is not None else None
    except (TypeError, ValueError):
        importe = None

    # 2. Cargar snapshot previo
    prev = await db[SNAPSHOTS].find_one({"order_id": order_id}, {"_id": 0}) or {}
    prev_hashes = set(prev.get("observaciones_hashes") or [])
    prev_estado = prev.get("estado_codigo")
    prev_importe = prev.get("importe")
    es_primera_revision = not prev

    # 3. Diff
    notificaciones_creadas: list[str] = []
    nuevas_obs = []
    obs_hashes_actuales: list[str] = []
    for o in observaciones:
        h = _hash_obs(o)
        obs_hashes_actuales.append(h)
        if h not in prev_hashes:
            nuevas_obs.append(o)

    # 3a. Observaciones nuevas — en primera revisión NO disparar notifs
    # (evita inundar notificaciones al desplegar sobre histórico existente)
    if not es_primera_revision:
        for o in nuevas_obs:
            autor = _pick_obs_user(o)
            texto = _pick_obs_text(o)
            fecha = _pick_obs_date(o)
            if not texto:
                continue
            preview = texto if len(texto) <= 180 else texto[:177] + "…"
            nid = await create_notification(
                db,
                categoria="PROVEEDORES",
                tipo="insurama_mensaje",
                titulo=f"Insurama · Nuevo mensaje de {autor}",
                mensaje=f"OT {orden.get('numero_orden','')} [{codigo}] · {preview}",
                orden_id=order_id,
                source="insurama_inbox",
                meta={
                    "codigo_siniestro": codigo,
                    "budget_id": budget_id,
                    "autor": autor,
                    "fecha_observacion": fecha,
                    "texto": texto,
                    "obs_hash": _hash_obs(o),
                },
            )
            notificaciones_creadas.append(nid)

    # 3b. Cambio de estado
    if not es_primera_revision and prev_estado is not None and estado_codigo is not None and prev_estado != estado_codigo:
        nid = await create_notification(
            db,
            categoria="PROVEEDORES",
            tipo="insurama_estado_cambio",
            titulo="Insurama · Cambio de estado",
            mensaje=(
                f"OT {orden.get('numero_orden','')} [{codigo}] · "
                f"estado: {prev.get('estado_texto') or prev_estado} → {estado_texto or estado_codigo}"
            ),
            orden_id=order_id,
            source="insurama_inbox",
            meta={
                "codigo_siniestro": codigo,
                "budget_id": budget_id,
                "estado_anterior_codigo": prev_estado,
                "estado_anterior_texto": prev.get("estado_texto"),
                "estado_nuevo_codigo": estado_codigo,
                "estado_nuevo_texto": estado_texto,
            },
        )
        notificaciones_creadas.append(nid)

    # 3c. Cambio de precio
    if not es_primera_revision and prev_importe is not None and importe is not None:
        try:
            if abs(float(prev_importe) - float(importe)) >= 0.01:
                delta = float(importe) - float(prev_importe)
                nid = await create_notification(
                    db,
                    categoria="PROVEEDORES",
                    tipo="insurama_precio_cambio",
                    titulo="Insurama · Cambio de importe",
                    mensaje=(
                        f"OT {orden.get('numero_orden','')} [{codigo}] · "
                        f"importe: {prev_importe:.2f}€ → {importe:.2f}€ "
                        f"({'+' if delta >= 0 else ''}{delta:.2f}€)"
                    ),
                    orden_id=order_id,
                    source="insurama_inbox",
                    meta={
                        "codigo_siniestro": codigo,
                        "budget_id": budget_id,
                        "importe_anterior": float(prev_importe),
                        "importe_nuevo": float(importe),
                        "delta": delta,
                    },
                )
                notificaciones_creadas.append(nid)
        except (TypeError, ValueError):
            pass

    # 4. Actualizar snapshot (upsert)
    snapshot_doc = {
        "order_id": order_id,
        "codigo_siniestro": codigo,
        "budget_id": budget_id,
        "observaciones_hashes": obs_hashes_actuales,
        "estado_codigo": estado_codigo,
        "estado_texto": estado_texto,
        "importe": importe,
        "ultima_revision": _now_iso(),
        "actor_ultima": actor,
    }
    await db[SNAPSHOTS].update_one(
        {"order_id": order_id},
        {"$set": snapshot_doc},
        upsert=True,
    )

    return {
        "ok": True,
        "order_id": order_id,
        "codigo": codigo,
        "budget_id": budget_id,
        "observaciones_totales": len(observaciones),
        "observaciones_nuevas": len(nuevas_obs),
        "estado_cambio": (not es_primera_revision and prev_estado is not None
                          and estado_codigo is not None and prev_estado != estado_codigo),
        "precio_cambio": (not es_primera_revision and prev_importe is not None
                          and importe is not None
                          and abs(float(prev_importe) - float(importe)) >= 0.01),
        "changes": len(notificaciones_creadas),
        "notificaciones": notificaciones_creadas,
        "es_primera_revision": es_primera_revision,
    }


async def check_all_active() -> dict:
    """Barrido de todas las órdenes activas con numero_autorizacion."""
    q = {
        "numero_autorizacion": {"$exists": True, "$nin": ["", None]},
        "estado": {"$nin": ["entregado", "anulado", "facturado", "liquidado"]},
    }
    ordenes = await db.ordenes.find(
        q, {"_id": 0, "id": 1, "numero_orden": 1, "numero_autorizacion": 1, "estado": 1},
    ).limit(500).to_list(500)

    stats = {"total": len(ordenes), "ok": 0, "errores": 0, "cambios": 0,
             "notificaciones": 0, "primera_revision": 0}
    for o in ordenes:
        r = await check_orden(o, actor="scheduler")
        if r.get("ok"):
            stats["ok"] += 1
            stats["cambios"] += int(r.get("changes", 0) or 0)
            stats["notificaciones"] += len(r.get("notificaciones") or [])
            if r.get("es_primera_revision"):
                stats["primera_revision"] += 1
        else:
            stats["errores"] += 1

    # Audit log del barrido
    await db.audit_logs.insert_one({
        "source": "scheduler", "agent_id": None,
        "tool": "_insurama_inbox_sweep",
        "params": {"ordenes": len(ordenes)},
        "result_summary": stats,
        "error": None, "duration_ms": 0,
        "timestamp": _now_iso(),
        "timestamp_dt": datetime.now(timezone.utc),
        "actor": "scheduler",
    })

    return stats


# ══════════════════════════════════════════════════════════════════════════════
# Endpoints
# ══════════════════════════════════════════════════════════════════════════════

class RefreshResponse(BaseModel):
    ok: bool
    order_id: Optional[str] = None
    codigo: Optional[str] = None
    changes: int = 0
    observaciones_nuevas: int = 0
    estado_cambio: bool = False
    precio_cambio: bool = False
    notificaciones: list[str] = []
    es_primera_revision: bool = False
    reason: Optional[str] = None


@router.post("/orden/{order_id}/refresh", response_model=RefreshResponse)
async def refresh_orden(order_id: str, user: dict = Depends(require_admin)):
    """Consulta Insurama AHORA para una OT concreta y crea notificaciones si detecta cambios."""
    orden = await db.ordenes.find_one(
        {"id": order_id},
        {"_id": 0, "id": 1, "numero_orden": 1, "numero_autorizacion": 1},
    )
    if not orden:
        raise HTTPException(404, "Orden no encontrada")
    res = await check_orden(orden, actor=user.get("email", "manual"))
    return RefreshResponse(**{k: v for k, v in res.items()
                              if k in RefreshResponse.model_fields})


@router.get("/orden/{order_id}")
async def inbox_orden(
    order_id: str,
    solo_no_leidas: bool = False,
    limit: int = Query(50, ge=1, le=200),
    user: dict = Depends(require_admin),
):
    """Lista mensajes Insurama (notificaciones de categoría PROVEEDORES con tipo insurama_*) de una OT."""
    q: dict = {
        "orden_id": order_id,
        "$or": [
            {"categoria": "PROVEEDORES"},
            {"tipo": {"$in": [
                "insurama_mensaje", "insurama_estado_cambio",
                "insurama_precio_cambio", "insurama_cambio",
            ]}},
        ],
    }
    if solo_no_leidas:
        q["leida"] = False
    items = await db.notificaciones.find(
        q, {"_id": 0},
    ).sort("created_at", -1).limit(limit).to_list(limit)
    no_leidas = await db.notificaciones.count_documents({**q, "leida": False})
    snapshot = await db[SNAPSHOTS].find_one(
        {"order_id": order_id}, {"_id": 0},
    ) or None
    return {
        "order_id": order_id,
        "total": len(items),
        "no_leidas": no_leidas,
        "mensajes": items,
        "snapshot": snapshot,
    }


@router.post("/mensaje/{notificacion_id}/marcar-leido")
async def marcar_mensaje_leido(notificacion_id: str, user: dict = Depends(require_admin)):
    """Marca una notificación Insurama como leída."""
    r = await db.notificaciones.update_one(
        {"id": notificacion_id}, {"$set": {"leida": True,
                                            "leida_en": _now_iso(),
                                            "leida_por": user.get("email", "")}},
    )
    if r.matched_count == 0:
        raise HTTPException(404, "Notificación no encontrada")
    return {"ok": True, "id": notificacion_id}


@router.get("/resumen")
async def resumen_inbox(user: dict = Depends(require_admin)):
    """Resumen global del inbox Insurama (para campanita dedicada)."""
    q = {
        "$or": [
            {"categoria": "PROVEEDORES"},
            {"tipo": {"$in": [
                "insurama_mensaje", "insurama_estado_cambio",
                "insurama_precio_cambio", "insurama_cambio",
            ]}},
        ],
    }
    total = await db.notificaciones.count_documents(q)
    no_leidas = await db.notificaciones.count_documents({**q, "leida": False})
    por_tipo: dict = {}
    async for n in db.notificaciones.find(
        {**q, "leida": False}, {"_id": 0, "tipo": 1, "orden_id": 1},
    ):
        t = n.get("tipo", "insurama_cambio")
        por_tipo[t] = por_tipo.get(t, 0) + 1

    ordenes_con_mensajes = await db.notificaciones.distinct(
        "orden_id", {**q, "leida": False, "orden_id": {"$ne": None}},
    )
    return {
        "total": total,
        "no_leidas": no_leidas,
        "por_tipo": por_tipo,
        "ordenes_con_mensajes": len(ordenes_con_mensajes),
    }


@router.get("/por-orden")
async def conteo_por_orden(user: dict = Depends(require_admin)):
    """
    Devuelve un dict {order_id: count_no_leidas} para pintar badges en la
    lista de OT de `/crm/ordenes` con UNA sola llamada.
    """
    q = {
        "leida": False,
        "orden_id": {"$ne": None},
        "$or": [
            {"categoria": "PROVEEDORES"},
            {"tipo": {"$in": [
                "insurama_mensaje", "insurama_estado_cambio",
                "insurama_precio_cambio", "insurama_cambio",
            ]}},
        ],
    }
    counts: dict[str, int] = {}
    async for n in db.notificaciones.find(q, {"_id": 0, "orden_id": 1}):
        oid = n.get("orden_id")
        if not oid:
            continue
        counts[oid] = counts.get(oid, 0) + 1
    return {"por_orden": counts, "total_ordenes": len(counts)}


@router.post("/sweep")
async def sweep_ahora(user: dict = Depends(require_admin)):
    """Fuerza un barrido completo del inbox (solo master/admin)."""
    role = user.get("role") or user.get("rol")
    if role not in ("master", "admin"):
        raise HTTPException(403, "Solo master/admin")
    stats = await check_all_active()
    return {"ok": True, **stats}
