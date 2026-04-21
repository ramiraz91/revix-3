"""
Revix MCP · Scheduler autónomo de agentes.

Permite que un agente ejecute una tool periódicamente (cron-like).
  - Almacena configuración en `mcp_scheduled_tasks`.
  - Scheduler loop en background lee tareas con `proxima_ejecucion <= now`.
  - Respeta rate-limit por agente (usa execute_tool_internal que ya lo comprueba).
  - Retry: máx 3 fallos consecutivos → notifica a master@revix.es y desactiva.

Formato cron soportado: "m h d m w"  (5 campos estándar).
Usamos croniter si está disponible; si no, un parser mínimo estilo:
  "*/5 * * * *", "0 8 * * *", etc.
"""
from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger('revix.mcp.scheduler')

TASKS_COLLECTION = 'mcp_scheduled_tasks'
NOTIFY_EMAIL = os.environ.get('MCP_FAILURE_NOTIFY_EMAIL', 'master@revix.es')

# ──────────────────────────────────────────────────────────────────────────────
# Cron parsing
# ──────────────────────────────────────────────────────────────────────────────

try:
    from croniter import croniter
    _HAS_CRONITER = True
except ImportError:  # pragma: no cover
    _HAS_CRONITER = False


def compute_next_run(cron_expr: str, base: Optional[datetime] = None) -> datetime:
    """Devuelve el próximo datetime UTC que matchee `cron_expr` desde `base`.

    Si croniter no está instalado, usa un parser mínimo que soporta:
      - '*' (cualquiera)
      - '*/N' (cada N)
      - 'N' (valor fijo)
      - 'N,M,...' (lista)
    """
    if base is None:
        base = datetime.now(timezone.utc)
    if base.tzinfo is None:
        base = base.replace(tzinfo=timezone.utc)

    if _HAS_CRONITER:
        it = croniter(cron_expr, base)
        return it.get_next(datetime).replace(tzinfo=timezone.utc)

    # Fallback simple: avanza minuto a minuto hasta encontrar match (límite 24h)
    parts = cron_expr.strip().split()
    if len(parts) != 5:
        raise ValueError(f'Expresión cron inválida (se esperaban 5 campos): {cron_expr}')
    m_f, h_f, d_f, mo_f, w_f = parts

    def _matches(value: int, field: str, minv: int, maxv: int) -> bool:
        if field == '*':
            return True
        if field.startswith('*/'):
            step = int(field[2:])
            return ((value - minv) % step) == 0
        if ',' in field:
            return value in {int(x) for x in field.split(',')}
        return value == int(field)

    cur = base.replace(second=0, microsecond=0) + timedelta(minutes=1)
    for _ in range(60 * 24 * 7):  # hasta 7 días
        if (_matches(cur.minute, m_f, 0, 59)
                and _matches(cur.hour, h_f, 0, 23)
                and _matches(cur.day, d_f, 1, 31)
                and _matches(cur.month, mo_f, 1, 12)
                and _matches(cur.weekday(), w_f, 0, 6)):
            return cur
        cur += timedelta(minutes=1)
    raise ValueError(f'No se pudo calcular próxima ejecución para: {cron_expr}')


# ──────────────────────────────────────────────────────────────────────────────
# CRUD tareas
# ──────────────────────────────────────────────────────────────────────────────

async def ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    try:
        await db[TASKS_COLLECTION].create_index('agent_id', name='idx_agent')
        await db[TASKS_COLLECTION].create_index(
            [('activo', 1), ('proxima_ejecucion', 1)],
            name='idx_activo_proxima',
        )
    except Exception as e:  # noqa: BLE001
        logger.warning(f'Index scheduled_tasks: {e}')


async def crear_tarea(
    db: AsyncIOMotorDatabase,
    *, agent_id: str, cron_expression: str, tool: str,
    params: Optional[dict] = None, descripcion: Optional[str] = None,
    created_by: str = 'system',
) -> dict:
    from .tools._registry import get_tool
    if not get_tool(tool):
        raise ValueError(f'Tool "{tool}" no existe en el registry')
    next_run = compute_next_run(cron_expression)
    doc = {
        'id': str(uuid.uuid4()),
        'agent_id': agent_id,
        'cron_expression': cron_expression,
        'tool': tool,
        'params': params or {},
        'descripcion': descripcion or f'{agent_id} → {tool} ({cron_expression})',
        'activo': True,
        'consecutive_failures': 0,
        'ultima_ejecucion': None,
        'ultima_ejecucion_resultado': None,
        'ultima_ejecucion_error': None,
        'proxima_ejecucion': next_run.isoformat(),
        'created_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'created_by': created_by,
    }
    await db[TASKS_COLLECTION].insert_one(dict(doc))
    return doc


