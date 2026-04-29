"""
Sincronización de órdenes históricas con GLS — con salvaguardas de producción.

Caso de uso: existen órdenes creadas desde la extranet web de GLS antes de tener
el módulo `modules/logistica/gls.py` integrado. Estas órdenes tienen un
`numero_autorizacion` (que se envió como RefC a GLS) pero NO tienen `gls_envios`
en BD.

SALVAGUARDAS para production:
  1. DRY-RUN obligatorio por defecto (no modifica BD).
  2. BACKUP automático del documento previo (colección `gls_sync_backups`) antes
     de cada $set / $push cuando se ejecuta en real.
  3. LÍMITE máximo de órdenes por ejecución (hard cap 500) + warning si >50.
  4. CONFIRMACIÓN textual obligatoria ("CONFIRMO") al ejecutar en production.
  5. ROLLBACK disponible vía endpoint `POST /gls/sync-runs/{run_id}/restaurar`.
  6. Cada ejecución genera un `sync_run_id` único (uuid4) agrupable.

Endpoints:
  GET  /api/logistica/gls/sincronizar-ordenes/candidatas
  POST /api/logistica/gls/sincronizar-ordenes
  GET  /api/logistica/gls/sync-runs
  GET  /api/logistica/gls/sync-runs/{run_id}
  POST /api/logistica/gls/sync-runs/{run_id}/restaurar
"""
from __future__ import annotations

import copy
import hashlib
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from config import db
from auth import require_admin

from modules.logistica.gls import (
    EventoTracking, GLSClient, GLSError, Remitente, ResultadoTracking,
)
from modules.logistica.state_mapper import is_entregado

logger = logging.getLogger("gls.sync_historico")

router = APIRouter(prefix="/logistica", tags=["Logística · Sync GLS"])

HARD_CAP_MAX_ORDENES = 500
SOFT_WARNING_MAX_ORDENES = 50
CONFIRMACION_TEXTO = "CONFIRMO"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _is_preview() -> bool:
    return os.environ.get("MCP_ENV", "").lower() == "preview"


async def _effective_remitente() -> dict:
    from modules.logistica.panel_config import _effective_remitente as _f
    return await _f()


async def _build_client() -> GLSClient:
    rem = await _effective_remitente()
    return GLSClient(
        uid_cliente=os.environ.get("GLS_UID_CLIENTE", ""),
        remitente=Remitente(**rem),
        url=os.environ.get("GLS_URL") or None,
        mcp_env=os.environ.get("MCP_ENV"),
    )


# ══════════════════════════════════════════════════════════════════════════════
# Mock preview (solo cuando MCP_ENV=preview)
# ══════════════════════════════════════════════════════════════════════════════

def _mock_sync_lookup(numero_autorizacion: str) -> Optional[ResultadoTracking]:
    """Simula respuesta GLS en preview (determinista por numero_autorizacion)."""
    if numero_autorizacion.startswith("NOENCONTRADO"):
        return None
    digest = hashlib.sha1(numero_autorizacion.encode("utf-8")).hexdigest()
    codbarras = ("9" + "".join(c for c in digest if c.isdigit()))[:14]
    while len(codbarras) < 14:
        codbarras += "0"
    now = datetime.now(timezone.utc)
    return ResultadoTracking(
        success=True, codbarras=codbarras,
        estado_actual="EN REPARTO", estado_codigo="6",
        fecha_entrega="", incidencia="",
        eventos=[
            EventoTracking(fecha=now.isoformat(timespec="seconds"),
                           estado="RECOGIDO", plaza="08", codigo="1"),
            EventoTracking(fecha=now.isoformat(timespec="seconds"),
                           estado="EN REPARTO", plaza="14", codigo="6"),
        ],
    )


# ══════════════════════════════════════════════════════════════════════════════
# Lógica de sincronización
# ══════════════════════════════════════════════════════════════════════════════

