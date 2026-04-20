"""
Tests fundación MCP.

Cubren:
  - Generación y hashing de API keys
  - Validación de scopes (known / unknown / jerarquía)
  - Creación, validación, revocación de keys
  - Enforcement de scopes en runtime
  - Audit log
  - Idempotencia end-to-end
  - Sandbox en modo preview
  - Tool "ping" end-to-end
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import pytest
import pytest_asyncio

# Añadir /app al path para importar el paquete `revix_mcp`
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from motor.motor_asyncio import AsyncIOMotorClient

# Import y registramos la tool `ping` antes del resto
from revix_mcp import auth, scopes, audit
from revix_mcp.config import MONGO_URL, DB_NAME, AUDIT_COLLECTION, API_KEYS_COLLECTION, IDEMPOTENCY_COLLECTION
from revix_mcp.runtime import execute_tool, ToolExecutionError
from revix_mcp.tools import meta  # noqa: F401


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def db():
    """DB aislada para tests. Limpia antes y después."""
    assert DB_NAME != 'production', 'Tests no corren sobre production'
    client = AsyncIOMotorClient(MONGO_URL)
    database = client[DB_NAME]

    # Limpieza antes
    for coll in (API_KEYS_COLLECTION, IDEMPOTENCY_COLLECTION):
        await database[coll].delete_many({'agent_id': {'$regex': '^test_'}})
    await database[AUDIT_COLLECTION].delete_many({'source': 'mcp_agent', 'env': 'preview'})

    yield database

    # Limpieza después
    for coll in (API_KEYS_COLLECTION, IDEMPOTENCY_COLLECTION):
        await database[coll].delete_many({'agent_id': {'$regex': '^test_'}})
    await database[AUDIT_COLLECTION].delete_many({'source': 'mcp_agent', 'env': 'preview'})
    client.close()


# ──────────────────────────────────────────────────────────────────────────────
# Scopes
# ──────────────────────────────────────────────────────────────────────────────

def test_scopes_catalog_contains_essentials():
    assert 'meta:ping' in scopes.SCOPES_CATALOG
    assert 'orders:read' in scopes.SCOPES_CATALOG
    assert '*:read' in scopes.SCOPES_CATALOG


def test_is_known_scope():
    assert scopes.is_known_scope('orders:read')
    assert not scopes.is_known_scope('nonexistent:scope')


def test_has_scope_exact():
    assert scopes.has_scope(['orders:read'], 'orders:read')
    assert not scopes.has_scope(['orders:read'], 'orders:write')


def test_has_scope_wildcard_read():
    """*:read satisface cualquier X:read."""
    assert scopes.has_scope(['*:read'], 'orders:read')
    assert scopes.has_scope(['*:read'], 'finance:read')
    # pero no scopes de escritura
    assert not scopes.has_scope(['*:read'], 'orders:write')


def test_validate_scopes_rejects_unknown():
    with pytest.raises(ValueError):
        scopes.validate_scopes(['not:real'])


def test_validate_scopes_dedupe_sort():
    result = scopes.validate_scopes(['orders:read', 'meta:ping', 'orders:read'])
    assert result == ['meta:ping', 'orders:read']


def test_agent_profiles_all_valid():
    """Cada perfil predefinido debe tener scopes conocidos."""
    for agent_id, agent_scopes in scopes.AGENT_PROFILES.items():
        cleaned = scopes.validate_scopes(agent_scopes)
        assert cleaned, f'Perfil vacío: {agent_id}'


# ──────────────────────────────────────────────────────────────────────────────
# API keys
# ──────────────────────────────────────────────────────────────────────────────

def test_generate_api_key_format():
    key = auth.generate_api_key()
    assert key.startswith('revix_mcp_')
    assert len(key) > 40  # prefijo + >30 chars entropía


@pytest.mark.asyncio
async def test_create_and_verify_api_key(db):
    plain, doc = await auth.create_api_key(
        db, agent_id='test_kpi', agent_name='Test KPI',
        scopes=['orders:read', 'meta:ping'], created_by='pytest',
    )
    assert plain.startswith('revix_mcp_')
    assert doc['active'] is True
    assert 'key_hash' in doc
    assert doc['key_prefix'] == plain[:20]

    # Verificar recuperación
    identity = await auth.verify_api_key(db, plain)
    assert identity.agent_id == 'test_kpi'
    assert identity.has_scope('orders:read')
    assert not identity.has_scope('finance:write')


@pytest.mark.asyncio
async def test_verify_invalid_key_raises(db):
    with pytest.raises(auth.AuthError):
        await auth.verify_api_key(db, 'invalid_format')
    with pytest.raises(auth.AuthError):
        await auth.verify_api_key(db, 'revix_mcp_inventada_1234567890')


@pytest.mark.asyncio
async def test_revoked_key_fails(db):
    plain, doc = await auth.create_api_key(
        db, agent_id='test_rev', agent_name='Test Rev',
        scopes=['meta:ping'], created_by='pytest',
    )
    ok = await auth.revoke_api_key(db, doc['id'])
    assert ok
    with pytest.raises(auth.AuthError):
        await auth.verify_api_key(db, plain)


@pytest.mark.asyncio
async def test_create_key_rejects_unknown_scope(db):
    with pytest.raises(ValueError):
        await auth.create_api_key(
            db, agent_id='test_bad', agent_name='Bad',
            scopes=['orders:nuke'], created_by='pytest',
        )


# ──────────────────────────────────────────────────────────────────────────────
# Runtime end-to-end
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ping_ok(db):
    plain, _ = await auth.create_api_key(
        db, agent_id='test_ping', agent_name='Test Ping',
        scopes=['meta:ping'], created_by='pytest',
    )
    result = await execute_tool(db, api_key=plain, tool_name='ping', params={})
    assert result['pong'] is True
    assert result['agent_id'] == 'test_ping'


@pytest.mark.asyncio
async def test_ping_without_scope_fails(db):
    plain, _ = await auth.create_api_key(
        db, agent_id='test_noping', agent_name='No Ping',
        scopes=['orders:read'], created_by='pytest',
    )
    with pytest.raises(ToolExecutionError, match='meta:ping'):
        await execute_tool(db, api_key=plain, tool_name='ping', params={})


@pytest.mark.asyncio
async def test_unknown_tool_fails(db):
    plain, _ = await auth.create_api_key(
        db, agent_id='test_unk', agent_name='Unknown',
        scopes=['meta:ping'], created_by='pytest',
    )
    with pytest.raises(ToolExecutionError, match='no existe'):
        await execute_tool(db, api_key=plain, tool_name='ghost_tool', params={})


@pytest.mark.asyncio
async def test_audit_log_is_written(db):
    plain, _ = await auth.create_api_key(
        db, agent_id='test_audit', agent_name='Audit',
        scopes=['meta:ping'], created_by='pytest',
    )
    await execute_tool(db, api_key=plain, tool_name='ping', params={})

    log = await db[AUDIT_COLLECTION].find_one(
        {'source': 'mcp_agent', 'agent_id': 'test_audit', 'tool': 'ping'}
    )
    assert log is not None
    assert log['result_summary']
    assert log['error'] is None


@pytest.mark.asyncio
async def test_audit_log_sanitizes_secrets(db):
    """Params con 'token'/'password' en la clave se enmascaran en el audit."""
    plain, _ = await auth.create_api_key(
        db, agent_id='test_secret', agent_name='Secret',
        scopes=['meta:ping'], created_by='pytest',
    )
    # ping no usa params secretos realmente — probamos el sanitizador directo
    identity = await auth.verify_api_key(db, plain)
    await audit.log_tool_call(
        db, identity=identity, tool='ping',
        params={'normal': 'ok', 'api_token': 'SECRETAZO', 'password': 'S3CR3T'},
        result={'ok': True},
    )
    log = await db[AUDIT_COLLECTION].find_one({'agent_id': 'test_secret'})
    assert log['params']['normal'] == 'ok'
    assert log['params']['api_token'] == '***'
    assert log['params']['password'] == '***'


@pytest.mark.asyncio
async def test_idempotency_returns_same_result(db):
    """Tool writes con misma idempotency_key devuelve resultado cacheado."""
    # Insertamos manualmente un ToolSpec write para este test
    from revix_mcp.tools._registry import register, ToolSpec, get_tool

    calls = {'n': 0}

    async def _count_handler(database, identity, params):
        calls['n'] += 1
        return {'call_number': calls['n']}

    if get_tool('test_count_writes') is None:
        register(ToolSpec(
            name='test_count_writes',
            description='Test write-only tool',
            required_scope='meta:ping',
            input_schema={'type': 'object'},
            handler=_count_handler,
            writes=True,
        ))

    plain, _ = await auth.create_api_key(
        db, agent_id='test_idem', agent_name='Idem',
        scopes=['meta:ping'], created_by='pytest',
    )

    r1 = await execute_tool(db, api_key=plain, tool_name='test_count_writes',
                            params={'_idempotency_key': 'abc'})
    r2 = await execute_tool(db, api_key=plain, tool_name='test_count_writes',
                            params={'_idempotency_key': 'abc'})
    assert r1 == r2  # mismo resultado
    assert calls['n'] == 1  # handler solo se ejecutó una vez


@pytest.mark.asyncio
async def test_wildcard_read_scope_access(db):
    """*:read permite tools con required_scope terminado en :read."""
    from revix_mcp.tools._registry import register, ToolSpec, get_tool

    async def _list_handler(database, identity, params):
        return {'items': []}

    if get_tool('test_fake_list') is None:
        register(ToolSpec(
            name='test_fake_list',
            description='Fake read tool',
            required_scope='orders:read',
            input_schema={'type': 'object'},
            handler=_list_handler,
        ))

    plain, _ = await auth.create_api_key(
        db, agent_id='test_wild', agent_name='Wild',
        scopes=['*:read'], created_by='pytest',
    )
    # *:read cubre orders:read
    r = await execute_tool(db, api_key=plain, tool_name='test_fake_list', params={})
    assert 'items' in r