async def listar_tareas(db: AsyncIOMotorDatabase, *, agent_id: Optional[str] = None) -> list:
    q = {}
    if agent_id:
        q['agent_id'] = agent_id
    cursor = db[TASKS_COLLECTION].find(q, {'_id': 0}).sort('created_at', -1)
    return [t async for t in cursor]


async def actualizar_tarea(
    db: AsyncIOMotorDatabase, task_id: str, updates: dict,
) -> bool:
    if 'cron_expression' in updates:
        updates['proxima_ejecucion'] = compute_next_run(updates['cron_expression']).isoformat()
    res = await db[TASKS_COLLECTION].update_one({'id': task_id}, {'$set': updates})
    return res.matched_count > 0


async def borrar_tarea(db: AsyncIOMotorDatabase, task_id: str) -> bool:
    res = await db[TASKS_COLLECTION].delete_one({'id': task_id})
    return res.deleted_count > 0


# ──────────────────────────────────────────────────────────────────────────────
# Notificación de fallo tras 3 intentos
# ──────────────────────────────────────────────────────────────────────────────

async def _notificar_fallo_maestro(
    db: AsyncIOMotorDatabase, task: dict, error_msg: str,
) -> None:
    """Notifica al master y desactiva la tarea (tras 3 fallos consecutivos)."""
    logger.warning(
        f'[scheduler] Tarea {task["id"]} desactivada tras 3 fallos: {error_msg}',
    )
    # Notificación interna en BD
    await db.notificaciones.insert_one({
        'id': str(uuid.uuid4()),
        'tipo': 'mcp_scheduled_task_failure',
        'mensaje': (
            f'Tarea MCP {task.get("descripcion")} desactivada tras 3 fallos '
            f'consecutivos. Último error: {error_msg[:300]}'
        ),
        'agent_id': task.get('agent_id'),
        'task_id': task['id'],
        'destinatario_email': NOTIFY_EMAIL,
        'leida': False,
        'created_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'source': 'mcp_scheduler',
        'preview_mock': (os.environ.get('MCP_ENV') == 'preview'),
    })
    # Intento envío por email (opcional, solo en production)
    if os.environ.get('MCP_ENV') != 'preview':
        try:
            from email_service import send_email  # type: ignore
            send_email(
                to=NOTIFY_EMAIL,
                subject=f'[Revix MCP] Tarea {task.get("descripcion")} desactivada',
                html_body=(
                    f'<p>La tarea MCP ha sido desactivada tras 3 fallos consecutivos.</p>'
                    f'<ul><li>ID: {task["id"]}</li>'
                    f'<li>Agente: {task.get("agent_id")}</li>'
                    f'<li>Tool: {task.get("tool")}</li>'
                    f'<li>Último error: {error_msg}</li></ul>'
                ),
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(f'No se pudo enviar email de fallo: {e}')


# ──────────────────────────────────────────────────────────────────────────────
# Ejecución de tareas
# ──────────────────────────────────────────────────────────────────────────────

async def ejecutar_tarea_una_vez(
    db: AsyncIOMotorDatabase, task: dict,
) -> dict:
    """Ejecuta una tarea ahora. Maneja éxito/fallo, actualiza próxima ejecución.

    Retorna dict con `success`, `result`, `error`.
    """
    from .auth import AgentIdentity
    from .runtime import ToolRateLimitError, execute_tool_internal

    agent_id = task['agent_id']
    tool_name = task['tool']
    params = dict(task.get('params') or {})

    # Obtener scopes del agente
    try:
        from backend.modules.agents.agent_defs import get_agent  # type: ignore
    except ImportError:  # durante tests el path del backend no está en sys.path
        import sys as _sys
        _sys.path.insert(0, '/app/backend')
        from modules.agents.agent_defs import get_agent  # type: ignore

    agent_def = get_agent(agent_id)
    if not agent_def:
        err = f'Agente "{agent_id}" no existe'
        await _marcar_fallo(db, task, err)
        return {'success': False, 'error': err}

    identity = AgentIdentity(
        key_id=f'scheduler:{agent_id}',
        agent_id=agent_id,
        agent_name=f'{agent_def.nombre} (scheduler)',
        scopes=list(agent_def.scopes),
        rate_limit_per_min=0,
        key_prefix='scheduler',
    )

    now_iso = datetime.now(timezone.utc).isoformat(timespec='seconds')
    try:
        result = await execute_tool_internal(
            db, identity=identity, tool_name=tool_name, params=params,
        )
        next_run = compute_next_run(task['cron_expression']).isoformat()
        await db[TASKS_COLLECTION].update_one(
            {'id': task['id']},
            {'$set': {
                'ultima_ejecucion': now_iso,
                'ultima_ejecucion_resultado': 'ok',
                'ultima_ejecucion_error': None,
                'consecutive_failures': 0,
                'proxima_ejecucion': next_run,
            }},
        )
        return {'success': True, 'result': result, 'next_run': next_run}
    except ToolRateLimitError as e:
        # No cuenta como fallo: posponer 60s
        logger.warning(f'[scheduler] rate-limit en tarea {task["id"]}: {e}')
        await db[TASKS_COLLECTION].update_one(
            {'id': task['id']},
            {'$set': {
                'proxima_ejecucion': (datetime.now(timezone.utc) + timedelta(minutes=1)).isoformat(),
                'ultima_ejecucion_error': f'rate_limit_deferred: {e}',
            }},
        )
        return {'success': False, 'error': 'rate_limit_deferred'}
    except Exception as e:  # noqa: BLE001
        err = f'{type(e).__name__}: {e}'
        logger.exception(f'[scheduler] fallo tarea {task["id"]}')
        await _marcar_fallo(db, task, err)
        return {'success': False, 'error': err}


async def _marcar_fallo(db: AsyncIOMotorDatabase, task: dict, err: str) -> None:
    failures = (task.get('consecutive_failures') or 0) + 1
    now_iso = datetime.now(timezone.utc).isoformat(timespec='seconds')
    next_run = compute_next_run(task['cron_expression']).isoformat()
    updates = {
        'ultima_ejecucion': now_iso,
        'ultima_ejecucion_resultado': 'error',
        'ultima_ejecucion_error': err[:500],
        'consecutive_failures': failures,
        'proxima_ejecucion': next_run,
    }
    if failures >= 3:
        updates['activo'] = False
        updates['desactivada_en'] = now_iso
        updates['desactivada_motivo'] = f'3 fallos consecutivos: {err[:200]}'
    await db[TASKS_COLLECTION].update_one({'id': task['id']}, {'$set': updates})
    if failures >= 3:
        await _notificar_fallo_maestro(db, task, err)


# ──────────────────────────────────────────────────────────────────────────────
# Scheduler loop (background task en FastAPI startup)
# ──────────────────────────────────────────────────────────────────────────────

_SCHEDULER_TASK: Optional[asyncio.Task] = None
_SCHEDULER_STOP_EVENT: Optional[asyncio.Event] = None


async def scheduler_tick(db: AsyncIOMotorDatabase) -> int:
    """Ejecuta todas las tareas vencidas. Retorna cuántas se ejecutaron."""
    now_iso = datetime.now(timezone.utc).isoformat()
    cursor = db[TASKS_COLLECTION].find(
        {'activo': True, 'proxima_ejecucion': {'$lte': now_iso}},
        {'_id': 0},
    ).limit(50)
    tareas = [t async for t in cursor]
    for t in tareas:
        try:
            await ejecutar_tarea_una_vez(db, t)
        except Exception as e:  # noqa: BLE001 — no parar el loop por un fallo
            logger.exception(f'Scheduler tick fallo en {t.get("id")}: {e}')
    return len(tareas)


async def _scheduler_loop(db: AsyncIOMotorDatabase, interval_seconds: int = 30) -> None:
    logger.info(f'[scheduler] loop iniciado (cada {interval_seconds}s)')
    stop = _SCHEDULER_STOP_EVENT
    while stop is None or not stop.is_set():
        try:
            await scheduler_tick(db)
        except Exception as e:  # noqa: BLE001
            logger.exception(f'[scheduler] tick error: {e}')
        try:
            await asyncio.wait_for(stop.wait() if stop else asyncio.sleep(interval_seconds),
                                   timeout=interval_seconds)
        except asyncio.TimeoutError:
            pass
    logger.info('[scheduler] loop terminado')


async def start_scheduler(db: AsyncIOMotorDatabase, interval_seconds: int = 30) -> None:
    global _SCHEDULER_TASK, _SCHEDULER_STOP_EVENT
    if _SCHEDULER_TASK and not _SCHEDULER_TASK.done():
        return
    await ensure_indexes(db)
    _SCHEDULER_STOP_EVENT = asyncio.Event()
    _SCHEDULER_TASK = asyncio.create_task(_scheduler_loop(db, interval_seconds))


async def stop_scheduler() -> None:
    global _SCHEDULER_TASK, _SCHEDULER_STOP_EVENT
    if _SCHEDULER_STOP_EVENT:
        _SCHEDULER_STOP_EVENT.set()
    if _SCHEDULER_TASK:
        try:
            await asyncio.wait_for(_SCHEDULER_TASK, timeout=5)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            pass
    _SCHEDULER_TASK = None
    _SCHEDULER_STOP_EVENT = None