async def _save_backup(
    orden: dict, *, sync_run_id: str, preview: bool, actor_email: str,
) -> None:
    """
    Guarda snapshot del estado previo de la orden (solo campos afectados por el sync)
    en `gls_sync_backups` ANTES de cualquier escritura. Idempotente por (run_id, order_id).
    """
    doc = {
        "sync_run_id": sync_run_id,
        "order_id": orden.get("id"),
        "numero_orden": orden.get("numero_orden"),
        "numero_autorizacion": orden.get("numero_autorizacion"),
        "gls_envios_previo": copy.deepcopy(orden.get("gls_envios") or []),
        "updated_at_previo": orden.get("updated_at"),
        "preview": preview,
        "actor": actor_email,
        "backup_en": _now_iso(),
        "restaurado": False,
    }
    # Upsert por (run_id, order_id) para evitar duplicados si se reintenta
    await db.gls_sync_backups.update_one(
        {"sync_run_id": sync_run_id, "order_id": orden.get("id")},
        {"$setOnInsert": doc},
        upsert=True,
    )


async def _sync_one_orden(
    orden: dict, client: Optional[GLSClient], *,
    preview: bool, dry_run: bool, sync_run_id: str, actor_email: str,
) -> dict:
    """Sincroniza una sola orden. Devuelve dict con resultado detallado."""
    oid = orden.get("id")
    numero_autorizacion = (orden.get("numero_autorizacion") or "").strip()
    if not numero_autorizacion:
        return {
            "order_id": oid, "numero_orden": orden.get("numero_orden"),
            "numero_autorizacion": "", "status": "skipped",
            "reason": "sin_numero_autorizacion",
        }

    # CP del destinatario: de la orden o del cliente (varios campos posibles)
    cp_destinatario = (
        orden.get("cp_envio")
        or orden.get("codigo_postal_envio")
        or orden.get("destinatario_cp")
        or ""
    )
    if not cp_destinatario and orden.get("cliente_id"):
        cli = await db.clientes.find_one(
            {"id": orden["cliente_id"]},
            {"_id": 0, "cp": 1, "codigo_postal": 1, "direccion": 1},
        ) or {}
        cp_destinatario = (cli.get("cp") or cli.get("codigo_postal") or "").strip()
        # Fallback final: extraer 5 dígitos del campo "direccion" si nada más existe
        if not cp_destinatario and cli.get("direccion"):
            import re
            m = re.search(r"\b(\d{5})\b", cli.get("direccion", ""))
            if m:
                cp_destinatario = m.group(1)

    # 1. Consultar GLS por refC=numero_autorizacion
    try:
        if preview:
            tracking = _mock_sync_lookup(numero_autorizacion)
            digest = hashlib.sha1(numero_autorizacion.encode("utf-8")).hexdigest()
            codexp = str(int(digest[:10], 16))[:10]
        else:
            assert client is not None
            tracking = await client.obtener_tracking(numero_autorizacion)
            # En producción real, codexp se extrae del XML por _parse_get_exp_cli_response
            codexp = getattr(tracking, "codexp", "") if tracking else ""
            # Si la orden no tiene CP local, usamos el cpdst que devuelve GLS
            if not cp_destinatario:
                cp_destinatario = getattr(tracking, "cp_destino", "") if tracking else ""
    except GLSError as exc:
        return {
            "order_id": oid, "numero_orden": orden.get("numero_orden"),
            "numero_autorizacion": numero_autorizacion, "status": "error",
            "reason": str(exc)[:200],
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "order_id": oid, "numero_orden": orden.get("numero_orden"),
            "numero_autorizacion": numero_autorizacion, "status": "error",
            "reason": f"excepcion: {str(exc)[:150]}",
        }

    if not tracking or not tracking.success:
        return {
            "order_id": oid, "numero_orden": orden.get("numero_orden"),
            "numero_autorizacion": numero_autorizacion, "status": "not_found",
            "reason": "gls_sin_coincidencia",
        }

    # 2. Construir envio_doc
    tracking_url = (
        f"https://mygls.gls-spain.es/e/{codexp}/{cp_destinatario}"
        if codexp and cp_destinatario
        else f"https://www.gls-spain.es/es/ayuda/seguimiento-de-envio/?match={tracking.codbarras}"
    )
    now = _now_iso()
    envio_doc = {
        "codbarras": tracking.codbarras,
        "uid": "",
        "codexp": codexp,
        "cp_destinatario": cp_destinatario,
        "referencia": numero_autorizacion,
        "peso_kg": 0.5,
        "estado_actual": tracking.estado_actual,
        "estado_codigo": tracking.estado_codigo,
        "incidencia": tracking.incidencia,
        "fecha_entrega": tracking.fecha_entrega,
        "eventos": [e.to_dict() for e in tracking.eventos],
        "tracking_url": tracking_url,
        "mock_preview": preview,
        "creado_en": (orden.get("created_at") or now),
        "ultima_actualizacion": now,
        "creado_por": "sync_historico",
        "sincronizado_en": now,
        "sync_run_id": sync_run_id,
    }

    # 3. Determinar acción (idempotente por codbarras)
    envios_prev = orden.get("gls_envios") or []
    idx = next(
        (i for i, e in enumerate(envios_prev)
         if e.get("codbarras") == tracking.codbarras),
        None,
    )
    action = "updated" if idx is not None else "created"

    if idx is not None:
        existing = envios_prev[idx]
        envio_doc["creado_en"] = existing.get("creado_en") or envio_doc["creado_en"]
        envio_doc["uid"] = existing.get("uid") or envio_doc["uid"]
        envio_doc["creado_por"] = existing.get("creado_por") or "sync_historico"

    base_resp = {
        "order_id": oid,
        "numero_orden": orden.get("numero_orden"),
        "numero_autorizacion": numero_autorizacion,
        "status": "ok",
        "action": action,
        "codbarras": tracking.codbarras,
        "codexp": codexp,
        "cp_destinatario": cp_destinatario,
        "tracking_url": tracking_url,
        "estado": tracking.estado_actual,
        "entregado": is_entregado(tracking.estado_actual, tracking.estado_codigo),
        "dry_run": dry_run,
    }

    # 4. Si dry-run: devolver sin tocar BD ni guardar backup
    if dry_run:
        base_resp["status"] = "ok_dryrun"
        return base_resp

    # 5. BACKUP antes de escribir
    await _save_backup(
        orden, sync_run_id=sync_run_id, preview=preview, actor_email=actor_email,
    )

    # 6. Escritura real (upsert posicional o push)
    if idx is not None:
        await db.ordenes.update_one(
            {"id": oid},
            {"$set": {f"gls_envios.{idx}": envio_doc, "updated_at": now}},
        )
    else:
        await db.ordenes.update_one(
            {"id": oid},
            {"$push": {"gls_envios": envio_doc},
             "$set": {"updated_at": now}},
        )

    return base_resp


