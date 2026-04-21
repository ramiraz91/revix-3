"""
Tests Fase 2 · Scheduler autónomo MCP.

Cubre:
  - compute_next_run con cron básico
  - crear/listar/actualizar/borrar tareas
  - ejecutar_tarea_una_vez → éxito + actualiza ultima_ejecucion + calcula próxima
  - rate-limit diferido (no cuenta como fallo)
  - 3 fallos consecutivos → activo=false + notificación interna
  - scheduler_tick procesa solo tareas vencidas y activas
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import pytest_asyncio

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from motor.motor_asyncio import AsyncIOMotorClient

from revix_mcp import auth, rate_limit, scheduler
from revix_mcp.config import (
    API_KEYS_COLLECTION, AUDIT_COLLECTION, DB_NAME, IDEMPOTENCY_COLLECTION, MONGO_URL,
)
from revix_mcp.tools import meta  # noqa: F401


PFX = 'test_sch_'


@pytest_asyncio.fixture
async def db():
    assert DB_NAME != 'production'
    client = AsyncIOMotorClient(MONGO_URL)
    database = client[DB_NAME]
    # Limpieza previa
    await database[scheduler.TASKS_COLLECTION].delete_many({'agent_id': {'$regex': f'^{PFX}'}})
    await database[scheduler.TASKS_COLLECTION].delete_many({'descripcion': {'$regex': f'^{PFX}'}})
    await database.notificaciones.delete_many({'tipo': 'mcp_scheduled_task_failure'})
    await database[rate_limit.USAGE_COLLECTION].delete_many({'agent_id': {'$regex': f'^{PFX}'}})
    await database[rate_limit.LIMITS_COLLECTION].delete_many({'agent_id': {'$regex': f'^{PFX}'}})
    rate_limit.invalidate_limits_cache()

    yield database

    await database[scheduler.TASKS_COLLECTION].delete_many({'agent_id': {'$regex': f'^{PFX}'}})
    await database[scheduler.TASKS_COLLECTION].delete_many({'descripcion': {'$regex': f'^{PFX}'}})
    await database.notificaciones.delete_many({'tipo': 'mcp_scheduled_task_failure'})
    await database[rate_limit.USAGE_COLLECTION].delete_many({'agent_id': {'$regex': f'^{PFX}'}})
    await database[rate_limit.LIMITS_COLLECTION].delete_many({'agent_id': {'$regex': f'^{PFX}'}})
    rate_limit.invalidate_limits_cache()
    client.close()


# ──────────────────────────────────────────────────────────────────────────────
# Cron parsing
# ──────────────────────────────────────────────────────────────────────────────

def test_compute_next_run_cada_5_min():
    base = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    nxt = scheduler.compute_next_run('*/5 * * * *', base=base)
    assert nxt == datetime(2026, 1, 1, 10, 5, 0, tzinfo=timezone.utc)


def test_compute_next_run_hora_fija_diaria():
    base = datetime(2026, 1, 1, 7, 0, 0, tzinfo=timezone.utc)
    nxt = scheduler.compute_next_run('0 8 * * *', base=base)
    assert nxt.hour == 8 and nxt.minute == 0


# ──────────────────────────────────────────────────────────────────────────────
# CRUD
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_crear_listar_actualizar_borrar(db):
    # Usamos un agent_id que existe (kpi_analyst) para que el scheduler pueda ejecutarlo si quisiéramos
    t = await scheduler.crear_tarea(
        db, agent_id='kpi_analyst', cron_expression='*/10 * * * *',
        tool='ping', descripcion=f'{PFX}test-task',
        created_by='pytest',
    )
    assert t['activo'] is True
    assert t['proxima_ejecucion']

    # listar
    tareas = await scheduler.listar_tareas(db, agent_id='kpi_analyst')
    ids = [x['id'] for x in tareas]
    assert t['id'] in ids

    # actualizar cron recalcula proxima_ejecucion
    ok = await scheduler.actualizar_tarea(db, t['id'], {'cron_expression': '0 */2 * * *'})
    assert ok
    doc = await db[scheduler.TASKS_COLLECTION].find_one({'id': t['id']}, {'_id': 0})
    assert doc['cron_expression'] == '0 */2 * * *'

    # borrar
    assert await scheduler.borrar_tarea(db, t['id'])


@pytest.mark.asyncio
async def test_crear_tool_invalida_falla(db):
    with pytest.raises(ValueError):
        await scheduler.crear_tarea(
            db, agent_id='kpi_analyst', cron_expression='*/5 * * * *',
            tool='tool_que_no_existe', descripcion=f'{PFX}bad',
        )


# ──────────────────────────────────────────────────────────────────────────────
# Ejecución
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ejecutar_tarea_ok_actualiza_estado(db):
    t = await scheduler.crear_tarea(
        db, agent_id='kpi_analyst', cron_expression='*/10 * * * *',
        tool='ping', descripcion=f'{PFX}exec',
    )
    res = await scheduler.ejecutar_tarea_una_vez(db, t)
    assert res['success']
    doc = await db[scheduler.TASKS_COLLECTION].find_one({'id': t['id']}, {'_id': 0})
    assert doc['ultima_ejecucion'] is not None
    assert doc['ultima_ejecucion_resultado'] == 'ok'
    assert doc['consecutive_failures'] == 0


@pytest.mark.asyncio
async def test_3_fallos_desactivan_y_notifican(db):
    """Tarea con tool válida pero params que provocan fallo (nunca completa) → 3 fallos → disabled."""
    # Tarea con tool 'obtener_metricas' pero metrica inexistente → ValidationError dentro del handler
    t = await scheduler.crear_tarea(
        db, agent_id='kpi_analyst', cron_expression='*/10 * * * *',
        tool='obtener_metricas',
        params={'metrica': 'no_existe_metrica', 'periodo': 'mes'},
        descripcion=f'{PFX}fail',
    )
    for _ in range(3):
        res = await scheduler.ejecutar_tarea_una_vez(db, t)
        assert res['success'] is False
        # refrescar task entre intentos para reflejar el incremento
        t = await db[scheduler.TASKS_COLLECTION].find_one({'id': t['id']}, {'_id': 0})

    final = await db[scheduler.TASKS_COLLECTION].find_one({'id': t['id']}, {'_id': 0})
    assert final['activo'] is False
    assert final['consecutive_failures'] >= 3
    assert 'desactivada_motivo' in final

    # Notificación creada
    notif = await db.notificaciones.find_one(
        {'tipo': 'mcp_scheduled_task_failure', 'task_id': t['id']},
    )
    assert notif is not None


# ──────────────────────────────────────────────────────────────────────────────
# scheduler_tick
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_tick_solo_procesa_vencidas_y_activas(db):
    now = datetime.now(timezone.utc)
    # Una vencida
    vencida = await scheduler.crear_tarea(
        db, agent_id='kpi_analyst', cron_expression='*/10 * * * *',
        tool='ping', descripcion=f'{PFX}vencida',
    )
    # Forzar proxima_ejecucion al pasado
    await db[scheduler.TASKS_COLLECTION].update_one(
        {'id': vencida['id']},
        {'$set': {'proxima_ejecucion': (now - timedelta(minutes=5)).isoformat()}},
    )
    # Una NO vencida (futura)
    futura = await scheduler.crear_tarea(
        db, agent_id='kpi_analyst', cron_expression='0 0 * * *',
        tool='ping', descripcion=f'{PFX}futura',
    )
    # Una vencida pero inactiva
    inactiva = await scheduler.crear_tarea(
        db, agent_id='kpi_analyst', cron_expression='*/10 * * * *',
        tool='ping', descripcion=f'{PFX}inactiva',
    )
    await db[scheduler.TASKS_COLLECTION].update_one(
        {'id': inactiva['id']},
        {'$set': {
            'proxima_ejecucion': (now - timedelta(minutes=5)).isoformat(),
            'activo': False,
        }},
    )

    n = await scheduler.scheduler_tick(db)
    assert n >= 1

    # Verificar que vencida se ejecutó, pero inactiva y futura no
    v_doc = await db[scheduler.TASKS_COLLECTION].find_one({'id': vencida['id']}, {'_id': 0})
    f_doc = await db[scheduler.TASKS_COLLECTION].find_one({'id': futura['id']}, {'_id': 0})
    i_doc = await db[scheduler.TASKS_COLLECTION].find_one({'id': inactiva['id']}, {'_id': 0})
    assert v_doc['ultima_ejecucion'] is not None
    assert f_doc['ultima_ejecucion'] is None
    assert i_doc['ultima_ejecucion'] is None


# ──────────────────────────────────────────────────────────────────────────────
# Rate-limit diferido
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_rate_limit_se_difiere_no_cuenta_fallo(db):
    # Limit muy bajo para este agente
    from revix_mcp.rate_limit import set_limits
    # Creamos un agent_id específico, pero scheduler usa identity de agent_defs,
    # por eso sembramos en el agente real y restauramos al final
    await set_limits(db, agent_id='kpi_analyst', soft_limit=1, hard_limit=1)
    try:
        # 1ª llamada consume el cupo
        await db[rate_limit.USAGE_COLLECTION].insert_one({
            'agent_id': 'kpi_analyst',
            'timestamp': datetime.now(timezone.utc),
            'ts_epoch': datetime.now(timezone.utc).timestamp(),
        })
        t = await scheduler.crear_tarea(
            db, agent_id='kpi_analyst', cron_expression='*/10 * * * *',
            tool='ping', descripcion=f'{PFX}ratelim',
        )
        res = await scheduler.ejecutar_tarea_una_vez(db, t)
        assert res['success'] is False
        assert res['error'] == 'rate_limit_deferred'
        doc = await db[scheduler.TASKS_COLLECTION].find_one({'id': t['id']}, {'_id': 0})
        # NO cuenta como fallo
        assert doc['consecutive_failures'] == 0
    finally:
        # Restaurar límite por defecto para no contaminar otros tests
        await set_limits(db, agent_id='kpi_analyst', soft_limit=120, hard_limit=600)


# ──────────────────────────────────────────────────────────────────────────────
# Integración: ejecución autónoma completa en preview
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_integracion_autonoma_completa(db):
    """Crea tarea → tick → ejecuta → verifica audit_log MCP."""
    t = await scheduler.crear_tarea(
        db, agent_id='kpi_analyst', cron_expression='*/1 * * * *',
        tool='ping', descripcion=f'{PFX}autonomo',
    )
    # Forzar vencida
    await db[scheduler.TASKS_COLLECTION].update_one(
        {'id': t['id']},
        {'$set': {'proxima_ejecucion': (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()}},
    )
    n = await scheduler.scheduler_tick(db)
    assert n >= 1

    # Debe haber un audit_log con source=mcp_agent para kpi_analyst/ping
    log = await db.audit_logs.find_one({
        'source': 'mcp_agent', 'agent_id': 'kpi_analyst', 'tool': 'ping',
    })
    assert log is not None
