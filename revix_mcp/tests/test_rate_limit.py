"""
Tests para el rate limiting por agente (Fase 1).

Estrategia: sembrar en BD límites pequeños (soft=2, hard=3) y hacer llamadas
consecutivas al runtime para verificar:
  · count <= soft       → éxito, sin warning
  · soft < count <= hard → éxito, con entrada `rate_limit_soft_crossed` en audit
  · count > hard         → ToolRateLimitError + entrada `rate_limit_exceeded` en audit
  · aislamiento entre agentes (un agente no consume cupo del otro)
  · configurable desde BD (set_limits → refleja al siguiente check)
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import pytest_asyncio

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from motor.motor_asyncio import AsyncIOMotorClient

from revix_mcp import auth, rate_limit
from revix_mcp.config import (
    API_KEYS_COLLECTION, AUDIT_COLLECTION, DB_NAME, IDEMPOTENCY_COLLECTION, MONGO_URL,
)
from revix_mcp.runtime import ToolRateLimitError, execute_tool
from revix_mcp.tools import meta  # noqa: F401 — registra ping


@pytest_asyncio.fixture
async def db():
    assert DB_NAME != 'production'
    client = AsyncIOMotorClient(MONGO_URL)
    database = client[DB_NAME]

    # Limpieza antes
    await database[API_KEYS_COLLECTION].delete_many({'agent_id': {'$regex': '^test_rl_'}})
    await database[rate_limit.LIMITS_COLLECTION].delete_many({'agent_id': {'$regex': '^test_rl_'}})
    await database[rate_limit.USAGE_COLLECTION].delete_many({'agent_id': {'$regex': '^test_rl_'}})
    await database[AUDIT_COLLECTION].delete_many({'agent_id': {'$regex': '^test_rl_'}})
    rate_limit.invalidate_limits_cache()

    yield database

    # Limpieza después
    await database[API_KEYS_COLLECTION].delete_many({'agent_id': {'$regex': '^test_rl_'}})
    await database[rate_limit.LIMITS_COLLECTION].delete_many({'agent_id': {'$regex': '^test_rl_'}})
    await database[rate_limit.USAGE_COLLECTION].delete_many({'agent_id': {'$regex': '^test_rl_'}})
    await database[AUDIT_COLLECTION].delete_many({'agent_id': {'$regex': '^test_rl_'}})
    rate_limit.invalidate_limits_cache()
    client.close()


async def _make_key(db, agent_id: str, scopes=None) -> str:
    plain, _ = await auth.create_api_key(
        db, agent_id=agent_id, agent_name=agent_id,
        scopes=scopes or ['meta:ping'], created_by='pytest',
    )
    return plain


# ──────────────────────────────────────────────────────────────────────────────
# Límites y defaults
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_limits_fallback_cuando_no_existe(db):
    soft, hard = await rate_limit.get_limits(db, 'test_rl_inexistente')
    assert (soft, hard) == (120, 600)


@pytest.mark.asyncio
async def test_set_y_get_limits_persisten(db):
    await rate_limit.set_limits(db, agent_id='test_rl_agente', soft_limit=10, hard_limit=50)
    soft, hard = await rate_limit.get_limits(db, 'test_rl_agente')
    assert (soft, hard) == (10, 50)


@pytest.mark.asyncio
async def test_seed_default_limits_idempotente_y_correcto(db):
    # 1ª vez: siembra
    await rate_limit.seed_default_limits(db)
    # 2ª vez: no sobrescribe
    await rate_limit.set_limits(db, agent_id='kpi_analyst', soft_limit=999, hard_limit=9999)
    await rate_limit.seed_default_limits(db)
    soft, hard = await rate_limit.get_limits(db, 'kpi_analyst')
    assert (soft, hard) == (999, 9999), 'seed debe respetar cambios manuales'
    # Los otros dos sí quedan con los defaults
    assert await rate_limit.get_limits(db, 'auditor') == (120, 600)
    assert await rate_limit.get_limits(db, 'seguimiento_publico') == (60, 300)
    # Limpieza final (el test modificó un doc que no arranca con test_rl_)
    await db[rate_limit.LIMITS_COLLECTION].delete_one({'agent_id': 'kpi_analyst', 'soft_limit': 999})


# ──────────────────────────────────────────────────────────────────────────────
# Check + record
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_check_record_dentro_del_soft(db):
    await rate_limit.set_limits(db, agent_id='test_rl_a', soft_limit=5, hard_limit=10)
    r = await rate_limit.check_and_record(db, agent_id='test_rl_a')
    assert r.count == 1
    assert r.within_soft and r.within_hard and not r.crossed_soft


@pytest.mark.asyncio
async def test_check_record_cruza_soft_pero_no_hard(db):
    await rate_limit.set_limits(db, agent_id='test_rl_b', soft_limit=2, hard_limit=5)
    for _ in range(2):
        await rate_limit.check_and_record(db, agent_id='test_rl_b')
    r = await rate_limit.check_and_record(db, agent_id='test_rl_b')
    assert r.count == 3
    assert r.within_hard
    assert not r.within_soft
    assert r.crossed_soft


@pytest.mark.asyncio
async def test_check_record_supera_hard(db):
    await rate_limit.set_limits(db, agent_id='test_rl_c', soft_limit=1, hard_limit=2)
    await rate_limit.check_and_record(db, agent_id='test_rl_c')  # 1
    await rate_limit.check_and_record(db, agent_id='test_rl_c')  # 2
    r = await rate_limit.check_and_record(db, agent_id='test_rl_c')  # 3
    assert r.count == 3
    assert not r.within_hard


@pytest.mark.asyncio
async def test_aislamiento_entre_agentes(db):
    await rate_limit.set_limits(db, agent_id='test_rl_d1', soft_limit=1, hard_limit=2)
    await rate_limit.set_limits(db, agent_id='test_rl_d2', soft_limit=1, hard_limit=2)
    for _ in range(2):
        await rate_limit.check_and_record(db, agent_id='test_rl_d1')
    # d1 al borde, d2 debe estar limpio
    r2 = await rate_limit.check_and_record(db, agent_id='test_rl_d2')
    assert r2.count == 1 and r2.within_soft


# ──────────────────────────────────────────────────────────────────────────────
# Integración end-to-end con runtime + audit
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_runtime_429_cuando_hard_excedido(db):
    await rate_limit.set_limits(db, agent_id='test_rl_e', soft_limit=1, hard_limit=2)
    key = await _make_key(db, 'test_rl_e', ['meta:ping'])

    # 2 llamadas exitosas
    r1 = await execute_tool(db, api_key=key, tool_name='ping')
    r2 = await execute_tool(db, api_key=key, tool_name='ping')
    assert r1['pong'] and r2['pong']

    # 3ª llamada debe fallar con ToolRateLimitError
    with pytest.raises(ToolRateLimitError) as exc_info:
        await execute_tool(db, api_key=key, tool_name='ping')
    assert exc_info.value.agent_id == 'test_rl_e'
    assert exc_info.value.hard_limit == 2

    # Debe quedar un audit log con error rate_limit_exceeded
    logs = await db[AUDIT_COLLECTION].find(
        {'agent_id': 'test_rl_e', 'error': {'$regex': '^rate_limit_exceeded'}},
    ).to_list(10)
    assert len(logs) >= 1


@pytest.mark.asyncio
async def test_runtime_soft_log_en_audit(db):
    await rate_limit.set_limits(db, agent_id='test_rl_f', soft_limit=1, hard_limit=5)
    key = await _make_key(db, 'test_rl_f', ['meta:ping'])

    # 1ª → dentro de soft
    await execute_tool(db, api_key=key, tool_name='ping')
    # 2ª → ha cruzado soft pero está dentro de hard: debe haber dos audit entries
    await execute_tool(db, api_key=key, tool_name='ping')

    soft_logs = await db[AUDIT_COLLECTION].find(
        {'agent_id': 'test_rl_f', 'error': {'$regex': '^rate_limit_soft_crossed'}},
    ).to_list(10)
    assert len(soft_logs) >= 1


@pytest.mark.asyncio
async def test_set_limits_invalida_cache(db):
    await rate_limit.set_limits(db, agent_id='test_rl_g', soft_limit=100, hard_limit=200)
    await rate_limit.get_limits(db, 'test_rl_g')  # pone en cache
    await rate_limit.set_limits(db, agent_id='test_rl_g', soft_limit=1, hard_limit=2)
    soft, hard = await rate_limit.get_limits(db, 'test_rl_g')
    assert (soft, hard) == (1, 2)