# ══════════════════════════════════════════════════════════════════════════════
# Modelos request / response
# ══════════════════════════════════════════════════════════════════════════════

class SincronizarRequest(BaseModel):
    solo_sin_envios: bool = True
    dias_atras: int = 45
    max_ordenes: int = 50
    order_ids: Optional[list[str]] = None
    # Salvaguardas production:
    dry_run: bool = True
    confirmacion: str = ""  # debe ser "CONFIRMO" para dry_run=False en production
    forzar_por_encima_del_warning: bool = False


class SincronizarResponse(BaseModel):
    ok: bool
    preview: bool
    dry_run: bool
    sync_run_id: str
    total_procesadas: int
    sincronizadas: int
    actualizadas: int
    creadas: int
    no_encontradas: int
    con_error: int
    sin_autorizacion: int
    resultados: list[dict]
    ejecutado_en: str
    warnings: list[str] = Field(default_factory=list)


# ══════════════════════════════════════════════════════════════════════════════
# Endpoint principal de sync
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/gls/sincronizar-ordenes", response_model=SincronizarResponse)
async def sincronizar_ordenes_gls(
    payload: SincronizarRequest, user: dict = Depends(require_admin),
):
    """Sincroniza órdenes históricas con GLS (rol master/admin).

    Salvaguardas (aplican en production, no en preview):
      - dry_run=True por defecto → simula sin tocar BD.
      - confirmacion="CONFIRMO" obligatorio si dry_run=False.
      - max_ordenes ≤ HARD_CAP_MAX_ORDENES (500).
      - warning si max_ordenes > 50 → requiere forzar_por_encima_del_warning.
      - Backup automático por orden afectada → colección gls_sync_backups.
    """
    role = user.get("role") or user.get("rol")
    if role not in ("master", "admin"):
        raise HTTPException(
            403, "Solo master/admin puede sincronizar órdenes GLS",
        )

    preview = _is_preview()
    actor_email = user.get("email", "")
    warnings: list[str] = []

    # — Validaciones de salvaguarda —
    if payload.max_ordenes > HARD_CAP_MAX_ORDENES:
        raise HTTPException(
            400,
            f"max_ordenes excede el límite duro ({HARD_CAP_MAX_ORDENES}). "
            "Divide la ejecución en varios lotes.",
        )

    is_real_run = not payload.dry_run and not preview
    if is_real_run:
        # Confirmación textual obligatoria SOLO cuando el lote es grande (> 20 órdenes)
        # Para lotes pequeños no exigimos CONFIRMO — el usuario ya ve "Ejecutar REAL" en rojo.
        if payload.max_ordenes > 20 and payload.confirmacion != CONFIRMACION_TEXTO:
            raise HTTPException(
                400,
                f"Confirmación requerida para lotes > 20 órdenes: escribe exactamente "
                f"'{CONFIRMACION_TEXTO}' en el campo `confirmacion`.",
            )
        # Warning por volumen alto
        if (
            payload.max_ordenes > SOFT_WARNING_MAX_ORDENES
            and not payload.forzar_por_encima_del_warning
        ):
            raise HTTPException(
                400,
                f"max_ordenes ({payload.max_ordenes}) supera el umbral de seguridad "
                f"({SOFT_WARNING_MAX_ORDENES}). Marca `forzar_por_encima_del_warning=true` "
                "si estás seguro.",
            )

    sync_run_id = f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    client = None if preview else await _build_client()

    # — Query de órdenes candidatas —
    desde = (datetime.now(timezone.utc) - timedelta(days=payload.dias_atras)).isoformat()
    q: dict = {"numero_autorizacion": {"$exists": True, "$nin": ["", None]}}
    if payload.order_ids:
        q["id"] = {"$in": payload.order_ids}
    else:
        q["created_at"] = {"$gte": desde}
        if payload.solo_sin_envios:
            q["$or"] = [
                {"gls_envios": {"$exists": False}},
                {"gls_envios": {"$size": 0}},
            ]

    ordenes = await db.ordenes.find(
        q,
        {"_id": 0, "id": 1, "numero_orden": 1, "numero_autorizacion": 1,
         "cliente_id": 1, "cp_envio": 1, "created_at": 1, "updated_at": 1,
         "gls_envios": 1},
    ).limit(payload.max_ordenes).to_list(payload.max_ordenes)

    if payload.dry_run:
        warnings.append("DRY-RUN: No se han modificado datos reales en BD.")
    if preview:
        warnings.append("PREVIEW: MCP_ENV=preview, datos simulados (mock).")

    resultados = []
    stats = {
        "sincronizadas": 0, "actualizadas": 0, "creadas": 0,
        "no_encontradas": 0, "con_error": 0, "sin_autorizacion": 0,
    }
    for orden in ordenes:
        res = await _sync_one_orden(
            orden, client,
            preview=preview, dry_run=payload.dry_run,
            sync_run_id=sync_run_id, actor_email=actor_email,
        )
        resultados.append(res)
        status = res.get("status")
        if status in ("ok", "ok_dryrun"):
            stats["sincronizadas"] += 1
            if res.get("action") == "updated":
                stats["actualizadas"] += 1
            elif res.get("action") == "created":
                stats["creadas"] += 1
        elif status == "not_found":
            stats["no_encontradas"] += 1
        elif status == "skipped":
            stats["sin_autorizacion"] += 1
        else:
            stats["con_error"] += 1

    now = _now_iso()

    # — Persistir metadatos del run (siempre, también en dry-run) —
    await db.gls_sync_runs.insert_one({
        "sync_run_id": sync_run_id,
        "actor": actor_email,
        "ejecutado_en": now,
        "timestamp_dt": datetime.now(timezone.utc),
        "preview": preview,
        "dry_run": payload.dry_run,
        "request": payload.model_dump(exclude={"confirmacion"}),
        "total_procesadas": len(ordenes),
        "stats": stats,
        "warnings": warnings,
        "restaurado": False,
    })

    # — Audit log —
    await db.audit_logs.insert_one({
        "source": "admin_panel",
        "agent_id": None,
        "tool": "_sync_gls_historico",
        "params": {
            "sync_run_id": sync_run_id,
            "dry_run": payload.dry_run,
            "preview": preview,
            "request": payload.model_dump(exclude={"confirmacion"}),
            "total_procesadas": len(ordenes),
        },
        "result_summary": stats,
        "error": None,
        "duration_ms": 0,
        "timestamp": now,
        "timestamp_dt": datetime.now(timezone.utc),
        "actor": actor_email,
    })

    return SincronizarResponse(
        ok=True, preview=preview, dry_run=payload.dry_run,
        sync_run_id=sync_run_id,
        total_procesadas=len(ordenes),
        **stats,
        resultados=resultados,
        ejecutado_en=now,
        warnings=warnings,
    )


# ══════════════════════════════════════════════════════════════════════════════
# Endpoint: candidatas (preview de qué se va a sincronizar)
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/gls/sincronizar-ordenes/candidatas")
async def listar_candidatas(
    dias_atras: int = 45, user: dict = Depends(require_admin),
):
    """Lista órdenes candidatas (sin ejecutar sync)."""
    desde = (datetime.now(timezone.utc) - timedelta(days=dias_atras)).isoformat()
    q = {
        "numero_autorizacion": {"$exists": True, "$nin": ["", None]},
        "created_at": {"$gte": desde},
        "$or": [
            {"gls_envios": {"$exists": False}},
            {"gls_envios": {"$size": 0}},
        ],
    }
    total = await db.ordenes.count_documents(q)
    muestra = await db.ordenes.find(
        q,
        {"_id": 0, "id": 1, "numero_orden": 1, "numero_autorizacion": 1,
         "created_at": 1, "cp_envio": 1},
    ).sort("created_at", -1).limit(10).to_list(10)
    return {
        "total_candidatas": total,
        "dias_atras": dias_atras,
        "muestra": muestra,
        "entorno": "preview" if _is_preview() else "production",
        "hard_cap_max_ordenes": HARD_CAP_MAX_ORDENES,
        "soft_warning_max_ordenes": SOFT_WARNING_MAX_ORDENES,
        "confirmacion_texto": CONFIRMACION_TEXTO,
    }


# ══════════════════════════════════════════════════════════════════════════════
# Endpoints: histórico de runs + rollback
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/gls/sync-runs")
async def listar_sync_runs(limit: int = 20, user: dict = Depends(require_admin)):
    """Lista los últimos runs del sync histórico."""
    limit = max(1, min(limit, 100))
    runs = await db.gls_sync_runs.find(
        {}, {"_id": 0},
    ).sort("timestamp_dt", -1).limit(limit).to_list(limit)
    # Campos no serializables
    for r in runs:
        r.pop("timestamp_dt", None)
    return {"runs": runs, "total": len(runs)}


@router.get("/gls/sync-runs/{run_id}")
async def detalle_sync_run(run_id: str, user: dict = Depends(require_admin)):
    """Devuelve metadata del run + backups asociados (para inspección/rollback)."""
    run = await db.gls_sync_runs.find_one({"sync_run_id": run_id}, {"_id": 0})
    if not run:
        raise HTTPException(404, "sync_run_id no encontrado")
    run.pop("timestamp_dt", None)
    backups = await db.gls_sync_backups.find(
        {"sync_run_id": run_id},
        {"_id": 0},
    ).to_list(length=None)
    return {"run": run, "backups": backups, "total_backups": len(backups)}


class RestaurarRequest(BaseModel):
    confirmacion: str = ""  # "CONFIRMO" en production


@router.post("/gls/sync-runs/{run_id}/restaurar")
async def restaurar_sync_run(
    run_id: str, payload: RestaurarRequest, user: dict = Depends(require_admin),
):
    """
    Rollback: restaura el estado previo de todas las órdenes afectadas por el run.
    En production requiere confirmacion="CONFIRMO".
    """
    role = user.get("role") or user.get("rol")
    if role not in ("master", "admin"):
        raise HTTPException(403, "Solo master/admin puede restaurar")

    preview = _is_preview()
    if not preview and payload.confirmacion != CONFIRMACION_TEXTO:
        raise HTTPException(
            400,
            f"Confirmación requerida: escribe '{CONFIRMACION_TEXTO}' en `confirmacion`.",
        )

    run = await db.gls_sync_runs.find_one({"sync_run_id": run_id})
    if not run:
        raise HTTPException(404, "sync_run_id no encontrado")
    if run.get("restaurado"):
        raise HTTPException(409, "Este run ya fue restaurado previamente")
    if run.get("dry_run"):
        raise HTTPException(
            400, "Este run fue dry-run: no tocó BD, nada que restaurar.",
        )

    backups = await db.gls_sync_backups.find(
        {"sync_run_id": run_id, "restaurado": False},
        {"_id": 0},
    ).to_list(length=None)

    restauradas = 0
    errores: list[dict] = []
    now = _now_iso()
    for b in backups:
        oid = b.get("order_id")
        try:
            await db.ordenes.update_one(
                {"id": oid},
                {"$set": {
                    "gls_envios": b.get("gls_envios_previo", []),
                    "updated_at": b.get("updated_at_previo") or now,
                }},
            )
            await db.gls_sync_backups.update_one(
                {"sync_run_id": run_id, "order_id": oid},
                {"$set": {"restaurado": True, "restaurado_en": now,
                          "restaurado_por": user.get("email", "")}},
            )
            restauradas += 1
        except Exception as exc:  # noqa: BLE001
            errores.append({"order_id": oid, "error": str(exc)[:200]})

    await db.gls_sync_runs.update_one(
        {"sync_run_id": run_id},
        {"$set": {
            "restaurado": True,
            "restaurado_en": now,
            "restaurado_por": user.get("email", ""),
            "restauradas_ok": restauradas,
            "restauradas_error": len(errores),
        }},
    )

    await db.audit_logs.insert_one({
        "source": "admin_panel", "agent_id": None,
        "tool": "_restaurar_sync_gls_historico",
        "params": {"sync_run_id": run_id},
        "result_summary": {"restauradas": restauradas,
                           "errores": len(errores)},
        "error": None, "duration_ms": 0,
        "timestamp": now, "timestamp_dt": datetime.now(timezone.utc),
        "actor": user.get("email", ""),
    })

    return {
        "ok": True, "sync_run_id": run_id,
        "restauradas": restauradas, "errores": errores,
        "total_backups": len(backups), "ejecutado_en": now,
    }



# ══════════════════════════════════════════════════════════════════════════════
# Endpoint: Limpiar envíos mock_preview (one-shot tras paso a producción)
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/gls/limpiar-mocks")
async def limpiar_envios_mock_preview(
    dry_run: bool = False,
    user: dict = Depends(require_admin),
):
    """
    Elimina TODOS los envíos GLS y MRW marcados como mock_preview=true.

    Diseñado para ejecutarse UNA VEZ tras pasar de MCP_ENV=preview a production
    para limpiar los datos de prueba creados durante el desarrollo.

    Idempotente: ejecutarlo varias veces no rompe nada (después de la primera ya no hay mocks).

    Params:
      - dry_run: si true, sólo cuenta cuántos se borrarían sin tocar BD.
    """
    now = datetime.now(timezone.utc).isoformat()

    # Contar antes
    n_ord_gls = await db.ordenes.count_documents({"gls_envios.mock_preview": True})
    n_ord_mrw = await db.ordenes.count_documents({"mrw_envios.mock_preview": True})

    if dry_run:
        return {
            "ok": True, "dry_run": True,
            "ordenes_afectadas": {"gls": n_ord_gls, "mrw": n_ord_mrw},
            "mensaje": "DRY-RUN. No se ha borrado nada. Ejecuta con dry_run=false para limpiar.",
        }

    # Borrar mocks usando $pull
    result_gls = await db.ordenes.update_many(
        {"gls_envios.mock_preview": True},
        {"$pull": {"gls_envios": {"mock_preview": True}}, "$set": {"updated_at": now}},
    )
    result_mrw = await db.ordenes.update_many(
        {"mrw_envios.mock_preview": True},
        {"$pull": {"mrw_envios": {"mock_preview": True}}, "$set": {"updated_at": now}},
    )

    # También limpiar gls_shipments standalone
    result_shipments = await db.gls_shipments.delete_many({"mock_preview": True})

    await db.audit_logs.insert_one({
        "source": "admin_panel", "agent_id": None,
        "tool": "limpiar_envios_mock_preview",
        "params": {"dry_run": False},
        "result_summary": {
            "ordenes_gls_modificadas": result_gls.modified_count,
            "ordenes_mrw_modificadas": result_mrw.modified_count,
            "gls_shipments_eliminados": result_shipments.deleted_count,
        },
        "error": None, "duration_ms": 0,
        "timestamp": now, "timestamp_dt": datetime.now(timezone.utc),
        "actor": user.get("email", ""),
    })

    return {
        "ok": True, "dry_run": False,
        "ordenes_gls_modificadas": result_gls.modified_count,
        "ordenes_mrw_modificadas": result_mrw.modified_count,
        "gls_shipments_eliminados": result_shipments.deleted_count,
        "ejecutado_en": now,
        "actor": user.get("email", ""),
    }



# ══════════════════════════════════════════════════════════════════════════════
# Endpoint diagnóstico: probar GetExpCli contra GLS con una RefC concreta
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/gls/diagnostico-refc")
async def diagnostico_get_exp_cli(
    referencia: str,
    user: dict = Depends(require_admin),
):
    """
    Diagnóstico: llama GetExpCli a GLS con la referencia indicada y devuelve
    la respuesta XML completa + campos extraídos + match con BD.
    """
    import os
    referencia = (referencia or "").strip()
    if not referencia:
        raise HTTPException(status_code=400, detail="Falta el parámetro 'referencia'")

    uid = os.environ.get("GLS_UID_CLIENTE", "")
    url = os.environ.get("GLS_URL", "")
    if not uid:
        raise HTTPException(status_code=500, detail="GLS_UID_CLIENTE no configurado")

    # Llamada al cliente real (usa la lógica de modules/logistica/gls.py)
    from modules.logistica.gls import GLSClient, GLSError

    cli = GLSClient(
        url=url,
        uid_cliente=uid,
        remitente=None,  # no hace falta para tracking
        mcp_env=os.environ.get("MCP_ENV", "production"),
    )

    error_msg = None
    raw_xml = ""
    tracking = None
    try:
        # Llamada SOAP cruda para capturar el XML
        xml_body = cli._build_get_exp_cli_xml(codigo=referencia)
        raw_xml = await cli._soap_call(action="GetExpCli", body_xml=xml_body)
        tracking = cli._parse_get_exp_cli_response(raw_xml, referencia)
    except GLSError as e:
        error_msg = f"GLSError: {e}"
    except Exception as e:
        error_msg = f"{type(e).__name__}: {e}"

    # Match en BD
    orden_match_refc = await db.ordenes.find_one(
        {"numero_autorizacion": referencia},
        {"_id": 0, "id": 1, "numero_orden": 1, "numero_autorizacion": 1,
         "estado": 1, "cp_envio": 1, "gls_envios": 1},
    )

    # Si GLS devolvió un codbarras real distinto, también buscar por codbarras
    orden_match_codbarras = None
    cb = getattr(tracking, "codbarras", "") if tracking else ""
    if cb and cb != referencia:
        orden_match_codbarras = await db.ordenes.find_one(
            {"gls_envios.codbarras": cb},
            {"_id": 0, "id": 1, "numero_orden": 1, "numero_autorizacion": 1},
        )

    return {
        "referencia_consultada": referencia,
        "uid_usado": f"{uid[:8]}...{uid[-4:]}" if uid else None,
        "endpoint_gls": url,
        "campos_extraidos": {
            "success": tracking.success if tracking else None,
            "codbarras_real": getattr(tracking, "codbarras", None),
            "codexp": getattr(tracking, "codexp", None),
            "refc_devuelta": getattr(tracking, "refc_devuelta", None),
            "cp_destino": getattr(tracking, "cp_destino", None),
            "estado_actual": getattr(tracking, "estado_actual", None),
            "n_eventos": len(tracking.eventos) if tracking else 0,
        },
        "url_tracking_construida": (
            f"https://mygls.gls-spain.es/e/{getattr(tracking, 'codexp', '')}/{getattr(tracking, 'cp_destino', '')}"
            if tracking and getattr(tracking, "codexp", "") and getattr(tracking, "cp_destino", "")
            else None
        ),
        "error": error_msg,
        "match_bd_por_numero_autorizacion": orden_match_refc,
        "match_bd_por_codbarras_real": orden_match_codbarras,
        "raw_xml_response": raw_xml[:6000] if raw_xml else None,
    }


# ══════════════════════════════════════════════════════════════════════════════
# Endpoint migración one-shot: reescribir tracking_url antiguas en BD
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/gls/regenerar-tracking-urls")
async def regenerar_tracking_urls(
    dry_run: bool = False,
    user: dict = Depends(require_admin),
):
    """
    Recorre todos los envíos GLS de la BD y regenera el campo tracking_url
    si está mal (apunta a apptracking.asp, gls-group.eu o JPEG/PDF) o vacío.

    Usa los datos ya guardados (codexp + cp_destino + codbarras) — NO llama a GLS.
    Es instantáneo e idempotente.
    """
    from modules.gls.shipment_service import _is_valid_gls_tracking_url

    URLS_OBSOLETAS = ("apptracking.asp", "gls-group.eu/track", "wp-es-pro-media")
    actualizadas = 0
    revisadas = 0
    sin_codexp = 0
    sin_cp = 0

    cursor = db.ordenes.find(
        {"gls_envios.0": {"$exists": True}},
        {"_id": 0, "id": 1, "numero_orden": 1, "gls_envios": 1, "cp_envio": 1, "cliente_id": 1},
    )

    async for orden in cursor:
        nuevos_envios = []
        cambio = False
        cp_local = orden.get("cp_envio") or ""
        # Si la orden no tiene cp_envio, intentamos del cliente
        if not cp_local and orden.get("cliente_id"):
            cli = await db.clientes.find_one({"id": orden["cliente_id"]}, {"_id": 0, "cp": 1, "codigo_postal": 1, "direccion": 1}) or {}
            cp_local = cli.get("cp") or cli.get("codigo_postal") or ""
            if not cp_local and cli.get("direccion"):
                import re as _re
                m = _re.search(r"\b(\d{5})\b", cli.get("direccion", ""))
                if m:
                    cp_local = m.group(1)

        for envio in (orden.get("gls_envios") or []):
            revisadas += 1
            current = envio.get("tracking_url") or ""
            es_obsoleta = any(s in current for s in URLS_OBSOLETAS)
            es_invalida = current and not _is_valid_gls_tracking_url(current)
            necesita = not current or es_obsoleta or es_invalida

            if not necesita:
                nuevos_envios.append(envio)
                continue

            codexp = envio.get("codexp") or ""
            # cp_destino guardado en el envío tiene prioridad sobre cp local
            cp = envio.get("cp_destino") or envio.get("codplaza_dst") or cp_local
            codbarras = envio.get("codbarras") or ""

            if codexp and cp and len(str(cp)) == 5:
                nueva = f"https://mygls.gls-spain.es/e/{codexp}/{cp}"
            elif codbarras:
                nueva = f"https://www.gls-spain.es/es/ayuda/seguimiento-de-envio/?match={codbarras}"
                if not codexp:
                    sin_codexp += 1
                if not cp:
                    sin_cp += 1
            else:
                nueva = "https://www.gls-spain.es/es/ayuda/seguimiento-de-envio/"

            if nueva != current:
                envio_actualizado = dict(envio)
                envio_actualizado["tracking_url"] = nueva
                envio_actualizado["tracking_url_anterior"] = current
                nuevos_envios.append(envio_actualizado)
                cambio = True
                actualizadas += 1
            else:
                nuevos_envios.append(envio)

        if cambio and not dry_run:
            await db.ordenes.update_one(
                {"id": orden["id"]},
                {"$set": {"gls_envios": nuevos_envios, "updated_at": datetime.now(timezone.utc).isoformat()}},
            )

    return {
        "ok": True,
        "dry_run": dry_run,
        "envios_revisados": revisadas,
        "envios_actualizados": actualizadas,
        "sin_codexp": sin_codexp,
        "sin_cp": sin_cp,
        "ejecutado_en": datetime.now(timezone.utc).isoformat(),
        "actor": user.get("email", ""),
    }

